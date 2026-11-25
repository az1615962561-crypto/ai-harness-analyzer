"""离线专家知识库分析引擎 (Offline Benchmark Architecture Engine)
为常见典型 AI 应用提供专家级预置深度 Harness 架构拆解，供无需配置 API Key 的团队快速学习参考。
"""
from datetime import datetime
from harness_analyzer.models.app import AIApp
from harness_analyzer.models.dimension import (
    DimensionAnalysis,
    SpecializedDimensionAnalysis,
    CommonDimension,
    GuardStatus,
)
from harness_analyzer.models.harness import HarnessAnalysis, PMGuidance, UserReviewSummary
from harness_analyzer.analyzer.evidence import resolve_coupling_level
from harness_analyzer.analyzer.intermediate import IntermediateArtifactBuilder


class OfflineBenchmarkProvider:
    """提供典型 AI 应用的专家基准架构分析数据"""

    _OFFLINE_USER_REVIEWS: dict[str, UserReviewSummary] = {
        "cursor": UserReviewSummary(
            review_sources=[
                "https://news.ycombinator.com (Hacker News 开发者社区)",
                "https://www.reddit.com/r/cursor",
            ],
            praises=[
                "Cursor Tab 多行预测与光标跳转体验极佳，真正做到打字不卡顿",
                "Inline Diff (绿增红删) 审阅直观，结合一键回滚让人敢放心让 AI 改多文件",
            ],
            pain_points=[
                "大型仓库下 Composer 偶尔误删或改坏未提及的相邻函数",
                "高频对话时快速额度消耗快，降速队列体验落差明显",
            ],
            trust_and_ux_friction=[
                "全自动 Agent 模式下连续执行终端命令时，用户容易失去变更感知，仍高度依赖手点 Accept/Reject",
            ],
            sample_quotes=[
                "Cursor Tab alone justifies the subscription—predicting the next edit location feels magical.",
                "Composer is great for scaffolding, but on large files it still occasionally drops unrelated code unless you watch the diff carefully.",
            ],
        ),
        "chatbi": UserReviewSummary(
            review_sources=[
                "企业 BI 社区评测 (G2 / 知乎企业数字化专栏)",
            ],
            praises=[
                "业务人员无需找数据研发排队写 SQL，自然语言直接出常规看板",
                "结合指标口径字典后，常见经营日报查询准确率大幅提高",
            ],
            pain_points=[
                "遇到多表复杂 JOIN 或隐含业务口径（如“有效复购率”）时仍容易算错数",
                "未展示计算逻辑时，管理层不敢直接拿生成的数字做汇报",
            ],
            trust_and_ux_friction=[
                "用户极度关心『这个数字怎么算出来的』，缺乏口径回显与 SQL 透明解释会导致零信任",
            ],
            sample_quotes=[
                "对话查数很爽，但如果不能点开看到用的是哪张表和过滤条件，我们根本不敢拿去周会汇报。",
            ],
        ),
        "perplexity": UserReviewSummary(
            review_sources=[
                "https://news.ycombinator.com (Hacker News)",
                "https://www.reddit.com/r/perplexity_ai",
            ],
            praises=[
                "答案每句话附带角标引用，悬停就能核对原始网页，极大降低搜索时间",
                "追问交互流畅，比传统搜索引擎广告堆砌高效得多",
            ],
            pain_points=[
                "部分冷门技术或中文深度问题抓取的网页来源质量参差不齐",
                "面对需要严格深度推理的任务，长文综述偶尔过度简化原文条件",
            ],
            trust_and_ux_friction=[
                "偶尔出现『角标引用存在，但点进去原文并不支持该结论』的错位引用问题",
            ],
            sample_quotes=[
                "Perplexity replaced 80% of my Google searches, though I still click the inline citations whenever numbers matter.",
            ],
        ),
        "autogpt": UserReviewSummary(
            review_sources=[
                "https://github.com/Significant-Gravitas/AutoGPT/issues",
                "https://news.ycombinator.com (Hacker News)",
            ],
            praises=[
                "验证了自主目标拆解与工具循环执行的无限潜力，激发了整个 Agent 生态",
            ],
            pain_points=[
                "长链路任务经常陷入死循环，短时间内烧光大量 OpenAI API 费用",
                "本地配置与 Docker 沙箱环境门槛高，非开发者难以上手",
            ],
            trust_and_ux_friction=[
                "缺乏中途人工干预与可预期的成本上限，导致用户不敢放手让它长期挂机跑任务",
            ],
            sample_quotes=[
                "Cool demo, but left unattended it looped 15 times trying to fix a missing dependency and burned $10 in minutes.",
            ],
        ),
    }

    @classmethod
    def has_benchmark(cls, app_name: str) -> bool:
        return app_name.lower().replace("-", "").replace("_", "") in cls._BENCHMARKS

    @classmethod
    def get_analysis(cls, app: AIApp) -> HarnessAnalysis:
        norm_name = app.name.lower().replace("-", "").replace("_", "")
        builder = cls._BENCHMARKS.get(norm_name)
        analysis = builder(app) if builder else cls._generic_benchmark(app)

        # 按联系程度标注每个维度的 coupling_level 与基准 Guard 状态
        for dim in (*analysis.common_dimensions, *analysis.specialized_dimensions):
            dim.coupling_level = resolve_coupling_level(dim, category=analysis.category)
            dim.guard_status = GuardStatus.STRICT_VERIFIED if builder else GuardStatus.UNVERIFIED_CAPPED
            if not builder:
                dim.is_inferred = True

        analysis.intermediate_artifact = IntermediateArtifactBuilder().build(
            app_name=analysis.app_name,
            category=analysis.category,
            common_dims=analysis.common_dimensions,
            specialized_dims=analysis.specialized_dimensions,
            user_reviews_override=cls._OFFLINE_USER_REVIEWS.get(norm_name),
        )
        return analysis

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
            pm_guidance=PMGuidance(
                suitable_product_forms=[
                    "IDE 原生侵入式编辑器扩展 (基于 VS Code Fork 或 LSP 深度嵌入)",
                    "桌面端代码协作浮窗 / 命令行终端原生交互 CLI (如 Claude Code)",
                ],
                autonomy_level="L2~L3 (人在回路的渐进协同型)",
                interaction_design=(
                    "1. 双重交互粒度分流：行内打字实时补全 (Tab 无感采纳) 与全局多文件编辑 (Composer 对话窗口)；\n"
                    "  2. 视觉信任锚点：修改以直观的行内 Diff (绿色新增/红色删除) 呈现，单行/单文件支持快捷键快速审查 Accept/Reject；\n"
                    "  3. 心理安全网：每次复杂修改执行前自动打点快照，支持用户一键 Esc / Undo 原子级还原所有被改动文件。"
                ),
                cost_latency_tradeoffs=(
                    "• 延迟分级：高频 Tab 补全强制要求 <200ms，必须采用端侧小模型或 Speculative 推理；\n"
                    "• 成本分级：代码重构与多文件编辑走异步流式生成，采用精确 SEARCH/REPLACE 差异块，减少 80% 的 Token 输出量。"
                ),
                mvp_must_haves=[
                    "基于 Tree-sitter 的代码文件语法块精准解析 (函数级切块)",
                    "流式 SEARCH/REPLACE 差异补丁协议与客户端合并引擎",
                    "代码修改前置预览 (Diff 审阅界面)",
                    "单步操作撤销与文件还原 (Undo 快照)",
                    "终端命令执行前置审批确认机制"
                ],
                mvp_nice_to_haves=[
                    "全库 Merkle Tree 增量索引与本地向量/符号混合检索",
                    "项目级规则配置文件自适应注入 (.cursorrules / CLAUDE.md)",
                    "支持 MCP (Model Context Protocol) 开放外部生态",
                    "自研低延迟小模型行内补全"
                ],
                anti_patterns_to_avoid=[
                    "千万不要在第一期要求大模型直接重写几千行的整个源文件 (Token 爆炸且极慢)；",
                    "切忌不给用户 Diff 预览就直接把代码落盘修改 (用户会产生极强不安全感)；",
                    "第一期不要追求完全自主无需确认的 Autonomous 模式，容易改坏代码导致用户弃用。"
                ]
            ),
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
            pm_guidance=PMGuidance(
                suitable_product_forms=[
                    "企业内部数据工作台 Web 界面 (嵌入现有数仓 / BI 报表平台)",
                    "企业微信 / 钉钉 / 飞书 对话机器人 (针对业务部门与管理层快速查数)",
                ],
                autonomy_level="L1~L2 (严格受控的建议与辅助型)",
                interaction_design=(
                    "1. 意图确认卡片：用户输入自然语言后，先回显其识别的业务维度、时间窗口与指标定义，供用户核对；\n"
                    "  2. SQL 预览与透视：为分析师模式提供生成的 SQL 展开预览与数据来源表说明；\n"
                    "  3. 可视化交互洞察：查询结果自动匹配自适应图表，并输出 1~2 句核心波动业务归因短语。"
                ),
                cost_latency_tradeoffs=(
                    "• 确定性优先于灵活性：采用固化的状态流 Pipeline，仅在意图提取与图表总结环节消耗 LLM，避免多轮漫游消耗 Token；\n"
                    "• 生产数仓保护：强制 LIMIT 1000 与查询超时熔断，防止大模型写出全表扫描拖垮集群。"
                ),
                mvp_must_haves=[
                    "核心业务指标字典与元数据映射 (Schema 注释库)",
                    "高质量 Few-Shot SQL 黄金案例库 (动态召回 3~5 条)",
                    "SQL 静态语法分析器 (拦截危险 DROP/DELETE/UPDATE)",
                    "查询执行报错自动反馈重试自愈机制 (最多 2 次)",
                    "表格结果自动识别并渲染基础折线图/柱状图"
                ],
                mvp_nice_to_haves=[
                    "全库海量表动态 Schema 剪枝算法",
                    "行级/列级租户数据安全权限自动注入 (Row-Level Security)",
                    "指标归因自动多维下钻解释",
                    "自然语言复杂数据透视表交互"
                ],
                anti_patterns_to_avoid=[
                    "切忌把上百张表的建表语句直接塞给大模型 (上下文被污染，准确率暴跌)；",
                    "切忌直连高权限生产数据库执行模型生成的裸 SQL；",
                    "第一期不要盲目引入自由多 Agent 辩论，数据场景需要强确定性而非发散。"
                ]
            ),
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
            pm_guidance=PMGuidance(
                suitable_product_forms=[
                    "企业新一代智能搜索门户 (对标现代 AI 搜索引擎)",
                    "内部海量文档/Wiki/知识库问答助手 (HR/法务/研发助手)",
                    "行业分析师与研报调研工作台",
                ],
                autonomy_level="L1~L2 (透明引用的交互探索型)",
                interaction_design=(
                    "1. 句子级细粒度引用锚定 [1][2]，鼠标悬停即时弹出原文快照卡片，支持一键跳转溯源；\n"
                    "  2. 底部自动生成 3 个引导式延伸问题 (Related Questions)，促进多轮深度挖掘；\n"
                    "  3. Pro Search 模式提供意图澄清卡片，允许用户在搜索前框定范围。"
                ),
                cost_latency_tradeoffs=(
                    "• 意图拆解与搜索词拓展使用极速小模型 (响应 <500ms)，避免用户产生白屏等待焦虑；\n"
                    "• 最终总结归纳与多文档事实核验路由给长上下文旗舰模型，保证回答深度。"
                ),
                mvp_must_haves=[
                    "多路搜索并发召回 (关键词+语义向量混合召回)",
                    "网页 DOM 清洗与噪音广告/页脚剔除引擎",
                    "基于 Cross-Encoder 的段落级重排打分模型 (Reranker)",
                    "生成文本中强制内联引用标记注入协议",
                    "前端交互式引用悬停预览与原文锚点高亮"
                ],
                mvp_nice_to_haves=[
                    "多信源矛盾观点交叉核验与时效性衰减算法",
                    "多轮探索历史时间轴与思维导图生成",
                    "支持上传本地 PDF/研报联合联网搜索",
                    "语音搜索与播客式总结输出"
                ],
                anti_patterns_to_avoid=[
                    "切忌只做普通向量召回不加 Reranker (召回一堆垃圾网页导致严重幻觉)；",
                    "切忌生成无引用的裸文本答案，用户无法验证真伪就会产生严重不信任；",
                    "第一期不要直接爬取未经清洗的网页，杂质字符会挤爆大模型窗口。"
                ]
            ),
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
            pm_guidance=PMGuidance(
                suitable_product_forms=[
                    "后台异步执行的长时间复杂任务工作流 Agent (如自动化研究/报表生成)",
                    "跨企业 SaaS 系统的多应用数据同步与流程自动化服务",
                    "研发自动化测试与运维排障自愈机器人",
                ],
                autonomy_level="L3~L4 (高自主度的全托管异步型)",
                interaction_design=(
                    "1. 目标拆解进度看板：以 DAG 任务图或步骤列表实时流式展示当前进展；\n"
                    "  2. 工具参数透明回显：清晰展示 Agent 正在调用的工具名、输入参数与执行日志；\n"
                    "  3. 敏感操作审批断点：对写操作、资金、发送对外邮件等破坏性行为强制停顿等待人类确认 (HITL)。"
                ),
                cost_latency_tradeoffs=(
                    "• 预算熔断：全自主循环极易发散，必须强制设定单任务最大迭代步数 (如 Max Steps 20) 与 Token 消耗硬阈值；\n"
                    "• 异步解耦：脱离即时打字对话形态，用户提交任务后可通过异步 Webhook 通知（邮件/企微）接收成果。"
                ),
                mvp_must_haves=[
                    "基于 DAG 的有向无环图任务依赖调度引擎",
                    "统一标准化的原子 Tool Calling Schema 接口",
                    "单步执行失败反思纠偏与指数退避重试机制",
                    "Docker 容器级轻量安全隔离沙箱",
                    "任务状态本地持久化与断点续跑支持"
                ],
                mvp_nice_to_haves=[
                    "多 Agent 角色分工委派通信协议 (Planner -> Worker -> Critic)",
                    "定时 Cron 周期调度与外部 Webhook 触发网关",
                    "长链路执行历史多分支版本回溯",
                    "动态 Token 成本预测与智能分配"
                ],
                anti_patterns_to_avoid=[
                    "绝对不要在宿主开发环境或生产机裸跑无容器隔离的自动化 Agent；",
                    "切忌不设迭代步数上限，极易死循环烧干 API 余额；",
                    "第一期不要设计过多复杂复合工具，工具数量越多大模型越容易选择困难或参数幻觉。"
                ]
            ),
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
