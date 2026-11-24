"""Mermaid 架构流程图生成器"""
from typing import Any


class DiagramGenerator:
    """生成应用 Harness 架构的 Mermaid 流程图"""

    def generate(self, analysis: Any) -> str:
        """根据分析对象生成 Mermaid 流程图代码字符串"""
        # 如果 analysis 自身已经携带了有效的 mermaid_diagram，直接返回
        existing = getattr(analysis, "mermaid_diagram", None)
        if not existing and isinstance(analysis, dict):
            existing = analysis.get("mermaid_diagram")

        if existing and isinstance(existing, str) and "flowchart" in existing:
            return existing.strip()

        # 根据应用分类或通用架构生成适配的 Mermaid 图
        app_name = (
            getattr(analysis, "app_display_name", None)
            or getattr(analysis, "app_name", None)
            or "AI 应用"
        )
        category = str(getattr(analysis, "category", "") or "")

        # 判断品类定制节点
        if "工程" in category or "engineering" in category.lower():
            return (
                "flowchart TD\n"
                f'    User(["开发者 / 用户"]) --> IDE["{app_name} 客户端 / IDE 插件"]\n'
                '    IDE --> ContextMgr["代码上下文索引 (LSP / AST / Embeddings)"]\n'
                '    ContextMgr --> Orchestrator["Agent 编排与模型路由"]\n'
                '    Orchestrator --> LLM["大语言模型 (Reasoning / Code LLM)"]\n'
                '    LLM --> ToolCall{"工具调用决策"}\n'
                '    ToolCall -- 代码补全/重构 --> DiffEngine["文件编辑与 Diff 引擎"]\n'
                '    ToolCall -- 终端命令/测试 --> Sandbox["隔离代码执行沙箱"]\n'
                '    DiffEngine --> IDE\n'
                '    Sandbox --> Orchestrator\n'
                '    Orchestrator --> Mem["长短期记忆 / 规则沉淀 (.cursorrules 等)"]'
            )
        elif "数据" in category or "data" in category.lower():
            return (
                "flowchart TD\n"
                f'    User(["业务分析师 / 用户"]) --> WebUI["{app_name} Web 界面"]\n'
                '    WebUI --> SchemaParser["数据 Schema 理解与元数据管理"]\n'
                '    SchemaParser --> Orchestrator["NL2SQL / Python 代码生成 Agent"]\n'
                '    Orchestrator --> LLM["大语言模型"]\n'
                '    LLM --> SQLValidator{"SQL / 查询安全性校验"}\n'
                '    SQLValidator -- 校验通过 --> QueryEngine["数据库 / 计算引擎执行"]\n'
                '    SQLValidator -- 报错或拒绝 --> Orchestrator\n'
                '    QueryEngine --> Viz["图表渲染与数据洞察解释"]\n'
                '    Viz --> WebUI'
            )
        elif "知识" in category or "knowledge" in category.lower():
            return (
                "flowchart TD\n"
                f'    User(["研究者 / 用户"]) --> UI["{app_name} 检索与对话界面"]\n'
                '    UI --> QueryDecomp["问题拆解与多路由搜索"]\n'
                '    QueryDecomp --> RAG["大规模向量检索与重排 (Reranker)"]\n'
                '    RAG --> Orchestrator["引用溯源与事实核验 Agent"]\n'
                '    Orchestrator --> LLM["大语言模型"]\n'
                '    LLM --> FactCheck{"引用一致性校验"}\n'
                '    FactCheck -- 核验通过 --> UI\n'
                '    FactCheck -- 幻觉抑制重试 --> Orchestrator'
            )
        elif "创作" in category or "creative" in category.lower():
            return (
                "flowchart TD\n"
                f'    User(["创作者"]) --> Canvas["{app_name} 交互画布"]\n'
                '    Canvas --> PromptEngine["提示词增强与风格控制"]\n'
                '    PromptEngine --> Router["多模态生成路由"]\n'
                '    Router --> Diffusion["多模态大模型 / Diffusion"]\n'
                '    Diffusion --> PostProcess["后处理与迭代变体引擎"]\n'
                '    PostProcess --> Canvas'
            )
        elif "自动化" in category or "automation" in category.lower():
            return (
                "flowchart TD\n"
                f'    User(["用户"]) --> GoalInput["{app_name} 任务目标输入"]\n'
                '    GoalInput --> Planner["多步目标拆解与状态机规划"]\n'
                '    Planner --> Executor["Agent 执行器 (Browser / OS CLI)"]\n'
                '    Executor --> LLM["大语言模型"]\n'
                '    LLM --> ActionCheck{"执行结果与环境反馈"}\n'
                '    ActionCheck -- 出现异常 --> SelfHeal["容错重试与自愈机制"]\n'
                '    SelfHeal --> Planner\n'
                '    ActionCheck -- 步骤完成 --> Planner\n'
                '    ActionCheck -- 最终完成 --> GoalInput'
            )
        else:
            return (
                "flowchart TD\n"
                f'    User(["用户"]) --> UI["{app_name} 交互界面"]\n'
                '    UI --> Context["上下文管理与提示词组装"]\n'
                '    Context --> Orchestrator["Agent 编排与模型路由"]\n'
                '    Orchestrator --> LLM["大语言模型 (LLM)"]\n'
                '    LLM --> ToolCall{"工具调用决策"}\n'
                '    ToolCall -- 执行工具 --> Sandbox["安全沙箱 / 执行环境"]\n'
                '    Sandbox -- 执行结果 --> Orchestrator\n'
                '    ToolCall -- 最终输出 --> UI'
            )
