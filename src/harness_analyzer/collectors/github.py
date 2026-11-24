"""GitHub 数据采集器"""
import os
import re
from typing import Any
import httpx
from .base import BaseCollector, CollectedData


class GitHubCollector(BaseCollector):
    """从 GitHub 公开仓库采集 README 与文件树结构"""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    @staticmethod
    def _parse_github_url(url: str) -> tuple[str, str] | None:
        """从 GitHub URL 中解析出 (owner, repo)

        支持的形式包括：
        - https://github.com/owner/repo
        - https://github.com/owner/repo.git
        - git@github.com:owner/repo.git
        - owner/repo
        """
        if not url:
            return None
        cleaned = url.strip()
        # 匹配标准 GitHub URL 或 SSH 形式
        pattern = r"(?:https?://github\.com/|git@github\.com:)?([^/\s]+)/([^/\s#?]+?)(?:\.git)?(?:/|$)"
        match = re.search(pattern, cleaned)
        if match:
            owner, repo = match.group(1), match.group(2)
            # 过滤掉明显的非仓库路径（例如 features, pricing 等）
            if owner and repo:
                return owner, repo
        return None

    def _extract_github_url(self, app: Any) -> str | None:
        """从应用对象或字典中提取 GitHub 地址"""
        # 直接属性获取
        for attr in ("github_url", "repo_url", "repository_url"):
            val = getattr(app, attr, None)
            if not val and isinstance(app, dict):
                val = app.get(attr)
            if val:
                return str(val)

        # 从 info_sources 列表中查找
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

    async def collect(self, app: Any) -> list[CollectedData]:
        """采集指定应用的 GitHub README 与代码仓库目录树"""
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
            # 1. 尝试采集 README
            try:
                readme_item = await self._fetch_readme(client, owner, repo)
                if readme_item:
                    collected.append(readme_item)
            except Exception:
                # 容错处理：不阻断其他数据采集
                pass

            # 2. 尝试采集仓库目录结构树
            try:
                tree_item = await self._fetch_repo_tree(client, owner, repo)
                if tree_item:
                    collected.append(tree_item)
            except Exception:
                # 容错处理：不阻断其他数据采集
                pass

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

    async def _fetch_repo_tree(self, client: httpx.AsyncClient, owner: str, repo: str) -> CollectedData | None:
        """通过 api.github.com 获取仓库文件结构"""
        branches = ["main", "master"]
        for branch in branches:
            api_url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
            try:
                resp = await client.get(api_url)
                if resp.status_code == 200:
                    data = resp.json()
                    tree = data.get("tree", [])
                    paths = [item.get("path") for item in tree if item.get("path")]
                    if paths:
                        display_paths = paths[:300]
                        content_lines = [
                            f"仓库: {owner}/{repo}",
                            f"默认分支: {branch}",
                            f"文件总数: {len(paths)}",
                            "",
                            "目录树结构:",
                        ]
                        content_lines.extend(display_paths)
                        if len(paths) > 300:
                            content_lines.append(f"... 其余 {len(paths) - 300} 个文件省略")

                        return CollectedData(
                            source_url=f"https://github.com/{owner}/{repo}/tree/{branch}",
                            source_type="github_tree",
                            title=f"{owner}/{repo} 代码目录结构",
                            content="\n".join(content_lines),
                        )
            except Exception:
                continue
        return None
