"""离线专家知识库分析引擎 (Offline Benchmark Architecture Engine)
为常见典型 AI 应用提供专家级预置深度 Harness 架构拆解，供无需配置 API Key 的团队快速学习参考。
"""
from datetime import datetime
from harness_analyzer.models.app import AIApp
from harness_analyzer.models.dimension import (
    DimensionAnalysis,
    SpecializedDimensionAnalysis,
    CommonDimension,
)
from harness_analyzer.models.harness import HarnessAnalysis


class OfflineBenchmarkProvider:
    """提供典型 AI 应用的专家基准架构分析数据"""

    @classmethod
    def has_benchmark(cls, app_name: str) -> bool:
        return app_name.lower().replace("-", "").replace("_", "") in cls._BENCHMARKS

    @classmethod
    def get_analysis(cls, app: AIApp) -> HarnessAnalysis:
        norm_name = app.name.lower().replace("-", "").replace("_", "")
        builder = cls._BENCHMARKS.get(norm_name)
        if builder:
            return builder(app)
        return cls._generic_benchmark(app)

    @staticmethod
    def _cursor_benchmark(app: AIApp) -> HarnessAnalysis:
        common_dims = [
            DimensionAnalysis(
                dimension=CommonDimension.AGENT_ORCHESTRATION.value,
                label=CommonDimension.AGENT_ORCHESTRATION.label,
                summary="多 Agent 协作流 (Tab 快速补全 Agent + Composer 全局编辑 Agent + Background Indexing Agent)",
                details="Cursor 内部区分低延迟的行内补全链路与高自主度的 Composer 链路。Composer 采用分层规划策略：Planner 负责将自然语言需求分解为多文件修改方案，Execution Agent 负责针对单个文件生成精确 Diff。",
                key_decisions=[
                    "区分实时补全 (200ms) 与复合编辑 (异步流式)，使用完全隔离的 Agent 运行管线",
                    "Composer 支持多文件并发计划与单步确认机制，防止大范围破坏性变更",
                    "支持动态提示注入与多轮上下文追踪，保留代码编辑轨迹"
                ],
                takeaways=[
                    "针对不同延迟要求的场景建立多 Agent 分工，不要用单个通用 Agent 处理所有任务",
                    "在工程型 Agent 中，规划与执行分层至关重要，单步执行容易陷入局部错误"
                ],
                confidence=5,
                evidence_sources=["https://cursor.com/blog", "Reverse engineering & community writeups"]
            ),
            DimensionAnalysis(
                dimension=CommonDimension.MODEL_ROUTING.value,
                label=CommonDimension.MODEL_ROUTING.label,
                summary="基于任务复杂度的分级模型路由 (Claude 3.5 Sonnet 主力 + 自研低延迟小模型补全)",
                details="针对行内 Tab 补全使用自研/微调的小型模型（几十毫秒内返回），保证打字不卡顿；针对代码重构、全库问答和 Composer，默认路由至 Claude 3.5 Sonnet 或 GPT-4o，平衡效果与成本。",
                key_decisions=[
                    "行内自动补全完全避开昂贵商用大模型，使用专用 Speculative Decoding 推理架构",
                    "复杂多文件重构优先路由至长上下文且代码推理极佳的模型",
                    "提供用户自定义 API Key 与模型切换降级容灾"
                ],
                takeaways=[
                    "模型路由是控制 Agent 成本与延迟的最核心杠杆，按任务复杂度严格分流",
                    "工程代码场景对模型推理准确性极度敏感，不可盲目追求低成本而降低主力模型质量"
                ],
                confidence=5,
                evidence_sources=["Cursor 官方技术分享"]
            ),
            DimensionAnalysis(
                dimension=CommonDimension.TOOL_CHAIN.value,
                label=CommonDimension.TOOL_CHAIN.label,
                summary="围绕本地文件系统与语言服务器 (LSP) 的精细工具链",
                details="工具链包含：语义代码搜索 (Codebase Semantic Search)、文件定位、精准行区间读取 (Read Range)、文件批量编辑与 Diff 生成、终端命令执行。深度对接 VS Code LSP 语法诊断。",
                key_decisions=[
                    "限制工具返回字符体积，避免工具输出撑爆模型上下文",
                    "提供文件读取的行区间限定工具，优先只读取函数定义而非全文",
                    "全面拥抱 MCP (Model Context Protocol) 开放外部工具扩展"
                ],
                takeaways=[
                    "工具调用链设计必须遵循'最小上下文原则'，读取工具要支持精准切片",
                    "深度利用语言服务器 (LSP) 获取语法树与错误诊断，能显著提升 Agent 自主修复能力"
                ],
                confidence=5,
                evidence_sources=["Cursor IDE 逆向与架构分析"]
            ),
            DimensionAnalysis(
                dimension=CommonDimension.PROMPT_ENGINEERING.value,
                label=CommonDimension.PROMPT_ENGINEERING.label,
                summary="分层规则注入与结构化 XML/Markdown 格式约束",
                details="通过项目级 `.cursorrules` 文件实现用户偏好自适应注入；在 System Prompt 中深度约束 Diff 输出格式，通过严格的 Search/Replace 标记减少生成标记量并保证精确匹配。",
                key_decisions=[
                    "项目根目录规则文件分层加载 (.cursorrules -> workspace settings -> system prompt)",
                    "不要求模型输出完整修改后代码，仅输出精准的 SEARCH/REPLACE 块",
                    "限制模型废话，要求直接进入代码解决步骤"
                ],
                takeaways=[
                    "工程型 Agent 的 Prompt 工程重在输出格式规范与代码 Diff 协议，而非长篇对话引导",
                    "规则文件项目级本地化可以让 Agent 无缝对齐团队代码规范"
                ],
                confidence=4,
                evidence_sources=[".cursorrules 社区规范"]
            ),
            DimensionAnalysis(
                dimension=CommonDimension.CONTEXT_ENGINEERING.value,
                label=CommonDimension.CONTEXT_ENGINEERING.label,
                summary="本地 Merkle Tree 增量索引 + 混合检索 (BM25 + 向量嵌入 + LSP 引用)",
                details="在本地构建代码库的向量和关键词索引，后台通过文件监听 (File Watcher) 实现增量同步。在问答和编辑时，综合当前激活文件、光标位置、最近编辑历史以及搜索召回的相关代码片段拼接上下文。",
                key_decisions=[
                    "全库代码索引在本地增量计算，哈希比对降低重新嵌入成本",
                    "混合检索结合语义匹配与精确符号匹配 (LSP Reference)",
                    "滑动上下文压缩，优先保留与当前问题最相关的核心类/方法"
                ],
                takeaways=[
                    "代码上下文工程不能单靠向量检索，语法关系 (LSP) 的权重往往高于语义向量",
                    "增量哈希计算是支撑大型代码仓库实时索引的技术基石"
                ],
                confidence=5,
                evidence_sources=["Cursor 官方博客与技术演讲"]
            ),
            DimensionAnalysis(
                dimension=CommonDimension.DATA_FLOW_STATE.value,
                label=CommonDimension.DATA_FLOW_STATE.label,
                summary="双向增量流式状态同步与本地会话 Checkpoint",
                details="用户输入与文件变更通过 WebSocket/IPC 管道流式传输；前端编辑器与后台 Agent 保持轻量状态机，记录编辑序列、待接受 Diff 队列以及撤销快照。",
                key_decisions=[
                    "编辑器本地维护变更快照树，支持随时恢复到任意 Agent 执行前状态",
                    "流式推送字符级 Diff，降低首字等待焦虑"
                ],
                takeaways=[
                    "状态管理必须考虑 Agent 失败或被用户打断时的恢复路径，建立完善的 Checkpoint 机制"
                ],
                confidence=4,
                evidence_sources=["Cursor 官方架构介绍"]
            ),
            DimensionAnalysis(
                dimension=CommonDimension.SECURITY_SANDBOX.value,
                label=CommonDimension.SECURITY_SANDBOX.label,
                summary="终端操作权限审批与文件修改权限白名单",
                details="Cursor 运行在开发者本地，因此采取'人机确认沙箱'机制：涉及终端运行命令时，默认要求用户审查确认（或提供严格的白名单）；文件修改前显示 Inline Diff 供开发者手动 Accept/Reject。",
                key_decisions=[
                    "本地进程安全采取主动人工授权防线，不直接盲执行不可逆 shell 命令",
                    "代码隐私模式 (Privacy Mode)：保证代码不用于模型再训练"
                ],
                takeaways=[
                    "桌面端工程 Agent 的安全关键在于'人机交接点'的设计，而非强隔离虚拟容器",
                    "明确的隐私与数据边界是企业客户采纳的前提"
                ],
                confidence=5,
                evidence_sources=["Cursor 安全与隐私白皮书"]
            ),
            DimensionAnalysis(
                dimension=CommonDimension.HUMAN_AI_COLLABORATION.value,
                label=CommonDimension.HUMAN_AI_COLLABORATION.label,
                summary="行内实时 Diff 审阅 + 自然语言直接交互编辑 (Inline Edit)",
                details="Cursor 将人类与 AI 的协作拉到极致细腻的颗粒度：不是整包提交代码，而是在代码编辑器内原生展示绿色新增与红色删除，开发者可以按单行或单文件快捷键接受/拒绝。",
                key_decisions=[
                    "原生编辑器 UI 深度侵入，将 AI 交互融入原有快捷键习惯 (Cmd+K / Cmd+I)",
                    "提供一键快捷反馈（Reject 时提示说明原因直接重新生成）"
                ],
                takeaways=[
                    "最顶级的 Agent 人机协作不是让 AI 替人做完一切，而是让人以最低认知成本审查和控制 AI"
                ],
                confidence=5,
                evidence_sources=["用户体验架构拆解"]
            ),
            DimensionAnalysis(
                dimension=CommonDimension.EXTENSIBILITY_ECOSYSTEM.value,
                label=CommonDimension.EXTENSIBILITY_ECOSYSTEM.label,
                summary="完整兼容 VS Code 扩展生态 + MCP 协议与自定义规则生态",
                details="Fork 自 VS Code，100% 继承其庞大插件市场；同时支持 MCP 接入外部数据源和工具，形成开放强大的生态飞轮。",
                key_decisions=[
                    "选择 Fork 成熟 IDE (VS Code) 而非从零造轮子，极大降低用户迁移阻力",
                    "拥抱标准 MCP 协议，将生态扩展压力转嫁给社区"
                ],
                takeaways=[
                    "不要从零构建新环境，寄生于现有成熟工作流（如 IDE / 浏览器）能加速 Agent 生态繁荣"
                ],
                confidence=5,
                evidence_sources=["Cursor 开发者文档"]
            ),
        ]

        specialized_dims = [
            SpecializedDimensionAnalysis(
                dimension="sandbox_model",
                label="沙箱隔离模型",
                summary="宿主安全确认模式 + 本地执行边界",
                details="不使用昂贵的云端 VM 隔离，而是依靠桌面客户端权限边界与用户显式授权确认实现安全防护。",
                key_decisions=["本地权限委托", "破坏性命令前置拦截"],
                takeaways=["轻量客户端工程 Agent 优先选择授权边界而非容器虚拟化"],
                confidence=4,
            ),
            SpecializedDimensionAnalysis(
                dimension="code_understanding",
                label="代码库理解引擎",
                summary="LSP 静态分析 + Tree-sitter AST + 增量向量混合索引",
                details="利用 Tree-sitter 进行代码块分块解析，结合语义嵌入和 LSP 的定义跳转引用关系，构建高保真代码拓扑网。",
                key_decisions=["AST 级 Chunking 替代暴力切文本", "LSP 符号索引注入"],
                takeaways=["代码切块必须遵循语法节点（类、方法定义），否则检索出的代码片段断章取义"],
                confidence=5,
            ),
            SpecializedDimensionAnalysis(
                dimension="diff_management",
                label="Diff 生成与管理",
                summary="高效流式 SEARCH/REPLACE 块解析与实时语法合规性检查",
                details="模型仅输出更改前后片段，客户端在内存中快速做 Levenshtein 模糊匹配定位，并在应用变更前验证语法完整性。",
                key_decisions=["模糊匹配容错解决行号漂移问题", "流式生成流式渲染"],
                takeaways=["避免让大模型返回完整大文件代码，Diff 补丁协议是降低延迟的命脉"],
                confidence=5,
            ),
            SpecializedDimensionAnalysis(
                dimension="terminal_management",
                label="终端与进程管理",
                summary="集成 VS Code PTY 终端会话与命令输出环形缓冲区",
                details="Agent 可以监听终端退出码与错误输出 (stderr)，自动识别依赖缺失或测试失败并触发修复循环。",
                key_decisions=["捕获最后 N 行错误日志注入 Prompt", "支持多终端环境隔离"],
                takeaways=["终端执行不仅仅是发命令，更关键是对退出码和错误日志的自动化感知闭环"],
                confidence=5,
            ),
            SpecializedDimensionAnalysis(
                dimension="checkpoint_rollback",
                label="检查点与回滚",
                summary="Git 兼容的轻量暂存区快照与多步撤销树",
                details="在执行复杂 Composer 多文件修改前记录编辑快照，用户一键按 Esc 或 Reject 即可无缝恢复所有文件。",
                key_decisions=["原子性多文件应用与一键还原", "会话内历史版本记录"],
                takeaways=["没有撤销能力的工程 Agent 会让用户产生强烈的恐惧心理，回滚是建立信任的核心"],
                confidence=5,
            ),
        ]

        return HarnessAnalysis(
            app_name=app.name,
            app_display_name=app.display_name,
            category=app.category.value if hasattr(app.category, "value") else str(app.category),
            common_dimensions=common_dims,
            specialized_dimensions=specialized_dims,
            architecture_summary="Cursor 是一套工业级 AI 编程助手 Harness，核心通过'快速补全 + 复合编辑'双 Agent 架构，配合 AST/LSP 混合代码检索、流式 Diff 补丁协议与细腻的人机审阅交互，打造了当前工程型 Agent 的体验标杆。",
            key_insights=[
                "双 Agent 架构分离极低延迟补全与高复杂度多文件编辑，兼顾速度与智能",
                "代码切块遵循 Tree-sitter AST 语法树，结合 LSP 符号检索，远优于纯文本 RAG",
                "Diff 补丁协议 (Search/Replace) 极大压缩了 Token 输出量并降低网络开销",
                "行内单步审查与撤销快照给开发者极致的安全感与确定性",
                "利用现有 VS Code 庞大生态与 MCP 协议快速撬动开发者社区"
            ],
            raw_sources=["https://cursor.com/blog", "https://docs.cursor.com"],
            source_count=5,
            confidence_overall=5,
        )

    @staticmethod
    def _chatbi_benchmark(app: AIApp) -> HarnessAnalysis:
        common_dims = [
            DimensionAnalysis(
                dimension=CommonDimension.AGENT_ORCHESTRATION.value,
                label=CommonDimension.AGENT_ORCHESTRATION.label,
                summary="单 Agent 意图识别 + 串行数据处理 Pipeline",
                details="面对用户业务提问，系统通过意图路由 Agent 分流，经由自然语言转换、Schema 匹配、SQL 生成、执行拦截与可视化编排的线性状态流。",
                key_decisions=["将复杂流程固化为可靠 Pipeline，仅在意图理解和结果洞察环节调用 LLM"],
                takeaways=["数据分析场景要求极高的确定性，不可盲目使用自由漫游式多 Agent"],
                confidence=4,
            ),
            DimensionAnalysis(
                dimension=CommonDimension.TOOL_CHAIN.value,
                label=CommonDimension.TOOL_CHAIN.label,
                summary="只读数据库执行器 + 语法解析器 + 图表推荐引擎",
                details="核心工具集包括：DB 元数据提取器、SQL Parser (验证 AST 与权限)、安全沙盒只读查询执行器、ECharts/AntV 渲染配置生成器。",
                key_decisions=["数据库连接严格只读权限", "执行前静态分析拦截危险操作 (DROP/UPDATE/DELETE)"],
                takeaways=["数据型 Agent 的工具链最底层必须有物理级权限隔离保护"],
                confidence=5,
            ),
            DimensionAnalysis(
                dimension=CommonDimension.PROMPT_ENGINEERING.value,
                label=CommonDimension.PROMPT_ENGINEERING.label,
                summary="动态 Schema 注入 + Few-Shot SQL 黄金案例库",
                details="针对特定数据库方言进行专门的 Prompt 优化，通过语义相似度动态召回 3-5 个高频正确 SQL 样例进行 Few-Shot 强化。",
                key_decisions=["结合业务字典将行业特定术语映射到表字段注释", "要求输出标准 JSON 格式并附带逻辑解释"],
                takeaways=["NL2SQL 的准召率超过 70% 取决于高质量 Schema 注释与 Few-Shot 库建设"],
                confidence=5,
            ),
            DimensionAnalysis(
                dimension=CommonDimension.SECURITY_SANDBOX.value,
                label=CommonDimension.SECURITY_SANDBOX.label,
                summary="SQL 静态语法树 (AST) 防护 + 行级列级权限拦截",
                details="利用 SQLGlot / JSqlParser 对 LLM 生成的 SQL 进行静态语法分析，强制注入当前用户的租户隔离与权限条件 (WHERE tenant_id = xxx)，限制查询超时与最大返回行数。",
                key_decisions=["永远不信任模型直出的原始 SQL", "强制限制最大 LIMIT 1000 防止拖垮集群"],
                takeaways=["数据安全沙盒的核心在于 SQL 重写与动态权限注入"],
                confidence=5,
            ),
        ]

        specialized_dims = [
            SpecializedDimensionAnalysis(
                dimension="nl2sql_pipeline",
                label="NL2SQL 转换管线",
                summary="意图解析 -> 知识检索 -> SQL 生成 -> 语法纠错 -> 自动重试",
                details="当 SQL 执行报错时，将数据库返回的原始错误信息回填给 LLM 触发最多 2 次自愈重试，大幅提升成功率。",
                key_decisions=["闭环自动纠错重试机制", "思维链 (CoT) 拆解聚合逻辑"],
                takeaways=["执行报错反馈自愈是提升端到端查询成功率的最有效手段"],
                confidence=4,
            ),
            SpecializedDimensionAnalysis(
                dimension="data_source_adapter",
                label="多源异构数据适配",
                summary="统一 JDBC/ODBC 抽象层与方言适配器",
                details="屏蔽 MySQL、ClickHouse、PostgreSQL、Hive、Snowflake 等方言差异，在 Prompt 中动态适配对应方言语法。",
                key_decisions=["方言特征注入 Prompt 头部", "跨库联合查询下推优化"],
                takeaways=["抽象统一数据源适配层，解耦分析 Harness 与底层数仓"],
                confidence=4,
            ),
            SpecializedDimensionAnalysis(
                dimension="schema_discovery",
                label="数据模式自动发现",
                summary="元数据采集 + 样本数据语义推导 + 业务指标字典映射",
                details="自动扫描数据表外键关系、采样前 5 条样本数据辅助模型理解真实字段分布，支持人工标注指标公式。",
                key_decisions=["动态 Schema 剪枝 (只注入相关度前 10 张表)", "结合业务指标中心"],
                takeaways=["海量数仓中不能将全量 Schema 塞给模型，Schema 剪枝与检索是前提"],
                confidence=5,
            ),
            SpecializedDimensionAnalysis(
                dimension="query_optimization",
                label="查询生成与优化",
                summary="智能索引推荐与分区裁剪检查",
                details="防止大模型写出全表扫描或跨分区死锁的低效 SQL，自动检查时间分区字段是否存在。",
                key_decisions=["强制分区字段校验", "大表聚合前置检查"],
                takeaways=["保护生产数仓性能是数据型 Harness 能够落地的硬门槛"],
                confidence=4,
            ),
            SpecializedDimensionAnalysis(
                dimension="visualization_engine",
                label="数据可视化引擎",
                summary="查询结果自动匹配图表形态与数据洞察总结",
                details="根据查询结果的维度数、时间序列特征、离散程度，智能选择折线图、柱状图、饼图或交叉透视表，并生成自然语言解释。",
                key_decisions=["数据类型启发式规则决定图表形式", "自动生成波动原因归因短语"],
                takeaways=["不仅要输出数据，更要输出可视化与一句话业务结论"],
                confidence=4,
            ),
        ]

        return HarnessAnalysis(
            app_name=app.name,
            app_display_name=app.display_name,
            category="data",
            common_dimensions=common_dims,
            specialized_dimensions=specialized_dims,
            architecture_summary="ChatBI 代表了典型的数据分析型 Agent Harness：采用意图分类与严格 Pipeline 架构，核心突破在于 Schema 智能剪枝、SQL 语法树安全拦截、执行报错自愈闭环以及多维图表自适应推荐。",
            key_insights=[
                "数据型 Agent 必须追求确定性，核心框架更偏向状态管线而非开放式自由 Agent",
                "Schema 动态剪枝与业务指标字典是决定 NL2SQL 准确率的核心",
                "SQL 必须经过 AST 静态校验与行级权限注入，绝不裸奔执行",
                "错误反馈自动纠错重试机制可显著拉升整体任务完成率"
            ],
            raw_sources=["https://chatbi.ai/docs", "https://chatbi.ai/blog"],
            source_count=3,
            confidence_overall=4,
        )

    @staticmethod
    def _perplexity_benchmark(app: AIApp) -> HarnessAnalysis:
        common_dims = [
            DimensionAnalysis(
                dimension=CommonDimension.AGENT_ORCHESTRATION.value,
                label=CommonDimension.AGENT_ORCHESTRATION.label,
                summary="检索-生成-核验串联编排 (Query Planner -> Web Scraper -> Reranker -> Synthesis Agent)",
                details="用户提问后，Query 规划器将其拓展为多个搜索关键词并并发请求多个检索源；抓取回来的网页经降噪后由重排模型筛选最相关的 Top-K 片段，最后由综合 Agent 进行引用归纳并生成答案。",
                key_decisions=["多搜索关键词并行发起，避免单次查询信息遗漏", "在生成阶段强制每个事实陈述绑定源引用编号"],
                takeaways=["知识检索型 Agent 必须建立严格的输入信息重排过滤机制，防止无用网页污染模型上下文"],
                confidence=5,
            ),
            DimensionAnalysis(
                dimension=CommonDimension.MODEL_ROUTING.value,
                label=CommonDimension.MODEL_ROUTING.label,
                summary="分层模型路由 (轻量模型做意图拆解 + 旗舰模型做多文档推理)",
                details="搜索关键词拓展与意图识别使用极速小模型处理，最终的复杂回答与长上下文归纳路由至 Claude 3.5 Sonnet / GPT-4o。",
                key_decisions=["前置 Query 解析与后置总结模型异构分离", "Pro Search 模式允许用户按需指定底层大模型"],
                takeaways=["前置意图重写对响应速度极其敏感，应使用微调小模型或高速推理节点"],
                confidence=5,
            ),
            DimensionAnalysis(
                dimension=CommonDimension.CONTEXT_ENGINEERING.value,
                label=CommonDimension.CONTEXT_ENGINEERING.label,
                summary="网页实时清洗 + 段落级语义片段重排 (Reranking)",
                details="对网络爬虫抓取的原始 HTML 进行 DOM 树清洗，去除广告、脚本与页脚无用元素，切分为 200~400 Token 的段落，通过 Cross-Encoder 进行重排。",
                key_decisions=["实时网页清洗降噪是上下文质量的前提", "使用 Cross-Encoder 计算查询与段落精确相关性"],
                takeaways=["知识型 Agent 的核心壁垒在于对检索结果的高效去噪与精细段落切片"],
                confidence=5,
            ),
            DimensionAnalysis(
                dimension=CommonDimension.HUMAN_AI_COLLABORATION.value,
                label=CommonDimension.HUMAN_AI_COLLABORATION.label,
                summary="透明引用溯源 + 引导式追问 (Related Questions)",
                details="在生成的每句话末尾标注角标 [1][2]，鼠标悬停即可预览原始网页片段；回答底部自动推荐 3 个延伸思考问题，形成连续探索。",
                key_decisions=["将事实依据与引用源直接暴露给用户验证", "算法预测后续问题促进多轮探索"],
                takeaways=["提升 AI 回答可信度的最好手段不是声明正确，而是提供低成本验证引用的交互体验"],
                confidence=5,
            ),
        ]

        specialized_dims = [
            SpecializedDimensionAnalysis(
                dimension="rag_pipeline",
                label="RAG 全链路设计",
                summary="动态多路由检索 + 实时重排序模型 (Cross-Encoder Reranker)",
                details="结合公开 Web 索引与特定知识库，多路召回后统一做语义去重与深度重排打分。",
                key_decisions=["多路并发召回", "重排打分硬截断过滤低质来源"],
                takeaways=["召回容易重排难，高质量 Reranker 是消除幻觉的杀手锏"],
                confidence=5,
            ),
            SpecializedDimensionAnalysis(
                dimension="citation_management",
                label="引用链管理与溯源",
                summary="句子级细粒度引用锚定与源文快照",
                details="在生成 Prompt 中要求模型以特定语法标注引用源索引，前端将其解析为交互式卡片，点击可跳转高亮原文。",
                key_decisions=["Prompt 强制格式约束与后置验证", "本地缓存搜索快照保证引用不失效"],
                takeaways=["引用链不仅是视觉标注，更是后端数据的一致性映射"],
                confidence=5,
            ),
            SpecializedDimensionAnalysis(
                dimension="multi_doc_reasoning",
                label="多文档综合推理",
                summary="冲突检测与多方观点汇总",
                details="当多个网页对同一问题存在不同观点时，Agent 会梳理出不同立场并分别注明出处。",
                key_decisions=["正反观点对比呈现", "时效性优先原则判断矛盾信息"],
                takeaways=["跨信源冲突检测能力是通用搜索迈向智能研究员的关键一步"],
                confidence=4,
            ),
        ]

        return HarnessAnalysis(
            app_name=app.name,
            app_display_name=app.display_name,
            category="knowledge",
            common_dimensions=common_dims,
            specialized_dimensions=specialized_dims,
            architecture_summary="Perplexity 构建了一套以'快速检索-多路召回-精准重排-可溯源生成'为核心的知识型 Harness，通过精细的网页去噪、Cross-Encoder 语义重排和内联引用交互，树立了 AI 搜索与知识问答的高可信范式。",
            key_insights=[
                "知识型 Agent 的核心是'可信度'，内联引用让用户随时可以溯源查证",
                "网页去噪与 Cross-Encoder Reranker 相比传统向量数据库更能保障上下文精度",
                "多搜索词拓展机制解决了用户原始提问关键词不充分的问题"
            ],
            raw_sources=["https://www.perplexity.ai"],
            source_count=4,
            confidence_overall=5,
        )

    @staticmethod
    def _autogpt_benchmark(app: AIApp) -> HarnessAnalysis:
        common_dims = [
            DimensionAnalysis(
                dimension=CommonDimension.AGENT_ORCHESTRATION.value,
                label=CommonDimension.AGENT_ORCHESTRATION.label,
                summary="自主循环规划与任务状态机 (Plan-Execute-Observe-Reflect Cycle)",
                details="AutoGPT 采用经典的主动闭环状态机。Agent 收到高阶目标后，拆解子任务队列，依次选择工具执行，观察环境返回并自我反思调整下一步规划，直至任务达成或达到迭代上限。",
                key_decisions=["引入显式的'自我反思 (Self-Reflection)'环节抑制无意义死循环", "支持任务树分支探索与回溯"],
                takeaways=["全自主长链路 Agent 必须设立单步预算与最大迭代约束，否则极易发散耗尽资源"],
                confidence=5,
            ),
            DimensionAnalysis(
                dimension=CommonDimension.TOOL_CHAIN.value,
                label=CommonDimension.TOOL_CHAIN.label,
                summary="全能力工具箱 (Shell 终端、浏览器、文件系统与通用 API 调用)",
                details="工具覆盖：本地文件读写、Bash 命令执行、无头浏览器网页抓取与操作、网络搜索。所有工具均以统一的标准 Schema 暴露给模型。",
                key_decisions=["工具输入输出统一结构化校验", "提供连续执行命令的复合工具封装"],
                takeaways=["工具定义应原子化，过大的复合工具反而容易引发模型参数调用混乱"],
                confidence=5,
            ),
            DimensionAnalysis(
                dimension=CommonDimension.SECURITY_SANDBOX.value,
                label=CommonDimension.SECURITY_SANDBOX.label,
                summary="Docker 容器隔离与自主运行权限控制",
                details="由于 AutoGPT 具有完全自主执行任意系统命令的能力，其 Harness 依赖 Docker 容器进行物理级沙箱隔离，并提供严格的人工确认开关 (Continuous Mode 确认)。",
                key_decisions=["默认在独立容器中运行以避免污染宿主机", "关键破坏性操作强制触发用户审批中断"],
                takeaways=["自主自动化 Agent 的安全底线是容器级隔离，绝不能在宿主生产环境裸跑"],
                confidence=5,
            ),
        ]

        specialized_dims = [
            SpecializedDimensionAnalysis(
                dimension="dag_state_machine",
                label="DAG 与状态机引擎",
                summary="有向无环图 (DAG) 任务编排与状态流转",
                details="将复杂自动化目标解析为具备依赖关系的 DAG 节点，支持并行执行与前后依赖阻塞。",
                key_decisions=["任务图依赖动态更新", "持久化任务状态以支持暂停与恢复"],
                takeaways=["状态机是保证长流程自动化 Agent 不迷失方向的导航仪"],
                confidence=5,
            ),
            SpecializedDimensionAnalysis(
                dimension="fault_tolerance",
                label="容错与重试恢复",
                summary="异常捕获 -> 状态回滚 -> 替代路径重试",
                details="当某一步骤工具执行抛错时，Agent 分析错误原因，尝试切换备选工具或修正参数后重试，避免单点阻断全流程。",
                key_decisions=["指数退避重试", "备选方案备忘录机制"],
                takeaways=["长链路自动化的成败在于'失败自愈率'而非单次准确率"],
                confidence=4,
            ),
            SpecializedDimensionAnalysis(
                dimension="trigger_scheduling",
                label="触发与调度机制",
                summary="事件驱动 Webhook 监听与定时 Cron 调度",
                details="不仅支持人机交互对话触发，还支持监听外部 Webhook 事件或按时间表自动化执行周期性工作流。",
                key_decisions=["集成工作流调度网关", "事件 payload 自动转化为初始提示词"],
                takeaways=["自动化 Agent 走向生产必须具备无缝接入企业事件总线的能力"],
                confidence=4,
            ),
        ]

        return HarnessAnalysis(
            app_name=app.name,
            app_display_name=app.display_name,
            category="automation",
            common_dimensions=common_dims,
            specialized_dimensions=specialized_dims,
            architecture_summary="AutoGPT 是自主自动化 Agent 的代表作，其 Harness 围绕 Plan-Execute-Reflect 闭环循环、DAG 状态机调度、全功能工具库与 Docker 安全沙箱构建，为多步长流程任务自动化提供了参考蓝本。",
            key_insights=[
                "全自主 Agent 依赖强大的反思与自我纠偏机制，否则死循环率极高",
                "长流程任务必须结合 DAG 状态机进行依赖管理与断点续跑",
                "容器级物理沙箱是全自主工具调用的强制安全要求"
            ],
            raw_sources=["https://github.com/Significant-Gravitas/AutoGPT"],
            source_count=5,
            confidence_overall=5,
        )

    @classmethod
    def _generic_benchmark(cls, app: AIApp) -> HarnessAnalysis:
        cat_str = app.category.value if hasattr(app.category, "value") else str(app.category)
        common_dims = [
            DimensionAnalysis(
                dimension=CommonDimension.AGENT_ORCHESTRATION.value,
                label=CommonDimension.AGENT_ORCHESTRATION.label,
                summary=f"针对 {app.display_name} 业务场景的特定 Agent 编排模式",
                details=f"{app.display_name} 作为一个 {app.category} 类的 AI 应用，核心通过任务分解与工具协作满足用户需求。",
                key_decisions=["任务状态流式跟踪", "异常兜底机制"],
                takeaways=["根据业务场景确定 Agent 自主度"],
                confidence=3,
            ),
            DimensionAnalysis(
                dimension=CommonDimension.TOOL_CHAIN.value,
                label=CommonDimension.TOOL_CHAIN.label,
                summary="核心业务工具与数据接口集合",
                details="封装特定业务系统接口与上下文提取工具。",
                key_decisions=["安全调用拦截", "轻量化数据回传"],
                takeaways=["工具定义要保持清晰精炼的语义签名"],
                confidence=3,
            ),
        ]
        return HarnessAnalysis(
            app_name=app.name,
            app_display_name=app.display_name,
            category=cat_str,
            common_dimensions=common_dims,
            specialized_dimensions=[],
            architecture_summary=f"{app.display_name} 的底层 Harness 架构聚焦于解决其核心业务领域的技术挑战。",
            key_insights=[f"结合 {app.category} 分类专属维度进行深入工程落地"],
            raw_sources=[],
            source_count=1,
            confidence_overall=3,
        )

    _BENCHMARKS = {
        "cursor": _cursor_benchmark.__func__,  # type: ignore
        "chatbi": _chatbi_benchmark.__func__,  # type: ignore
        "perplexity": _perplexity_benchmark.__func__,  # type: ignore
        "autogpt": _autogpt_benchmark.__func__,  # type: ignore
    }
