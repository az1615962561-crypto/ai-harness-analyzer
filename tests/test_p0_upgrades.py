"""Tests for P0 accuracy upgrades: GitHub key-file selection, Blog drill-down, RE search, and Evidence gating."""
import asyncio
import httpx
from harness_analyzer.collectors.github import GitHubCollector
from harness_analyzer.collectors.blog import BlogCollector
from harness_analyzer.collectors.web_utils import parse_html, rank_article_links
from harness_analyzer.analyzer.evidence import verify_dimension_evidence, verify_all_dimensions
from harness_analyzer.models.app import AIApp, AppCategory, InfoSource
from harness_analyzer.models.dimension import DimensionAnalysis, SpecializedDimensionAnalysis
from harness_analyzer.output.markdown import MarkdownReportGenerator
from harness_analyzer.models.harness import HarnessAnalysis


def test_github_select_key_files_prioritizes_harness_sources():
    paths = [
        "README.md",
        "tests/test_agent.py",
        "node_modules/foo/index.js",
        "package-lock.json",
        "pyproject.toml",
        "src/agent/orchestrator.py",
        "src/prompts/system_prompt.md",
        "src/tools/mcp_client.py",
        "src/sandbox/docker_runner.py",
        "src/context/ast_indexer.py",
        "assets/logo.png",
    ]
    selected = GitHubCollector.select_key_files(paths, max_files=5)
    assert "src/prompts/system_prompt.md" in selected
    assert "src/agent/orchestrator.py" in selected
    assert "src/tools/mcp_client.py" in selected
    assert "src/sandbox/docker_runner.py" in selected
    assert "tests/test_agent.py" not in selected
    assert "package-lock.json" not in selected
    assert "README.md" not in selected


def test_web_utils_drops_nav_footer_and_ranks_architecture_links():
    html = """
    <html>
      <head><title>Acme AI Blog</title></head>
      <body>
        <nav><a href="/pricing">Pricing</a><a href="/login">Login</a></nav>
        <main>
          <h1>Engineering Blog</h1>
          <a href="/blog/how-we-built-our-agent-harness">How We Built Our Agent Harness Architecture</a>
          <a href="/blog/company-picnic-2026">Company Picnic</a>
          <a href="https://external.com/other">External Link</a>
        </main>
        <footer><a href="/privacy">Privacy</a></footer>
      </body>
    </html>
    """
    title, clean_text, links = parse_html(html, base_url="https://acme.ai/blog")
    assert title == "Acme AI Blog"
    assert "Pricing" not in clean_text
    assert "Privacy" not in clean_text
    assert "Engineering Blog" in clean_text

    ranked = rank_article_links("https://acme.ai/blog", links, limit=2)
    assert len(ranked) == 1
    assert ranked[0][0] == "https://acme.ai/blog/how-we-built-our-agent-harness"


def test_blog_collector_drills_down_into_index_articles(monkeypatch):
    index_html = """
    <html><head><title>Acme Blog</title></head><body>
      <main>
        <p>Welcome to our engineering blog where we share technical updates.</p>
        <a href="/blog/agent-sandbox-architecture">Inside Our Agent Sandbox Architecture</a>
      </main>
    </body></html>
    """
    article_html = """
    <html><head><title>Inside Our Agent Sandbox</title></head><body>
      <article>
        <p>We isolate untrusted user code execution using lightweight Firecracker microVMs and strict network policies to keep latency under 150ms across sessions.</p>
      </article>
    </body></html>
    """

    def handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/blog":
            return httpx.Response(200, text=index_html, headers={"content-type": "text/html"})
        if request.url.path == "/blog/agent-sandbox-architecture":
            return httpx.Response(200, text=article_html, headers={"content-type": "text/html"})
        return httpx.Response(404)

    transport = httpx.MockTransport(handler)
    orig_async_client = httpx.AsyncClient

    def patched_client(*args, **kwargs):
        kwargs["transport"] = transport
        return orig_async_client(*args, **kwargs)

    monkeypatch.setattr(httpx, "AsyncClient", patched_client)

    app = AIApp(
        name="acme",
        display_name="Acme",
        category=AppCategory.ENGINEERING,
        info_sources=[InfoSource(url="https://acme.ai/blog", source_type="blog", description="Blog")],
    )
    results = asyncio.run(BlogCollector(max_drilldown=2).collect(app))
    types = [r.source_type for r in results]
    assert "blog" in types
    assert "blog_article" in types
    assert any("Firecracker microVMs" in r.content for r in results)


def test_evidence_verification_caps_hallucinated_confidence():
    corpus = (
        "Cursor uses Tree-sitter AST chunking combined with Merkle Tree hash verification "
        "to synchronize codebase embeddings locally."
    )

    verified_dim = DimensionAnalysis(
        dimension="context_engineering",
        label="上下文工程",
        summary="Tree-sitter + Merkle Tree",
        confidence=5,
        verbatim_quotes=["Tree-sitter AST chunking combined with Merkle Tree hash verification"],
    )
    fabricated_dim = DimensionAnalysis(
        dimension="security_sandbox",
        label="安全沙箱",
        summary="Claims WASM sandbox",
        confidence=5,
        verbatim_quotes=["Uses custom WebAssembly kernel sandbox for every command"],
    )
    empty_spec = SpecializedDimensionAnalysis(
        dimension="terminal_management",
        label="终端管理",
        summary="No direct evidence",
        confidence=4,
        verbatim_quotes=[],
    )

    v_common, v_spec = verify_all_dimensions([verified_dim, fabricated_dim], [empty_spec], corpus)

    # Verified quote keeps 5 stars and is_inferred=False
    assert v_common[0].confidence == 5
    assert v_common[0].is_inferred is False
    assert len(v_common[0].verbatim_quotes) == 1

    # Fabricated quote is stripped, marked inferred, and CORE unverified is strictly capped at 1 star
    assert v_common[1].confidence == 1
    assert v_common[1].is_inferred is True
    assert v_common[1].verbatim_quotes == []

    # Empty quote on specialized (CORE) dimension is marked inferred and capped at 1 star
    assert v_spec[0].confidence == 1
    assert v_spec[0].is_inferred is True

    # Verify Markdown renders both Verified Quotes and Inferred warning
    md = MarkdownReportGenerator().generate(
        HarnessAnalysis(
            app_name="cursor",
            app_display_name="Cursor",
            category="engineering",
            common_dimensions=v_common,
            specialized_dimensions=v_spec,
        )
    )
    assert "原文佐证片段 (Verified Quotes)" in md
    assert "Tree-sitter AST chunking" in md
    assert "缺乏原文实证" in md
    assert "★☆☆☆☆" in md
