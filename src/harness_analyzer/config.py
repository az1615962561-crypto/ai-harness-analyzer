"""配置管理"""
import os
from pathlib import Path
from pydantic import BaseModel, Field, ConfigDict
from dotenv import load_dotenv

load_dotenv()


class Settings(BaseModel):
    """应用配置"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    llm_provider: str = Field(default_factory=lambda: os.getenv("HARNESS_LLM_PROVIDER", "gemini"))
    llm_model: str = Field(default_factory=lambda: os.getenv("HARNESS_LLM_MODEL", "gemini/gemini-2.0-flash"))
    api_key: str | None = Field(default_factory=lambda: os.getenv("GEMINI_API_KEY") or os.getenv("OPENAI_API_KEY") or os.getenv("ANTHROPIC_API_KEY"))
    cache_dir: Path = Field(default_factory=lambda: Path(os.getenv("HARNESS_CACHE_DIR", ".cache")))
    reports_dir: Path = Field(default_factory=lambda: Path(os.getenv("HARNESS_REPORTS_DIR", "reports")))


_settings: Settings | None = None


def get_settings() -> Settings:
    """获取配置单例"""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
