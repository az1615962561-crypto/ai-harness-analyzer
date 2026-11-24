"""AI Application models."""
from __future__ import annotations

from enum import Enum
from typing import Literal
from pydantic import BaseModel, Field


class AppCategory(str, Enum):
    """AI 应用分类"""
    ENGINEERING = "engineering"
    DATA = "data"
    KNOWLEDGE = "knowledge"
    CREATIVE = "creative"
    AUTOMATION = "automation"

    @property
    def label(self) -> str:
        _labels = {
            AppCategory.ENGINEERING: "工程型",
            AppCategory.DATA: "数据型",
            AppCategory.KNOWLEDGE: "知识型",
            AppCategory.CREATIVE: "创作型",
            AppCategory.AUTOMATION: "自动化型",
        }
        return _labels[self]


class AppTag(str, Enum):
    """AI 应用标签"""
    PERSONAL = "personal"
    TEAM = "team"
    ENTERPRISE = "enterprise"
    OPEN_SOURCE = "open_source"

    @property
    def label(self) -> str:
        _labels = {
            AppTag.PERSONAL: "个人",
            AppTag.TEAM: "团队",
            AppTag.ENTERPRISE: "企业",
            AppTag.OPEN_SOURCE: "开源",
        }
        return _labels[self]


class InfoSource(BaseModel):
    """信息来源"""
    url: str
    source_type: str = "docs"
    description: str = ""


class AIApp(BaseModel):
    """AI 应用元数据与信息定义"""
    name: str
    display_name: str
    category: AppCategory
    tags: list[AppTag | str] = Field(default_factory=list)
    description: str = ""
    website: str | None = None
    github_url: str | None = None
    info_sources: list[InfoSource] = Field(default_factory=list)
    info_richness: int = Field(default=3, ge=1, le=5)


CATEGORY_ICONS: dict[str, str] = {
    "engineering": "🔧",
    "data": "📊",
    "knowledge": "🧠",
    "creative": "🎨",
    "automation": "🤖",
}
