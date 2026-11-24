"""Tests for AI Harness Analyzer data models."""
import pytest
from harness_analyzer.models.app import AIApp, AppCategory, AppTag, InfoSource
from harness_analyzer.models.dimension import (
    CommonDimension,
    DimensionAnalysis,
    SpecializedDimensionAnalysis,
    DIMENSION_WEIGHTS,
    CATEGORY_DIMENSIONS,
)
from harness_analyzer.models.harness import HarnessAnalysis


def test_app_category_labels():
    assert AppCategory.ENGINEERING.label == "工程型"
    assert AppCategory.DATA.label == "数据型"
    assert AppCategory.KNOWLEDGE.label == "知识型"
    assert AppCategory.CREATIVE.label == "创作型"
    assert AppCategory.AUTOMATION.label == "自动化型"


def test_ai_app_model_creation():
    app = AIApp(
        name="test-agent",
        display_name="Test Agent",
        category=AppCategory.ENGINEERING,
        tags=[AppTag.PERSONAL, "custom_tag"],
        description="A test agent description",
        info_richness=4,
        info_sources=[
            InfoSource(url="https://example.com/blog", source_type="blog", description="Blog")
        ]
    )
    assert app.name == "test-agent"
    assert app.display_name == "Test Agent"
    assert app.category == AppCategory.ENGINEERING
    assert app.info_richness == 4
    assert len(app.tags) == 2


def test_common_dimension_properties():
    assert len(CommonDimension) == 9
    assert CommonDimension.AGENT_ORCHESTRATION.label == "Agent 编排"
    assert CommonDimension.SECURITY_SANDBOX.label == "安全沙箱"


def test_dimension_weights_matrix():
    assert "engineering" in DIMENSION_WEIGHTS
    assert "data" in DIMENSION_WEIGHTS
    # Engineering places maximum weight (5) on security sandbox and agent orchestration
    assert DIMENSION_WEIGHTS["engineering"]["security_sandbox"] == 5
    assert DIMENSION_WEIGHTS["engineering"]["agent_orchestration"] == 5
    # Data places high weight (5) on prompt engineering & data flow, but low on agent orchestration (2)
    assert DIMENSION_WEIGHTS["data"]["prompt_engineering"] == 5
    assert DIMENSION_WEIGHTS["data"]["agent_orchestration"] == 2


def test_category_specialized_dimensions():
    assert len(CATEGORY_DIMENSIONS["engineering"]) == 5
    assert len(CATEGORY_DIMENSIONS["data"]) == 5
    assert len(CATEGORY_DIMENSIONS["knowledge"]) == 5


def test_harness_analysis_model():
    analysis = HarnessAnalysis(
        app_name="cursor",
        app_display_name="Cursor",
        category="engineering",
        common_dimensions=[
            DimensionAnalysis(
                dimension="agent_orchestration",
                label="Agent 编排",
                summary="Multi-agent orchestration",
                confidence=5,
            )
        ],
        specialized_dimensions=[
            SpecializedDimensionAnalysis(
                dimension="sandbox_model",
                label="沙箱隔离模型",
                summary="Local security boundary",
                confidence=4,
            )
        ],
        architecture_summary="Test summary",
        key_insights=["Insight 1"],
    )
    assert analysis.app_name == "cursor"
    assert len(analysis.common_dimensions) == 1
    assert len(analysis.specialized_dimensions) == 1
