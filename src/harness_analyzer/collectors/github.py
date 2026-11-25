"""GitHub 数据采集器（支持 README、目录树及高价值核心源码文件自动下钻读取）"""
import asyncio
import os
import re
from typing import Any
import httpx
from .base import BaseCollector, CollectedData


# 按架构信号价值加权的路径关键词
_HIGH_VALUE_PATTERNS: list[tuple[str, int]] = [
    (r"(system[_-]?prompt|prompt|instruction|\.rules|\.cursorrules)", 10),
    (r"(orchestrat|planner|agent_loop|workflow|state_machine|graph)", 9),
    (r"(tool|function_call|mcp|schema)", 8),
    (r"(sandbox|docker|container|executor|runtime|security)", 8),
    (r"(context|retriev|rag|embed|chunk|index|lsp|ast|tree_sitter)", 7),
    (r"(router|routing|model_select|llm|provider)", 7),
    (r"(diff|patch|edit|apply|checkpoint|rollback)", 7),
    (r"(agent|core|engine)", 5),
]

_LOW_VALUE_NOISE = (
    "test/", "tests/", "__tests__", "spec/", ".github/", "docs/zh", "locales/",
    "i18n/", "assets/", "images/", "icons/", "examples/", "benchmarks/",
)

_ALLOWED_EXTENSIONS = (".py", ".ts", ".tsx", ".js", ".go", ".rs", ".md", ".yaml", ".yml", ".json", ".toml")


