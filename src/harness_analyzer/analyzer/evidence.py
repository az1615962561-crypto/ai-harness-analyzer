"""按联系程度划分的分维度独立 Guard (Coupling-Tiered Individual Anti-Hallucination Guard)
第二步输出在第三步进行「分别 Guard」：根据维度与目标品类的联系程度（CORE / MODERATE / LOOSE），
对每个维度施加差异化的原文引用门控与置信度封顶约束。
"""
from __future__ import annotations

import re
from typing import TypeVar

from harness_analyzer.models.dimension import (
    CouplingLevel,
    DIMENSION_WEIGHTS,
    DimensionAnalysis,
    GuardStatus,
    SpecializedDimensionAnalysis,
)

DimT = TypeVar("DimT", DimensionAnalysis, SpecializedDimensionAnalysis)


def _normalize_text(text: str) -> str:
    """空白折叠并转小写，用于鲁棒的原文子串匹配"""
    return re.sub(r"\s+", " ", text).strip().lower()


def _quote_matches_corpus(quote: str, normalized_corpus: str) -> bool:
    """判断单条引用是否在语料中真实存在"""
    if not normalized_corpus:
        return False
    norm_q = _normalize_text(quote)
    if len(norm_q) < 8:
        return False

    if norm_q in normalized_corpus:
        return True

    alnum_q = re.sub(r"[^\w\u4e00-\u9fff ]+", "", norm_q).strip()
    alnum_corpus = re.sub(r"[^\w\u4e00-\u9fff ]+", "", normalized_corpus)
    if len(alnum_q) >= 8 and alnum_q in alnum_corpus:
        return True

    tokens = [tok for tok in re.findall(r"[a-z0-9_]{3,}|[\u4e00-\u9fff]{2,}", norm_q)]
    if len(tokens) >= 4:
        matched = sum(1 for tok in tokens if tok in normalized_corpus)
        if matched / len(tokens) >= 0.75:
            return True

    return False


def resolve_coupling_level(dim_analysis: DimT, category: str = "engineering") -> CouplingLevel:
    """根据所属品类确定单个维度的联系程度（CORE / MODERATE / LOOSE）"""
    if isinstance(dim_analysis, SpecializedDimensionAnalysis):
        return CouplingLevel.CORE

    cat_weights = DIMENSION_WEIGHTS.get(category, {})
    weight = cat_weights.get(dim_analysis.dimension, 3)
    if weight >= 5:
        return CouplingLevel.CORE
    if weight >= 3:
        return CouplingLevel.MODERATE
    return CouplingLevel.LOOSE


