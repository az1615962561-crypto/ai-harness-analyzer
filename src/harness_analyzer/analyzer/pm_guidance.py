"""应用层：产品经理方案指导生成器 (PM Guidance Extractor)
将中间层 9+5 维度的底层技术拆解，提炼转化为面向产品经理与业务负责人的产品形态、交互信任机制、成本权衡与 PRD MVP 清单。
"""
from harness_analyzer.models.dimension import DimensionAnalysis, SpecializedDimensionAnalysis
from harness_analyzer.models.harness import PMGuidance
from .llm import LLMClient


class PMGuidanceExtractor:
    """基于技术维度分析结果，生成产品经理视角的落地指导方案"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract(
        self,
        app_info: str,
        category: str,
        common_dims: list[DimensionAnalysis],
        specialized_dims: list[SpecializedDimensionAnalysis],
    ) -> PMGuidance:
        """综合维度拆解结论，输出产品经理方案指导"""
        dim_summary_lines = []
        for d in common_dims:
            dim_summary_lines.append(f"- [{d.label}] {d.summary}")
        for sd in specialized_dims:
            dim_summary_lines.append(f"- [{sd.label}] {sd.summary}")

        dims_text = "\n".join(dim_summary_lines) or "暂无维度摘要"

        system_prompt = (
            "你是一位既懂 AI 底层 Harness 工程又精通商业产品落地的资深 AI 产品总监。"
            "请把下面的技术架构拆解翻译为产品经理可直接写入 PRD 的方案指导。"
        )

        prompt = (
            f"## 目标对标应用信息\n{app_info}\n\n"
            f"## 所属品类\n{category}\n\n"
            f"## 中间层技术维度分析摘要\n{dims_text}\n\n"
            "## 任务\n"
            "请从产品经理视角给出落地指导，严格返回以下 JSON 结构：\n"
            "{\n"
            '  "suitable_product_forms": ["最适合的产品形态1", "形态2"],\n'
            '  "autonomy_level": "L1~L4 自主度评级及一句话定位",\n'
            '  "interaction_design": "人机协同与用户信任建立机制设计（包含审查粒度、预览方式、安全撤销网）",\n'
            '  "cost_latency_tradeoffs": "响应延迟与 Token 成本的体验权衡策略",\n'
            '  "mvp_must_haves": ["第一期 P0 必须功能1", "功能2", "功能3"],\n'
            '  "mvp_nice_to_haves": ["第二期 P1 增强功能1", "功能2"],\n'
            '  "anti_patterns_to_avoid": ["产品经理需避开的坑1", "坑2"]\n'
            "}"
        )

        try:
            data = self.llm.structured_analyze(prompt, system_prompt)
            return PMGuidance(
                suitable_product_forms=data.get("suitable_product_forms", []) or [],
                autonomy_level=data.get("autonomy_level", "L2 (协同辅助型)"),
                interaction_design=data.get("interaction_design", ""),
                cost_latency_tradeoffs=data.get("cost_latency_tradeoffs", ""),
                mvp_must_haves=data.get("mvp_must_haves", []) or [],
                mvp_nice_to_haves=data.get("mvp_nice_to_haves", []) or [],
                anti_patterns_to_avoid=data.get("anti_patterns_to_avoid", []) or [],
            )
        except Exception:
            return self._fallback_guidance(category)

    @staticmethod
    def _fallback_guidance(category: str) -> PMGuidance:
        """LLM 解析失败时的分类兜底建议"""
        return PMGuidance(
            suitable_product_forms=[f"面向 {category} 场景的嵌入式协同工作台或对话助手"],
            autonomy_level="L2 (人在回路协同型)",
            interaction_design="为关键操作提供前置预览、结构化确认和一键撤销机制，降低用户心理门槛。",
            cost_latency_tradeoffs="高频轻量任务路由至高速小模型，复杂推理异步流式返回以兼顾体验与成本。",
            mvp_must_haves=["核心业务流程端到端闭环", "结果前置确认与错误处理", "用户反馈收集入口"],
            mvp_nice_to_haves=["多模型分级路由降本", "历史版本快照回滚"],
            anti_patterns_to_avoid=["首期切忌盲目追求全自动黑盒托管", "避免未做上下文剪枝直接全量塞入大模型"],
        )
