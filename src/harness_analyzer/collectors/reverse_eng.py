"""应用逆向工程与系统提示词/协议采集器 (Reverse Engineering & Artifact Collector)
支持通过检索公开逆向仓库 (GitHub RE)、提示词泄漏 (Prompt Leaks) 以及本地解包资源，深度提取应用的真实底层 Harness 细节。
"""
import re
import os
import asyncio
from pathlib import Path
import httpx
from harness_analyzer.collectors.base import BaseCollector, CollectedData


class ReverseEngineeringCollector(BaseCollector):
    """逆向工程采集器：定位系统提示词 (System Prompt)、内部协议及 Tool Calling 真实定义"""

    def __init__(self, local_app_path: str | Path | None = None, timeout: float = 10.0):
        self.local_app_path = Path(local_app_path) if local_app_path else None
        self.timeout = timeout

    async def collect(self, app) -> list[CollectedData]:
        """综合执行本地逆向检查与公网逆向仓库嗅探"""
        collected: list[CollectedData] = []
        app_name = getattr(app, "name", "")
        display_name = getattr(app, "display_name", app_name)

        # 1. 本地解包目录扫描 (如果提供了本地 app 路径)
        if self.local_app_path and self.local_app_path.exists():
            local_data = self._scan_local_app(self.local_app_path, display_name)
            collected.extend(local_data)

        # 2. 公网逆向嗅探 (GitHub 逆向工程仓库与 Prompt 泄漏检索)
        re_data = await self._hunt_public_re_artifacts(app_name, display_name)
        collected.extend(re_data)

        return collected

    def _scan_local_app(self, app_dir: Path, app_name: str) -> list[CollectedData]:
        """扫描本地 Electron / Web 应用解包目录中的系统提示词、规则文件与工具定义"""
        results: list[CollectedData] = []
        interesting_patterns = [
            r".*\.prompt$",
            r".*\.rules$",
            r".*system_prompt.*",
            r".*agent_config.*",
            r".*tools?_def.*\.json$",
        ]

        try:
            for root, _, files in os.walk(app_dir):
                for f in files:
                    file_path = Path(root) / f
                    # 避免扫描庞大的 node_modules 或 .git
                    if any(part in ("node_modules", ".git", ".venv", "dist") for part in file_path.parts):
                        continue

                    # 检查文件名特征
                    is_match = any(re.match(pat, f, re.IGNORECASE) for pat in interesting_patterns)
                    # 或者体积小于 200KB 且包含敏感关键字
                    if is_match or (file_path.stat().st_size < 200_000 and f.endswith((".ts", ".js", ".json", ".md"))):
                        try:
                            content = file_path.read_text(encoding="utf-8", errors="ignore")
                            if any(kw in content for kw in ("systemPrompt", "instructions", "TOOLS_SCHEMA", "SEARCH/REPLACE", "agent_loop")):
                                results.append(
                                    CollectedData(
                                        source_url=str(file_path),
                                        source_type="local_reverse_engineering",
                                        title=f"[本地逆向解包] {file_path.name}",
                                        content=content[:4000],
                                    )
                                )
                        except Exception:
                            continue
        except Exception:
            pass

        return results

    async def _hunt_public_re_artifacts(self, app_name: str, display_name: str) -> list[CollectedData]:
        """检索 GitHub 及公开技术社区中的逆向拆解成果 (Prompt Leaks & Protocol Specs)"""
        results: list[CollectedData] = []
        target_name = app_name.lower().replace("-", "")

        # 针对常见顶级产品的知名公开逆向仓库直连探测
        known_re_sources = {
            "cursor": [
                (
                    "https://raw.githubusercontent.com/getcursor/cursor/main/README.md",
                    "Cursor 官方代码库结构",
                ),
            ],
            "devin": [
                (
                    "https://raw.githubusercontent.com/All-Hands-AI/OpenHands/main/README.md",
                    "OpenHands 对标 Devin 的开源参考逆向架构",
                )
            ],
            "autogpt": [
                (
                    "https://raw.githubusercontent.com/Significant-Gravitas/AutoGPT/master/classic/original_autogpt/autogpt/agent/agent.py",
                    "AutoGPT Agent 核心循环与状态机源码",
                )
            ]
        }

        urls_to_fetch = known_re_sources.get(target_name, [])

        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for url, desc in urls_to_fetch:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200 and len(resp.text) > 100:
                        results.append(
                            CollectedData(
                                source_url=url,
                                source_type="re_repository",
                                title=f"[逆向信源] {desc}",
                                content=resp.text[:3500],
                            )
                        )
                except Exception:
                    continue

        return results
