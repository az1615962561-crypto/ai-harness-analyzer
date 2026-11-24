"""通用维度分析器"""
from harness_analyzer.models.dimension import (
    CommonDimension,
    DimensionAnalysis,
    DIMENSION_WEIGHTS,
)
from .llm import LLMClient


DIMENSION_PROMPTS: dict[str, str] = {
    "agent_orchestration": (
        "分析该 AI 应用的 Agent 编排架构：\n"
        "1) 是单 Agent 还是多 Agent 系统？\n"
        "2) 编排模式是什么（层级式/对等式/Swarm/管线式）？\n"
        "3) Agent 的规划策略是什么（ReAct/Plan-Execute/Tree-of-thought）？\n"
        "4) Agent 之间如何通信和协调？\n"
        "5) 是否支持动态创建/销毁 Agent？"
    ),
    "context_management": (
        "分析该 AI 应用的上下文管理策略：\n"
        "1) 上下文窗口管理方式（滑动窗口/摘要压缩/RAG 增强）？\n"
        "2) 长对话如何保持一致性？\n"
        "3) 多轮对话中的上下文传递机制？\n"
        "4) 上下文溢出时的降级策略？\n"
        "5) 是否支持跨会话的上下文持久化？"
    ),
    "tool_integration": (
        "分析该 AI 应用的工具集成架构：\n"
        "1) 工具注册与发现机制（静态配置/动态发现/MCP 协议）？\n"
        "2) 工具调用协议与接口标准？\n"
        "3) 工具执行的权限控制与安全策略？\n"
        "4) 工具调用结果的解析与错误处理？\n"
        "5) 工具编排与组合能力（串行/并行/条件调用）？"
    ),
    "memory_architecture": (
        "分析该 AI 应用的记忆架构：\n"
        "1) 短期记忆的实现方式（会话缓存/工作记忆区）？\n"
        "2) 长期记忆的存储机制（向量数据库/知识图谱/关系型存储）？\n"
        "3) 记忆的检索与召回策略？\n"
        "4) 记忆的更新与遗忘机制？\n"
        "5) 记忆在多 Agent 间的共享方式？"
    ),
    "evaluation_quality": (
        "分析该 AI 应用的评估与质量保障体系：\n"
        "1) 输出质量评估方式（自动评估/人工评估/LLM-as-Judge）？\n"
        "2) 是否有自动化测试与回归测试？\n"
        "3) 幻觉检测与事实核查机制？\n"
        "4) 用户反馈收集与模型改进闭环？\n"
        "5) 评估指标体系设计（准确率/延迟/用户满意度）？"
    ),
    "prompt_engineering": (
        "分析该 AI 应用的 Prompt 工程策略：\n"
        "1) Prompt 模板管理方式（硬编码/配置化/动态生成）？\n"
        "2) System Prompt 的设计哲学与结构？\n"
        "3) Few-shot 示例的选取与管理？\n"
        "4) Prompt 链的编排方式？\n"
        "5) Prompt 版本管理与 A/B 测试？"
    ),
    "safety_guardrails": (
        "分析该 AI 应用的安全护栏机制：\n"
        "1) 输入过滤与内容审核策略？\n"
        "2) 输出安全检查（有害内容/PII 泄露/注入攻击防护）？\n"
        "3) 权限边界与操作限制？\n"
        "4) 人机协同的审批流程（Human-in-the-loop）？\n"
        "5) 安全事件的监控与告警机制？"
    ),
    "ux_interaction": (
        "分析该 AI 应用的用户体验与交互设计：\n"
        "1) 交互模式（对话式/表单式/混合式/GUI+CLI）？\n"
        "2) 流式输出与实时反馈机制？\n"
        "3) 错误恢复与用户引导策略？\n"
        "4) 多模态交互支持（文本/图像/语音/代码）？\n"
        "5) 个性化与自适应交互能力？"
    ),
    "scalability_ops": (
        "分析该 AI 应用的可扩展性与运维设计：\n"
        "1) 系统架构的水平扩展能力？\n"
        "2) 多模型/多供应商的切换与负载均衡？\n"
        "3) 成本控制与资源优化策略？\n"
        "4) 监控、日志与可观测性体系？\n"
        "5) 部署模式（SaaS/On-Premise/混合部署）？"
    ),
}


class CommonDimensionExtractor:
    """通用维度分析提取器"""

    def __init__(self, llm: LLMClient):
        self.llm = llm

    def extract_dimension(
        self,
        dimension: CommonDimension,
        app_info: str,
        collected_data: str,
    ) -> DimensionAnalysis:
        """针对单个维度进行分析"""
        dim_value = dimension.value
        prompt_template = DIMENSION_PROMPTS.get(dim_value, "请分析该维度。")
        weight = DIMENSION_WEIGHTS.get(dimension, 3)

        depth_hint = "请进行深入、详尽的分析" if weight >= 4 else "请进行简要分析"

        system_prompt = (
            "你是一位资深 AI 产品架构分析师，擅长从公开信息中推断 AI 应用的技术架构。"
            "基于提供的信息进行分析，如果信息不足请标注置信度较低。"
        )

        full_prompt = (
            f"## 应用信息\n{app_info}\n\n"
            f"## 采集数据\n{collected_data}\n\n"
            f"## 分析任务\n{prompt_template}\n\n"
            f"{depth_hint}\n\n"
            '请返回 JSON：{"summary": "一句话总结", "details": "详细分析", '
            '"evidence": ["依据1", ...], "confidence": 3, '
            '"recommendations": ["建议1", ...]}'
        )

        try:
            result = self.llm.structured_analyze(full_prompt, system_prompt)
            return DimensionAnalysis(
                dimension=dimension,
                summary=result.get("summary", ""),
                details=result.get("details", ""),
                evidence=result.get("evidence", []),
                confidence=result.get("confidence", 3),
                recommendations=result.get("recommendations", []),
            )
        except Exception as e:
            return DimensionAnalysis(
                dimension=dimension,
                summary=f"分析失败: {e}",
                confidence=1,
            )

    def extract_all(
        self,
        app_info: str,
        collected_data: str,
        category: str = "engineering",
    ) -> list[DimensionAnalysis]:
        """分析所有通用维度

        weight >= 4 → 详细分析
        weight 2-3  → 简要分析
        weight 1    → 跳过
        """
        results: list[DimensionAnalysis] = []

        for dimension in CommonDimension:
            weight = DIMENSION_WEIGHTS.get(dimension, 3)
            if weight <= 1:
                continue  # 权重太低，跳过
            analysis = self.extract_dimension(dimension, app_info, collected_data)
            results.append(analysis)

        return results
