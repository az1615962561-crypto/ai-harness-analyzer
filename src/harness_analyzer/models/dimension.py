"""Dimension models for Harness architecture analysis."""
from __future__ import annotations

from enum import Enum
from pydantic import BaseModel, Field


class CommonDimension(str, Enum):
    """9 个通用架构维度"""
    AGENT_ORCHESTRATION = "agent_orchestration"
    MODEL_ROUTING = "model_routing"
    TOOL_CHAIN = "tool_chain"
    PROMPT_ENGINEERING = "prompt_engineering"
    CONTEXT_ENGINEERING = "context_engineering"
    DATA_FLOW_STATE = "data_flow_state"
    SECURITY_SANDBOX = "security_sandbox"
    HUMAN_AI_COLLABORATION = "human_ai_collaboration"
    EXTENSIBILITY_ECOSYSTEM = "extensibility_ecosystem"

    @property
    def label(self) -> str:
        _labels = {
            CommonDimension.AGENT_ORCHESTRATION: "Agent 编排",
            CommonDimension.MODEL_ROUTING: "模型路由",
            CommonDimension.TOOL_CHAIN: "工具链",
            CommonDimension.PROMPT_ENGINEERING: "提示词工程",
            CommonDimension.CONTEXT_ENGINEERING: "上下文工程",
            CommonDimension.DATA_FLOW_STATE: "数据流与状态管理",
            CommonDimension.SECURITY_SANDBOX: "安全沙箱",
            CommonDimension.HUMAN_AI_COLLABORATION: "人机协同",
            CommonDimension.EXTENSIBILITY_ECOSYSTEM: "扩展生态",
        }
        return _labels[self]

    @property
    def description(self) -> str:
        _descriptions = {
            CommonDimension.AGENT_ORCHESTRATION: "分析多 Agent 协作机制、任务规划分解、反思评估与执行流控制架构",
            CommonDimension.MODEL_ROUTING: "分析底层多模型选择策略、动态分流路由、降级容灾与成本性能平衡",
            CommonDimension.TOOL_CHAIN: "分析工具调用与函数执行机制、外部系统集成、工具协议与生命周期管理",
            CommonDimension.PROMPT_ENGINEERING: "分析提示词构建策略、动态提示注入、元提示与角色约束设计",
            CommonDimension.CONTEXT_ENGINEERING: "分析长上下文管理、注意力聚焦、记忆机制与上下文压缩检索",
            CommonDimension.DATA_FLOW_STATE: "分析系统数据流向、会话状态保持、持久化存储与缓存架构设计",
            CommonDimension.SECURITY_SANDBOX: "分析代码执行安全隔离、网络访问控制、权限管理与内容合规风控",
            CommonDimension.HUMAN_AI_COLLABORATION: "分析人机交互界面形态、用户意图干预介入、反馈闭环与协同编辑体验",
            CommonDimension.EXTENSIBILITY_ECOSYSTEM: "分析插件扩展机制、开放 API、自定义规则系统与开发者生态支持",
        }
        return _descriptions[self]