class GitHubCollector(BaseCollector):
    """从 GitHub 公开仓库采集 README、文件树及关键架构源码文件"""

    def __init__(self, timeout: float = 15.0, max_source_files: int = 6):
        self.timeout = timeout
        self.max_source_files = max_source_files

    @staticmethod
    def _parse_github_url(url: str) -> tuple[str, str] | None:
        """从 GitHub URL 中解析出 (owner, repo)"""
        if not url:
            return None
        cleaned = url.strip()
        pattern = r"(?:https?://github\.com/|git@github\.com:)?([^/\s]+)/([^/\s#?]+?)(?:\.git)?(?:/|$)"
        match = re.search(pattern, cleaned)
        if match:
            owner, repo = match.group(1), match.group(2)
            if owner and repo:
                return owner, repo
        return None

    def _extract_github_url(self, app: Any) -> str | None:
        """从应用对象或字典中提取 GitHub 地址"""
        for attr in ("github_url", "repo_url", "repository_url"):
            val = getattr(app, attr, None)
            if not val and isinstance(app, dict):
                val = app.get(attr)
            if val:
                return str(val)

        sources = getattr(app, "info_sources", None)
        if sources is None and isinstance(app, dict):
            sources = app.get("info_sources")

        if sources and isinstance(sources, list):
            for src in sources:
                stype = getattr(src, "source_type", None) or (src.get("source_type") if isinstance(src, dict) else None)
                surl = getattr(src, "url", None) or (src.get("url") if isinstance(src, dict) else None)
                if stype in ("github", "repo", "repository") and surl:
                    return str(surl)
                if surl and "github.com" in str(surl):
                    return str(surl)

        return None

    @staticmethod
    def select_key_files(paths: list[str], max_files: int = 6) -> list[str]:
        """从仓库目录树中启发式挑选最能反映 Harness 架构的核心源码文件"""
        scored: list[tuple[int, str]] = []
        config_files: list[str] = []

        for p in paths:
            lower = p.lower()
            if not lower.endswith(_ALLOWED_EXTENSIONS):
                continue
            if any(noise in lower for noise in _LOW_VALUE_NOISE):
                continue
            if lower.endswith(("package-lock.json", "uv.lock", "yarn.lock", "pnpm-lock.yaml", ".min.js")):
                continue

            if lower in ("pyproject.toml", "package.json", "cargo.toml", "go.mod"):
                config_files.append(p)
                continue

            score = 0
            for pattern, pts in _HIGH_VALUE_PATTERNS:
                if re.search(pattern, lower):
                    score += pts

            # 优先核心源码文件而非普通说明文档
            if lower.endswith((".py", ".ts", ".go", ".rs")):
                score += 2
            elif lower.endswith("readme.md"):
                continue  # README 已单独抓取

            if score >= 6:
                scored.append((score, p))

        scored.sort(key=lambda item: (item[0], -len(item[1])), reverse=True)
        selected = [p for _, p in scored[:max_files]]

        # 补充最多 1 个依赖配置文件（帮助识别技术栈与沙箱/LLM SDK）
        if config_files and len(selected) < max_files + 1:
            selected.append(config_files[0])

        return selected

    async def collect(self, app: Any) -> list[CollectedData]:
        """采集指定应用的 GitHub README、目录树及高价值核心源码文件"""
        collected: list[CollectedData] = []
        github_url = self._extract_github_url(app)
        if not github_url:
            return collected

        parsed = self._parse_github_url(github_url)
        if not parsed:
            return collected

        owner, repo = parsed
        headers = {
            "User-Agent": "HarnessAnalyzer/1.0",
            "Accept": "application/vnd.github.v3+json",
        }
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"

        async with httpx.AsyncClient(headers=headers, timeout=self.timeout, follow_redirects=True) as client:
            # 1. 并发获取 README 与目录结构树
            readme_res, tree_res = await asyncio.gather(
                self._fetch_readme(client, owner, repo),
                self._fetch_repo_tree(client, owner, repo),
                return_exceptions=True,
            )

            if isinstance(readme_res, CollectedData):
                collected.append(readme_res)

            if isinstance(tree_res, tuple):
                tree_item, branch, all_paths = tree_res
                collected.append(tree_item)

                # 2. 从目录树中挑选关键架构源码并发深读
                key_files = self.select_key_files(all_paths, max_files=self.max_source_files)
                if key_files:
                    src_items = await self._fetch_selected_files(client, owner, repo, branch, key_files)
                    collected.extend(src_items)

        return collected

    async def _fetch_readme(self, client: httpx.AsyncClient, owner: str, repo: str) -> CollectedData | None:
        """从 raw.githubusercontent.com 获取仓库 README 内容"""
        branches = ["main", "master"]
        filenames = ["README.md", "README.rst", "README.txt", "readme.md"]

        for branch in branches:
            for fname in filenames:
                raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{fname}"
                try:
                    resp = await client.get(raw_url)
                    if resp.status_code == 200 and resp.text:
                        return CollectedData(
                            source_url=raw_url,
                            source_type="github_readme",
                            title=f"{owner}/{repo} README ({fname})",
                            content=resp.text,
                        )
                except Exception:
                    continue
        return None

    async def _fetch_repo_tree(
        self, client: httpx.AsyncClient, owner: str, repo: str
    ) -> tuple[CollectedData, str, list[str]] | None:
        """通过 api.github.com 获取仓库文件结构"""
        for branch in ("main", "master"):
            api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            try:
                resp = await client.get(api_url)
                if resp.status_code == 200:
                    data = resp.json()
                    tree = data.get("tree", [])
                    paths = [item.get("path") for item in tree if item.get("path") and item.get("type") == "blob"]
                    if not paths:
                        paths = [item.get("path") for item in tree if item.get("path")]
                    if paths:
                        display_paths = paths[:300]
                        content_lines = [
                            f"仓库: {owner}/{repo}",
                            f"默认分支: {branch}",
                            f"文件总数: {len(paths)}",
                            "",
                            "目录树结构:",
                            *display_paths,
                        ]
                        if len(paths) > 300:
                            content_lines.append(f"... 其余 {len(paths) - 300} 个文件省略")

                        tree_item = CollectedData(
                            source_url=f"https://github.com/{owner}/{repo}/tree/{branch}",
                            source_type="github_tree",
                            title=f"{owner}/{repo} 代码目录结构",
                            content="\n".join(content_lines),
                        )
                        return tree_item, branch, paths
            except Exception:
                continue
        return None

    async def _fetch_selected_files(
        self,
        client: httpx.AsyncClient,
        owner: str,
        repo: str,
        branch: str,
        file_paths: list[str],
    ) -> list[CollectedData]:
        """并发读取筛选出的核心架构源码文件"""

        async def _get_one(path: str) -> CollectedData | None:
            raw_url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
            try:
                resp = await client.get(raw_url)
                if resp.status_code == 200 and resp.text.strip():
                    return CollectedData(
                        source_url=raw_url,
                        source_type="github_source",
                        title=f"{owner}/{repo} 核心源码: {path}",
                        content=resp.text[:4500],
                    )
            except Exception:
                pass
            return None

        results = await asyncio.gather(*[_get_one(p) for p in file_paths], return_exceptions=True)
        return [r for r in results if isinstance(r, CollectedData)]
