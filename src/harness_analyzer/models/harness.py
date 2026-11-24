"""Harness Architecture Analysis models."""
from __future__ import annotations

from datetime import datetime
from pydantic import BaseModel, Field

from harness_analyzer.models.dimension import (
    DimensionAnalysis,
    SpecializedDimensionAnalysis,
)


class PMGuidance(BaseModel):
    """应用层：产品经理产品方案指导 (PM Guidance)"""
    suitable_product_forms: list[str] = Field(default_factory=list, description="适合的产品形态")
    autonomy_level: str = Field(default="L2 (协同辅助型)", description="产品自主度分级 (L1建议 ~ L4全自动)")
    interaction_design: str = Field(default="", description="人机协同与信任机制设计建议")
    cost_latency_tradeoffs: str = Field(default="", description="响应延迟与 Token 成本控制权衡")
    mvp_must_haves: list[str] = Field(default_factory=list, description="MVP 必须功能清单 (P0)")
    mvp_nice_to_haves: list[str] = Field(default_factory=list, description="增强功能建议 (P1)")
    anti_patterns_to_avoid: list[str] = Field(default_factory=list, description="产品经理避坑建议")


class HarnessAnalysis(BaseModel):
    """AI 应用 Harness 架构分析全景报告"""
    app_name: str
    app_display_name: str
    category: str
    analyzed_at: datetime = Field(default_factory=datetime.now)
    pm_guidance: PMGuidance | None = None
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