class SpecializedDimension(str, Enum):
    """品类专属特性维度"""
    # 工程型 (Engineering)
    ENG_SANDBOX_MODEL = "eng_sandbox_model"
    ENG_CODE_UNDERSTANDING = "eng_code_understanding"
    ENG_DIFF_MANAGEMENT = "eng_diff_management"
    ENG_TERMINAL_MANAGEMENT = "eng_terminal_management"
    ENG_CHECKPOINT_ROLLBACK = "eng_checkpoint_rollback"

    # 数据型 (Data)
    DATA_NL2SQL_PIPELINE = "data_nl2sql_pipeline"
    DATA_SOURCE_ADAPTER = "data_source_adapter"
    DATA_SCHEMA_DISCOVERY = "data_schema_discovery"
    DATA_QUERY_OPTIMIZATION = "data_query_optimization"
    DATA_VISUALIZATION_ENGINE = "data_visualization_engine"

    # 知识型 (Knowledge)
    KNOW_RAG_PIPELINE = "know_rag_pipeline"
    KNOW_INDEX_VECTOR_STORE = "know_index_vector_store"
    KNOW_CITATION_MANAGEMENT = "know_citation_management"
    KNOW_MULTI_DOC_REASONING = "know_multi_doc_reasoning"
    KNOW_KNOWLEDGE_UPDATE = "know_knowledge_update"

    # 创作型 (Creative)
    CREA_MULTIMODAL_PIPELINE = "crea_multimodal_pipeline"
    CREA_VERSION_VARIANT = "crea_version_variant"
    CREA_REALTIME_PREVIEW = "crea_realtime_preview"
    CREA_STYLE_CONSISTENCY = "crea_style_consistency"
    CREA_TEMPLATE_REUSE = "crea_template_reuse"

    # 自动化型 (Automation)
    AUTO_DAG_STATE_MACHINE = "auto_dag_state_machine"
    AUTO_MULTI_AGENT_PROTOCOL = "auto_multi_agent_protocol"
    AUTO_FAULT_TOLERANCE = "auto_fault_tolerance"
    AUTO_EXTERNAL_INTEGRATION = "auto_external_integration"
    AUTO_TRIGGER_SCHEDULING = "auto_trigger_scheduling"

    @property
    def label(self) -> str:
        _labels = {
            SpecializedDimension.ENG_SANDBOX_MODEL: "沙箱隔离模型",
            SpecializedDimension.ENG_CODE_UNDERSTANDING: "代码库理解",
            SpecializedDimension.ENG_DIFF_MANAGEMENT: "Diff 生成与管理",
            SpecializedDimension.ENG_TERMINAL_MANAGEMENT: "终端与进程管理",
            SpecializedDimension.ENG_CHECKPOINT_ROLLBACK: "检查点与回滚",
            SpecializedDimension.DATA_NL2SQL_PIPELINE: "NL2SQL 转换管线",
            SpecializedDimension.DATA_SOURCE_ADAPTER: "多源异构数据适配",
            SpecializedDimension.DATA_SCHEMA_DISCOVERY: "数据模式自动发现",
            SpecializedDimension.DATA_QUERY_OPTIMIZATION: "查询生成与优化",
            SpecializedDimension.DATA_VISUALIZATION_ENGINE: "数据可视化引擎",
            SpecializedDimension.KNOW_RAG_PIPELINE: "RAG 检索增强管线",
            SpecializedDimension.KNOW_INDEX_VECTOR_STORE: "知识索引与向量存储",
            SpecializedDimension.KNOW_CITATION_MANAGEMENT: "引用与事实溯源",
            SpecializedDimension.KNOW_MULTI_DOC_REASONING: "跨文档综合推理",
            SpecializedDimension.KNOW_KNOWLEDGE_UPDATE: "知识动态更新机制",
            SpecializedDimension.CREA_MULTIMODAL_PIPELINE: "多模态生成管线",
            SpecializedDimension.CREA_VERSION_VARIANT: "版本与变体生成",
            SpecializedDimension.CREA_REALTIME_PREVIEW: "实时渲染与预览",
            SpecializedDimension.CREA_STYLE_CONSISTENCY: "风格一致性控制",
            SpecializedDimension.CREA_TEMPLATE_REUSE: "模板与资产复用",
            SpecializedDimension.AUTO_DAG_STATE_MACHINE: "DAG/状态机工作流",
            SpecializedDimension.AUTO_MULTI_AGENT_PROTOCOL: "多智能体通信协议",
            SpecializedDimension.AUTO_FAULT_TOLERANCE: "容错重试与断点续跑",
            SpecializedDimension.AUTO_EXTERNAL_INTEGRATION: "外部系统与连接器集成",
            SpecializedDimension.AUTO_TRIGGER_SCHEDULING: "事件触发与任务调度",
        }
        return _labels[self]


