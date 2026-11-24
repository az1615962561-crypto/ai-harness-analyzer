"""Harness Architecture Analysis models."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

from harness_analyzer.models.dimension import (
    DimensionAnalysis,
    SpecializedDimensionAnalysis,
)


class HarnessAnalysis(BaseModel):
    """AI 应用 Harness 架构分析全景报告"""
    app_name: str
    app_display_name: str
    category: str
    analyzed_at: datetime = Field(default_factory=datetime.now)
    common_dimensions: list[DimensionAnalysis] = Field(default_factory=list)
    specialized_dimensions: list[SpecializedDimensionAnalysis] = Field(default_factory=list)
    architecture_summary: str = ""
    key_insights: list[str] = Field(default_factory=list)
    mermaid_diagram: str = ""
    raw_sources: list[str] = Field(default_factory=list)
    source_count: int = 0
    confidence_overall: int = Field(default=3, ge=1, le=5)


class ComparisonReport(BaseModel):
    """多应用 Harness 架构对比报告"""
    apps: list[str]
    analyzed_at: datetime = Field(default_factory=datetime.now)
    dimension_comparisons: list[dict] = Field(default_factory=list)
    key_differences: list[str] = Field(default_factory=list)
    recommendations: list[str] = Field(default_factory=list)
