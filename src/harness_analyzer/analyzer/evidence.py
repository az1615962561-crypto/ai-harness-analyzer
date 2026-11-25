"""证据强制锚定与反幻觉门控 (Evidence-Gated Anti-Hallucination Verification)
核验 LLM 输出的逐字引用 (verbatim_quotes) 是否真实存在于采集语料中。
若无一手原文佐证，强制标记 is_inferred=True 并将 confidence 封顶为 2 星。
"""
from __future__ import annotations

import re
from typing import TypeVar

from harness_analyzer.models.dimension import DimensionAnalysis, SpecializedDimensionAnalysis

DimT = TypeVar("DimT", DimensionAnalysis, SpecializedDimensionAnalysis)


def _normalize_text(text: str) -> str:
    """空白折叠并转小写，用于鲁棒的原文子串匹配"""
    return re.sub(r"\s+", " ", text).strip().lower()


def _quote_matches_corpus(quote: str, normalized_corpus: str) -> bool:
    """判断单条引用是否在语料中真实存在"""
    norm_q = _normalize_text(quote)
    if len(norm_q) < 8:
        return False

    # 1. 直接子串精确匹配
    if norm_q in normalized_corpus:
        return True

    # 2. 去除标点后子串匹配（容忍轻微标点差异）
    alnum_q = re.sub(r"[^\w\u4e00-\u9fff ]+", "", norm_q).strip()
    alnum_corpus = re.sub(r"[^\w\u4e00-\u9fff ]+", "", normalized_corpus)
    if len(alnum_q) >= 8 and alnum_q in alnum_corpus:
        return True

    # 3. 词元重叠加权匹配（容忍少量省略号或换行格式差异）
    tokens = [tok for tok in re.findall(r"[a-z0-9_]{3,}|[\u4e00-\u9fff]{2,}", norm_q)]
    if len(tokens) >= 4:
        matched = sum(1 for tok in tokens if tok in normalized_corpus)
        if matched / len(tokens) >= 0.75:
            return True

    return False


def verify_dimension_evidence(dim_analysis: DimT, collected_corpus: str) -> DimT:
    """校验单个维度分析结果的原文证据，无有效证据则降级封顶置信度"""
    normalized_corpus = _normalize_text(collected_corpus or "")
    raw_quotes = getattr(dim_analysis, "verbatim_quotes", None) or []

    if not normalized_corpus:
        dim_analysis.verbatim_quotes = []
        dim_analysis.is_inferred = True
        dim_analysis.confidence = min(dim_analysis.confidence, 2)
        return dim_analysis

    verified_quotes = [
        q for q in raw_quotes if isinstance(q, str) and _quote_matches_corpus(q, normalized_corpus)
    ]

    dim_analysis.verbatim_quotes = verified_quotes
    if verified_quotes:
        dim_analysis.is_inferred = False
    else:
        dim_analysis.is_inferred = True
        dim_analysis.confidence = min(dim_analysis.confidence, 2)

    return dim_analysis


def verify_all_dimensions(
    common_dims: list[DimensionAnalysis],
    specialized_dims: list[SpecializedDimensionAnalysis],
    collected_corpus: str,
) -> tuple[list[DimensionAnalysis], list[SpecializedDimensionAnalysis]]:
    """批量校验共性与专属维度的证据锚定"""
    verified_common = [verify_dimension_evidence(d, collected_corpus) for d in common_dims]
    verified_spec = [verify_dimension_evidence(sd, collected_corpus) for sd in specialized_dims]
    return verified_common, verified_spec
