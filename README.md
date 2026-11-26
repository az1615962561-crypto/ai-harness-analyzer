# 🔍 AI Harness Analyzer

> 从公开信息源自动采集并分析主流 AI 应用背后的 **Harness 架构**，生成结构化分析报告，助力团队学习先进 AI 架构进行高效落地与项目搭建。

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://www.python.org/)
[![CLI](https://img.shields.io/badge/CLI-Typer%20%2B%20Rich-green.svg)](https://typer.tiangolo.com/)
[![License](https://img.shields.io/badge/License-MIT-purple.svg)](LICENSE)

---

## 🎯 核心理念：双层架构分析模型

面对业界形形色色的 AI 应用，传统一刀切的分析往往流于表面。本项目提出**「分类定性 → 双层分析」**框架：

```
输入 AI 应用 ───> 第一步：分类定性 (工程 / 数据 / 知识 / 创作 / 自动化)
                       │
       ┌───────────────┴───────────────┐
       ▼                               ▼
 ┌───────────────┐             ┌────────────────┐
 │   共性层      │             │    特性层      │
 │  9 大通用维度  │             │ 5 大品类专属维度 │
 └───────────────┘             └────────────────┘
       │                               │
       └───────────────┬───────────────┘
                       ▼
       输出：深度架构分析与借鉴建议报告
```

### 1. 五大分类与核心难题

分类的唯一标准：**这类 Agent 的 Harness 必须解决的不可绕过的核心工程难题是什么？**

| 分类 | 核心 Harness 难题 | 代表产品 |
| :--- | :--- | :--- |
| 🔧 **工程型** | 安全代码执行环境 + 代码库深度理解与变更回滚 | Cursor, Claude Code, Devin, Antigravity |
| 📊 **数据型** | 业务意图到精准查询翻译 (NL2SQL) + 交互式可视化 | ChatBI, Julius AI, Databricks Assistant |
| 🧠 **知识型** | 大规模知识精准切分召回 (RAG) + 严格引用溯源 | Perplexity, NotebookLM, Notion AI |
| 🎨 **创作型** | 多模态异构模型协同管线 + 用户满意的渐进迭代 | Midjourney, v0.dev, Bolt.new |
| 🤖 **自动化型** | 多系统跨长链路工作流编排 + 强健容错重试恢复 | AutoGPT, CrewAI, LangGraph, Manus AI |

### 2. 9 大共性维度

1. **Agent 编排** (Agent Orchestration)
2. **模型路由** (Model Routing)
3. **工具调用链** (Tool Chain)
4. **Prompt 工程** (Prompt Engineering)
5. **上下文工程** (Context Engineering)
6. **数据流与状态管理** (Data Flow & State)
7. **安全与沙箱** (Security & Sandbox)
8. **人机协作模式** (Human-in-the-Loop)
9. **扩展性与生态** (Extensibility & Ecosystem)

> 各品类对这 9 个维度赋予动态权重（1~5 分），并自动追加 5 个品类专属维度（如工程型的*沙箱隔离模型*、数据型的*NL2SQL管线*、知识型的*引用链管理*等）。

---

## 🚀 快速上手

### 1. 安装环境

```bash
git clone https://github.com/az1615962561-crypto/ai-harness-analyzer.git
cd ai-harness-analyzer

# 推荐使用 uv 或 pip 安装
pip install -e .
```

### 2. 两种运行方式（智能体零 Key 直跑 & CLI 独立 API 跑）

#### 方式 A：Coding Agent 原生直跑（零 LLM API Key，智能体拉仓库即用）
适用于在 `Antigravity`、`Codex`、`Claude Code`、`Cursor` 等编码智能体中直接使用智能体自身推理能力：
```bash
# 1. 真机联网五路采集原始事实与契约（无需 LLM Key）
harness collect <app_name> --lang zh

# 2. 智能体读取 reports/<app_name>.collected.json 完成 9+5 维度、模式识别与 PM 方案，
#    产出 reports/<app_name>.agent_draft.json

# 3. 由程序执行分维度 Guard 原文硬校验、生成 Mermaid 图、写入 SQLite 缓存与双报告
harness finalize reports/<app_name>.agent_draft.json
```

#### 方式 B：CLI 命令行独立 API 自动化运行（适合终端批处理 / CI / 无人值守）
复制环境配置并填写任一主流模型 Key：
```bash
cp .env.example .env
# 在 .env 中填入 GEMINI_API_KEY / OPENAI_API_KEY / ANTHROPIC_API_KEY
```

### 3. 命令行操作

```bash
# 0. 检查环境就绪状态
harness doctor

# 1. 查看已收录的 22+ 款主流 AI 应用
harness list
harness info cursor

# 2a. 方式 A：智能体零 Key 两段式实测（先采集后校验交付）
harness collect cline --lang zh
harness finalize reports/cline.agent_draft.json

# 2b. 方式 B：CLI 一键全自动分析（需配置 LLM API Key）
harness analyze cursor --depth full --lang zh

# 2c. 离线专家基准库模式（零 API Key 查看标杆报告与中间产物）
harness analyze cursor --offline

# 3. 对本地 Electron app.asar 或解包 JS 目录执行深度逆向取证（自动/可选调用 rea-agents）
harness collect my-app --local-app /abs/path/to/app.asar --use-rea

# 4. 对比多款应用的 Harness 架构差异（两种方式生成的报告互通对比）
harness compare cursor chatbi

# 5. 查看报告与缓存管理
harness report cursor
harness cache list
```

### 4. 跨 Agent 智能体零锁定使用（Codex / Claude Code / Cursor / Antigravity / OpenHands）

本项目遵循跨平台开放规范，**不绑定任何特定 IDE 或平台**。任意编码智能体拉取仓库后即可直接读取指引并调用：

- [`AGENTS.md`](AGENTS.md)：通用跨智能体运行手册（Codex、Cursor、Antigravity、OpenHands 等直接识别）
- [`CLAUDE.md`](CLAUDE.md)：Claude Code 入口指引
- [`.agents/skills/harness-analyzer/SKILL.md`](.agents/skills/harness-analyzer/SKILL.md)：开放标准 Skill 定义，教智能体何时调用、如何读取中间产物 `reports/<app>.intermediate.json` 与最终报告 `reports/<app>.md`

---

## 📂 项目结构

```
├── AGENTS.md                   # 🤖 跨智能体通用操作指引 (Codex/Cursor/Antigravity等)
├── CLAUDE.md                   # 🤖 Claude Code 入口指引
├── LICENSE                     # 📄 MIT 开源协议
├── .agents/skills/             # 🧩 开放标准 Agent Skill 定义
│   └── harness-analyzer/SKILL.md
├── docs/                       # 📚 项目知识库
│   ├── README.md               # 知识库索引
│   ├── project-plan.md         # 实施方案与技术选型
│   ├── classification.md       # 五大分类体系深度解析
│   ├── dimensions.md           # 双层维度与权重指标规范
│   └── logical-mindmap.md      # 核心逻辑思维导图与推演闭环
├── src/harness_analyzer/       # 💻 核心源代码
│   ├── cli.py                  # Typer + Rich 终端入口
│   ├── models/                 # Pydantic 强类型数据模型
│   ├── registry/               # 应用知识注册表 (22+ 预置应用 YAML)
│   ├── collectors/             # 五路采集器 (双语搜索/GitHub深读/博客下钻/RE+rea-agents/真实评论)
│   ├── analyzer/               # Fact Sheet + 并发9+5分析 + 分维度Guard + 中间产物 + PM转化
│   ├── output/                 # 三层 Markdown 报告、PM对比矩阵与 Mermaid 架构图
│   └── storage/                # SQLite 报告持久化与缓存
├── data/
│   ├── patterns/               # 常见 Agent 架构模式库 (YAML)
│   └── prompts/                # 结构化抽取提示词模板
└── reports/                    # 📊 生成的中间产物 (.intermediate.json) 与架构报告 (.md)
```

---

## 📚 详细设计与交付物文档

- [项目知识库导航](docs/README.md)
- [五大分类体系与决策边界](docs/classification.md)
- [Harness 架构 9+5 维度深度指标矩阵](docs/dimensions.md)
- [项目整体设计与演进路线](docs/project-plan.md)

---

## License

[MIT](LICENSE)
