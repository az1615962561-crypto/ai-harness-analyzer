"""专属分析器基类（支持同步与并发异步分析）"""
import asyncio
from abc import ABC, abstractmethod
from harness_analyzer.models.dimension import SpecializedDimensionAnalysis
from harness_analyzer.logging_utils import get_logger

logger = get_logger(__name__)


class BaseSpecializedAnalyzer(ABC):
    category: str = ""

    def __init__(self, llm):
        self.llm = llm

    @abstractmethod
    def get_dimension_prompts(self) -> dict[str, tuple[str, str]]:
        """返回维度名 -> (Chinese label, analysis prompt) 的映射"""
        ...

    def _analyze_one(
        self,
        dim_key: str,
        label: str,
        prompt_template: str,
        app_info: str,
        collected_data: str,
        system_prompt: str,
    ) -> SpecializedDimensionAnalysis:
        full_prompt = (
            f"## 应用信息\n{app_info}\n\n## 采集数据\n{collected_data}\n\n"
            f"## 分析任务\n{prompt_template}\n\n"
            '请返回 JSON：{"summary": "一句话总结", "details": "详细分析", '
            '"key_decisions": ["关键设计决策1", ...], "takeaways": ["可借鉴点1", ...], '
            '"verbatim_quotes": ["直接摘自采集数据的原文短句或代码片段(无证据则留空[])"], '
            '"evidence_sources": ["来源URL或标题"], "confidence": 3}'
        )
        try:
            result = self.llm.structured_analyze(full_prompt, system_prompt)
            return SpecializedDimensionAnalysis(
                dimension=dim_key,
                label=label,
                summary=result.get("summary", ""),
                details=result.get("details", ""),
                key_decisions=result.get("key_decisions", []) or [],
                takeaways=result.get("takeaways", []) or [],
                confidence=max(1, min(5, int(result.get("confidence", 3)))),
                evidence_sources=result.get("evidence_sources", []) or [],
                verbatim_quotes=result.get("verbatim_quotes", []) or [],
            )
        except Exception as e:
            logger.warning("Specialized dimension '%s' analysis failed: %s", dim_key, e)
            return SpecializedDimensionAnalysis(
                dimension=dim_key, label=label,
                summary=f"分析失败: {e}", confidence=1, is_inferred=True,
            )

    def _build_system_prompt(self) -> str:
        return (
            f"你是一位资深 AI 产品架构分析师，正在深度分析一个{self.category}类 AI 应用的专属架构维度。"
            "必须严格基于提供的采集数据并附带逐字原文引用 (verbatim_quotes)；"
            "若采集数据中缺乏该维度的直接事实，必须将 verbatim_quotes 置为 [] 且 confidence 不超过 2，严禁臆造。"
        )

    def analyze(self, app_info: str, collected_data: str) -> list[SpecializedDimensionAnalysis]:
        """串行分析所有专属维度"""
        system_prompt = self._build_system_prompt()
        return [
            self._analyze_one(dim_key, label, prompt_template, app_info, collected_data, system_prompt)
            for dim_key, (label, prompt_template) in self.get_dimension_prompts().items()
        ]

    async def aanalyze(
        self, app_info: str, collected_data: str, max_concurrency: int = 5
    ) -> list[SpecializedDimensionAnalysis]:
        """并发异步分析所有专属维度"""
        system_prompt = self._build_system_prompt()
        sem = asyncio.Semaphore(max_concurrency)

        async def _run_one(dim_key: str, label: str, prompt_template: str) -> SpecializedDimensionAnalysis:
            async with sem:
                return await asyncio.to_thread(
                    self._analyze_one, dim_key, label, prompt_template, app_info, collected_data, system_prompt
                )

        return list(
            await asyncio.gather(
                *[
                    _run_one(dim_key, label, prompt_template)
                    for dim_key, (label, prompt_template) in self.get_dimension_prompts().items()
                ]
            )
        )
