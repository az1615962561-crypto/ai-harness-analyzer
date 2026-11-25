"""Tests for WebSearchCollector and ReverseEngineeringCollector."""
import asyncio
from unittest.mock import patch
from harness_analyzer.collectors.search import WebSearchCollector
from harness_analyzer.collectors.reverse_eng import ReverseEngineeringCollector
from harness_analyzer.models.app import AIApp, AppCategory


def test_search_collector_fallback():
    collector = WebSearchCollector()
    app = AIApp(
        name="test-unknown-agent",
        display_name="Test Unknown Agent",
        category=AppCategory.ENGINEERING,
    )
    with patch("harness_analyzer.collectors.search.run_search_query") as mock_search:
        mock_search.side_effect = Exception("Network offline")
        results = asyncio.run(collector.collect(app))
        assert isinstance(results, list)
        assert len(results) == 0


def test_reverse_engineering_local_scan(tmp_path):
    # Create mock unpacked Electron app directory
    prompt_file = tmp_path / "agent_system_prompt.txt"
    prompt_file.write_text("systemPrompt: Use SEARCH/REPLACE blocks for edits.", encoding="utf-8")

    ignored_dir = tmp_path / "node_modules" / "pkg"
    ignored_dir.mkdir(parents=True)
    (ignored_dir / "system_prompt.js").write_text("systemPrompt: should be ignored", encoding="utf-8")

    collector = ReverseEngineeringCollector(local_app_path=tmp_path)
    results = collector._scan_local_app(tmp_path, "TestApp")
    assert len(results) == 1
    assert results[0].source_type == "local_reverse_engineering"
    assert "SEARCH/REPLACE" in results[0].content
