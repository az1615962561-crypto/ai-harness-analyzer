"""Engineering completeness tests covering parity, retries, patterns, HTTP mocks, CLI & E2E."""
from __future__ import annotations

import asyncio
import json
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import httpx
import pytest
from typer.testing import CliRunner

import harness_analyzer.config as cfg
from harness_analyzer.analyzer.llm import LLMClient
from harness_analyzer.analyzer.offline import OfflineBenchmarkProvider
from harness_analyzer.analyzer.patterns import PatternMatcher, load_pattern_catalog
from harness_analyzer.analyzer.specialized import get_specialized_analyzer
from harness_analyzer.cli import app
from harness_analyzer.collectors.base import CollectedData
from harness_analyzer.collectors.github import GitHubCollector
from harness_analyzer.models.app import AIApp, AppCategory
from harness_analyzer.models.dimension import (
    CATEGORY_DIMENSIONS,
    DimensionAnalysis,
    SpecializedDimension,
    SpecializedDimensionAnalysis,
)
from harness_analyzer.models.harness import HarnessAnalysis, QueryCoverageItem
from harness_analyzer.output.markdown import MarkdownReportGenerator

runner = CliRunner()


def test_specialized_dimension_parity_across_all_categories():
    for category, enum_dims in CATEGORY_DIMENSIONS.items():
        analyzer = get_specialized_analyzer(category, llm=None)
        prompts = analyzer.get_dimension_prompts()
        assert list(prompts.keys()) == [d.value for d in enum_dims], f"Key mismatch for {category}"
        assert [lbl for lbl, _ in prompts.values()] == [d.label for d in enum_dims], (
            f"Label mismatch for {category}"
        )


def test_offline_benchmarks_align_with_specialized_dimension_enum():
    cat_map = {
        "cursor": ("engineering", AppCategory.ENGINEERING),
        "chatbi": ("data", AppCategory.DATA),
        "perplexity": ("knowledge", AppCategory.KNOWLEDGE),
        "autogpt": ("automation", AppCategory.AUTOMATION),
    }
    valid_by_key = {d.value: d.label for d in SpecializedDimension}
    for name, (cat_val, cat_enum) in cat_map.items():
        analysis = OfflineBenchmarkProvider.get_analysis(
            AIApp(name=name, display_name=name, category=cat_enum)
        )
        assert analysis.specialized_dimensions, f"No specialized dims for {name}"
        allowed_keys = {d.value for d in CATEGORY_DIMENSIONS[cat_val]}
        for sdim in analysis.specialized_dimensions:
            assert sdim.dimension in allowed_keys
            assert sdim.label == valid_by_key[sdim.dimension]


def test_llm_client_exponential_retry_and_fatal_fail_fast():
    client = LLMClient(model="gpt-4o", api_key="test-key", max_retries=3, retry_base_delay=0.0)

    class RateLimitError(Exception):
        pass

    good_resp = SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content="ok-json"))])
    side_effects = [
        RateLimitError("429 Too Many Requests"),
        TimeoutError("Request timed out"),
        good_resp,
    ]

    with patch("harness_analyzer.analyzer.llm.litellm.completion", side_effect=side_effects) as mock_comp:
        out = client.analyze("test prompt")
        assert out == "ok-json"
        assert mock_comp.call_count == 3

    # Fatal 401 should NOT burn retry attempts
    with patch(
        "harness_analyzer.analyzer.llm.litellm.completion",
        side_effect=ValueError("401 Invalid API key"),
    ) as mock_fatal:
        with pytest.raises(RuntimeError, match="LLM 调用失败"):
            client.analyze("test prompt")
        assert mock_fatal.call_count == 1


