"""工程类 AI 应用专属分析器"""
from .base import BaseSpecializedAnalyzer


class EngineeringAnalyzer(BaseSpecializedAnalyzer):
    category = "engineering"

    def get_dimension_prompts(self) -> dict[str, tuple[str, str]]:
        return {
            "sandbox_model": (
                "沙箱隔离模型",
                "分析沙箱隔离模型：\n"
                "1) 代码执行环境类型（容器/VM/WASM/进程隔离）？\n"
                "2) 文件系统权限边界？\n"
                "3) 网络访问控制？\n"
                "4) 资源限制策略（CPU/内存/磁盘/超时）？\n"
                "5) 与宿主系统的隔离程度？",
            ),
            "code_understanding": (
                "代码理解引擎",
                "分析代码理解引擎：\n"
                "1) 代码索引方式（AST/LSP/语义嵌入）？\n"
                "2) 跨文件引用分析能力？\n"
                "3) 代码搜索能力（全文/语义/正则）？\n"
                "4) 语言支持范围与深度？\n"
                "5) 增量更新策略与实时性？",
            ),
            "diff_management": (
                "变更管理",
                "分析变更管理：\n"
                "1) Diff 生成方式（unified/side-by-side/语义 diff）？\n"
                "2) 变更预览机制与用户确认流程？\n"
                "3) Apply/Reject 流程设计？\n"
                "4) 多文件变更原子性保证？\n"
                "5) 回滚能力与版本追踪？",
            ),
            "terminal_management": (
                "终端管理",
                "分析终端管理：\n"
                "1) 终端会话模型（PTY/虚拟终端/Web Terminal）？\n"
                "2) 多终端支持与会话管理？\n"
                "3) 长运行进程处理（后台任务/超时控制）？\n"
                "4) 输出流处理（流式/缓冲/截断）？\n"
                "5) 状态保持机制与环境隔离？",
            ),
            "checkpoint_rollback": (
                "检查点与回滚",
                "分析检查点与回滚：\n"
                "1) 状态快照机制（Git commit/文件系统快照/自定义）？\n"
                "2) 快照粒度（文件/目录/全项目/运行时状态）？\n"
                "3) 回滚策略（全量/增量/选择性）？\n"
                "4) 增量快照与存储优化？\n"
                "5) 分支探索支持（多路径尝试/A-B 对比）？",
            ),
        }
