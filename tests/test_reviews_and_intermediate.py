"""Tests for coupling-tiered individual Guard, UserReviewCollector, and IntermediateArtifact pipeline."""
import asyncio
from unittest.mock import MagicMock
import httpx
from typer.testing import CliRunner

from harness_analyzer.cli import app as cli_app
from harness_analyzer.collectors.base import CollectedData
from harness_analyzer.collectors.reviews import UserReviewCollector
from harness_analyzer.analyzer.evidence import verify_all_dimensions, resolve_coupling_level
from harness_analyzer.analyzer.intermediate import IntermediateArtifactBuilder
from harness_analyzer.analyzer.pm_guidance import PMGuidanceExtractor
from harness_analyzer.models.app import AIApp, AppCategory
from harness_analyzer.models.dimension import (
    CouplingLevel,
    DimensionAnalysis,
    GuardStatus,
    SpecializedDimensionAnalysis,
)


def test_coupling_tiered_individual_guard():
    # For 'data' category:
    # - prompt_engineering has weight=5 -> CORE
    # - context_engineering has weight=3 -> MODERATE
    # - extensibility_ecosystem has weight=2 -> LOOSE
    core_dim = DimensionAnalysis(
        dimension="prompt_engineering",
        label="提示词工程",
        summary="Schema injection",
        confidence=5,
        verbatim_quotes=["Dynamic schema pruning selects top 10 tables"],
    )
    core_secondary_only = DimensionAnalysis(
        dimension="tool_chain",
        label="工具链",
        summary="SQL runner",
        confidence=5,
        verbatim_quotes=["Users complain about slow query timeouts on Reddit"],
    )
    mod_unverified = DimensionAnalysis(
        dimension="context_engineering",
        label="上下文工程",
        summary="Window sliding",
        confidence=5,
        verbatim_quotes=[],
    )
    loose_unverified = DimensionAnalysis(
        dimension="extensibility_ecosystem",
        label="扩展生态",
        summary="Plugin hooks",
        confidence=4,
        verbatim_quotes=[],
    )
    spec_unverified = SpecializedDimensionAnalysis(
        dimension="nl2sql_pipeline",
        label="NL2SQL 管线",
        summary="CoT translation",
        confidence=5,
        verbatim_quotes=[],
    )

    primary_corpus = "Dynamic schema pruning selects top 10 tables before SQL generation."
    full_corpus = primary_corpus + "\nUsers complain about slow query timeouts on Reddit."

    v_common, v_spec = verify_all_dimensions(
        [core_dim, core_secondary_only, mod_unverified, loose_unverified],
        [spec_unverified],
        collected_corpus=full_corpus,
        category="data",
        primary_corpus=primary_corpus,
    )

    # 1. CORE with primary source hit -> STRICT_VERIFIED, keeps 5 stars
    assert v_common[0].coupling_level == CouplingLevel.CORE
    assert v_common[0].guard_status == GuardStatus.STRICT_VERIFIED
    assert v_common[0].confidence == 5

    # 2. CORE with only 1 secondary quote -> PARTIAL_VERIFIED, capped at 3 stars
    assert v_common[1].coupling_level == CouplingLevel.CORE
    assert v_common[1].guard_status == GuardStatus.PARTIAL_VERIFIED
    assert v_common[1].confidence == 3

    # 3. MODERATE unverified -> UNVERIFIED_CAPPED, capped at 2 stars
    assert v_common[2].coupling_level == CouplingLevel.MODERATE
    assert v_common[2].guard_status == GuardStatus.UNVERIFIED_CAPPED
    assert v_common[2].confidence == 2

    # 4. LOOSE unverified -> UNVERIFIED_CAPPED, capped at 2 stars, flagged as loose
    assert v_common[3].coupling_level == CouplingLevel.LOOSE
    assert v_common[3].guard_status == GuardStatus.UNVERIFIED_CAPPED
    assert v_common[3].confidence == 2

    # 5. Specialized (always CORE) unverified -> strictly capped at 1 star
    assert v_spec[0].coupling_level == CouplingLevel.CORE
    assert v_spec[0].guard_status == GuardStatus.UNVERIFIED_CAPPED
    assert v_spec[0].confidence == 1


