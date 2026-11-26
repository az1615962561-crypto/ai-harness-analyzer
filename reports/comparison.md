# AI Harness 架构对比报告：OpenHands vs Cursor

> 生成时间：2026-11-26 11:44:06 | 对比数量：2 款 AI 应用

## 1. 概览横向对比

| 对比维度 | OpenHands | Cursor |
| :--- | :--- | :--- |
| **应用分类** | engineering | engineering |
| **架构置信度** | ★★★★☆ | ★★★★★ |
| **信息源数量** | 32 | 5 |
| **架构核心摘要** | OpenHands 已演进为由 Agent Canvas（浏览器/桌面控制面客户端）、Agent Server（核心执行后端）与 Software Agent SDK（无状态事件驱动内核）组成的三层工程型 Harness 平台：支持接入 D... | Cursor 是一套工业级 AI 编程助手 Harness，核心通过'快速补全 + 复合编辑'双 Agent 架构，配合 AST/LSP 混合代码检索、流式 Diff 补丁协议与细腻的人机审阅交互，打造了当前工程型 Agent 的体验标杆。 |

## 2. 应用层：产品方案横向对比 (PM Guidance)

| 产品决策维度 | OpenHands | Cursor |
| :--- | :--- | :--- |
| **适合产品形态** | 可独立部署的工程型 AI Agent 控制工作台（Web 控制面 + Docker/云端隔离沙箱执行器）；面向团队的异步研发助手（通过 Webhook 接收 GitHub/GitLab/Slack/Jira 任务并自动提 PR）；企业内部兼容多种编程 Agent（如通过 ACP/MCP 纳管各研发工具）的统一管控门户 | IDE 原生侵入式编辑器扩展 (基于 VS Code Fork 或 LSP 深度嵌入)；桌面端代码协作浮窗 / 命令行终端原生交互 CLI (如 Claude Code) |
| **自主度评级** | L3（沙箱隔离下的半自动端到端执行；本地直连模式建议降级为 L2 逐关键操作人工确认） | L2~L3 (人在回路的渐进协同型) |
| **MVP P0 必做项** | • 可一键挂载指定工程目录的 Docker 隔离沙箱与端口自检启动器<br>• 事件流化的工具执行卡片 UI（Bash + 文件编辑 + xterm 终端）<br>• MCP 标准客户端接入（stdio/SSE），复用外部工具生态 | • 基于 Tree-sitter 的代码文件语法块精准解析 (函数级切块)<br>• 流式 SEARCH/REPLACE 差异补丁协议与客户端合并引擎<br>• 代码修改前置预览 (Diff 审阅界面) |
| **关键避坑红线** | ❌ 切忌在未明确警示或隔离边界的情况下让浏览器/桌面客户端直接无约束执行本地 Shell 与文件系统写入；<br>❌ 切忌将多工具结果全部无结构化塞进聊天流，导致用户失去对变更和终端状态的感知； | ❌ 千万不要在第一期要求大模型直接重写几千行的整个源文件 (Token 爆炸且极慢)；<br>❌ 切忌不给用户 Diff 预览就直接把代码落盘修改 (用户会产生极强不安全感)； |

## 3. 中间层：关键架构维度对比

