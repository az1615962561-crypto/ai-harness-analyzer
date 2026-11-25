"""单个应用的 Harness 架构分析 Markdown 报告生成器
分为三层结构：
1. 概览与架构总览 (Mermaid)
2. 🎯 应用层：产品经理产品方案指导 (PM Solution Guidance - 产品形态、自主度、人机协同交互、MVP清单、避坑指南)
3. 🔬 中间层：Harness 维度深度分析报告 (Dimension Analysis - 9大共性维度 + 5大品类专属维度分析手法)
4. 📑 事实层：信源与逆向采集追踪 (Fact & Source Traceability)
"""
from datetime import datetime
from typing import Any

try:
    from harness_analyzer.models.harness import HarnessAnalysis, PMGuidance
except ImportError:
    class HarnessAnalysis:  # type: ignore
        pass
    class PMGuidance:  # type: ignore
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
        verbatim_quotes = self._get_val(item, "verbatim_quotes", default=[])
        is_inferred = bool(self._get_val(item, "is_inferred", default=False))

        lines = [
            f"### {label}\n",
            f"**置信度**：{self._format_stars(confidence)}\n",
        ]

        if is_inferred:
            lines.append("> ⚠️ *缺乏一手采集原文直接佐证，本维度主要基于同类架构模式推断（置信度已封顶受限）。*\n")

        if summary:
            lines.append(f"{summary}\n")

        if details:
            lines.append(f"{details}\n")

        if isinstance(verbatim_quotes, list) and verbatim_quotes:
            lines.append("**原文佐证片段 (Verified Quotes)**：")
            for q in verbatim_quotes:
                clean_q = str(q).replace("\n", " ").strip()
                if clean_q:
                    lines.append(f'> "{clean_q}"')
            lines.append("")

        # 关键设计决策
        lines.append("**关键设计决策 (Engineering Decisions)**：")
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
        lines.append("**架构借鉴点 (Takeaways)**：")
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

    def _render_pm_guidance(self, pm_data: Any, app_name: str, category: str) -> str:
        """渲染应用层：产品经理产品方案指导"""
        forms = self._get_val(pm_data, "suitable_product_forms", default=[])
        autonomy = self._get_val(pm_data, "autonomy_level", default="L2 (协同辅助型)")
        interaction = self._get_val(pm_data, "interaction_design", default="")
        tradeoffs = self._get_val(pm_data, "cost_latency_tradeoffs", default="")
        must_haves = self._get_val(pm_data, "mvp_must_haves", default=[])
        nice_to_haves = self._get_val(pm_data, "mvp_nice_to_haves", default=[])
        anti_patterns = self._get_val(pm_data, "anti_patterns_to_avoid", default=[])

        lines = [
            "## 🎯 应用层：产品经理产品方案指导 (PM Solution Guidance)\n",
            "> **定位说明**：本节专为公司**产品经理 (PM)** 与**业务负责人**编写，将底层复杂的 Harness 架构拆解转化为具体的产品形态定义、交互信任机制及第一期 PRD 落地清单。\n",
        ]

        # 1. 适合的产品形态
        lines.append("### 1. 适配产品形态定位")
        if forms and isinstance(forms, list):
            for f in forms:
                lines.append(f"- **{f}**")
        else:
            lines.append(f"- 推荐作为针对 `{category}` 领域的独立工作台或深度嵌入式工作流插件。")
        lines.append("")

        # 2. 自主度与人机协同机制
        lines.append("### 2. 产品自主度评级与人机信任机制")
        lines.append(f"- **建议自主度评级**：`{autonomy}`")
        if interaction:
            lines.append(f"- **用户审查与信任设计**：\n  {interaction}")
        else:
            lines.append("- **用户审查与信任设计**：设计明确的人机确认交接点（如关键操作前置预览、差异高亮、一键撤销安全网），建立渐进式信任。")
        lines.append("")

        # 3. 体验与成本权衡
        lines.append("### 3. 响应体验与成本控制权衡 (Trade-offs)")
        if tradeoffs:
            lines.append(f"{tradeoffs}\n")
        else:
            lines.append("- **延迟与成本分级**：高频微操作采用低延迟自研/小模型，复杂任务流式生成并前置展示思考状态。\n")

        # 4. 公司自建 MVP 落地功能清单
        lines.append(f"### 4. 公司自建同类产品 MVP 功能清单 (PRD 参考)\n")
        lines.append("**P0 必须项 (不做产品无法上线)**：")
        if must_haves and isinstance(must_haves, list):
            for m in must_haves:
                lines.append(f"- [x] {m}")
        else:
            lines.append("- [x] 核心业务意图解析与结果展示")
            lines.append("- [x] 用户确认机制与基础报错提示")
        lines.append("")

        lines.append("**P1 增强项 (第二期迭代推荐)**：")
        if nice_to_haves and isinstance(nice_to_haves, list):
            for n in nice_to_haves:
                lines.append(f"- [ ] {n}")
        else:
            lines.append("- [ ] 复杂任务历史快照回滚")
            lines.append("- [ ] 多模型分级路由降本")
        lines.append("")

        lines.append("🚨 **产品经理避坑红线 (Do NOT do in V1)**：")
        if anti_patterns and isinstance(anti_patterns, list):
            for a in anti_patterns:
                lines.append(f"- ❌ {a}")
        else:
            lines.append("- ❌ 切忌在第一期做全自动无审查黑盒执行，极易引发用户安全恐慌。")
            lines.append("- ❌ 切忌盲目设计自由漫游多 Agent，优先固化为确定性 Pipeline。")
        lines.append("")

        return "\n".join(lines)

    def generate(self, analysis: HarnessAnalysis | Any) -> str:
        """生成标准化三层架构分析报告"""
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

        confidence = self._get_val(analysis, "confidence_overall", "confidence", default=None)
        confidence_stars = self._format_stars(confidence)

        # 架构流程图
        mermaid_diagram = self._get_val(analysis, "mermaid_diagram", default="")
        if not mermaid_diagram:
            mermaid_diagram = DiagramGenerator().generate(analysis)
        cleaned_diagram = mermaid_diagram.strip()
        if cleaned_diagram.startswith("```mermaid"):
            cleaned_diagram = cleaned_diagram[len("```mermaid"):]
        if cleaned_diagram.startswith("```"):
            cleaned_diagram = cleaned_diagram[len("```"):]
        if cleaned_diagram.endswith("```"):
            cleaned_diagram = cleaned_diagram[:-3]
        cleaned_diagram = cleaned_diagram.strip()

        architecture_summary = self._get_val(
            analysis, "architecture_summary", default="暂无架构摘要说明。"
        )
        pm_guidance = self._get_val(analysis, "pm_guidance", default=None)
        common_dimensions = self._get_val(analysis, "common_dimensions", default=[])
        specialized_dimensions = self._get_val(analysis, "specialized_dimensions", default=[])
        key_insights = self._get_val(analysis, "key_insights", default=[])
        raw_sources = self._get_val(analysis, "raw_sources", "evidence_sources", default=[])

        parts = []

        # 1. 标题
        parts.append(f"# {app_display_name} — Harness 架构深度分析报告\n")

        # 2. 概览
        parts.append("## 概览指标\n")
        parts.append(
            "| 所属品类 | 分析时间 | 信源覆盖数 | 架构置信度 |\n"
            "| :--- | :--- | :--- | :--- |\n"
            f"| {category} | {analyzed_at_str} | {source_count} | {confidence_stars} |\n"
        )

        # 3. 架构总览拓扑图
        parts.append("## 架构总览拓扑 (System Topology)\n")
        parts.append("```mermaid\n" + cleaned_diagram + "\n```\n")

        # 4. 架构核心摘要
        parts.append("## 核心架构摘要\n")
        parts.append(f"{architecture_summary}\n")

        # 5. 【核心交付层】应用层：产品经理产品方案指导
        parts.append(self._render_pm_guidance(pm_guidance, app_display_name, category))

        # 6. 【论据分析层】中间层：Harness 架构维度深度拆解
        parts.append("## 🔬 中间层：Harness 架构维度深度拆解 (Dimension Analysis)\n")
        parts.append("> **分析手法说明**：本节运用 9 大共性工程维度与 5 大品类专属穿透维度，对底层调度、上下文、沙箱与工具链进行技术解剖，作为上层产品决策的论据支撑。\n")

        # 共性维度
        parts.append("### 1. 基础共性维度拆解\n")
        if common_dimensions and isinstance(common_dimensions, list):
            for dim in common_dimensions:
                parts.append(self._render_dimension_item(dim))
        else:
            parts.append("*暂无共性维度分析数据。*\n")

        # 品类专属维度
        parts.append("### 2. 品类专属穿透维度拆解\n")
        if specialized_dimensions and isinstance(specialized_dimensions, list):
            for sdim in specialized_dimensions:
                parts.append(self._render_dimension_item(sdim))
        else:
            parts.append("*暂无品类专属分析数据。*\n")

        # 7. 核心架构洞察
        parts.append("## 💡 关键架构洞察 (Key Insights)\n")
        if isinstance(key_insights, list) and key_insights:
            for idx, insight in enumerate(key_insights, 1):
                parts.append(f"{idx}. {insight}")
            parts.append("")
        elif isinstance(key_insights, str) and key_insights.strip():
            for idx, insight in enumerate(key_insights.splitlines(), 1):
                if insight.strip():
                    parts.append(f"{idx}. {insight.strip().lstrip('0123456789.-*• ')}")
            parts.append("")

        # 8. 事实层：信源与逆向采集追踪
        parts.append("## 📑 事实层：信源与逆向采集追踪 (Fact Traceability)\n")
        if raw_sources and isinstance(raw_sources, list):
            parts.append("**主要参考信源与逆向资产**：")
            for src in raw_sources:
                parts.append(f"- {src}")
            parts.append("")

        parts.append(
            "> **分析与免责声明**：\n"
            "> 本分析报告基于全网公开逆向仓库、官方技术博客、开源代码及逆向提示词线索，"
            "结合大语言模型分析推断得出。报告聚焦于指导公司内部产品与架构建设，"
            "不代表对应产品官方的保密实现细节。\n"
        )

        return "\n".join(parts)
