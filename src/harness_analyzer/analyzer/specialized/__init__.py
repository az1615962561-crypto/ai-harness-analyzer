from .base import BaseSpecializedAnalyzer
from .engineering import EngineeringAnalyzer
from .data_analysis import DataAnalyzer
from .knowledge import KnowledgeAnalyzer
from .creative import CreativeAnalyzer
from .automation import AutomationAnalyzer

_ANALYZERS = {
    "engineering": EngineeringAnalyzer,
    "data": DataAnalyzer,
    "knowledge": KnowledgeAnalyzer,
    "creative": CreativeAnalyzer,
    "automation": AutomationAnalyzer,
}

def get_specialized_analyzer(category: str, llm=None) -> BaseSpecializedAnalyzer:
    cls = _ANALYZERS.get(category)
    if cls is None:
        raise ValueError(f"Unknown category: {category}")
    return cls(llm)
