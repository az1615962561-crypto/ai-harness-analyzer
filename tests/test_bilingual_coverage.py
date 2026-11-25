"""Tests for BilingualQueryPlanner, dual-language search, and coverage evaluation."""
import asyncio
from unittest.mock import patch
from harness_analyzer.collectors.query_planner import BilingualQueryPlanner
from harness_analyzer.collectors.search import WebSearchCollector
from harness_analyzer.models.app import AIApp, AppCategory
from harness_analyzer.models.harness import IntermediateArtifact, QueryCoverageItem
from harness_analyzer.output.markdown import MarkdownReportGenerator
from harness_analyzer.models.harness import HarnessAnalysis


def test_bilingual_query_planner_generates_zh_and_en_question_queries():
    names, queries = BilingualQueryPlanner.plan_search_queries("claude", question_lang="zh")
    assert names["en"] == "Claude"
    query_strings = [q.query for q in queries]
    langs = {q.language for q in queries}
    assert langs == {"zh", "en"}
    assert any("Claude的架构是什么" in qs for qs in query_strings)
    assert any("how the Claude works" in qs for qs in query_strings)

    # Chinese app name resolves to English equivalent alias
    names_cn, queries_cn = BilingualQueryPlanner.plan_search_queries("扣子", question_lang="zh")
    assert names_cn["en"] == "Coze"
    assert any("how the Coze works" in q.query for q in queries_cn)
    assert any("扣子的架构是什么" in q.query for q in queries_cn)


def test_coverage_report_tracks_hits_and_missing_angles():
    items = [
        QueryCoverageItem(query="Claude的架构是什么", language="zh", angle="architecture_qa", hits_count=4, pages_fetched=1, chars_collected=1200),
        QueryCoverageItem(query="how the Claude works AI architecture", language="en", angle="architecture_qa", hits_count=5, pages_fetched=1, chars_collected=2400),
        QueryCoverageItem(query="Claude system prompt tools agent harness", language="en", angle="implementation_tech", hits_count=3),
        QueryCoverageItem(query="Claude 开源 源码 逆向", language="zh", angle="source_reverse", hits_count=0),
    ]
    report = BilingualQueryPlanner.build_coverage_report(items, question_lang="zh", bilingual_names={"local": "Claude", "en": "Claude"})
    assert report.zh_hits == 4
    assert report.en_hits == 8
    assert "architecture_qa" in report.covered_angles
    assert "implementation_tech" in report.covered_angles
    assert "source_reverse" in report.missing_angles
    assert "user_reviews" in report.missing_angles
    assert 0.5 < report.coverage_score < 1.0


def test_web_search_collector_records_bilingual_coverage(monkeypatch):
    def fake_run_search(query, language="en", max_results=4, timeout=6):
        return [
            {
                "title": f"Result for {query}",
                "href": f"https://example.com/{abs(hash(query))}",
                "body": f"Architecture details found for {query}",
            }
        ]

    monkeypatch.setattr("harness_analyzer.collectors.search.run_search_query", fake_run_search)
    # Skip real HTTP page fetch in unit test
    async def fake_fetch(client, url, max_chars=4500, use_jina_fallback=True):
        return ("Mock Page", "Mock clean article content explaining agent architecture and tool calling in depth." * 3, [])
    monkeypatch.setattr("harness_analyzer.collectors.search.fetch_clean_page", fake_fetch)

    collector = WebSearchCollector(question_lang="zh")
    app = AIApp(name="claude", display_name="Claude", category=AppCategory.ENGINEERING)
    results = asyncio.run(collector.collect(app))
    assert len(results) > 0
    assert len(collector.last_coverage_items) == 8  # 4 zh + 4 en
    cov = BilingualQueryPlanner.build_coverage_report(collector.last_coverage_items, question_lang="zh")
    assert cov.zh_hits > 0
    assert cov.en_hits > 0

    # Verify Markdown renders coverage table cleanly
    md = MarkdownReportGenerator().generate(
        HarnessAnalysis(
            app_name="claude",
            app_display_name="Claude",
            category="engineering",
            intermediate_artifact=IntermediateArtifact(
                app_name="claude",
                category="engineering",
                search_coverage=cov,
            ),
        )
    )
    assert "双语多维度检索覆盖度评估" in md
    assert "Claude的架构是什么" in md
    assert "how the Claude works AI architecture" in md
