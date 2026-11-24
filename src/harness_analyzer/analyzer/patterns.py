"""模式匹配器"""
from __future__ import annotations

from .llm import LLMClient


class PatternMatcher:
    """基于 LLM 的架构模式匹配器"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def match(self, app_info: str, collected_data: str) -> list[dict]:
        """识别应用中使用的已知架构模式

        Returns:
            list[dict]: 每个 dict 包含 pattern_name, description, evidence, confidence
        """
        system_prompt = (
            "你是一位资深 AI 架构分析师。请识别该 AI 应用中所使用的已知"
            "架构模式和设计模式，包括但不限于：RAG、Agent Loop、"
            "Tool-use、Chain-of-Thought、ReAct、Map-Reduce、"
            "Human-in-the-loop、Guardrails、Router/Dispatcher 等。"
        )

        full_prompt = (
            f"## 应用信息\n{app_info}\n\n"
            f"## 采集数据\n{collected_data}\n\n"
            "## 分析任务\n"
            "请识别该应用中使用的所有架构模式，并返回 JSON 数组：\n"
            '[{{"pattern_name": "模式名", "description": "模式描述", '
            '"evidence": ["证据1", ...], "confidence": 4}}]'
        )

        try:
            result = self.llm.structured_analyze(full_prompt, system_prompt)
            if isinstance(result, list):
                return result
            # In case LLM wraps in an object
            if isinstance(result, dict) and "patterns" in result:
                return result["patterns"]
            return [result]
        except Exception:
            return []
