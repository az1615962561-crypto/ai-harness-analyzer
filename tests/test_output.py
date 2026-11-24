"""Tests for Output Generators."""
from harness_analyzer.models.app import AIApp, AppCategory
from harness_analyzer.models.dimension import DimensionAnalysis
from harness_analyzer.models.harness import HarnessAnalysis
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
        architecture_summary="A leading engineering agent harness.",
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
    assert "# Cursor — Harness 架构分析" in md
    assert "## 概览" in md
    assert "### Agent 编排" in md
    assert "Dual-agent flow" in md
    assert "flowchart TD" in md


def test_comparison_report_generator():
    gen = ComparisonReportGenerator()
    a1 = HarnessAnalysis(
        app_name="cursor",
        app_display_name="Cursor",
        category="engineering",
        common_dimensions=[
            DimensionAnalysis(dimension="tool_chain", label="工具链", summary="LSP tools", confidence=5)
        ],
    )
    a2 = HarnessAnalysis(
        app_name="chatbi",
        app_display_name="ChatBI",
        category="data",
        common_dimensions=[
            DimensionAnalysis(dimension="tool_chain", label="工具链", summary="SQL tools", confidence=5)
        ],
    )
    report = gen.generate([a1, a2])
    assert "AI Harness 架构对比报告" in report
    assert "Cursor" in report
    assert "ChatBI" in report
    assert "LSP tools" in report
    assert "SQL tools" in report
