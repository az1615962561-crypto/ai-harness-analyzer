"""Tests for anti-bot detection, domain rate-limiter circuit breaker, FactSheetExtractor, and concurrent dimension extraction."""
import asyncio
from unittest.mock import MagicMock
import httpx

from harness_analyzer.analyzer.dimensions import CommonDimensionExtractor
from harness_analyzer.analyzer.fact_sheet import FactSheetExtractor
from harness_analyzer.analyzer.specialized import get_specialized_analyzer
from harness_analyzer.collectors.base import CollectedData
from harness_analyzer.collectors.query_planner import BilingualQueryPlanner
from harness_analyzer.collectors.web_utils import (
    DomainRateLimiter,
    detect_antibot_block,
    fetch_clean_page,
)


def test_detect_antibot_block_variants():
    assert detect_antibot_block(429, {}, "Too many requests") == "rate_limited_429"
    assert detect_antibot_block(403, {"cf-mitigated": "challenge"}, "") == "cloudflare_challenge"
    assert detect_antibot_block(200, {}, "<html><title>Just a moment...</title></html>") == "cloudflare_challenge"
    assert detect_antibot_block(200, {}, '<div class="cf-turnstile"></div>') == "captcha_or_antibot"
    assert detect_antibot_block(403, {}, "Access Denied") == "forbidden_403"
    assert detect_antibot_block(200, {}, "<html><body><p>Normal engineering blog post.</p></body></html>") is None


def test_fetch_clean_page_trips_circuit_on_cloudflare_and_skips_jina():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        return httpx.Response(
            403,
            headers={"cf-mitigated": "challenge"},
            text="<html><title>Just a moment...</title></html>",
        )

    limiter = DomainRateLimiter(min_interval=0.0, max_concurrency=2)

    async def run():
        async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
            t1, txt1, _ = await fetch_clean_page(client, "https://blocked.example.com/blog", rate_limiter=limiter)
            # Second call to same domain should be short-circuited without hitting HTTP
            t2, txt2, _ = await fetch_clean_page(client, "https://blocked.example.com/docs", rate_limiter=limiter)
            return (t1, txt1), (t2, txt2)

    (_, txt1), (_, txt2) = asyncio.run(run())
    assert txt1 == ""
    assert txt2 == ""
    # Only 1 HTTP call was made; neither Jina fallback nor 2nd domain request ran
    assert calls == ["https://blocked.example.com/blog"]
    assert limiter.is_blocked("https://blocked.example.com/other") == "cloudflare_challenge"
    assert len(limiter.blocked_records) == 1


def test_fact_sheet_and_concurrent_extraction():
    mock_llm = MagicMock()
    mock_llm.analyze.return_value = "- [上下文] Uses Tree-sitter AST (\"Tree-sitter AST chunking\")"
    mock_llm.structured_analyze.return_value = {
        "summary": "Uses Tree-sitter AST",
        "details": "Detailed info",
        "key_decisions": ["AST chunking"],
        "takeaways": ["Use AST"],
        "verbatim_quotes": ["Tree-sitter AST chunking"],
        "evidence_sources": ["https://example.com"],
        "confidence": 5,
    }

    # Build > 7000 chars so FactSheetExtractor invokes chunk extraction
    big_items = [
        CollectedData(
            source_url=f"https://example.com/{i}",
            source_type="blog_article",
            title=f"Article {i}",
            content=("Tree-sitter AST chunking and sandbox execution details. " * 80),
        )
        for i in range(3)
    ]

    async def run():
        fs = await FactSheetExtractor(mock_llm, max_chunk_chars=5000).build_fact_sheet("Cursor", big_items)
        c_dims, s_dims = await asyncio.gather(
            CommonDimensionExtractor(mock_llm).aextract_all("Cursor", fs, category="engineering", depth="quick"),
            get_specialized_analyzer("engineering", mock_llm).aanalyze("Cursor", fs),
        )
        return fs, c_dims, s_dims

    fs, c_dims, s_dims = asyncio.run(run())
    assert "Fact Sheet" in fs
    assert "Tree-sitter AST" in fs
    assert len(c_dims) == 9
    assert len(s_dims) == 5


def test_refill_queries_for_missing_angles():
    refills = BilingualQueryPlanner.plan_refill_queries("扣子", ["architecture_qa", "user_reviews"], question_lang="zh")
    q_strs = [r.query for r in refills]
    assert any("Coze AI explained" in q for q in q_strs)
    assert any("扣子 AI 原理" in q for q in q_strs)
    assert any("扣子 好用吗 评测" in q for q in q_strs)
