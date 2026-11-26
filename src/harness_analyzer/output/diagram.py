"""Mermaid 架构与机制参考图生成器（覆盖总体拓扑、PM决策、Guard漏斗、维度机制与横向对比）"""
from __future__ import annotations

import re
from typing import Any
from urllib.parse import urlparse


class DiagramGenerator:
    """生成应用 Harness 架构与各分析章节的 Mermaid 参考图"""

    @staticmethod
    def _safe_label(text: Any, max_len: int = 44) -> str:
        """清洗文本为合法 Mermaid 引号内节点标签，避免括号/HTML/换行引发语法错误"""
        s = str(text or "").replace("\n", " ").replace('"', "'").strip()
        s = re.sub(r"<[^>]+>", " ", s)
        s = s.replace("[", "(").replace("]", ")").replace("{", "(").replace("}", ")")
        s = re.sub(r"\s+", " ", s).strip()
        if len(s) > max_len:
            s = s[: max_len - 1].rstrip() + "…"
        return s or "N/A"

    @staticmethod
    def _get(obj: Any, *keys: str, default: Any = None) -> Any:
        for k in keys:
            if isinstance(obj, dict) and k in obj and obj[k] is not None:
                return obj[k]
            if hasattr(obj, k) and getattr(obj, k) is not None:
                return getattr(obj, k)
        return default

    def generate(self, analysis: Any) -> str:
        """生成系统总体架构拓扑 Mermaid 图"""
        existing = getattr(analysis, "mermaid_diagram", None)
        if not existing and isinstance(analysis, dict):
            existing = analysis.get("mermaid_diagram")

        if existing and isinstance(existing, str) and "flowchart" in existing:
            return existing.strip()

        app_name = self._safe_label(
            self._get(analysis, "app_display_name", "app_name", default="AI 应用"),
            max_len=28,
        )
        category = str(self._get(analysis, "category", default="") or "")

        if "工程" in category or "engineering" in category.lower():
            return (
                "flowchart TD\n"
                f'    User(["开发者 / 用户"]) --> IDE["{app_name} 客户端 / IDE / CLI"]\n'
                '    IDE --> ContextMgr["代码上下文索引 (LSP / AST / Agentic Search)"]\n'
                '    ContextMgr --> Orchestrator["Agent 编排与模型路由"]\n'
                '    Orchestrator --> LLM["大语言模型 (Reasoning / Code LLM)"]\n'
                '    LLM --> ToolCall{"工具调用决策"}\n'
                '    ToolCall -- 代码补全/重构 --> DiffEngine["文件编辑与 Diff / Patch 引擎"]\n'
                '    ToolCall -- 终端命令/测试 --> Sandbox["隔离代码执行沙箱"]\n'
                '    DiffEngine --> IDE\n'
                '    Sandbox --> Orchestrator\n'
                '    Orchestrator --> Mem["长短期记忆 / 规则沉淀 (AGENTS.md / Skills)"]'
            )
        if "数据" in category or "data" in category.lower():
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
        if "知识" in category or "knowledge" in category.lower():
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
        if "创作" in category or "creative" in category.lower():
            return (
                "flowchart TD\n"
                f'    User(["创作者"]) --> Canvas["{app_name} 交互画布"]\n'
                '    Canvas --> PromptEngine["提示词增强与风格控制"]\n'
                '    PromptEngine --> Router["多模态生成路由"]\n'
                '    Router --> Diffusion["多模态大模型 / Diffusion"]\n'
                '    Diffusion --> PostProcess["后处理与迭代变体引擎"]\n'
                '    PostProcess --> Canvas'
            )
        if "自动化" in category or "automation" in category.lower():
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

    def generate_pm_flow(self, analysis: Any, pm_data: Any) -> str:
        """生成应用层 PM 方案决策与自主度边界 Mermaid 图"""
        app_name = self._safe_label(
            self._get(analysis, "app_display_name", "app_name", default="目标应用"), 24
        )
        autonomy = self._safe_label(self._get(pm_data, "autonomy_level", default="L2 (协同辅助型)"), 34)
        must_haves = self._get(pm_data, "mvp_must_haves", default=[]) or []
        nice_to_haves = self._get(pm_data, "mvp_nice_to_haves", default=[]) or []
        anti_patterns = self._get(pm_data, "anti_patterns_to_avoid", default=[]) or []

        artifact = self._get(analysis, "intermediate_artifact", default=None)
        guard_summary = self._get(artifact, "guard_summary", default={}) or {}
        strict_n = guard_summary.get("strict_verified", 0)
        warnings_n = len(self._get(artifact, "inferred_warnings", default=[]) or [])

        p0_sample = self._safe_label(must_haves[0], 30) if must_haves else "核心闭环与人工审批"
        anti_sample = self._safe_label(anti_patterns[0], 30) if anti_patterns else "无沙箱越权执行"

        return (
            "flowchart LR\n"
            f'    Facts["已实证技术锚点 ({strict_n} 项)"] --> Decide["{app_name} 产品定位与自主度: {autonomy}"]\n'
            f'    Friction["社区真实痛点与警示 ({warnings_n} 项风险)"] --> Decide\n'
            f'    Decide --> P0["V1 P0 必做 ({len(must_haves)} 项): {p0_sample}"]\n'
            f'    Decide --> P1["V2 P1 增强 ({len(nice_to_haves)} 项): 进阶路由与生态"]\n'
            f'    Decide -. 避坑红线 .-> Avoid["严禁 ({len(anti_patterns)} 项): {anti_sample}"]'
        )

    def generate_evidence_flow(self, artifact: Any, analysis: Any = None) -> str:
        """生成中间产物 Guard 分层验证与采集漏斗 Mermaid 图"""
        source_count = self._get(analysis, "source_count", default=0) if analysis else 0
        search_cov = self._get(artifact, "search_coverage", default=None)
        cov_pct = f"{float(self._get(search_cov, 'coverage_score', default=0.0)):.0%}" if search_cov else "N/A"
        zh_hits = self._get(search_cov, "zh_hits", default=0) if search_cov else 0
        en_hits = self._get(search_cov, "en_hits", default=0) if search_cov else 0
        blocked_n = len(self._get(search_cov, "blocked_sources", default=[]) or []) if search_cov else 0

        gs = self._get(artifact, "guard_summary", default={}) or {}
        strict_n = gs.get("strict_verified", 0)
        partial_n = gs.get("partial_verified", 0)
        capped_n = gs.get("unverified_capped", 0)

        lines = [
            "flowchart LR",
            f'    Collect["五路采集 ({source_count} 条信源 | 中{zh_hits}/英{en_hits} | 覆盖率 {cov_pct})"] --> Guard{{"分维度 Guard 原文校验"}}',
            f'    Guard -- "一级/多重实证 ({strict_n})" --> Core["✅ P0 强实证锚点"]',
            f'    Guard -- "单条/二手实证 ({partial_n})" --> Mod["⚠️ 受限补充论据 (≤3★)"]',
            f'    Guard -- "缺原文实证 ({capped_n})" --> Warn["🚧 推断封顶警示 (≤2★)"]',
        ]
        if blocked_n:
            lines.append(f'    Collect -. "反爬/429熔断" .-> Blocked["🛡️ 礼貌跳过 ({blocked_n} 处)"]')
        return "\n".join(lines)

    def generate_dimensions_chart(
        self,
        dims: list[Any],
        title: str = "维度实证置信度分布",
        weights_map: dict[str, int] | None = None,
    ) -> str:
        """生成维度置信度（及权重）xychart-beta 柱状图"""
        if not dims:
            return ""
        labels = []
        confs = []
        weights = []
        for d in dims[:9]:
            raw_lbl = self._get(d, "label", "dimension_label", "dimension", default="dim")
            clean_lbl = self._safe_label(raw_lbl, max_len=10)
            labels.append(f'"{clean_lbl}"')
            c = self._get(d, "confidence", default=3)
            confs.append(str(max(1, min(5, int(round(float(c) * 5 if isinstance(c, float) and c <= 1 else float(c)))))))
            if weights_map is not None:
                dim_key = str(self._get(d, "dimension", default=""))
                weights.append(str(weights_map.get(dim_key, 3)))

        lines = [
            "xychart-beta",
            f'    title "{self._safe_label(title, 36)}"',
            f'    x-axis [{", ".join(labels)}]',
            '    y-axis "评分 (1-5★)" 0 --> 5',
            f'    bar [{", ".join(confs)}]',
        ]
        if weights:
            lines.append(f'    line [{", ".join(weights)}]')
        return "\n".join(lines)

    def generate_dimension_diagram(self, item: Any, category: str = "engineering", app_name: str = "AI 应用") -> str:
        """为单个 Harness 维度返回自定义或领域匹配的 Mermaid 机制参考图"""
        custom = self._get(item, "mermaid_diagram", default="")
        if isinstance(custom, str) and custom.strip() and any(
            k in custom for k in ("flowchart", "sequenceDiagram", "stateDiagram", "xychart-beta")
        ):
            return custom.strip().replace("```mermaid", "").replace("```", "").strip()

        dim_key = str(self._get(item, "dimension", default="")).lower()
        lbl = self._safe_label(self._get(item, "label", "dimension_label", default=dim_key), 24)
        app_lbl = self._safe_label(app_name, 18)

        templates: dict[str, str] = {
            "agent_orchestration": (
                "sequenceDiagram\n"
                f'    participant U as "{app_lbl} 用户"\n'
                '    participant O as "Orchestrator / Loop"\n'
                '    participant M as "LLM"\n'
                '    participant T as "Tools / Subagent"\n'
                '    U->>O: 输入工程目标\n'
                '    loop 推理-执行闭环\n'
                '        O->>M: 上下文与工具 Schema\n'
                '        M-->>O: 结构化 Tool Call\n'
                '        O->>T: 权限校验并执行\n'
                '        T-->>O: 返回 Observation\n'
                '    end\n'
                '    O-->>U: 产出最终变更或结果'
            ),
            "model_routing": (
                "flowchart LR\n"
                f'    Req["{app_lbl} 任务请求"] --> Router{{"模型/推理档位路由"}}\n'
                '    Router -- 高频/实时探索 --> Fast["轻量高速模型 / Low Effort"]\n'
                '    Router -- 复杂架构/疑难修复 --> Strong["旗舰推理模型 / High Effort"]\n'
                '    Router -. 限流/跨厂商兜底 .-> Ext["Proxy / ACP / BYOK"]'
            ),
            "tool_chain": (
                "flowchart LR\n"
                '    LLM["LLM Tool Request"] --> Gate{"Schema + 风险策略校验"}\n'
                '    Gate -- 内置核心工具 --> Builtin["Read / Edit / Patch / Exec"]\n'
                '    Gate -- 开放标准协议 --> MCP["MCP Servers (stdio / SSE / SHTTP)"]\n'
                '    Builtin --> Obs["结构化 Observation 回传"]\n'
                '    MCP --> Obs'
            ),
            "prompt_engineering": (
                "flowchart LR\n"
                '    Sys["系统 Preset / 总纲"] --> Stack["Prompt 运行时装配层"]\n'
                '    ToolDesc["工具微规程 (Description)"] --> Stack\n'
                '    ProjMem["仓库规则 (AGENTS.md / CLAUDE.md / Skills)"] --> Stack\n'
                f'    Stack --> Call["发送至 {app_lbl} 模型"]'
            ),
            "context_engineering": (
                "flowchart LR\n"
                '    Repo["工作区 / 知识源"] --> Retrieve["按需检索 (Search / AST / RAG)"]\n'
                '    Hist["历史消息流"] --> Compress["超限压缩 / 标签保留"]\n'
                '    Retrieve --> Window["模型上下文窗口"]\n'
                '    Compress --> Window'
            ),
            "data_flow_state": (
                "stateDiagram-v2\n"
                '    [*] --> Idle: 新建或恢复会话\n'
                '    Idle --> Inferring: 组装上下文调用 LLM\n'
                '    Inferring --> ToolExecuting: 输出工具调用事件\n'
                '    Inferring --> WaitingApproval: 触发敏感审批\n'
                '    WaitingApproval --> ToolExecuting: 人工批准\n'
                '    ToolExecuting --> Inferring: 写入状态并回传 Observation\n'
                '    Inferring --> [*]: 任务完成持久化'
            ),
            "security_sandbox": (
                "flowchart LR\n"
                '    Act["提议执行写文件 / Shell / 联网"] --> Pol{"可执行权限与策略网关"}\n'
                '    Pol -- 命中受限规则 --> Human["人工审批 / Guardian 复审"]\n'
                '    Pol -- 安全策略允许 --> Box["受控沙箱 (OS / Docker / Cloud VM)"]\n'
                '    Human -- 批准升级 --> Box\n'
                '    Human -- 拒绝 --> Abort["拦截终止"]'
            ),
            "human_ai_collaboration": (
                "flowchart LR\n"
                f'    Agent["{app_lbl} 流式产出 / 计划"] --> UI["差异预览 / 工具可视化卡片"]\n'
                '    UI --> Check{"人类审查介入点"}\n'
                '    Check -- Accept / Approve --> Apply["应用变更继续执行"]\n'
                '    Check -- Reject / Edit --> Steer["人工纠正方向回传"]'
            ),
            "extensibility_ecosystem": (
                "flowchart LR\n"
                f'    Core["{app_lbl} 核心引擎"] --> MCP["MCP 工具协议生态"]\n'
                '    Core --> Skills["Markdown Skills / 规则模板"]\n'
                '    Core --> Hooks["Before / After 生命周期 Hooks"]\n'
                '    Core --> SDK["SDK / IDE Server 开放协议"]'
            ),
            "sandbox_model": (
                "flowchart TD\n"
                '    Cmd["命令与文件操作请求"] --> Mode{"隔离模式选择"}\n'
                '    Mode -- 轻量开发 --> Local["本地 OS 权限边界 (文件/网络策略)"]\n'
                '    Mode -- 强隔离任务 --> Container["Docker / 微VM / 云端沙箱"]'
            ),
            "code_understanding": (
                "flowchart LR\n"
                '    Root["工程根目录 (Workspace)"] --> Scan["符号 / AST / Grep / Agentic Search"]\n'
                '    Scan --> Graph["跨文件引用与依赖心智图"]\n'
                '    Graph --> EditCtx["精准定位待改片段"]'
            ),
            "diff_management": (
                "flowchart LR\n"
                '    Gen["生成增量补丁 (Patch / Diff)"] --> Verify["上游语法与审批检查"]\n'
                '    Verify --> Apply["原子写入目标工作区"]\n'
                '    Apply --> Delta["产出文件 Delta 变更回执"]'
            ),
            "terminal_management": (
                "flowchart LR\n"
                '    Shell["终端命令下发"] --> PTY["PTY / Exec Server 会话"]\n'
                '    PTY --> Stream["流式捕获 Stdout / Stderr / 退出码"]\n'
                '    Stream -- 退出码非0 --> SelfFix["错误回传触发自愈修复"]'
            ),
            "checkpoint_rollback": (
                "flowchart LR\n"
                '    Pre["编辑前自动快照 / Git Stash"] --> Mutate["多文件变更应用"]\n'
                '    Mutate --> Check{"结果符合预期?"}\n'
                '    Check -- 是 --> Commit["保留进入下一轮"]\n'
                '    Check -- 否 --> Rollback["一键回滚恢复安全点"]'
            ),
            "nl2sql_pipeline": (
                "flowchart LR\n"
                '    NL["自然语言查数"] --> Schema["Schema 裁剪与口径对齐"]\n'
                '    Schema --> SQL["生成候选 SQL"]\n'
                '    SQL --> DryRun{"语法/安全检查 & 执行"}\n'
                '    DryRun -- 报错 --> SQL\n'
                '    DryRun -- 成功 --> Chart["结果可视化输出"]'
            ),
            "rag_pipeline": (
                "flowchart LR\n"
                '    Q["用户提问"] --> Expand["查询改写与多路检索"]\n'
                '    Expand --> Recall["混合召回 (稠密 + 稀疏)"]\n'
                '    Recall --> Rerank["Cross-Encoder 语义重排"]\n'
                '    Rerank --> Cite["句级引用锚定生成"]'
            ),
            "dag_state_machine": (
                "flowchart LR\n"
                '    Trigger["事件 / 定时触发"] --> DAG["状态机 / DAG 调度"]\n'
                '    DAG --> Retry["异常指数退避与断点续跑"]\n'
                '    Retry --> Notify["SLA 监控与结果归档"]'
            ),
        }
        if dim_key in templates:
            return templates[dim_key]

        key_dec = self._get(item, "key_decisions", default=[]) or []
        dec_lbl = self._safe_label(key_dec[0], 32) if key_dec else "核心设计决策"
        sum_lbl = self._safe_label(self._get(item, "summary", default=lbl), 32)
        return (
            "flowchart LR\n"
            f'    In["{app_lbl} {lbl}"] --> Dec["{dec_lbl}"]\n'
            f'    Dec --> Out["{sum_lbl}"]'
        )

    def generate_patterns_diagram(self, analysis: Any) -> str:
        """生成识别到的经典架构模式组合 Mermaid 图"""
        patterns = self._get(analysis, "matched_patterns", default=[]) or []
        if not patterns:
            return ""
        app_name = self._safe_label(self._get(analysis, "app_display_name", "app_name", default="AI 应用"), 24)
        lines = ["flowchart LR", f'    Core["{app_name} 工程 Harness 内核"]']
        for idx, p in enumerate(patterns[:6]):
            pname = self._safe_label(self._get(p, "pattern_name", default=f"pattern_{idx}"), 28)
            pconf = self._get(p, "confidence", default=3)
            ev_count = len(self._get(p, "evidence", default=[]) or [])
            lines.append(f'    Core --> P{idx}["{pname} ({pconf}★ | {ev_count}条证据)"]')
        return "\n".join(lines)

    def generate_source_traceability_diagram(self, analysis: Any, artifact: Any = None) -> str:
        """生成事实层信源分布与采集通道汇总 Mermaid 图"""
        raw_sources = self._get(analysis, "raw_sources", "evidence_sources", default=[]) or []
        gh_n = docs_n = rev_n = other_n = 0
        for src in raw_sources:
            u = str(src).lower()
            host = urlparse(u).netloc
            if "github.com" in host or "raw.githubusercontent.com" in host:
                gh_n += 1
            elif any(k in u for k in ("docs.", "blog", "anthropic", "claude.com", "openai.com", "all-hands.dev")):
                docs_n += 1
            elif any(k in host for k in ("news.ycombinator.com", "reddit.com", "g2.com", "producthunt.com", "zhihu.com", "v2ex.com", "juejin.cn")):
                rev_n += 1
            else:
                other_n += 1

        search_cov = self._get(artifact, "search_coverage", default=None) if artifact else None
        blocked_n = len(self._get(search_cov, "blocked_sources", default=[]) or []) if search_cov else 0
        app_name = self._safe_label(self._get(analysis, "app_display_name", "app_name", default="应用"), 20)

        return (
            "flowchart TD\n"
            f'    Root["{app_name} 信源追踪总计 ({len(raw_sources)} 篇)"] --> GH["GitHub 源码/仓库/Issues: {gh_n} 条"]\n'
            f'    Root --> Docs["官方文档与技术文章: {docs_n} 条"]\n'
            f'    Root --> Comm["社区评测与真实吐槽: {rev_n} 条"]\n'
            f'    Root --> Other["泛网络与技术解析: {other_n} 条"]\n'
            f'    Root -. 反爬熔断 .-> Blk["礼貌跳过/限流: {blocked_n} 处"]'
        )

    def generate_comparison_chart(self, analyses: list[Any]) -> str:
        """生成横向对比报告的置信度 xychart-beta 柱状图"""
        if not analyses:
            return ""
        names = []
        confs = []
        for idx, a in enumerate(analyses):
            n = self._safe_label(self._get(a, "app_display_name", "app_name", default=f"App{idx+1}"), 16)
            names.append(f'"{n}"')
            c = self._get(a, "confidence_overall", "confidence", default=3) or 3
            val = max(1, min(5, int(round(float(c) * 5 if isinstance(c, float) and c <= 1 else float(c)))))
            confs.append(str(val))
        return "\n".join([
            "xychart-beta",
            '    title "架构总体置信度横向对比 (1-5★)"',
            f'    x-axis [{", ".join(names)}]',
            '    y-axis "置信度" 0 --> 5',
            f'    bar [{", ".join(confs)}]',
        ])

    def generate_comparison_flow(self, analyses: list[Any]) -> str:
        """生成横向对比的架构路线与定位差异 Mermaid 图"""
        if not analyses:
            return ""
        lines = ["flowchart LR"]
        for idx, a in enumerate(analyses):
            name = self._safe_label(self._get(a, "app_display_name", "app_name", default=f"App{idx+1}"), 18)
            cat = self._safe_label(self._get(a, "category", default="general"), 12)
            pm = self._get(a, "pm_guidance", default=None)
            auto = self._safe_label(self._get(pm, "autonomy_level", default="L2"), 24) if pm else "N/A"
            src_n = self._get(a, "source_count", default=0)
            lines.append(f'    A{idx}["{name} ({cat} | {src_n}源)"] --> R{idx}["自主度与形态: {auto}"]')
        return "\n".join(lines)