def test_pattern_matcher_loads_yaml_catalog_and_renders_markdown():
    catalog = load_pattern_catalog()
    names = {p["name"] for p in catalog}
    assert "single_agent" in names
    assert "mcp_protocol_standard" in names
    assert len(catalog) >= 15

    mock_llm = MagicMock()
    mock_llm.structured_analyze.return_value = [
        {
            "pattern_name": "mcp_protocol_standard",
            "description": "使用 MCP 统一挂载本地工具服务器",
            "evidence": ["Supports Model Context Protocol servers"],
            "confidence": 5,
        }
    ]
    matcher = PatternMatcher(mock_llm)
    patterns = matcher.match("TestApp", "Supports Model Context Protocol servers via stdio")
    assert len(patterns) == 1
    assert patterns[0]["pattern_name"] == "mcp_protocol_standard"

    system_arg = mock_llm.structured_analyze.call_args[0][1]
    assert "mcp_protocol_standard" in system_arg

    analysis = HarnessAnalysis(
        app_name="test-app",
        app_display_name="TestApp",
        category="engineering",
        common_dimensions=[
            DimensionAnalysis(dimension="tool_chain", label="工具调用链", summary="MCP tools", confidence=4)
        ],
        specialized_dimensions=[
            SpecializedDimensionAnalysis(dimension="sandbox_model", label="沙箱隔离模型", summary="Local", confidence=4)
        ],
        matched_patterns=patterns,
    )
    md = MarkdownReportGenerator().generate(analysis)
    assert "识别到的架构模式" in md
    assert "`mcp_protocol_standard`" in md


def test_github_collector_with_mock_transport():
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if url == "https://raw.githubusercontent.com/acme/demo/main/README.md":
            return httpx.Response(200, text="# Demo Agent\nUses Planner-Worker loop and Docker sandbox.")
        if url == "https://api.github.com/repos/acme/demo/git/trees/main?recursive=1":
            return httpx.Response(
                200,
                json={
                    "tree": [
                        {"path": "src/agent_loop.py", "type": "blob"},
                        {"path": "tests/test_dummy.py", "type": "blob"},
                    ]
                },
                headers={"x-ratelimit-remaining": "59"},
            )
        if url == "https://raw.githubusercontent.com/acme/demo/main/src/agent_loop.py":
            return httpx.Response(200, text="def run_loop():\n    return 'planner-worker'")
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    collector = GitHubCollector(max_source_files=2)

    async def _run():
        async with httpx.AsyncClient(transport=transport) as client:
            readme = await collector._fetch_readme(client, "acme", "demo")
            tree_res = await collector._fetch_repo_tree(client, "acme", "demo")
            assert readme is not None and "Planner-Worker" in readme.content
            assert tree_res is not None
            tree_item, branch, paths = tree_res
            key_files = collector.select_key_files(paths, max_files=2)
            assert "src/agent_loop.py" in key_files
            files = await collector._fetch_selected_files(client, "acme", "demo", branch, key_files)
            return [readme, tree_item, *files]

    items = asyncio.run(_run())
    assert [i.source_type for i in items] == ["github_readme", "github_tree", "github_source"]


