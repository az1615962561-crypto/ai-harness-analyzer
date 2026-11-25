"""中间产物合成器 (Intermediate Artifact Builder)
在第二步（双层维度剖析）与第三步（分维度 Guard 校验）之后生成结构化的中间产物，
并融合权威社区的真实用户评论洞察，作为第四步（应用层 PM 方案转化）的唯一权威输入。
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from harness_analyzer.collectors.base import CollectedData
from harness_analyzer.models.dimension import (
    CouplingLevel,
    DimensionAnalysis,
    GuardStatus,
    SpecializedDimensionAnalysis,
)
from harness_analyzer.models.harness import IntermediateArtifact, SearchCoverageReport, UserReviewSummary
from .llm import LLMClient


class IntermediateArtifactBuilder:
    """将已 Guard 校验的技术维度与真实用户评论合成为结构化中间产物"""

    def __init__(self, llm: LLMClient | None = None):
        self.llm = llm

    def summarize_user_reviews(self, app_name: str, review_items: Sequence[CollectedData]) -> UserReviewSummary | None:
        """从采集到的权威社区评论中提炼真实用户的爽点、痛点与信任摩擦"""
        if not review_items:
            return None

        review_sources = []
        for item in review_items:
            if item.source_url and item.source_url not in review_sources:
                review_sources.append(item.source_url)

        combined_reviews = "\n\n---\n\n".join(
            f"[{r.title}] ({r.source_url})\n{r.content[:2500]}" for r in review_items
        )

        if self.llm is not None:
            system_prompt = (
                "你是一位擅长做用户洞察与产品体验诊断的资深产品研究员。"
                "请严格根据提供的权威社区真实用户评论（HN/Reddit/G2/GitHub Issues/知乎），"
                "提取真实用户最认可的亮点、高频抱怨的痛点、以及与 AI 协作时的信任摩擦。"
            )
            prompt = (
                f"## 目标产品：{app_name}\n\n"
                f"## 真实用户评论语料\n{combined_reviews}\n\n"
                "请严格返回 JSON：\n"
                "{\n"
                '  "praises": ["用户真实好评点1", "好评点2"],\n'
                '  "pain_points": ["用户真实痛点/抱怨1", "痛点2"],\n'
                '  "trust_and_ux_friction": ["人机交互与信任摩擦点1", "摩擦点2"],\n'
                '  "sample_quotes": ["具有代表性的真实用户原话摘录1", "原话摘录2"]\n'
                "}"
            )
            try:
                data = self.llm.structured_analyze(prompt, system_prompt)
                return UserReviewSummary(
                    review_sources=review_sources,
                    praises=data.get("praises", []) or [],
                    pain_points=data.get("pain_points", []) or [],
                    trust_and_ux_friction=data.get("trust_and_ux_friction", []) or [],
                    sample_quotes=data.get("sample_quotes", []) or [],
                )
            except Exception:
                pass

        # 无 LLM 或解析失败时做确定性摘录兜底
        fallback_quotes = [
            f"{r.title}: {r.content.splitlines()[0][:180]}"
            for r in review_items[:4]
            if r.content.strip()
        ]
        return UserReviewSummary(
            review_sources=review_sources,
            praises=["已在权威社区收集到真实用户讨论样本，建议结合原话进一步审阅。"],
            pain_points=[],
            trust_and_ux_friction=[],
            sample_quotes=fallback_quotes,
        )

    def build(
        self,
        app_name: str,
        category: str,
        common_dims: Sequence[DimensionAnalysis],
        specialized_dims: Sequence[SpecializedDimensionAnalysis],
        review_items: Sequence[CollectedData] = (),
        user_reviews_override: UserReviewSummary | None = None,
        search_coverage: SearchCoverageReport | None = None,
    ) -> IntermediateArtifact:
        """构建第二步→第三步后的标准中间产物"""
        core_verified_facts: list[str] = []
        moderate_findings: list[str] = []
        inferred_warnings: list[str] = []
        guard_summary = {
            GuardStatus.STRICT_VERIFIED.value: 0,
            GuardStatus.PARTIAL_VERIFIED.value: 0,
            GuardStatus.UNVERIFIED_CAPPED.value: 0,
        }

        all_dims: list[DimensionAnalysis | SpecializedDimensionAnalysis] = [*specialized_dims, *common_dims]
        for dim in all_dims:
            g_status = dim.guard_status.value if hasattr(dim.guard_status, "value") else str(dim.guard_status)
            if g_status in guard_summary:
                guard_summary[g_status] += 1

            c_level = dim.coupling_level.value if hasattr(dim.coupling_level, "value") else str(dim.coupling_level)
            entry = f"[{dim.label}] {dim.summary} (置信度 {dim.confidence}★ | {c_level}/{g_status})"

            if dim.is_inferred or dim.guard_status == GuardStatus.UNVERIFIED_CAPPED:
                reason = dim.guard_reason or "缺乏直接原文佐证"
                inferred_warnings.append(f"[{dim.label}] {dim.summary} —— {reason}")
            elif dim.coupling_level == CouplingLevel.CORE:
                core_verified_facts.append(entry)
            else:
                moderate_findings.append(entry)

        user_reviews = user_reviews_override or self.summarize_user_reviews(app_name, review_items)

        return IntermediateArtifact(
            app_name=app_name,
            category=category,
            core_verified_facts=core_verified_facts,
            moderate_findings=moderate_findings,
            inferred_warnings=inferred_warnings,
            user_reviews=user_reviews,
            search_coverage=search_coverage,
            guard_summary=guard_summary,
        )

    @staticmethod
    def save_to_disk(artifact: IntermediateArtifact, reports_dir: Path, app_name: str) -> Path:
        """将中间产物持久化保存至 reports/<app_name>.intermediate.json，便于审计与二次转化"""
        reports_dir.mkdir(parents=True, exist_ok=True)
        out_path = reports_dir / f"{app_name}.intermediate.json"
        out_path.write_text(artifact.model_dump_json(indent=2), encoding="utf-8")
        return out_path
