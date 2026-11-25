"""二阶段技术事实底座提炼器 (Fact Sheet Extractor)
在并发拆解 9+5 个维度之前，先将采集到的海量多源文本（GitHub 源码、技术博客、逆向线索、用户评论）
并发压缩提炼为结构化、带原文引证和来源 URL 的《客观技术事实清单 (Fact Sheet)》，
从而彻底解决串行慢、重复喂全文 Token 贵、上下文稀释与维度口径打架的问题。
"""
from __future__ import annotations

import asyncio
from typing import Sequence

from harness_analyzer.collectors.base import CollectedData
from .llm import LLMClient


class FactSheetExtractor:
    """并发分块提炼带原文佐证的技术事实底座"""

    def __init__(self, llm: LLMClient, max_chunk_chars: int = 11000, max_concurrency: int = 4):
        self.llm = llm
        self.max_chunk_chars = max_chunk_chars
        self.max_concurrency = max_concurrency

    def _chunk_sources(self, items: Sequence[CollectedData]) -> list[str]:
        """将采集数据按字符预算分块，尽量保持单个来源完整不被生硬截断"""
        chunks: list[str] = []
        current_parts: list[str] = []
        current_len = 0

        for item in items:
            block = (
                f"### 信源 [{item.source_type}] {item.title}\n"
                f"URL: {item.source_url}\n"
                f"{item.content[:4500]}\n"
            )
            if current_parts and current_len + len(block) > self.max_chunk_chars:
                chunks.append("\n---\n".join(current_parts))
                current_parts = [block]
                current_len = len(block)
            else:
                current_parts.append(block)
                current_len += len(block)

        if current_parts:
            chunks.append("\n---\n".join(current_parts))
        return chunks

    def _extract_chunk_sync(self, app_name: str, chunk_text: str) -> str:
        """提炼单个分块的核心架构事实与逐字原文摘录"""
        system_prompt = (
            "你是一位高度严谨的技术情报提炼专家。请把提供的原始资料浓缩为精炼的【技术事实卡片】，"
            "必须保留关键技术名词、模型名、工具协议、沙箱策略，并为每条关键事实附带一段原始资料中的逐字短句。"
        )
        prompt = (
            f"## 目标应用：{app_name}\n\n"
            f"## 原始采集片段\n{chunk_text}\n\n"
            "请输出紧凑的 Markdown 事实条目，每条格式：\n"
            "- [领域标签] 客观技术事实（附来源与逐字原文片段：\"...\"）\n"
            "只提取有依据的工程细节与真实用户反馈，过滤营销废话，控制在 1200 字以内。"
        )
        return self.llm.analyze(prompt, system_prompt)

    async def build_fact_sheet(self, app_name: str, items: Sequence[CollectedData]) -> str:
        """并发执行分块提炼并合并为统一的 Fact Sheet；语料较短时直接返回原文避免冗余调用"""
        if not items:
            return "无额外采集数据。"

        raw_combined = "\n\n---\n\n".join(
            f"[{c.source_type}] {c.title} ({c.source_url})\n{c.content[:4500]}"
            for c in items
        )
        if len(raw_combined) <= 6500:
            return raw_combined

        chunks = self._chunk_sources(items)
        sem = asyncio.Semaphore(self.max_concurrency)

        async def _run_chunk(chunk_text: str) -> str:
            async with sem:
                try:
                    return await asyncio.to_thread(self._extract_chunk_sync, app_name, chunk_text)
                except Exception:
                    return chunk_text[:2000]

        summaries = await asyncio.gather(*[_run_chunk(ch) for ch in chunks])
        return "## 提炼后的客观技术事实底座 (Fact Sheet)\n\n" + "\n\n---\n\n".join(summaries)
