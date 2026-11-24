"""专属分析器基类"""
from abc import ABC, abstractmethod
from harness_analyzer.models.dimension import SpecializedDimensionAnalysis


class BaseSpecializedAnalyzer(ABC):
    category: str = ""
    
    def __init__(self, llm):
        self.llm = llm
    
    @abstractmethod
    def get_dimension_prompts(self) -> dict[str, tuple[str, str]]:
        """返回维度名 -> (Chinese label, analysis prompt) 的映射"""
        ...
    
    def analyze(self, app_info: str, collected_data: str) -> list[SpecializedDimensionAnalysis]:
        """分析所有专属维度"""
        results = []
        system_prompt = f"你是一位资深 AI 产品架构分析师，正在深度分析一个{self.category}类 AI 应用的专属架构维度。基于提供的信息进行分析，如果信息不足请标注置信度较低。"
        
        for dim_key, (label, prompt_template) in self.get_dimension_prompts().items():
            full_prompt = f"## 应用信息\n{app_info}\n\n## 采集数据\n{collected_data}\n\n## 分析任务\n{prompt_template}\n\n请返回 JSON：{{\"summary\": \"一句话总结\", \"details\": \"详细分析\", \"key_decisions\": [\"关键设计决策1\", ...], \"takeaways\": [\"可借鉴点1\", ...], \"confidence\": 3}}"
            
            try:
                result = self.llm.structured_analyze(full_prompt, system_prompt)
                results.append(SpecializedDimensionAnalysis(
                    dimension=dim_key,
                    label=label,
                    summary=result.get("summary", ""),
                    details=result.get("details", ""),
                    key_decisions=result.get("key_decisions", []),
                    takeaways=result.get("takeaways", []),
                    confidence=result.get("confidence", 3),
                ))
            except Exception as e:
                results.append(SpecializedDimensionAnalysis(
                    dimension=dim_key, label=label,
                    summary=f"分析失败: {e}", confidence=1,
                ))
        return results
