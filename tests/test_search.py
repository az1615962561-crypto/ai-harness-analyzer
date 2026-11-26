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


def test_reverse_engineering_rea_integration_and_fallback(tmp_path, monkeypatch):
    asar_file = tmp_path / "app.asar"
    asar_file.write_bytes(b"fake asar")

    # 1. Missing rea/npx -> graceful fallback to empty list
    monkeypatch.setattr("shutil.which", lambda name: None)
    collector = ReverseEngineeringCollector(local_app_path=asar_file, use_rea=True)
    assert collector._resolve_rea_command() is None
    assert asyncio.run(collector._run_rea_analyzer(asar_file)) == []

    # 2. Available rea + mocked subprocess JSON output -> formatted CollectedData
    monkeypatch.setattr("shutil.which", lambda name: "/usr/local/bin/rea" if name == "rea" else None)

    class FakeProc:
        returncode = 0
        async def communicate(self):
            payload = (
                'npx notice...\n'
                '{"normalized_result": {"summary": "Electron agent host", '
                '"endpoints": [{"path": "/api/agent/run", "method": "POST"}], '
                '"evidence": ["systemPrompt loaded from rules.json"]}}'
            ).encode("utf-8")
            return payload, b""

    async def fake_exec(*cmd, **kwargs):
        assert "analyze-javascript-application" in cmd
        assert "--json" in cmd
        return FakeProc()

    monkeypatch.setattr(asyncio, "create_subprocess_exec", fake_exec)
    rea_items = asyncio.run(collector._run_rea_analyzer(asar_file))
    assert len(rea_items) == 1
    assert rea_items[0].source_type == "local_reverse_engineering"
    assert "/api/agent/run" in rea_items[0].content
    assert "Electron agent host" in rea_items[0].content