def test_user_review_collector_hn_and_github_issues(monkeypatch):
    def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        if "hn.algolia.com/api/v1/search" in url:
            return httpx.Response(200, json={"hits": [{"objectID": "123", "title": "Show HN: Cursor", "num_comments": 20}]})
        if "hn.algolia.com/api/v1/items/123" in url:
            return httpx.Response(200, json={
                "children": [
                    {"author": "dev1", "text": "<p>Tab completion is super fast, but Composer breaks large files sometimes.</p>"}
                ]
            })
        if "api.github.com/repos/getcursor/cursor/issues" in url:
            return httpx.Response(200, json=[
                {"title": "Slow indexing on monorepos", "state": "open", "comments": 15, "body": "Takes 10 minutes on huge repo"}
            ])
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    orig_client = httpx.AsyncClient

    def patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return orig_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)
    # Prevent live DuckDuckGo call during unit test
    monkeypatch.setattr(UserReviewCollector, "_search_authoritative_review_sites", lambda self, name: [])

    app = AIApp(
        name="cursor",
        display_name="Cursor",
        category=AppCategory.ENGINEERING,
        github_url="https://github.com/getcursor/cursor",
    )
    reviews = asyncio.run(UserReviewCollector().collect(app))
    assert len(reviews) == 2
    assert all(r.source_type == "user_review" for r in reviews)
    combined = "\n".join(r.content for r in reviews)
    assert "Tab completion is super fast" in combined
    assert "Slow indexing on monorepos" in combined


def test_intermediate_artifact_builds_and_feeds_pm_extractor(tmp_path):
    mock_llm = MagicMock()
    mock_llm.structured_analyze.side_effect = [
        # 1st call: UserReviewSummary
        {
            "praises": ["Tab 补全极快"],
            "pain_points": ["大文件重构容易漏改"],
            "trust_and_ux_friction": ["缺少显式影响范围提示"],
            "sample_quotes": ["Tab completion is super fast"],
        },
        # 2nd call: PMGuidanceExtractor
        {
            "suitable_product_forms": ["IDE 插件"],
            "autonomy_level": "L2",
            "interaction_design": "针对大文件漏改痛点，提供行内 Diff 审阅与一键回滚",
            "cost_latency_tradeoffs": "Tab 走小模型",
            "mvp_must_haves": ["Diff 预览"],
            "mvp_nice_to_haves": ["MCP"],
            "anti_patterns_to_avoid": ["不要做无预览落盘"],
        },
    ]

    dim_core = DimensionAnalysis(
        dimension="model_routing",
        label="模型路由",
        summary="Tab small model + Composer Sonnet",
        confidence=5,
        coupling_level=CouplingLevel.CORE,
        guard_status=GuardStatus.STRICT_VERIFIED,
        is_inferred=False,
    )
    dim_warn = DimensionAnalysis(
        dimension="prompt_engineering",
        label="提示词工程",
        summary="Inferred rules",
        confidence=2,
        coupling_level=CouplingLevel.MODERATE,
        guard_status=GuardStatus.UNVERIFIED_CAPPED,
        is_inferred=True,
        guard_reason="缺乏直接原文引证",
    )
    review_items = [
        CollectedData(
            source_url="https://news.ycombinator.com/item?id=123",
            source_type="user_review",
            title="HN Discussion",
            content="Tab completion is super fast, but large files break.",
        )
    ]

    builder = IntermediateArtifactBuilder(mock_llm)
    artifact = builder.build("cursor", "engineering", [dim_core, dim_warn], [], review_items=review_items)

    assert len(artifact.core_verified_facts) == 1
    assert len(artifact.inferred_warnings) == 1
    assert artifact.guard_summary["strict_verified"] == 1
    assert artifact.guard_summary["unverified_capped"] == 1
    assert artifact.user_reviews is not None
    assert "大文件重构容易漏改" in artifact.user_reviews.pain_points

    saved_path = builder.save_to_disk(artifact, tmp_path, "cursor")
    assert saved_path.exists()

    pm = PMGuidanceExtractor(mock_llm).extract_from_artifact("Cursor", artifact)
    assert "Diff 审阅" in pm.interaction_design
    # Verify the prompt passed to PMGuidanceExtractor actually contains the intermediate sections
    second_call_prompt = mock_llm.structured_analyze.call_args_list[1][0][0]
    assert "大文件重构容易漏改" in second_call_prompt
    assert "缺乏直接原文引证" in second_call_prompt


def test_cli_offline_saves_intermediate_json_and_renders_reviews(tmp_path, monkeypatch):
    monkeypatch.setenv("HARNESS_CACHE_DIR", str(tmp_path / "cache"))
    monkeypatch.setenv("HARNESS_REPORTS_DIR", str(tmp_path / "reports"))
    import harness_analyzer.config as cfg
    cfg._settings = None

    runner = CliRunner()
    res = runner.invoke(cli_app, ["analyze", "cursor", "--offline"])
    assert res.exit_code == 0
    assert (tmp_path / "reports" / "cursor.intermediate.json").exists()
    md = (tmp_path / "reports" / "cursor.md").read_text(encoding="utf-8")
    assert "中间产物与权威用户真实评论" in md
    assert "权威社区真实用户评论拆解" in md