def verify_dimension_evidence(
    dim_analysis: DimT,
    collected_corpus: str,
    category: str = "engineering",
    primary_corpus: str | None = None,
) -> DimT:
    """对单个维度执行按联系程度分级的独立 Guard 校验

    分级规则：
    - CORE (核心强关联：专属维度或权重=5)：
      严格校验。若提供 primary_corpus（源码/逆向/官方深文），需至少 1 条命中一手源或 >=2 条命中总语料才放行高置信度；
      仅有 1 条二手碎片引证时降为 PARTIAL_VERIFIED（置信度封顶 3 星）；
      无任何实证时严格封顶 1 星（防 PM 拿核心臆测写进 P0）。
    - MODERATE (中度关联：权重 3~4)：
      标准校验。命中 >=1 条原文即通过；无实证则封顶 2 星并标为推测。
    - LOOSE (弱关联：权重 1~2)：
      参考校验。无实证封顶 2 星并提示 PM 首期无需重点投入。
    """
    coupling = resolve_coupling_level(dim_analysis, category=category)
    dim_analysis.coupling_level = coupling

    norm_corpus = _normalize_text(collected_corpus or "")
    norm_primary = _normalize_text(primary_corpus) if primary_corpus is not None else None
    raw_quotes = getattr(dim_analysis, "verbatim_quotes", None) or []

    if not norm_corpus:
        dim_analysis.verbatim_quotes = []
        dim_analysis.is_inferred = True
        dim_analysis.guard_status = GuardStatus.UNVERIFIED_CAPPED
        if coupling == CouplingLevel.CORE:
            dim_analysis.confidence = min(dim_analysis.confidence, 1)
            dim_analysis.guard_reason = "核心强关联维度无采集语料支撑，置信度已严格封顶 1 星。"
        else:
            dim_analysis.confidence = min(dim_analysis.confidence, 2)
            dim_analysis.guard_reason = "缺乏采集语料支撑，按常规模式推断（封顶 2 星）。"
        return dim_analysis

    verified_quotes = [
        q for q in raw_quotes if isinstance(q, str) and _quote_matches_corpus(q, norm_corpus)
    ]
    dim_analysis.verbatim_quotes = verified_quotes

    if not verified_quotes:
        dim_analysis.is_inferred = True
        dim_analysis.guard_status = GuardStatus.UNVERIFIED_CAPPED
        if coupling == CouplingLevel.CORE:
            dim_analysis.confidence = min(dim_analysis.confidence, 1)
            dim_analysis.guard_reason = "🔴 核心强关联维度缺乏原文实证（或引用未命中原文），置信度已严格封顶 1 星，PM 切勿直接作为 P0 硬依据。"
        elif coupling == CouplingLevel.MODERATE:
            dim_analysis.confidence = min(dim_analysis.confidence, 2)
            dim_analysis.guard_reason = "🟡 中度关联维度缺乏直接原文引证，已标记为模式推断（封顶 2 星）。"
        else:
            dim_analysis.confidence = min(dim_analysis.confidence, 2)
            dim_analysis.guard_reason = "⚪ 弱关联维度无直接引证，仅作背景参考，首期无需重点投入。"
        return dim_analysis

    # 存在有效原文引证，按联系程度分别判定校验等级
    dim_analysis.is_inferred = False
    if coupling == CouplingLevel.CORE:
        primary_hits = (
            [q for q in verified_quotes if _quote_matches_corpus(q, norm_primary)]
            if norm_primary is not None
            else verified_quotes
        )
        if primary_hits or len(verified_quotes) >= 2:
            dim_analysis.guard_status = GuardStatus.STRICT_VERIFIED
            dim_analysis.guard_reason = f"核心维度已通过严格实证校验（命中 {len(verified_quotes)} 条原文证据）。"
        else:
            dim_analysis.guard_status = GuardStatus.PARTIAL_VERIFIED
            dim_analysis.confidence = min(dim_analysis.confidence, 3)
            dim_analysis.guard_reason = "核心维度仅有单条二手/评论引证，尚缺源码或官方文档实锤（置信度封顶 3 星）。"
    elif coupling == CouplingLevel.MODERATE:
        dim_analysis.guard_status = GuardStatus.STRICT_VERIFIED
        dim_analysis.guard_reason = f"中度关联维度已通过原文引证校验（{len(verified_quotes)} 条）。"
    else:
        dim_analysis.guard_status = GuardStatus.STRICT_VERIFIED
        dim_analysis.guard_reason = f"弱关联维度已核验（{len(verified_quotes)} 条），建议作扩展参考。"

    return dim_analysis


def verify_all_dimensions(
    common_dims: list[DimensionAnalysis],
    specialized_dims: list[SpecializedDimensionAnalysis],
    collected_corpus: str,
    category: str = "engineering",
    primary_corpus: str | None = None,
) -> tuple[list[DimensionAnalysis], list[SpecializedDimensionAnalysis]]:
    """对第二步输出的每个共性与专属维度按联系程度逐一独立 Guard"""
    verified_common = [
        verify_dimension_evidence(d, collected_corpus, category=category, primary_corpus=primary_corpus)
        for d in common_dims
    ]
    verified_spec = [
        verify_dimension_evidence(sd, collected_corpus, category=category, primary_corpus=primary_corpus)
        for sd in specialized_dims
    ]
    return verified_common, verified_spec
