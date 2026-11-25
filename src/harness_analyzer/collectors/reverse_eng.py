"""应用逆向工程与系统提示词/协议采集器 (Reverse Engineering & Artifact Collector)
支持：
1. 扫描本地解包目录（如 Electron asar 提取后的 .prompt/.rules/tools 定义）
2. 通过 GitHub Search API 动态检索社区逆向仓库与 Prompt Leak 资料
3. 抓取知名公开逆向/参考仓库的核心源码
"""
import asyncio
import os
import re
from pathlib import Path
import httpx
from harness_analyzer.collectors.base import BaseCollector, CollectedData


class ReverseEngineeringCollector(BaseCollector):
    """逆向工程采集器：定位系统提示词 (System Prompt)、内部协议及 Tool Calling 真实定义"""

    def __init__(self, local_app_path: str | Path | None = None, timeout: float = 12.0):
        self.local_app_path = Path(local_app_path) if local_app_path else None
        self.timeout = timeout

    async def collect(self, app) -> list[CollectedData]:
        """综合执行本地逆向检查与公网逆向仓库嗅探"""
        collected: list[CollectedData] = []
        app_name = getattr(app, "name", "")
        display_name = getattr(app, "display_name", app_name)

        if self.local_app_path and self.local_app_path.exists():
            collected.extend(self._scan_local_app(self.local_app_path, display_name))

        collected.extend(await self._hunt_public_re_artifacts(app_name, display_name))
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
                    if any(part in ("node_modules", ".git", ".venv", "dist") for part in file_path.parts):
                        continue

                    is_match = any(re.match(pat, f, re.IGNORECASE) for pat in interesting_patterns)
                    if is_match or (file_path.stat().st_size < 200_000 and f.endswith((".ts", ".js", ".json", ".md"))):
                        try:
                            content = file_path.read_text(encoding="utf-8", errors="ignore")
                            if any(kw in content for kw in ("systemPrompt", "instructions", "TOOLS_SCHEMA", "SEARCH/REPLACE", "agent_loop")):
                                results.append(
                                    CollectedData(
                                        source_url=str(file_path),
                                        source_type="local_reverse_engineering",
                                        title=f"[本地逆向解包] {file_path.name}",
                                        content=content[:4500],
                                    )
                                )
                        except Exception:
                            continue
        except Exception:
            pass

        return results

    async def _search_github_re_repos(
        self, client: httpx.AsyncClient, display_name: str
    ) -> list[CollectedData]:
        """调用 GitHub Search API 动态检索目标应用的系统提示词泄漏与逆向分析仓库"""
        results: list[CollectedData] = []
        queries = [
            f"{display_name} system prompt",
            f"{display_name} reverse engineering agent",
        ]
        seen_repos: set[str] = set()

        for q in queries:
            try:
                resp = await client.get(
                    "https://api.github.com/search/repositories",
                    params={"q": q, "sort": "stars", "order": "desc", "per_page": 3},
                )
                if resp.status_code != 200:
                    continue
                items = resp.json().get("items", [])
                for item in items:
                    full_name = item.get("full_name")
                    if not full_name or full_name in seen_repos:
                        continue
                    seen_repos.add(full_name)
                    branch = item.get("default_branch", "main")
                    readme_url = f"https://raw.githubusercontent.com/{full_name}/{branch}/README.md"
                    try:
                        r_resp = await client.get(readme_url)
                        if r_resp.status_code == 200 and len(r_resp.text) > 100:
                            results.append(
                                CollectedData(
                                    source_url=item.get("html_url", readme_url),
                                    source_type="github_re_search",
                                    title=f"[GitHub 逆向/提示词仓库] {full_name} (★{item.get('stargazers_count', 0)})",
                                    content=r_resp.text[:4000],
                                )
                            )
                    except Exception:
                        continue
            except Exception:
                continue

        return results

    async def _hunt_public_re_artifacts(self, app_name: str, display_name: str) -> list[CollectedData]:
        """检索 GitHub 公开逆向仓库与提示词线索"""
        results: list[CollectedData] = []
        target_name = app_name.lower().replace("-", "")

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
            ],
        }

        headers = {
            "User-Agent": "HarnessAnalyzer/1.0",
            "Accept": "application/vnd.github.v3+json",
        }
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"

        async with httpx.AsyncClient(headers=headers, timeout=self.timeout, follow_redirects=True) as client:
            urls_to_fetch = known_re_sources.get(target_name, [])

            async def _fetch_known(url: str, desc: str) -> CollectedData | None:
                try:
                    resp = await client.get(url)
                    if resp.status_code == 200 and len(resp.text) > 100:
                        return CollectedData(
                            source_url=url,
                            source_type="re_repository",
                            title=f"[逆向信源] {desc}",
                            content=resp.text[:4000],
                        )
                except Exception:
                    pass
                return None

            known_tasks = [_fetch_known(u, d) for u, d in urls_to_fetch]
            search_task = self._search_github_re_repos(client, display_name or app_name)

            gathered = await asyncio.gather(*known_tasks, search_task, return_exceptions=True)
            for item in gathered:
                if isinstance(item, CollectedData):
                    results.append(item)
                elif isinstance(item, list):
                    results.extend(item)

        return results
