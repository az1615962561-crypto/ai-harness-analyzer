"""Tests for Output Generators."""
from harness_analyzer.models.dimension import DimensionAnalysis
from harness_analyzer.models.harness import HarnessAnalysis, PMGuidance
from harness_analyzer.output.markdown import MarkdownReportGenerator
from harness_analyzer.output.comparison import ComparisonReportGenerator
from harness_analyzer.output.diagram import DiagramGenerator


def test_diagram_generator():
    gen = DiagramGenerator()
    analysis = HarnessAnalysis(
        app_name="cursor",
        app_display_name="Cursor",
        category="engineering",
        architecture_summary="IDE agent",
    )
    diagram = gen.generate(analysis)
    assert "flowchart TD" in diagram
    assert "Cursor" in diagram


def test_markdown_report_generator():
    gen = MarkdownReportGenerator()
    analysis = HarnessAnalysis(
        app_name="cursor",
        app_display_name="Cursor",
        category="engineering",
        confidence_overall=5,
        architecture_summary="A leading engineering agent harness.",
        pm_guidance=PMGuidance(
            suitable_product_forms=["IDE 原生插件"],
            autonomy_level="L2~L3",
            mvp_must_haves=["Diff 预览"],
        ),
        common_dimensions=[
            DimensionAnalysis(
                dimension="agent_orchestration",
                label="Agent 编排",
                summary="Dual-agent flow",
                details="Detailed agent flow.",
                key_decisions=["Decision 1"],
                takeaways=["Takeaway 1"],
                confidence=5,
            )
        ],
        key_insights=["Insight 1"],
    )
    md = gen.generate(analysis)
    assert "# Cursor — Harness 架构" in md
    assert "★★★★★" in md
    assert "## 概览指标" in md
    assert "## 🎯 应用层：产品经理产品方案指导" in md
    assert "IDE 原生插件" in md
    assert "### Agent 编排" in md
    assert "Dual-agent flow" in md
    assert "flowchart TD" in md


def test_comparison_report_generator():
    gen = ComparisonReportGenerator()
    a1 = HarnessAnalysis(
        app_name="cursor",
        app_display_name="Cursor",
        category="engineering",
        confidence_overall=5,
        pm_guidance=PMGuidance(
            suitable_product_forms=["IDE 原生扩展"],
            autonomy_level="L2~L3",
            mvp_must_haves=["Diff 审阅"],
        ),
        common_dimensions=[
            DimensionAnalysis(dimension="tool_chain", label="工具链", summary="LSP tools", confidence=5)
        ],
    )
    a2 = HarnessAnalysis(
        app_name="chatbi",
        app_display_name="ChatBI",
        category="data",
        confidence_overall=4,
        pm_guidance=PMGuidance(
            suitable_product_forms=["企业 BI 工作台"],
            autonomy_level="L1~L2",
            mvp_must_haves=["SQL 校验"],
        ),
        common_dimensions=[
            DimensionAnalysis(dimension="tool_chain", label="工具链", summary="SQL tools", confidence=5)
        ],
    )
    report = gen.generate([a1, a2])
    assert "AI Harness 架构对比报告" in report
    assert "★★★★★" in report
    assert "★★★★☆" in report
    assert "应用层：产品方案横向对比" in report
    assert "IDE 原生扩展" in report
    assert "企业 BI 工作台" in report
    assert "LSP tools" in report
    assert "SQL tools" in report
