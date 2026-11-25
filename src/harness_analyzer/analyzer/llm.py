"""LLM 客户端封装"""
import json
import os
import re
from typing import Any

# 避免无外网/沙箱环境下 litellm 启动时反复拉取远程价格表并打印警告
os.environ.setdefault("LITELLM_LOCAL_MODEL_COST_MAP", "True")

import litellm
from harness_analyzer.config import get_settings


class LLMClient:
    """统一 LLM 调用客户端，支持 Gemini/Claude/OpenAI"""

    def __init__(self, model: str | None = None, api_key: str | None = None):
        settings = get_settings()
        self.model = model or settings.llm_model
        key = api_key or settings.api_key
        if key:
            lower_model = self.model.lower()
            if "gemini" in lower_model:
                os.environ.setdefault("GEMINI_API_KEY", key)
            elif "claude" in lower_model or "anthropic" in lower_model:
                os.environ.setdefault("ANTHROPIC_API_KEY", key)
            else:
                os.environ.setdefault("OPENAI_API_KEY", key)

    @staticmethod
    def extract_json(raw_text: str) -> Any:
        """从 LLM 响应文本中稳健提取 JSON（支持 Markdown 代码块与前后缀文本）"""
        text = raw_text.strip()

        # 1. 优先尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 2. 提取 ```json ... ``` 或 ``` ... ``` 代码块内容
        fence_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?\s*```", text, re.DOTALL | re.IGNORECASE)
        if fence_match:
            candidate = fence_match.group(1).strip()
            try:
                return json.loads(candidate)
            except json.JSONDecodeError:
                text = candidate

        # 3. 兜底提取最外层的 {...} 或 [...]
        obj_match = re.search(r"(\{.*\}|\[.*\])", text, re.DOTALL)
        if obj_match:
            return json.loads(obj_match.group(1))

        raise json.JSONDecodeError("无法从响应中解析有效 JSON", raw_text, 0)

    def analyze(self, prompt: str, system_prompt: str | None = None) -> str:
        """调用 LLM 进行分析"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        try:
            response = litellm.completion(model=self.model, messages=messages, temperature=0.3)
            return response.choices[0].message.content or ""
        except Exception as e:
            raise RuntimeError(f"LLM 调用失败: {e}") from e

    def structured_analyze(self, prompt: str, system_prompt: str | None = None) -> Any:
        """调用 LLM 并解析 JSON 输出"""
        full_prompt = prompt + "\n\n请严格以合法 JSON 格式返回结果，不要包含任何多余的解释文字。"
        result = self.analyze(full_prompt, system_prompt)
        return self.extract_json(result)
