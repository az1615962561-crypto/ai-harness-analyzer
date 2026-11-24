"""LLM 客户端封装"""
import json
import litellm
from harness_analyzer.config import get_settings


class LLMClient:
    """统一 LLM 调用客户端，支持 Gemini/Claude/OpenAI"""
    
    def __init__(self):
        settings = get_settings()
        self.model = settings.llm_model
        if settings.api_key:
            # litellm uses env vars, but we can also set directly
            import os
            if "gemini" in self.model.lower():
                os.environ.setdefault("GEMINI_API_KEY", settings.api_key)
            elif "claude" in self.model.lower() or "anthropic" in self.model.lower():
                os.environ.setdefault("ANTHROPIC_API_KEY", settings.api_key)
            else:
                os.environ.setdefault("OPENAI_API_KEY", settings.api_key)
    
    def analyze(self, prompt: str, system_prompt: str | None = None) -> str:
        """调用 LLM 进行分析"""
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})
        
        try:
            response = litellm.completion(model=self.model, messages=messages, temperature=0.3)
            return response.choices[0].message.content
        except Exception as e:
            raise RuntimeError(f"LLM 调用失败: {e}") from e
    
    def structured_analyze(self, prompt: str, system_prompt: str | None = None) -> dict:
        """调用 LLM 并解析 JSON 输出"""
        full_prompt = prompt + "\n\n请以 JSON 格式返回结果，不要包含 markdown 代码块标记。"
        result = self.analyze(full_prompt, system_prompt)
        # Try to extract JSON from response
        result = result.strip()
        if result.startswith("```"):
            lines = result.split("\n")
            result = "\n".join(lines[1:-1])
        return json.loads(result)
