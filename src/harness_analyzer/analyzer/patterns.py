"""架构模式匹配器（加载标准模式库并结合 LLM 识别工程设计模式）"""
from __future__ import annotations

import asyncio
from pathlib import Path

import yaml

from harness_analyzer.logging_utils import get_logger
from .llm import LLMClient

logger = get_logger(__name__)

_DEFAULT_PATTERNS: list[dict[str, str]] = [
    {"name": "single_agent", "display_name": "单 Agent", "description": "单个 LLM 配合工具集处理边界清晰任务"},
    {"name": "multi_agent_hierarchical", "display_name": "多 Agent 层级式", "description": "Planner-Worker 任务拆解与子任务并发执行"},
    {"name": "agent_loop", "display_name": "Agent 自治循环式", "description": "ReAct / Plan-Execute-Reflect 持续迭代闭环"},
    {"name": "hierarchical_recursive_summary", "display_name": "分层递归摘要压缩", "description": "超阈值时结构化压缩上下文并保留关键约束"},
    {"name": "speculative_draft_routing", "display_name": "投机草稿路由", "description": "小模型低延迟出草稿 + 大模型精修校验"},
    {"name": "mcp_protocol_standard", "display_name": "MCP 标准化协议集成", "description": "基于 Model Context Protocol 标准化接入工具与数据源"},
    {"name": "human_in_the_loop_guard", "display_name": "人机介入安全防护", "description": "高危操作前 Diff 预览与人工审批断点"},
]


def load_pattern_catalog(patterns_dir: Path | None = None) -> list[dict[str, str]]:
    """从 data/patterns/*.yaml 加载参考架构模式目录，缺失时返回内置兜底列表"""
    candidate_dirs = []
    if patterns_dir is not None:
        candidate_dirs.append(patterns_dir)
    else:
        candidate_dirs.append(Path.cwd() / "data" / "patterns")
        candidate_dirs.append(Path(__file__).resolve().parents[1] / "data" / "patterns")
        candidate_dirs.append(Path(__file__).resolve().parents[3] / "data" / "patterns")

    loaded: list[dict[str, str]] = []
    seen: set[str] = set()
    for pdir in candidate_dirs:
        if not pdir.is_dir():
            continue
        for yml_path in sorted(pdir.glob("*.yaml")):
            try:
                raw = yaml.safe_load(yml_path.read_text(encoding="utf-8")) or {}
                for item in raw.get("patterns", []) or []:
                    name = str(item.get("name", "")).strip()
                    if not name or name in seen:
                        continue
                    seen.add(name)
                    loaded.append({
                        "name": name,
                        "display_name": str(item.get("display_name") or name),
                        "description": str(item.get("description") or ""),
                    })
            except Exception as exc:
                logger.warning("Failed to parse pattern catalog %s: %s", yml_path, exc)
        if loaded:
            return loaded

    return list(_DEFAULT_PATTERNS)


class PatternMatcher:
    """基于参考模式目录与 LLM 的架构模式匹配器"""

    def __init__(self, llm: LLMClient, patterns_dir: Path | None = None):
        self.llm = llm
        self.catalog = load_pattern_catalog(patterns_dir)

    def match(self, app_info: str, collected_data: str) -> list[dict]:
        """识别应用中使用的已知架构模式

        Returns:
            list[dict]: 每个 dict 包含 pattern_name, description, evidence, confidence
        """
        catalog_lines = "\n".join(
            f"- {p['name']} ({p['display_name']}): {p['description']}"
            for p in self.catalog
        )
        system_prompt = (
            "你是一位资深 AI 架构分析师。请对照以下标准架构模式目录识别该 AI 应用明确使用的设计模式：\n"
            f"{catalog_lines}\n"
            "仅提取有采集证据支撑的模式，严禁臆造。"
        )

        full_prompt = (
            f"## 应用信息\n{app_info}\n\n"
            f"## 采集数据\n{collected_data[:9000]}\n\n"
            "## 分析任务\n"
            "请识别该应用中使用的所有架构模式，并返回 JSON 数组：\n"
            '[{"pattern_name": "模式名", "description": "在该应用中的具体落地方式", '
            '"evidence": ["直接来自采集数据的证据1", ...], "confidence": 4}]'
        )

        try:
            result = self.llm.structured_analyze(full_prompt, system_prompt)
            items = result if isinstance(result, list) else (result.get("patterns", []) if isinstance(result, dict) and "patterns" in result else [result])
            cleaned: list[dict] = []
            for it in items:
                if not isinstance(it, dict) or not it.get("pattern_name"):
                    continue
                cleaned.append({
                    "pattern_name": str(it["pattern_name"]),
                    "description": str(it.get("description", "")),
                    "evidence": list(it.get("evidence") or []),
                    "confidence": max(1, min(5, int(it.get("confidence", 3)))),
                })
            return cleaned
        except Exception as exc:
            logger.warning("Pattern matching failed: %s", exc)
            return []

    async def amatch(self, app_info: str, collected_data: str) -> list[dict]:
        """异步包装 PatternMatcher.match，便于与其他分析阶段并发执行"""
        return await asyncio.to_thread(self.match, app_info, collected_data)
