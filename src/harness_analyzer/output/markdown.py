"""单个应用的 Harness 架构分析 Markdown 报告生成器
分为三层结构：
1. 概览与架构总览 (Mermaid)
2. 🎯 应用层：产品经理产品方案指导 (PM Solution Guidance - 产品形态、自主度、人机协同交互、MVP清单、避坑指南)
3. 🔬 中间层：Harness 维度深度分析报告 (Dimension Analysis - 9大共性维度 + 5大品类专属维度分析手法)
4. 📑 事实层：信源与逆向采集追踪 (Fact & Source Traceability)
"""
from datetime import datetime
from typing import Any
from urllib.parse import urlparse

try:
    from harness_analyzer.models.dimension import DIMENSION_WEIGHTS
    from harness_analyzer.models.harness import HarnessAnalysis, PMGuidance
except ImportError:
    DIMENSION_WEIGHTS = {}  # type: ignore
    class HarnessAnalysis:  # type: ignore
        pass
    class PMGuidance:  # type: ignore
        pass

from .diagram import DiagramGenerator


class MarkdownReportGenerator:
    """生成标准化 Markdown 架构分析报告（含每节 Mermaid 参考图与数据例证）"""

    @staticmethod
    def _format_stars(conf: Any) -> str:
        """将置信度转化为 5 星显示"""
        if conf is None:
            return "★★★☆☆"
        if isinstance(conf, float) and 0.0 <= conf <= 1.0:
            stars = round(conf * 5)
        elif isinstance(conf, (int, float)):
            stars = round(conf)
        else:
            return str(conf)
        stars = max(1, min(5, stars))
        return "★" * stars + "☆" * (5 - stars)

    @staticmethod
    def _get_val(obj: Any, *keys: str, default: Any = None) -> Any:
        """获取对象或字典字段值"""
        for k in keys:
            if isinstance(obj, dict) and k in obj and obj[k] is not None:
                return obj[k]
            if hasattr(obj, k) and getattr(obj, k) is not None:
                return getattr(obj, k)
        return default

    def _render_dimension_item(
        self,
        item: Any,
        category: str = "engineering",
        app_name: str = "AI 应用",
        diagram_gen: DiagramGenerator | None = None,
    ) -> str:
        """渲染单个维度的分析段落（含量化数据例证与机制参考图）"""
        diag = diagram_gen or DiagramGenerator()
        dim_key = str(self._get_val(item, "dimension", default=""))
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
        verbatim_quotes = self._get_val(item, "verbatim_quotes", default=[]) or []
        evidence_sources = self._get_val(item, "evidence_sources", default=[]) or []
        is_inferred = bool(self._get_val(item, "is_inferred", default=False))
        coupling = self._get_val(item, "coupling_level", default=None)
        if hasattr(coupling, "value"):
            coupling = coupling.value
        guard_status = self._get_val(item, "guard_status", default=None)
        if hasattr(guard_status, "value"):
            guard_status = guard_status.value
        guard_reason = self._get_val(item, "guard_reason", default="")

        coupling_labels = {
            "core": "🔴 核心强关联",
            "moderate": "🟡 中度关联",
            "loose": "⚪ 弱关联",
        }
        guard_labels = {
            "strict_verified": "✅ 严格实证通过",
            "partial_verified": "⚠️ 部分实证受限",
            "unverified_capped": "🚧 无实证推断封顶",
        }

        weight = DIMENSION_WEIGHTS.get(category, {}).get(dim_key)
        meta_badges = [f"**置信度**：{self._format_stars(confidence)}"]
        if weight is not None:
            meta_badges.append(f"**品类权重**：`{weight}/5`")
        if coupling:
            meta_badges.append(f"**联系程度**：{coupling_labels.get(str(coupling), str(coupling))}")
        if guard_status:
            meta_badges.append(f"**Guard 状态**：{guard_labels.get(str(guard_status), str(guard_status))}")

        lines = [
            f"### {label}\n",
            " | ".join(meta_badges) + "\n",
        ]

        if is_inferred:
            warn_msg = guard_reason or "缺乏一手采集原文直接佐证，本维度主要基于同类架构模式推断（置信度已封顶受限）。"
            lines.append(f"> ⚠️ *{warn_msg}*\n")
        elif guard_reason and guard_status == "partial_verified":
            lines.append(f"> ℹ️ *{guard_reason}*\n")

        if summary:
            lines.append(f"{summary}\n")

        if details:
            lines.append(f"{details}\n")

        # 机制参考 Mermaid 图
        dim_mermaid = diag.generate_dimension_diagram(item, category=category, app_name=app_name)
        if dim_mermaid:
            lines.append("**机制参考图 (Mermaid)**：")
            lines.append("```mermaid\n" + dim_mermaid + "\n```\n")

        # 量化数据例证
        q_count = len(verbatim_quotes) if isinstance(verbatim_quotes, list) else 0
        s_count = len(evidence_sources) if isinstance(evidence_sources, list) else 0
        d_count = len(key_decisions) if isinstance(key_decisions, list) else 0
        lines.append(
            f"**📊 数据例证 (Data Evidence)**：命中原文片段 `{q_count}` 条 ｜ 关联信源 `{s_count}` 篇 ｜ 提炼工程决策 `{d_count}` 项"
        )
        if isinstance(verbatim_quotes, list) and verbatim_quotes:
            lines.append("**原文佐证片段 (Verified Quotes)**：")
            for q in verbatim_quotes:
                clean_q = str(q).replace("\n", " ").strip()
                if clean_q:
                    lines.append(f'> "{clean_q}"')
        if isinstance(evidence_sources, list) and evidence_sources:
            lines.append(f"- **实证来源**：{' ； '.join(str(s) for s in evidence_sources[:3])}")
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

    def _render_intermediate_summary(
        self,
        artifact: Any,
        analysis: Any = None,
        diagram_gen: DiagramGenerator | None = None,
    ) -> str:
        """渲染中间产物摘要与真实用户评论洞察（含 Guard 漏斗 Mermaid 与量化数据例证）"""
        diag = diagram_gen or DiagramGenerator()
        guard_summary = self._get_val(artifact, "guard_summary", default={}) or {}
        core_facts = self._get_val(artifact, "core_verified_facts", default=[]) or []
        warnings = self._get_val(artifact, "inferred_warnings", default=[]) or []
        user_reviews = self._get_val(artifact, "user_reviews", default=None)
        search_coverage = self._get_val(artifact, "search_coverage", default=None)

        lines = [
            "## 📦 中间产物与权威用户真实评论 (Intermediate Artifact & User Reviews)\n",
            "> **转化依据说明**：本节汇总经分维度 Guard 校验后的技术事实、双语检索覆盖度与权威社区真实用户反馈，是上方『产品经理方案指导』的直接转化底座。\n",
        ]

        ev_mermaid = diag.generate_evidence_flow(artifact, analysis=analysis)
        if ev_mermaid:
            lines.append("### 实证验证漏斗参考图 (Mermaid)\n")
            lines.append("```mermaid\n" + ev_mermaid + "\n```\n")

        if guard_summary:
            strict_n = guard_summary.get("strict_verified", 0)
            partial_n = guard_summary.get("partial_verified", 0)
            capped_n = guard_summary.get("unverified_capped", 0)
            total_g = max(1, strict_n + partial_n + capped_n)
            lines.append(
                f"- **📊 分维度 Guard 量化统计**：✅ 严格实证 `{strict_n}` 项 (`{strict_n / total_g:.0%}`) ｜ ⚠️ 部分实证 `{partial_n}` 项 ｜ 🚧 推断封顶 `{capped_n}` 项"
            )
        if core_facts:
            lines.append(f"- **核心实证锚点数**：`{len(core_facts)}` 项（已作为 P0 产品方案主依据）")
        if warnings:
            lines.append(f"- **未实证警示数**：`{len(warnings)}` 项（已拦截防照搬）")
        lines.append("")

        if search_coverage:
            cov_score = self._get_val(search_coverage, "coverage_score", default=0.0)
            zh_hits = self._get_val(search_coverage, "zh_hits", default=0)
            en_hits = self._get_val(search_coverage, "en_hits", default=0)
            missing = self._get_val(search_coverage, "missing_angles", default=[]) or []
            refill_triggered = bool(self._get_val(search_coverage, "refill_triggered", default=False))
            blocked_sources = self._get_val(search_coverage, "blocked_sources", default=[]) or []
            cov_items = self._get_val(search_coverage, "items", default=[]) or []
            lines.append("### 双语多维度检索覆盖度评估\n")
            refill_tag = " ｜ 🔄 *已触发盲区自动补搜*" if refill_triggered else ""
            lines.append(
                f"- **综合覆盖度**：`{cov_score:.0%}` ｜ **提问语言命中**：`{zh_hits}` 条 ｜ **英语命中**：`{en_hits}` 条{refill_tag}"
            )
            if missing:
                lines.append(f"- **覆盖盲区提示**：`{', '.join(missing)}`")
            if blocked_sources:
                lines.append(f"- **🛡️ 反爬/限流礼貌退出记录**：共 `{len(blocked_sources)}` 处（已自动熔断保护，未强行绕过）：")
                for bs in blocked_sources[:6]:
                    b_url = self._get_val(bs, "url", default="")
                    b_reason = self._get_val(bs, "reason", default="")
                    lines.append(f"  - `{b_url}` (`{b_reason}`)")
            if cov_items:
                lines.append("")
                lines.append("| 语言 | 检索角度 | 检索词 | 命中数 | 深抓正文 | 采集字符 |")
                lines.append("| :--- | :--- | :--- | :---: | :---: | :---: |")
                for ci in cov_items:
                    q_lang = self._get_val(ci, "language", default="")
                    q_angle = self._get_val(ci, "angle", default="")
                    q_text = str(self._get_val(ci, "query", default="")).replace("|", "\\|")
                    q_hits = self._get_val(ci, "hits_count", default=0)
                    q_pages = self._get_val(ci, "pages_fetched", default=0)
                    q_chars = self._get_val(ci, "chars_collected", default=0)
                    lines.append(f"| {q_lang} | {q_angle} | `{q_text}` | {q_hits} | {q_pages} | {q_chars} |")
            lines.append("")

        if user_reviews:
            praises = self._get_val(user_reviews, "praises", default=[]) or []
            pains = self._get_val(user_reviews, "pain_points", default=[]) or []
            frictions = self._get_val(user_reviews, "trust_and_ux_friction", default=[]) or []
            quotes = self._get_val(user_reviews, "sample_quotes", default=[]) or []
            sources = self._get_val(user_reviews, "review_sources", default=[]) or []

            lines.append("### 权威社区真实用户评论拆解\n")
            if praises:
                lines.append("**👍 真实用户高频好评 (核心爽点)**：")
                for p in praises:
                    lines.append(f"- {p}")
                lines.append("")
            if pains:
                lines.append("**👎 真实用户高频吐槽 (痛点与短板)**：")
                for p in pains:
                    lines.append(f"- {p}")
                lines.append("")
            if frictions:
                lines.append("**⚡ 人机协作与信任摩擦点**：")
                for f in frictions:
                    lines.append(f"- {f}")
                lines.append("")
            if quotes:
                lines.append("**💬 代表性一线用户原话**：")
                for q in quotes:
                    lines.append(f'> "{q}"')
                lines.append("")
            if sources:
                lines.append("**评论采集来源**：" + " / ".join(sources) + "\n")

        return "\n".join(lines)

    def _render_pm_guidance(
        self,
        pm_data: Any,
        app_name: str,
        category: str,
        analysis: Any = None,
        diagram_gen: DiagramGenerator | None = None,
    ) -> str:
        """渲染应用层：产品经理产品方案指导（含决策流 Mermaid 与数据例证）"""
        diag = diagram_gen or DiagramGenerator()
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

        if analysis is not None:
            pm_flow = diag.generate_pm_flow(analysis, pm_data)
            if pm_flow:
                lines.append("### 0. PM 决策链路与风控边界参考图 (Mermaid)\n")
                lines.append("```mermaid\n" + pm_flow + "\n```\n")

            artifact = self._get_val(analysis, "intermediate_artifact", default=None)
            gs = self._get_val(artifact, "guard_summary", default={}) or {} if artifact else {}
            strict_n = gs.get("strict_verified", 0)
            warn_n = len(self._get_val(artifact, "inferred_warnings", default=[]) or []) if artifact else 0
            ur = self._get_val(artifact, "user_reviews", default=None) if artifact else None
            rev_cnt = len(self._get_val(ur, "review_sources", default=[]) or []) if ur else 0
            lines.append(
                f"**📊 方案支撑数据例证**：实证技术锚点 `{strict_n}` 项 ｜ 社区评论来源 `{rev_cnt}` 处 ｜ 待避坑未实证警示 `{warn_n}` 项 ｜ 建议 MVP P0 `{len(must_haves or [])}` 项 / P1 `{len(nice_to_haves or [])}` 项\n"
            )

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

        diag = DiagramGenerator()
        # 架构流程图
        mermaid_diagram = self._get_val(analysis, "mermaid_diagram", default="")
        if not mermaid_diagram:
            mermaid_diagram = diag.generate(analysis)
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
        intermediate_artifact = self._get_val(analysis, "intermediate_artifact", default=None)
        pm_guidance = self._get_val(analysis, "pm_guidance", default=None)
        common_dimensions = self._get_val(analysis, "common_dimensions", default=[])
        specialized_dimensions = self._get_val(analysis, "specialized_dimensions", default=[])
        matched_patterns = self._get_val(analysis, "matched_patterns", default=[])
        key_insights = self._get_val(analysis, "key_insights", default=[])
        raw_sources = self._get_val(analysis, "raw_sources", "evidence_sources", default=[])

        parts = []

        # 1. 标题
        parts.append(f"# {app_display_name} — Harness 架构深度分析报告\n")

        # 2. 概览指标 + 数据例证
        all_dims_overview = [*(common_dimensions or []), *(specialized_dimensions or [])]
        total_quotes = sum(
            len(self._get_val(d, "verbatim_quotes", default=[]) or [])
            for d in all_dims_overview
        )
        strict_dims = sum(
            1
            for d in all_dims_overview
            if str(getattr(self._get_val(d, "guard_status", default=""), "value", self._get_val(d, "guard_status", default=""))) == "strict_verified"
        )
        strict_ratio = f"{strict_dims}/{len(all_dims_overview)}" if all_dims_overview else "0/0"

        parts.append("## 概览指标\n")
        parts.append(
            "| 所属品类 | 分析时间 | 信源覆盖数 | 严格实证维度比 | 原文实证摘录数 | 架构置信度 |\n"
            "| :--- | :--- | :---: | :---: | :---: | :---: |\n"
            f"| {category} | {analyzed_at_str} | {source_count} | {strict_ratio} | {total_quotes} | {confidence_stars} |\n"
        )

        # 3. 架构总览拓扑图
        parts.append("## 架构总览拓扑 (System Topology)\n")
        parts.append("```mermaid\n" + cleaned_diagram + "\n```\n")

        # 4. 架构核心摘要
        parts.append("## 核心架构摘要\n")
        parts.append(f"{architecture_summary}\n")

        # 5. 【核心交付层】应用层：产品经理产品方案指导
        parts.append(self._render_pm_guidance(pm_guidance, app_display_name, category, analysis=analysis, diagram_gen=diag))

        # 6. 【转化桥梁】中间产物与权威用户真实评论洞察
        if intermediate_artifact is not None:
            parts.append(self._render_intermediate_summary(intermediate_artifact, analysis=analysis, diagram_gen=diag))

        # 6. 【论据分析层】中间层：Harness 架构维度深度拆解
        parts.append("## 🔬 中间层：Harness 架构维度深度拆解 (Dimension Analysis)\n")
        parts.append("> **分析手法说明**：本节运用 9 大共性工程维度与 5 大品类专属穿透维度，对底层调度、上下文、沙箱与工具链进行技术解剖，每个维度均附带独立 **Mermaid 机制参考图** 与 **量化数据例证**。\n")

        # 共性维度
        parts.append("### 1. 基础共性维度拆解\n")
        if common_dimensions and isinstance(common_dimensions, list):
            weights_map = DIMENSION_WEIGHTS.get(category, {})
            common_chart = diag.generate_dimensions_chart(
                common_dimensions,
                title=f"{app_display_name} 共性维度评分与权重对比",
                weights_map=weights_map or None,
            )
            if common_chart:
                parts.append("**共性维度评分与权重全景图 (Mermaid)**：")
                parts.append("```mermaid\n" + common_chart + "\n```\n")

            parts.append("| 维度 | 品类权重 | 置信度 | Guard 状态 | 原文引用数 | 依据来源数 |")
            parts.append("| :--- | :---: | :---: | :---: | :---: | :---: |")
            for d in common_dimensions:
                d_key = str(self._get_val(d, "dimension", default=""))
                d_lbl = self._get_val(d, "label", "dimension_label", default=d_key)
                d_w = weights_map.get(d_key, "-")
                d_c = self._format_stars(self._get_val(d, "confidence", default=3))
                d_g = getattr(self._get_val(d, "guard_status", default="strict_verified"), "value", self._get_val(d, "guard_status", default="strict_verified"))
                d_q = len(self._get_val(d, "verbatim_quotes", default=[]) or [])
                d_s = len(self._get_val(d, "evidence_sources", default=[]) or [])
                parts.append(f"| {d_lbl} | {d_w}/5 | {d_c} | `{d_g}` | {d_q} | {d_s} |")
            parts.append("")

            for dim in common_dimensions:
                parts.append(self._render_dimension_item(dim, category=category, app_name=app_display_name, diagram_gen=diag))
        else:
            parts.append("*暂无共性维度分析数据。*\n")

        # 品类专属维度
        parts.append("### 2. 品类专属穿透维度拆解\n")
        if specialized_dimensions and isinstance(specialized_dimensions, list):
            spec_chart = diag.generate_dimensions_chart(
                specialized_dimensions,
                title=f"{app_display_name} {category} 专属维度实证评分",
            )
            if spec_chart:
                parts.append("**专属维度实证置信度图 (Mermaid)**：")
                parts.append("```mermaid\n" + spec_chart + "\n```\n")

            parts.append("| 专属维度 | 置信度 | Guard 状态 | 原文引用数 | 依据来源数 |")
            parts.append("| :--- | :---: | :---: | :---: | :---: |")
            for sd in specialized_dimensions:
                sd_lbl = self._get_val(sd, "label", "dimension_label", "dimension", default="-")
                sd_c = self._format_stars(self._get_val(sd, "confidence", default=3))
                sd_g = getattr(self._get_val(sd, "guard_status", default="strict_verified"), "value", self._get_val(sd, "guard_status", default="strict_verified"))
                sd_q = len(self._get_val(sd, "verbatim_quotes", default=[]) or [])
                sd_s = len(self._get_val(sd, "evidence_sources", default=[]) or [])
                parts.append(f"| {sd_lbl} | {sd_c} | `{sd_g}` | {sd_q} | {sd_s} |")
            parts.append("")

            for sdim in specialized_dimensions:
                parts.append(self._render_dimension_item(sdim, category=category, app_name=app_display_name, diagram_gen=diag))
        else:
            parts.append("*暂无品类专属分析数据。*\n")

        # 6.5. 经典架构模式识别 (Architecture Patterns)
        if matched_patterns and isinstance(matched_patterns, list):
            parts.append("### 3. 识别到的架构模式 (Architecture Patterns)\n")
            pat_mermaid = diag.generate_patterns_diagram(analysis)
            if pat_mermaid:
                parts.append("**架构模式协同关系图 (Mermaid)**：")
                parts.append("```mermaid\n" + pat_mermaid + "\n```\n")

            parts.append("| 模式名称 | 落地说明 | 数据/源码证据要点 | 置信度 |")
            parts.append("| :--- | :--- | :--- | :---: |")
            for p in matched_patterns:
                pname = self._get_val(p, "pattern_name", default="-")
                pdesc = str(self._get_val(p, "description", default="-")).replace("\n", " ")
                pevid = self._get_val(p, "evidence", default=[])
                ev_str = "; ".join(str(e) for e in pevid[:2]) if isinstance(pevid, list) else str(pevid)
                pconf = self._format_stars(self._get_val(p, "confidence", default=3))
                parts.append(f"| `{pname}` | {pdesc} | {ev_str or '-'} | {pconf} |")
            parts.append("")

        # 7. 核心架构洞察
        parts.append("## 💡 关键架构洞察 (Key Insights)\n")
        parts.append(f"**📊 洞察实证锚点支撑**：共提炼 `{len(key_insights) if isinstance(key_insights, list) else 1}` 条核心结论，基于 `{strict_dims}` 个严格实证维度与 `{total_quotes}` 条原文片段。\n")
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
        src_mermaid = diag.generate_source_traceability_diagram(analysis, artifact=intermediate_artifact)
        if src_mermaid:
            parts.append("**信源通道分布参考图 (Mermaid)**：")
            parts.append("```mermaid\n" + src_mermaid + "\n```\n")

        if raw_sources and isinstance(raw_sources, list):
            gh_n = docs_n = rev_n = other_n = 0
            for src in raw_sources:
                u = str(src).lower()
                host = urlparse(u).netloc
                if "github.com" in host or "raw.githubusercontent.com" in host:
                    gh_n += 1
                elif any(k in u for k in ("docs.", "blog", "anthropic", "claude.com", "openai.com", "all-hands.dev")):
                    docs_n += 1
                elif any(k in host for k in ("news.ycombinator.com", "reddit.com", "g2.com", "producthunt.com", "zhihu.com", "v2ex.com", "juejin.cn")):
                    rev_n += 1
                else:
                    other_n += 1
            parts.append(
                f"**📊 信源分布数据统计**：总计 `{len(raw_sources)}` 条（GitHub `{gh_n}` ｜ 官方文档/博客 `{docs_n}` ｜ 社区评论/讨论 `{rev_n}` ｜ 其他技术文章 `{other_n}`）\n"
            )
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