CATEGORY_DIMENSIONS: dict[str, list[SpecializedDimension]] = {
    "engineering": [
        SpecializedDimension.ENG_SANDBOX_MODEL,
        SpecializedDimension.ENG_CODE_UNDERSTANDING,
        SpecializedDimension.ENG_DIFF_MANAGEMENT,
        SpecializedDimension.ENG_TERMINAL_MANAGEMENT,
        SpecializedDimension.ENG_CHECKPOINT_ROLLBACK,
    ],
    "data": [
        SpecializedDimension.DATA_NL2SQL_PIPELINE,
        SpecializedDimension.DATA_SOURCE_ADAPTER,
        SpecializedDimension.DATA_SCHEMA_DISCOVERY,
        SpecializedDimension.DATA_QUERY_OPTIMIZATION,
        SpecializedDimension.DATA_VISUALIZATION_ENGINE,
    ],
    "knowledge": [
        SpecializedDimension.KNOW_RAG_PIPELINE,
        SpecializedDimension.KNOW_INDEX_VECTOR_STORE,
        SpecializedDimension.KNOW_CITATION_MANAGEMENT,
        SpecializedDimension.KNOW_MULTI_DOC_REASONING,
        SpecializedDimension.KNOW_KNOWLEDGE_UPDATE,
    ],
    "creative": [
        SpecializedDimension.CREA_MULTIMODAL_PIPELINE,
        SpecializedDimension.CREA_VERSION_VARIANT,
        SpecializedDimension.CREA_REALTIME_PREVIEW,
        SpecializedDimension.CREA_STYLE_CONSISTENCY,
        SpecializedDimension.CREA_TEMPLATE_REUSE,
    ],
    "automation": [
        SpecializedDimension.AUTO_DAG_STATE_MACHINE,
        SpecializedDimension.AUTO_MULTI_AGENT_PROTOCOL,
        SpecializedDimension.AUTO_FAULT_TOLERANCE,
        SpecializedDimension.AUTO_EXTERNAL_INTEGRATION,
        SpecializedDimension.AUTO_TRIGGER_SCHEDULING,
    ],
}

DIMENSION_WEIGHTS: dict[str, dict[str, int]] = {
    "engineering": {
        "agent_orchestration": 5,
        "model_routing": 5,
        "tool_chain": 5,
        "prompt_engineering": 4,
        "context_engineering": 5,
        "data_flow_state": 4,
        "security_sandbox": 5,
        "human_ai_collaboration": 5,
        "extensibility_ecosystem": 5,
    },
    "data": {
        "agent_orchestration": 2,
        "model_routing": 4,
        "tool_chain": 5,
        "prompt_engineering": 5,
        "context_engineering": 3,
        "data_flow_state": 5,
        "security_sandbox": 4,
        "human_ai_collaboration": 4,
        "extensibility_ecosystem": 2,
    },
    "knowledge": {
        "agent_orchestration": 2,
        "model_routing": 3,
        "tool_chain": 2,
        "prompt_engineering": 4,
        "context_engineering": 5,
        "data_flow_state": 3,
        "security_sandbox": 2,
        "human_ai_collaboration": 3,
        "extensibility_ecosystem": 3,
    },
    "creative": {
        "agent_orchestration": 3,
        "model_routing": 5,
        "tool_chain": 3,
        "prompt_engineering": 4,
        "context_engineering": 2,
        "data_flow_state": 3,
        "security_sandbox": 2,
        "human_ai_collaboration": 5,
        "extensibility_ecosystem": 2,
    },
    "automation": {
        "agent_orchestration": 5,
        "model_routing": 3,
        "tool_chain": 5,
        "prompt_engineering": 2,
        "context_engineering": 2,
        "data_flow_state": 5,
        "security_sandbox": 3,
        "human_ai_collaboration": 2,
        "extensibility_ecosystem": 5,
    },
}


class DimensionAnalysis(BaseModel):
    """通用维度分析结果"""
    dimension: str
    label: str
    summary: str
    details: str = ""
    key_decisions: list[str] = Field(default_factory=list)
    takeaways: list[str] = Field(default_factory=list)
    confidence: int = Field(default=3, ge=1, le=5)
    evidence_sources: list[str] = Field(default_factory=list)


class SpecializedDimensionAnalysis(BaseModel):
    """专属特性维度分析结果"""
    dimension: str
    label: str
    summary: str
    details: str = ""
    key_decisions: list[str] = Field(default_factory=list)
    takeaways: list[str] = Field(default_factory=list)
    confidence: int = Field(default=3, ge=1, le=5)
    evidence_sources: list[str] = Field(default_factory=list)
