"""Tests for App Registry."""
import pytest
from harness_analyzer.registry.loader import AppRegistry
from harness_analyzer.models.app import AppCategory


@pytest.fixture
def registry():
    return AppRegistry()


def test_registry_loads_apps(registry):
    apps = registry.list_apps()
    assert len(apps) >= 20


def test_get_specific_app(registry):
    cursor = registry.get_app("cursor")
    assert cursor is not None
    assert cursor.name == "cursor"
    assert cursor.display_name == "Cursor"
    assert cursor.category == AppCategory.ENGINEERING


def test_filter_by_category(registry):
    eng_apps = registry.list_apps(category="engineering")
    assert len(eng_apps) >= 5
    for a in eng_apps:
        assert a.category == AppCategory.ENGINEERING


def test_search_apps(registry):
    results = registry.search("编程")
    assert len(results) > 0
    names = [r.name for r in results]
    assert "cursor" in names or "claude-code" in names


def test_unique_categories(registry):
    cats = registry.categories()
    assert "engineering" in cats
    assert "data" in cats
    assert "knowledge" in cats
    assert "creative" in cats
    assert "automation" in cats