| 架构维度 | OpenHands | Cursor |
| :--- | :--- | :--- |
| **Agent 编排** | 控制面与执行后端分离的多后端编排（Agent Canvas + Agent Server + Software Agent SDK），支持原生 Agent 与 ACP 外部 Agent 协作<br>• *将前端交互与后端沙箱运行时解耦，有助于同一套 Agent 内核平滑切换本地开发、自托管服务器与云端托管模式* | 多 Agent 协作流 (Tab 快速补全 Agent + Composer 全局编辑 Agent + Background Indexing Agent)<br>• *针对不同延迟要求的场景建立多 Agent 分工，不要用单个通用 Agent 处理所有任务* |
| **模型路由** | 多模型与跨 Agent 异构路由，支持本地模型、商业模型 API（企业版结合 LiteLLM proxy）及 ACP 外部智能体接入<br>• *对开源开发者平台而言，BYOK 多模型适配与复用现有 CLI Agent（ACP）能显著降低迁移门槛* | 基于任务复杂度的分级模型路由 (Claude 3.5 Sonnet 主力 + 自研低延迟小模型补全)<br>• *模型路由是控制 Agent 成本与延迟的最核心杠杆，按任务复杂度严格分流* |
| **工具链** | 内置 Bash/文件编辑器/搜索/任务工具集并配合前端 React 专属工具可视化卡片，同时原生支持 MCP 工具协议<br>• *为高频 Bash 与文件编辑提供定制可视化卡片、同时为泛工具提供通用回退，能在开发成本与体验间取得最佳平衡* | 围绕本地文件系统与语言服务器 (LSP) 的精细工具链<br>• *工具调用链设计必须遵循'最小上下文原则'，读取工具要支持精准切片* |
| **提示词工程** | 基于仓库内 `.agents/skills` 与自定义 Agent 角色隔离（只读 Planning Prompt vs 全功能 Execution Prompt）管理提示策略<br>• *把冗长工作流规范拆成可插拔 Skill 并隔离规划/执行权限，比堆砌单一超长 System Prompt 更易维护* | 分层规则注入与结构化 XML/Markdown 格式约束<br>• *工程型 Agent 的 Prompt 工程重在输出格式规范与代码 Diff 协议，而非长篇对话引导* |
| **上下文工程** | 通过 AgentContext 容器加载 Skills/元数据，并在单步推理前调用 Condenser（压缩器）对超限事件流历史进行压缩<br>• *将上下文压缩封装成事件流上的独立钩子（Condenser），可在不改动核心执行循环的情况下迭代压缩算法* | 本地 Merkle Tree 增量索引 + 混合检索 (BM25 + 向量嵌入 + LSP 引用)<br>• *代码上下文工程不能单靠向量检索，语法关系 (LSP) 的权重往往高于语义向量* |
| **数据流与状态管理** | 前端 Agent Canvas 与无状态/持久化执行后端通过类型化 ActionEvent 与 ObservationEvent 事件流交互<br>• *类型化的 Action/Observation 事件契约是前后端协同渲染及断点恢复的清晰边界* | 双向增量流式状态同步与本地会话 Checkpoint<br>• *状态管理必须考虑 Agent 失败或被用户打断时的恢复路径，建立完善的 Checkpoint 机制* |
| **安全沙箱** | 明确标注本地 Agent Canvas 本身不提供强隔离，生产或高风险场景需切换 Docker 容器、VM 或云端托管沙箱，并在企业版配合 Keycloak 与 Runtime API<br>• *对桌面/浏览器控制的开源编程 Agent，必须在快速本地模式之外内建一级 Docker/VM 隔离切换并明示安全边界* | 终端操作权限审批与文件修改权限白名单<br>• *桌面端工程 Agent 的安全关键在于'人机交接点'的设计，而非强隔离虚拟容器* |
| **人机协同** | 集中式 Web/Desktop 控制面统一查看对话、文件编辑、终端与自动化任务，并对高风险操作提供确认状态中断与人工审批<br>• *高自主度编码 Agent 仍需清晰的实时文件/终端可观测面板，才能让开发者在出错时及时介入* | 行内实时 Diff 审阅 + 自然语言直接交互编辑 (Inline Edit)<br>• *最顶级的 Agent 人机协作不是让 AI 替人做完一切，而是让人以最低认知成本审查和控制 AI* |
| **扩展生态** | 四维开放扩展体系：MCP 协议（SSE/SHTTP/stdio）、`.agents/skills` 技能包、插件机制、以及开放的 ACP（外部编码智能体）协议<br>• *控制面开源平台通过同时拥抱 MCP（工具标准）和 ACP（智能体标准）能够避免生态孤岛* | 完整兼容 VS Code 扩展生态 + MCP 协议与自定义规则生态<br>• *不要从零构建新环境，寄生于现有成熟工作流（如 IDE / 浏览器）能加速 Agent 生态繁荣* |

## 4. 各应用关键洞察

### OpenHands
1. 采用客户端与执行面彻底解耦的「Agent Canvas + Agent Server + Runtime Sandbox」架构，既可本地直连也可切到 Docker/VM/Modal/OpenHands Cloud 隔离后端
2. Agent 核心遵循无状态事件驱动（ActionEvent / ObservationEvent）+ 可插拔 Condenser 上下文压缩器模型，通过 Software Agent SDK 统一本地、云端与自动化工作流
3. 安全模型在文档中诚实区分边界：默认本地 Agent Canvas 不做强隔离，高风险执行需显式切换容器/VM 沙箱或配合 SecurityAnalyzer 与操作确认
4. 支持通过 ACP 协议将 Claude Code、Codex、Gemini CLI 等外部 Agent 直接编排纳入统一工作台，并用 MCP 标准化接入外部工具服务

### Cursor
1. 双 Agent 架构分离极低延迟补全与高复杂度多文件编辑，兼顾速度与智能
2. 代码切块遵循 Tree-sitter AST 语法树，结合 LSP 符号检索，远优于纯文本 RAG
3. Diff 补丁协议 (Search/Replace) 极大压缩了 Token 输出量并降低网络开销
4. 行内单步审查与撤销快照给开发者极致的安全感与确定性
5. 利用现有 VS Code 庞大生态与 MCP 协议快速撬动开发者社区

## 5. 分析说明

> **说明**：本对比报告基于自动化采集的各产品公开信息（技术文章、开源代码、架构解析等）生成，旨在提炼不同产品在 Harness 架构设计上的差异与共性，为产品形态选型与系统设计提供参考。
