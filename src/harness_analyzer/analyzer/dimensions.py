"""通用维度分析器（9 大共性 Harness 维度）"""
from harness_analyzer.models.dimension import (
    CommonDimension,
    DimensionAnalysis,
    DIMENSION_WEIGHTS,
)
from .llm import LLMClient


DIMENSION_PROMPTS: dict[str, str] = {
    CommonDimension.AGENT_ORCHESTRATION.value: (
        "分析该 AI 应用的 Agent 编排架构：\n"
        "1) 是单 Agent、Pipeline 还是多 Agent 协作系统？\n"
        "2) 编排模式是什么（层级式 Planner-Worker / 对等式 / Swarm / 状态机）？\n"
        "3) Agent 的规划与反思策略是什么（ReAct / Plan-Execute / Tree-of-Thought）？\n"
        "4) Agent 之间如何通信、共享状态与交接任务？\n"
        "5) 是否支持动态创建/销毁子 Agent 或并行执行？"
    ),
    CommonDimension.MODEL_ROUTING.value: (
        "分析该 AI 应用的模型路由与调度策略：\n"
        "1) 底层依赖哪些大模型（旗舰模型/自研小模型/多模态模型）？\n"
        "2) 是否存在按任务复杂度、延迟或成本分级的动态路由？\n"
        "3) 是否支持多模型供应商切换、Cascade 降级容灾或 BYOK？\n"
        "4) 如何平衡推理质量、首字延迟 (TTFT) 与 Token 成本？\n"
        "5) 是否使用 Speculative Decoding、Prompt Caching 等推理加速手段？"
    ),
    CommonDimension.TOOL_CHAIN.value: (
        "分析该 AI 应用的工具调用链 (Tool Chain) 设计：\n"
        "1) 提供哪些核心工具（文件读写/终端/LSP/SQL 执行/浏览器/检索等）？\n"
        "2) 工具注册与协议标准（Function Calling / MCP / OpenAPI）？\n"
        "3) 工具输出如何做切片、截断与结构化清洗，避免撑爆上下文？\n"
        "4) 工具执行失败后的错误回传与自愈重试机制？\n"
        "5) 是否支持工具并发调用或条件编排？"
    ),
    CommonDimension.PROMPT_ENGINEERING.value: (
        "分析该 AI 应用的 Prompt 工程与行为控制策略：\n"
        "1) System Prompt 的结构设计哲学与指令分层？\n"
        "2) 如何实现项目级/用户级规则注入（如 .cursorrules / CLAUDE.md / 业务字典）？\n"
        "3) 输出格式约束协议（如 SEARCH/REPLACE Diff 块、XML/JSON Schema）？\n"
        "4) Few-Shot 示例的动态选取与注入策略？\n"
        "5) 如何防止模型产生废话或指令漂移？"
    ),
    CommonDimension.CONTEXT_ENGINEERING.value: (
        "分析该 AI 应用的上下文工程 (Context Engineering) 架构：\n"
        "1) 上下文是如何动态构建和排序的？\n"
        "2) 索引与检索策略（AST 代码解析/LSP 符号引用/RAG 混合检索/Schema 剪枝）？\n"
        "3) 上下文窗口压缩、滑动窗口与摘要策略？\n"
        "4) 增量同步与本地缓存机制（如 Merkle Tree 哈希比对）？\n"
        "5) 跨轮次、跨会话的长期记忆如何持久化与召回？"
    ),
    CommonDimension.DATA_FLOW_STATE.value: (
        "分析该 AI 应用的数据流与状态管理架构：\n"
        "1) 用户请求到模型推理再到前端渲染的端到端数据流向？\n"
        "2) 流式传输机制（SSE / WebSocket / IPC）与增量更新协议？\n"
        "3) 会话状态与工作区状态机如何持久化？\n"
        "4) 是否有 Checkpoint / 快照机制支持暂停、恢复与撤销？\n"
        "5) 多步任务或离线异步任务的断点续跑设计？"
    ),
    CommonDimension.SECURITY_SANDBOX.value: (
        "分析该 AI 应用的安全边界与沙箱隔离机制：\n"
        "1) 危险操作（Shell 执行/文件修改/SQL 查询）在何处、以何种方式隔离（容器/VM/WASM/权限白名单）？\n"
        "2) 输入输出安全检查（Prompt 注入防护 / SQL AST 静态校验 / PII 脱敏）？\n"
        "3) 行级/列级数据权限或文件系统访问边界控制？\n"
        "4) 资源配额限制（超时熔断 / 最大迭代步数 / 查询行数限制）？\n"
        "5) 隐私模式与企业数据合规保证？"
    ),
    CommonDimension.HUMAN_AI_COLLABORATION.value: (
        "分析该 AI 应用的人机协同 (Human-in-the-Loop) 设计：\n"
        "1) AI 的自主度定位（行内补全 / 协同编辑 / 审批托管 / 全自主）？\n"
        "2) 人在哪些关键节点介入审批（Diff 预览 / Plan 确认 / SQL 预审 / 高危断点）？\n"
        "3) 交互介入粒度（行级 / 块级 / 查询级 / 任务级）？\n"
        "4) 一键撤销、拒绝重生成与追问引导的反馈闭环设计？\n"
        "5) 如何通过透明化依据（引用锚点/执行日志）建立用户信任？"
    ),
    CommonDimension.EXTENSIBILITY_ECOSYSTEM.value: (
        "分析该 AI 应用的扩展性与生态机制：\n"
        "1) 是否支持自定义插件、Skills、Hooks 或子 Agent 扩展？\n"
        "2) 对开放协议的支持情况（如 MCP Model Context Protocol / OpenAPI）？\n"
        "3) 配置与规则的层级管理（全局 / 项目 / 会话三级配置）？\n"
        "4) 是否寄生或兼容现有成熟生态（如 VS Code 插件市场 / 企业 IM）？\n"
        "5) 团队协作与规则/模板共享机制？"
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
        weight: int = 3,
    ) -> DimensionAnalysis:
        """针对单个共性维度进行分析"""
        dim_value = dimension.value
        dim_label = dimension.label
        prompt_template = DIMENSION_PROMPTS.get(dim_value, f"请分析 {dim_label} 维度。")

        if weight >= 4:
            depth_hint = f"该维度在该品类中的权重为 {weight}/5（核心维度），请结合具体技术细节进行深入、详尽的分析。"
        else:
            depth_hint = f"该维度在该品类中的权重为 {weight}/5，请抓住重点进行精炼分析。"

        system_prompt = (
            "你是一位资深 AI 产品架构分析师，擅长从公开技术资料与逆向线索中推断 AI 应用的 Harness 架构。"
            "必须严格基于给定采集数据分析并引用原文短句作为证据；"
            "若采集数据中未提及该维度，必须将 verbatim_quotes 置为 []，并将 confidence 设为 1 或 2，严禁编造引用。"
        )

        full_prompt = (
            f"## 应用信息\n{app_info}\n\n"
            f"## 采集数据\n{collected_data}\n\n"
            f"## 分析任务：{dim_label}\n{prompt_template}\n\n"
            f"{depth_hint}\n\n"
            '请返回 JSON：{"summary": "一句话核心结论", "details": "详细技术分析", '
            '"key_decisions": ["关键设计决策1", "关键设计决策2"], '
            '"takeaways": ["公司团队可借鉴的工程实践1", ...], '
            '"verbatim_quotes": ["直接摘自上述采集数据的原文短句或代码片段(未提及则留空数组[])"], '
            '"evidence_sources": ["参考依据或URL1", ...], "confidence": 3}'
        )

        try:
            result = self.llm.structured_analyze(full_prompt, system_prompt)
            return DimensionAnalysis(
                dimension=dim_value,
                label=dim_label,
                summary=result.get("summary", "") or "暂无总结",
                details=result.get("details", ""),
                key_decisions=result.get("key_decisions", []) or [],
                takeaways=result.get("takeaways", []) or [],
                confidence=max(1, min(5, int(result.get("confidence", 3)))),
                evidence_sources=result.get("evidence_sources", []) or [],
                verbatim_quotes=result.get("verbatim_quotes", []) or [],
            )
        except Exception as e:
            return DimensionAnalysis(
                dimension=dim_value,
                label=dim_label,
                summary=f"分析失败: {e}",
                confidence=1,
                is_inferred=True,
            )

    def extract_all(
        self,
        app_info: str,
        collected_data: str,
        category: str = "engineering",
        depth: str = "full",
        only_dimensions: list[str] | None = None,
    ) -> list[DimensionAnalysis]:
        """提取所有（或指定）共性维度

        Args:
            category: 应用所属分类，用于查询 DIMENSION_WEIGHTS 权重矩阵
            depth: 'quick'（跳过权重 <= 2 的次要维度）或 'full'（全量分析权重 >= 2 的维度）
            only_dimensions: 若提供，仅提取列表匹配的维度 key
        """
        cat_weights = DIMENSION_WEIGHTS.get(category, {})
        min_weight = 3 if depth == "quick" else 2
        filter_set = {d.strip().lower() for d in only_dimensions} if only_dimensions else None

        results: list[DimensionAnalysis] = []
        for dimension in CommonDimension:
            if filter_set and dimension.value not in filter_set and dimension.label not in filter_set:
                continue
            weight = cat_weights.get(dimension.value, 3)
            if not filter_set and weight < min_weight:
                continue
            analysis = self.extract_dimension(dimension, app_info, collected_data, weight=weight)
            results.append(analysis)

        return results
