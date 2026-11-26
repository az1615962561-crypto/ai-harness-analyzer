"""权威真实用户评论采集器 (Authoritative User Review Collector)
从高信号技术与评测社区采集真实一线用户的正面评价、痛点吐槽与信任摩擦：
1. Hacker News (Algolia HN API + 热门主题高赞评论)
2. GitHub Issues (高评论数真实 Bug 与痛点反馈)
3. 权威软件评测与开发者社区定向检索 (G2 / Product Hunt / Trustpilot / Reddit / 知乎 / V2EX)
"""
from __future__ import annotations

import asyncio
import os
import re
from typing import Any
import httpx

from harness_analyzer.collectors.base import BaseCollector, CollectedData
from harness_analyzer.collectors.github import GitHubCollector
from harness_analyzer.collectors.query_planner import BilingualQueryPlanner
from harness_analyzer.collectors.web_utils import run_search_query
from harness_analyzer.models.harness import QueryCoverageItem
from harness_analyzer.logging_utils import get_logger

logger = get_logger(__name__)


class UserReviewCollector(BaseCollector):
    """采集权威社区与评测平台的真实用户评论，用于支撑人机体验与产品方案分析"""

    def __init__(
        self,
        timeout: float = 12.0,
        max_hn_stories: int = 3,
        max_review_hits: int = 4,
        question_lang: str = "zh",
    ):
        self.timeout = timeout
        self.max_hn_stories = max_hn_stories
        self.max_review_hits = max_review_hits
        self.question_lang = question_lang
        self.last_coverage_items: list[QueryCoverageItem] = []

    @staticmethod
    def _strip_hn_html(html_text: str) -> str:
        """清洗 HN 评论 HTML 为可读纯文本"""
        if not html_text:
            return ""
        text = html_text.replace("<p>", "\n").replace("&#x27;", "'").replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">")
        text = re.sub(r"<[^>]+>", " ", text)
        return re.sub(r"\s+", " ", text).strip()

    async def _fetch_hn_reviews(self, client: httpx.AsyncClient, app_name: str) -> list[CollectedData]:
        """从 Hacker News Algolia API 获取真实开发者讨论与高赞评论"""
        results: list[CollectedData] = []
        try:
            resp = await client.get(
                "https://hn.algolia.com/api/v1/search",
                params={"query": app_name, "tags": "story", "hitsPerPage": self.max_hn_stories},
            )
            if resp.status_code != 200:
                return results
            hits = resp.json().get("hits", [])
            # 过滤掉评论太少的帖子，确保真实用户讨论密度
            relevant_hits = [h for h in hits if (h.get("num_comments") or 0) >= 5][:self.max_hn_stories]

            async def _get_comments(hit: dict) -> CollectedData | None:
                story_id = hit.get("objectID")
                title = hit.get("title") or app_name
                if not story_id:
                    return None
                try:
                    item_resp = await client.get(f"https://hn.algolia.com/api/v1/items/{story_id}")
                    if item_resp.status_code != 200:
                        return None
                    children = item_resp.json().get("children", [])
                    comments: list[str] = []
                    for c in children[:12]:
                        raw_text = c.get("text") or ""
                        cleaned = self._strip_hn_html(raw_text)
                        author = c.get("author") or "anon"
                        if len(cleaned) >= 40:
                            comments.append(f"- @{author}: {cleaned[:400]}")
                        if len(comments) >= 8:
                            break
                    if not comments:
                        return None
                    hn_url = f"https://news.ycombinator.com/item?id={story_id}"
                    return CollectedData(
                        source_url=hn_url,
                        source_type="user_review",
                        title=f"[Hacker News 用户讨论] {title} ({hit.get('num_comments', 0)} 条评论)",
                        content="\n".join(comments),
                    )
                except Exception as exc:
                    logger.debug("Failed to fetch HN item comments: %s", exc)
                    return None

            gathered = await asyncio.gather(*[_get_comments(h) for h in relevant_hits], return_exceptions=True)
            results.extend(r for r in gathered if isinstance(r, CollectedData))
        except Exception as exc:
            logger.debug("HN search failed for %s: %s", app_name, exc)
        return results

    async def _fetch_github_issue_feedback(self, client: httpx.AsyncClient, app: Any) -> list[CollectedData]:
        """从开源项目的高评论数 Issues 提取一线用户真实痛点与诉求"""
        gh_url = GitHubCollector()._extract_github_url(app)
        if not gh_url:
            return []
        parsed = GitHubCollector._parse_github_url(gh_url)
        if not parsed:
            return []
        owner, repo = parsed

        headers = {"Accept": "application/vnd.github.v3+json"}
        token = os.getenv("GITHUB_TOKEN")
        if token:
            headers["Authorization"] = f"token {token}"

        try:
            resp = await client.get(
                f"https://api.github.com/repos/{owner}/{repo}/issues",
                params={"state": "all", "sort": "comments", "direction": "desc", "per_page": 8},
                headers=headers,
            )
            if resp.status_code != 200:
                return []
            issues = resp.json()
            lines = []
            for issue in issues:
                if "pull_request" in issue:
                    continue
                title = issue.get("title", "")
                comments_count = issue.get("comments", 0)
                body = (issue.get("body") or "").strip().replace("\n", " ")[:220]
                if title:
                    lines.append(f"- [{issue.get('state', 'open')}, {comments_count} 评论] {title}: {body}")
            if not lines:
                return []
            return [
                CollectedData(
                    source_url=f"https://github.com/{owner}/{repo}/issues",
                    source_type="user_review",
                    title=f"[GitHub Issues 一线用户痛点] {owner}/{repo}",
                    content="\n".join(lines),
                )
            ]
        except Exception as exc:
            logger.debug("GitHub issues review fetch failed: %s", exc)
            return []

    def _search_authoritative_review_sites(self, app_name: str) -> list[CollectedData]:
        """通过双语检索 G2 / Product Hunt / Reddit / 知乎 / V2EX 等权威真实评价并记录覆盖度"""
        planned = BilingualQueryPlanner.plan_review_queries(app_name, question_lang=self.question_lang)
        results: list[CollectedData] = []
        visited: set[str] = set()
        cov_items: list[QueryCoverageItem] = []

        for pq in planned:
            cov = QueryCoverageItem(query=pq.query, language=pq.language, angle=pq.angle)
            try:
                hits = run_search_query(pq.query, language=pq.language, max_results=self.max_review_hits)
                cov.hits_count = len(hits)
                for h in hits:
                    url = h.get("href") or ""
                    body = (h.get("body") or "").strip()
                    title = h.get("title") or "用户评价"
                    if url and body and url not in visited:
                        visited.add(url)
                        cov.chars_collected += len(body)
                        results.append(
                            CollectedData(
                                source_url=url,
                                source_type="user_review",
                                title=f"[权威社区评价|{pq.language}] {title}",
                                content=body,
                            )
                        )
            except Exception as exc:
                logger.debug("Review search query '%s' failed: %s", pq.query, exc)
            cov_items.append(cov)

        self.last_coverage_items = cov_items
        return results

    async def collect(self, app: Any) -> list[CollectedData]:
        """并发执行多渠道权威用户评论采集"""
        app_name = getattr(app, "display_name", None) or getattr(app, "name", "")
        if not app_name:
            return []

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "HarnessAnalyzer/1.0"},
        ) as client:
            hn_task = self._fetch_hn_reviews(client, app_name)
            gh_task = self._fetch_github_issue_feedback(client, app)
            site_task = asyncio.to_thread(self._search_authoritative_review_sites, app_name)

            hn_res, gh_res, site_res = await asyncio.gather(
                hn_task, gh_task, site_task, return_exceptions=True
            )

        collected: list[CollectedData] = []
        for batch in (hn_res, gh_res, site_res):
            if isinstance(batch, list):
                collected.extend(batch)
        return collected