def test_cli_doctor_and_cache_and_verbose(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("HARNESS_REPORTS_DIR", str(tmp_path / "reports"))
    cfg._settings = None

    doc_res = runner.invoke(app, ["-v", "doctor"])
    assert doc_res.exit_code == 0
    assert "Python 版本" in doc_res.stdout
    assert "内置应用注册表" in doc_res.stdout

    custom_out = tmp_path / "custom_reports"
    res_offline = runner.invoke(app, ["analyze", "cursor", "--offline", "-O", str(custom_out)])
    assert res_offline.exit_code == 0
    assert (custom_out / "cursor.md").exists()
    assert (custom_out / "cursor.intermediate.json").exists()

    cache_list_res = runner.invoke(app, ["cache", "list"])
    assert cache_list_res.exit_code == 0
    assert "cursor" in cache_list_res.stdout

    cache_clear_one = runner.invoke(app, ["cache", "clear", "cursor"])
    assert cache_clear_one.exit_code == 0

    cache_list_empty = runner.invoke(app, ["cache", "list"])
    assert cache_list_empty.exit_code == 0
    assert "暂无分析记录" in cache_list_empty.stdout


def test_cli_online_pipeline_e2e_mocked(tmp_path, monkeypatch):
    monkeypatch.setenv("GEMINI_API_KEY", "fake-gemini-key")
    monkeypatch.setenv("HARNESS_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("HARNESS_REPORTS_DIR", str(tmp_path / "reports"))
    cfg._settings = None

    evidence_text = (
        "MockApp executes user tools inside an isolated Docker sandbox and uses "
        "Model Context Protocol servers for tool orchestration."
    )

    fake_search = MagicMock(return_value=[
        CollectedData(
            source_url="https://example.com/mockapp-arch",
            source_type="blog",
            title="MockApp Architecture",
            content=evidence_text,
        )
    ])
    fake_cov = [
        QueryCoverageItem(query="MockApp harness", language="en", angle="architecture_qa", hits_count=1, chars_collected=len(evidence_text)),
        QueryCoverageItem(query="MockApp 架构", language="zh", angle="user_reviews", hits_count=1, chars_collected=len(evidence_text)),
    ]

    async def fake_search_app(self, app_name, planned_queries=None):
        self.last_coverage_items = fake_cov
        self.last_blocked_sources = []
        return fake_search()

    async def fake_refill(self, app_name, missing_angles, existing_urls=None):
        return [], []

    async def fake_gh(self, app_obj):
        return [
            CollectedData(
                source_url="https://github.com/acme/mockapp/README.md",
                source_type="github_readme",
                title="MockApp README",
                content=evidence_text,
            )
        ]

    async def fake_empty(self, app_obj):
        return []

    def fake_completion(model, messages, temperature=0.3):
        user_msg = messages[-1]["content"]
        sys_msg = messages[0]["content"] if len(messages) > 1 else ""
        if "只输出一个分类英文单词" in user_msg:
            content = "engineering"
        elif "技术事实清单" in sys_msg:
            content = f"- [Fact]: {evidence_text}"
        elif "所有架构模式" in user_msg:
            content = json.dumps([
                {
                    "pattern_name": "mcp_protocol_standard",
                    "description": "通过 MCP 集成工具",
                    "evidence": [evidence_text],
                    "confidence": 5,
                }
            ])
        elif "suitable_product_forms" in user_msg:
            content = json.dumps({
                "suitable_product_forms": ["CLI Coding Agent"],
                "autonomy_level": "L2",
                "interaction_design": "Human approval before destructive bash commands",
                "cost_latency_tradeoffs": "Fast routing + Frontier reasoning",
                "mvp_must_haves": ["Docker sandbox", "MCP client"],
                "mvp_nice_to_haves": ["Checkpoint snapshots"],
                "anti_patterns_to_avoid": ["Unbounded shell execution"],
            })
        elif "praises" in user_msg:
            content = json.dumps({
                "praises": ["Clean MCP ergonomics"],
                "pain_points": ["Container startup latency"],
                "trust_and_ux_friction": ["Needs diff preview"],
                "sample_quotes": ["Sandboxing works reliably."],
            })
        else:
            content = json.dumps({
                "summary": "Isolated Docker sandbox with MCP tools",
                "details": evidence_text,
                "key_decisions": ["Docker isolation", "MCP protocol"],
                "takeaways": ["Always isolate command execution"],
                "verbatim_quotes": [evidence_text],
                "evidence_sources": ["https://github.com/acme/mockapp/README.md"],
                "confidence": 5,
            })
        return SimpleNamespace(choices=[SimpleNamespace(message=SimpleNamespace(content=content))])

    out_dir = tmp_path / "e2e_reports"
    with (
        patch("harness_analyzer.collectors.search.WebSearchCollector.search_app", fake_search_app),
        patch("harness_analyzer.collectors.search.WebSearchCollector.refill_missing_angles", fake_refill),
        patch("harness_analyzer.collectors.github.GitHubCollector.collect", fake_gh),
        patch("harness_analyzer.collectors.blog.BlogCollector.collect", fake_empty),
        patch("harness_analyzer.collectors.reverse_eng.ReverseEngineeringCollector.collect", fake_empty),
        patch("harness_analyzer.collectors.reviews.UserReviewCollector.collect", fake_empty),
        patch("harness_analyzer.analyzer.llm.litellm.completion", side_effect=fake_completion),
    ):
        res = runner.invoke(app, ["analyze", "MockApp", "--depth", "quick", "-O", str(out_dir)])

    assert res.exit_code == 0, res.stdout
    md_path = out_dir / "mockapp.md"
    inter_path = out_dir / "mockapp.intermediate.json"
    assert md_path.exists()
    assert inter_path.exists()

    md_text = md_path.read_text(encoding="utf-8")
    assert "识别到的架构模式" in md_text
    assert "`mcp_protocol_standard`" in md_text
    assert "strict_verified" in inter_path.read_text(encoding="utf-8")
