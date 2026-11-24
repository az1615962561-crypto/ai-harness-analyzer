"""Tests for SQLite Storage Cache."""
import json
import pytest
from harness_analyzer.storage.cache import AnalysisCache


@pytest.fixture
def temp_cache(tmp_path):
    return AnalysisCache(cache_dir=tmp_path)


def test_save_and_get(temp_cache):
    data = {"app_name": "test_app", "summary": "Sample summary"}
    temp_cache.save("test_app", "engineering", json.dumps(data))

    cached = temp_cache.get("test_app")
    assert cached is not None
    assert cached["app_name"] == "test_app"
    assert cached["summary"] == "Sample summary"


def test_list_cached(temp_cache):
    temp_cache.save("app1", "engineering", json.dumps({"name": "app1"}))
    temp_cache.save("app2", "data", json.dumps({"name": "app2"}))

    cached_list = temp_cache.list_cached()
    assert len(cached_list) == 2
    names = [c["app_name"] for c in cached_list]
    assert "app1" in names and "app2" in names


def test_clear_cache(temp_cache):
    temp_cache.save("app1", "engineering", json.dumps({"name": "app1"}))
    temp_cache.clear("app1")
    assert temp_cache.get("app1") is None
