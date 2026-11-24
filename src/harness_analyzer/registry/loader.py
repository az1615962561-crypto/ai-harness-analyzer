"""App registry loader module."""
from __future__ import annotations

from pathlib import Path
from typing import Any
import yaml

try:
    from harness_analyzer.models.app import AIApp, AppCategory, AppTag, InfoSource
except (ImportError, ModuleNotFoundError):
    from dataclasses import dataclass, field
    from enum import Enum

    class AppCategory(str, Enum):
        ENGINEERING = "engineering"
        DATA = "data"
        KNOWLEDGE = "knowledge"
        CREATIVE = "creative"
        AUTOMATION = "automation"

    class AppTag(str, Enum):
        PERSONAL = "personal"
        TEAM = "team"
        ENTERPRISE = "enterprise"
        OPEN_SOURCE = "open_source"

    @dataclass
    class InfoSource:
        url: str
        source_type: str
        description: str = ""

    @dataclass
    class AIApp:
        name: str
        display_name: str
        category: AppCategory | str
        tags: list[AppTag | str] = field(default_factory=list)
        description: str = ""
        website: str | None = None
        github_url: str | None = None
        info_richness: int = 1
        info_sources: list[InfoSource] = field(default_factory=list)


class AppRegistry:
    """Registry of AI applications loaded from YAML configuration."""

    def __init__(self, registry_path: Path | None = None) -> None:
        self.registry_path: Path = (
            registry_path if registry_path is not None else Path(__file__).parent / "apps.yaml"
        )
        self._apps: dict[str, AIApp] | None = None

    def _ensure_loaded(self) -> dict[str, AIApp]:
        """Ensure apps dictionary is loaded."""
        if self._apps is None:
            self._apps = self._load()
        return self._apps

    def _load(self) -> dict[str, AIApp]:
        """Parse YAML file and create AIApp objects.

        Handles FileNotFoundError gracefully by returning an empty dict.
        """
        if not self.registry_path.exists():
            return {}

        try:
            with open(self.registry_path, "r", encoding="utf-8") as f:
                data = yaml.safe_load(f)
        except FileNotFoundError:
            return {}

        if not data or not isinstance(data, dict):
            return {}

        apps_list = data.get("apps", [])
        if not isinstance(apps_list, list):
            return {}

        apps: dict[str, AIApp] = {}
        for item in apps_list:
            if not isinstance(item, dict) or "name" not in item:
                continue

            raw_sources = item.get("info_sources", []) or []
            info_sources = []
            for s in raw_sources:
                if isinstance(s, dict):
                    try:
                        info_sources.append(InfoSource(**s))
                    except Exception:
                        info_sources.append(s)
                else:
                    info_sources.append(s)

            raw_category = item.get("category")
            try:
                category = AppCategory(raw_category) if raw_category is not None else raw_category
            except Exception:
                category = raw_category

            raw_tags = item.get("tags", []) or []
            tags = []
            for t in raw_tags:
                try:
                    tags.append(AppTag(t))
                except Exception:
                    tags.append(t)

            app_kwargs = {
                "name": item["name"],
                "display_name": item.get("display_name", item["name"]),
                "category": category,
                "tags": tags,
                "description": item.get("description", ""),
                "website": item.get("website"),
                "github_url": item.get("github_url"),
                "info_richness": item.get("info_richness", 1),
                "info_sources": info_sources,
            }

            try:
                app = AIApp(**app_kwargs)
            except Exception:
                app = AIApp(**item)

            apps[item["name"]] = app

        return apps

    @property
    def apps(self) -> dict[str, AIApp]:
        """Dictionary of loaded apps keyed by app name."""
        return self._ensure_loaded()

    def get_app(self, name: str) -> AIApp | None:
        """Get an app by name."""
        apps = self._ensure_loaded()
        if name in apps:
            return apps[name]
        name_lower = name.lower()
        for app_name, app in apps.items():
            if app_name.lower() == name_lower:
                return app
        return None

    def list_apps(self, category: str | None = None, tag: str | None = None) -> list[AIApp]:
        """List apps filtered by category and/or tag."""
        apps = self._ensure_loaded()
        results: list[AIApp] = []
        for app in apps.values():
            if category is not None:
                target_cat = category.value if hasattr(category, "value") else str(category)
                app_cat = app.category.value if hasattr(app.category, "value") else str(app.category)
                if app_cat.lower() != target_cat.lower():
                    continue
            if tag is not None:
                target_tag = tag.value if hasattr(tag, "value") else str(tag)
                app_tags = [
                    t.value if hasattr(t, "value") else str(t)
                    for t in (app.tags or [])
                ]
                if not any(t.lower() == target_tag.lower() for t in app_tags):
                    continue
            results.append(app)
        return results

    def search(self, query: str) -> list[AIApp]:
        """Search apps by name and description substring."""
        apps = self._ensure_loaded()
        q = query.lower()
        results: list[AIApp] = []
        for app in apps.values():
            name_match = (
                q in app.name.lower()
                or (bool(app.display_name) and q in app.display_name.lower())
            )
            desc_match = bool(app.description) and q in app.description.lower()
            if name_match or desc_match:
                results.append(app)
        return results

    def categories(self) -> list[str]:
        """Get list of unique categories."""
        apps = self._ensure_loaded()
        cats: list[str] = []
        for app in apps.values():
            cat_str = app.category.value if hasattr(app.category, "value") else str(app.category)
            if cat_str not in cats:
                cats.append(cat_str)
        return cats
