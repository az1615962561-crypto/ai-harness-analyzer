"""Tests for WebSearchCollector."""
import asyncio
from unittest.mock import patch
from harness_analyzer.collectors.search import WebSearchCollector
from harness_analyzer.models.app import AIApp, AppCategory


def test_search_collector_fallback():
    collector = WebSearchCollector()
    app = AIApp(
        name="test-unknown-agent",
        display_name="Test Unknown Agent",
        category=AppCategory.ENGINEERING,
    )
    # 模拟无网络环境下的健壮性兜底
    with patch("duckduckgo_search.DDGS") as mock_ddg:
        mock_ddg.side_effect = Exception("Network offline")
        results = asyncio.run(collector.collect(app))
        assert isinstance(results, list)
        assert len(results) == 0
