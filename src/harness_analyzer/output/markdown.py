"""单个应用的 Harness 架构分析 Markdown 报告生成器"""
from datetime import datetime
from typing import Any

try:
    from harness_analyzer.models.harness import HarnessAnalysis
except ImportError:
    class HarnessAnalysis:  # type: ignore
        """HarnessAnalysis 类型占位"""
        pass

from .diagram import DiagramGenerator


class MarkdownReportGenerator:
    """生成标准化 Markdown 架构分析报告"""

    @staticmethod
    def _format_stars(conf: Any) -> str:
        """将置信度转化为 5 星显示"""
        if conf is None:
            return "★★★☆☆"
        if isinstance(conf, (int, float)):
            if 0 < conf <= 1.0:
                stars = round(conf * 5)
            else:
                stars = round(conf)
            stars = max(1, min(5, stars))
            return "★" * stars + "☆" * (5 - stars)
        return str(conf)

    @staticmethod
    def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
        """获取对象或字典字段值"""
        for k in keys:
            if isinstance(obj, dict) and k in obj and obj[k] is not None:
                return obj[k]
            if hasattr(obj, k) and getattr(obj, k) is not None:
                return getattr(obj, k)
        return default

    def _render_dimension_item(self, item: Any) -> str:
        """渲染单个维度的分析段落"""
        label = self._get_val(
            item, "dimension_label", "label", "dimension_name", "dimension", "name", default="未命名维度"
        )
        summary = self._get_val(item, "summary", default="")
        details = self._get_val(item, "details", "description", default="")
        confidence = self._get_val(item, "confidence", default=None)
        key_decisions = self._get_val(item, "key_decisions", "decisions", default=[])
        takeaways = self._get_val(
            item, "takeaways", "key_takeaways", "lessons", "lessons_learned", default=[]
        )

        lines = [
            f"### {label}\n",
            f"**置信度**：{self._format_stars(confidence)}\n",
        ]

        if summary:
            lines.append(f"{summary}\n")

        if details:
            lines.append(f"{details}\n")

        # 关键设计决策
        lines.append("**关键设计决策**：")
        if isinstance(key_decisions, list) and key_decisions:
            for d in key_decisions:
                lines.append(f"- {d}")
        elif isinstance(key_decisions, str) and key_decisions.strip():
            for d in key_decisions.splitlines():
                if d.strip():
                    lines.append(f"- {d.strip().lstrip('-*• ')}")
        else:
            lines.append("- 暂无公开的关键决策记录")
        lines.append("")

        # 可借鉴点
        lines.append("**可借鉴点**：")
        if isinstance(takeaways, list) and takeaways:
            for idx, t in enumerate(takeaways, 1):
                lines.append(f"{idx}. {t}")
        elif isinstance(takeaways, str) and takeaways.strip():
            for idx, t in enumerate(takeaways.splitlines(), 1):
                if t.strip():
                    lines.append(f"{idx}. {t.strip().lstrip('0123456789.-*• ')}")
        else:
            lines.append("1. 暂无可直接借鉴的明确项")
        lines.append("")

        return "\n".join(lines)

    def generate(self, analysis: HarnessAnalysis | Any) -> str:
        """生成完整的 Markdown 架构分析报告"""
        app_display_name = self._get_val(
            analysis, "app_display_name", "app_name", default="AI 应用"
        )
        category = self._get_val(analysis, "category", default="未分类")
        if hasattr(category, "value"):
            category = category.value

        analyzed_at = self._get_val(analysis, "analyzed_at", default=None)
        if isinstance(analyzed_at, datetime):
            analyzed_at_str = analyzed_at.strftime("%Y-%m-%d %H:%M:%S")
        elif analyzed_at:
            analyzed_at_str = str(analyzed_at)
        else:
            analyzed_at_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        source_count = self._get_val(analysis, "source_count", default=None)
        if source_count is None:
            sources = self._get_val(
                analysis, "sources", "collected_data", "info_sources", default=[]
            )
            source_count = len(sources) if isinstance(sources, list) else 0

        confidence = self._get_val(analysis, "confidence", default=None)
        confidence_stars = self._format_stars(confidence)

        # 架构流程图
        mermaid_diagram = self._get_val(analysis, "mermaid_diagram", default="")
        if not mermaid_diagram:
            mermaid_diagram = DiagramGenerator().generate(analysis)
        # 清除外部代码块标记以避免重复包裹
        cleaned_diagram = mermaid_diagram.strip()
        if cleaned_diagram.startswith("```mermaid"):
            cleaned_diagram = cleaned_diagram[len("```mermaid"):]
        if cleaned_diagram.startswith("```"):
            cleaned_diagram = cleaned_diagram[len("```"):]
        if cleaned_diagram.endswith("```"):
            cleaned_diagram = cleaned_diagram[:-3]
        cleaned_diagram = cleaned_diagram.strip()

        # 架构摘要
        architecture_summary = self._get_val(
            analysis, "architecture_summary", default="暂无架构摘要说明。"
        )

        # 共性维度
        common_dimensions = self._get_val(analysis, "common_dimensions", default=[])

        # 品类专属维度
        specialized_dimensions = self._get_val(analysis, "specialized_dimensions", default=[])

        # 关键洞察
        key_insights = self._get_val(analysis, "key_insights", default=[])

        parts = []

        # 1. 标题
        parts.append(f"# {app_display_name} — Harness 架构分析\n")

        # 2. 概览
        parts.append("## 概览\n")
        parts.append(
            "| 应用分类 | 分析时间 | 信息源数量 | 整体置信度 |\n"
            "| :--- | :--- | :--- | :--- |\n"
            f"| {category} | {analyzed_at_str} | {source_count} | {confidence_stars} |\n"
        )

        # 3. 架构总览
        parts.append("## 架构总览\n")
        parts.append("```mermaid\n" + cleaned_diagram + "\n```\n")

        # 4. 架构摘要
        parts.append("## 架构摘要\n")
        parts.append(f"{architecture_summary}\n")

        # 5. 共性维度分析
        parts.append("## 共性维度分析\n")
        if common_dimensions and isinstance(common_dimensions, list):
            for dim in common_dimensions:
                parts.append(self._render_dimension_item(dim))
        else:
            parts.append("*暂无共性维度分析数据。*\n")

        # 6. 品类专属分析
        parts.append("## 品类专属分析\n")
        if specialized_dimensions and isinstance(specialized_dimensions, list):
            for sdim in specialized_dimensions:
                parts.append(self._render_dimension_item(sdim))
        else:
            parts.append("*暂无品类专属分析数据。*\n")

        # 7. 关键洞察
        parts.append("## 关键洞察\n")
        if isinstance(key_insights, list) and key_insights:
            for idx, insight in enumerate(key_insights, 1):
                parts.append(f"{idx}. {insight}")
            parts.append("")
        elif isinstance(key_insights, str) and key_insights.strip():
            for idx, insight in enumerate(key_insights.splitlines(), 1):
                if insight.strip():
                    parts.append(f"{idx}. {insight.strip().lstrip('0123456789.-*• ')}")
            parts.append("")
        else:
            parts.append("1. 暂无关键洞察记录。\n")

        # 8. 分析说明
        parts.append("## 分析说明\n")
        parts.append(
            "> **免责与分析声明**：\n"
            "> 本分析报告基于技术博客、公开技术分享、官方开源仓库（README 与代码目录组织）等公开信息源，"
            "结合大语言模型分析推断得出。分析结果仅代表对公开架构设计模式的解读与推断，"
            "供技术研究与架构设计参考，不代表对应产品官方的内部完整实现或商业机密。\n"
        )

        return "\n".join(parts)
