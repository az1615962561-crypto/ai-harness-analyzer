"""自动化类 AI 应用专属分析器"""
from .base import BaseSpecializedAnalyzer
from harness_analyzer.models.dimension import SpecializedDimension


class AutomationAnalyzer(BaseSpecializedAnalyzer):
    category = "automation"

    def get_dimension_prompts(self) -> dict[str, tuple[str, str]]:
        return {
            SpecializedDimension.AUTO_DAG_STATE_MACHINE.value: (
                SpecializedDimension.AUTO_DAG_STATE_MACHINE.label,
                "分析 DAG/状态机引擎：\n"
                "1) 工作流定义与状态表示（DAG/状态图/DSL/循环 ReAct 状态机）？\n"
                "2) 节点与流控支持（条件分支/循环迭代/并行/子流程）？\n"
                "3) 长耗时运行状态持久化与挂起唤醒机制？\n"
                "4) 工作流版本管理、调试与单步回放？\n"
                "5) 资源预算上限与死循环熔断防护？",
            ),
            SpecializedDimension.AUTO_MULTI_AGENT_PROTOCOL.value: (
                SpecializedDimension.AUTO_MULTI_AGENT_PROTOCOL.label,
                "分析多 Agent 通信协议：\n"
                "1) 多 Agent 协作拓扑（层级 Planner-Worker / 对等讨论 / Swarm 动态 Handoff）？\n"
                "2) Agent 间上下文共享方式（共享黑板/结构化消息/Scoped Memory）？\n"
                "3) 角色分工、任务交接与子任务结果聚合协议？\n"
                "4) 多 Agent 冲突仲裁、一致性校验与去重机制？\n"
                "5) 通信开销与循环调用保护？",
            ),
            SpecializedDimension.AUTO_FAULT_TOLERANCE.value: (
                SpecializedDimension.AUTO_FAULT_TOLERANCE.label,
                "分析容错与重试恢复：\n"
                "1) 错误分类体系（瞬时限流/参数错误/逻辑失败/需人工介入）？\n"
                "2) 自动重试与自愈策略（指数退避/错误回填 LLM 修复/降级路径）？\n"
                "3) Checkpoint 断点续跑与部分回滚/补偿事务？\n"
                "4) 失败告警通知与人工接管（HITL Escalation）？\n"
                "5) 运行监控指标、日志追踪与根因分析？",
            ),
            SpecializedDimension.AUTO_EXTERNAL_INTEGRATION.value: (
                SpecializedDimension.AUTO_EXTERNAL_INTEGRATION.label,
                "分析外部系统与连接器集成：\n"
                "1) 预置连接器与 SaaS/API/数据库覆盖范围？\n"
                "2) 自定义连接器扩展标准（MCP/OpenAPI/SDK）？\n"
                "3) 多系统凭据与认证安全（OAuth2/Secret Vault/最小权限委托）？\n"
                "4) 外部副作用操作的幂等性保护与 Dry-Run 校验？\n"
                "5) 连接器健康检查与版本兼容？",
            ),
            SpecializedDimension.AUTO_TRIGGER_SCHEDULING.value: (
                SpecializedDimension.AUTO_TRIGGER_SCHEDULING.label,
                "分析事件触发与调度机制：\n"
                "1) 触发器类型（Webhook/消息队列/定时 Cron/文件与邮件事件）？\n"
                "2) 事件过滤、去重防抖与 Payload 自动结构化注入？\n"
                "3) 任务队列优先级调度、并发隔离与背压限流？\n"
                "4) 触发SLA监控与积压告警？\n"
                "5) 多触发源统一网关与审计追踪？",
            ),
        }
