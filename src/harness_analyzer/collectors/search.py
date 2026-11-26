"""全网动态搜索采集器 (Web Search Collector)
支持：
1. 「提问语言 + 英语」双语问题式检索与内容覆盖度统计
2. 可插拔搜索引擎通道（优先 TAVILY_API_KEY / SERPER_API_KEY，未配置时安全降级 DuckDuckGo）
3. 检索退避限流保护 + 覆盖盲区自动二次补搜
4. 反爬侦测熔断与按域名速率控制 (DomainRateLimiter)
"""
from __future__ import annotations

import asyncio
import os
import random
import time
import httpx

from harness_analyzer.collectors.base import BaseCollector, CollectedData
from harness_analyzer.collectors.query_planner import BilingualQueryPlanner, PlannedQuery
from harness_analyzer.collectors.web_utils import DomainRateLimiter, fetch_clean_page, run_search_query
from harness_analyzer.models.harness import BlockedSource, QueryCoverageItem
from harness_analyzer.logging_utils import get_logger

logger = get_logger(__name__)


class WebSearchCollector(BaseCollector):
    """自动通过全网搜索引擎执行双语多角度检索，并统计搜索覆盖度"""

    def __init__(
        self,
        max_results: int = 4,
        timeout: float = 10.0,
        question_lang: str = "zh",
        rate_limiter: DomainRateLimiter | None = None,
    ):
        self.max_results = max_results
        self.timeout = timeout
        self.question_lang = question_lang
        self.rate_limiter = rate_limiter or DomainRateLimiter(min_interval=1.0, max_concurrency=4)
        self.last_coverage_items: list[QueryCoverageItem] = []
        self.last_bilingual_names: dict[str, str] = {}
        self.last_blocked_sources: list[BlockedSource] = []

    def _run_ddgs_batch_sync(self, queries: list[PlannedQuery]) -> tuple[list[tuple[PlannedQuery, dict]], dict[str, QueryCoverageItem], list[BlockedSource]]:
        """带礼貌间隔与限流退避的同步多后端检索批处理（运行在独立线程不阻塞事件循环）"""
        hits_out: list[tuple[PlannedQuery, dict]] = []
        cov_map = {
            pq.query: QueryCoverageItem(query=pq.query, language=pq.language, angle=pq.angle)
            for pq in queries
        }
        blocked: list[BlockedSource] = []
        consecutive_errors = 0

        for idx, pq in enumerate(queries):
            if consecutive_errors >= 4:
                blocked.append(BlockedSource(url="search://ddgs", reason="search_ratelimit_circuit_open", status_code=429))
                break
            if idx > 0:
                time.sleep(random.uniform(0.35, 0.75))
            try:
                raw_hits = run_search_query(pq.query, language=pq.language, max_results=self.max_results)
                cov_map[pq.query].hits_count = len(raw_hits)
                consecutive_errors = 0
                for h in raw_hits:
                    hits_out.append((pq, h))
            except Exception as exc:
                msg = str(exc).lower()
                # "no results found" 是正常空结果，不算限流异常
                if "no results found" in msg:
                    continue
                consecutive_errors += 1
                if "ratelimit" in msg or "429" in msg:
                    time.sleep(1.5 * consecutive_errors)

        return hits_out, cov_map, blocked

    async def _run_tavily_query(self, client: httpx.AsyncClient, api_key: str, pq: PlannedQuery) -> list[dict]:
        """可选工业级 Tavily 搜索 API 通道"""
        try:
            resp = await client.post(
                "https://api.tavily.com/search",
                json={"api_key": api_key, "query": pq.query, "max_results": self.max_results, "include_raw_content": False},
            )
            if resp.status_code == 200:
                return [
                    {"title": r.get("title", ""), "href": r.get("url", ""), "body": r.get("content", "")}
                    for r in resp.json().get("results", [])
                ]
        except Exception as exc:
            logger.debug("Tavily query failed for '%s': %s", pq.query, exc)
        return []

    async def _execute_query_batch(
        self,
        planned_queries: list[PlannedQuery],
        visited_urls: set[str],
    ) -> tuple[list[tuple[PlannedQuery, dict]], dict[str, QueryCoverageItem]]:
        """优先调用 Tavily API，未配置时使用带退避保护的 DuckDuckGo"""
        tavily_key = os.getenv("TAVILY_API_KEY")
        cov_map = {
            pq.query: QueryCoverageItem(query=pq.query, language=pq.language, angle=pq.angle)
            for pq in planned_queries
        }
        dedup_hits: list[tuple[PlannedQuery, dict]] = []

        if tavily_key:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                batches = await asyncio.gather(
                    *[self._run_tavily_query(client, tavily_key, pq) for pq in planned_queries],
                    return_exceptions=True,
                )
            for pq, raw_hits in zip(planned_queries, batches):
                if isinstance(raw_hits, list):
                    cov_map[pq.query].hits_count = len(raw_hits)
                    for h in raw_hits:
                        url = h.get("href")
                        if url and url not in visited_urls:
                            visited_urls.add(url)
                            dedup_hits.append((pq, h))
            return dedup_hits, cov_map

        raw_pairs, ddg_cov, blocked = await asyncio.to_thread(self._run_ddgs_batch_sync, planned_queries)
        self.last_blocked_sources.extend(blocked)
        for q_str, item in ddg_cov.items():
            cov_map[q_str] = item
        for pq, h in raw_pairs:
            url = h.get("href")
            if url and url not in visited_urls:
                visited_urls.add(url)
                dedup_hits.append((pq, h))
        return dedup_hits, cov_map

    async def collect(self, app) -> list[CollectedData]:
        """采集指定应用的公开互联网技术线索（自动执行提问语言 + 英语双语检索）"""
        app_name = getattr(app, "display_name", None) or getattr(app, "name", "")
        return await self.search_app(app_name)

    async def search_app(
        self,
        app_name: str,
        planned_queries: list[PlannedQuery] | None = None,
    ) -> list[CollectedData]:
        """执行双语多角度搜索、抓取正文、记录覆盖度并在需要时触发盲区补搜"""
        if planned_queries is None:
            names, planned_queries = BilingualQueryPlanner.plan_search_queries(
                app_name, question_lang=self.question_lang
            )
            self.last_bilingual_names = names

        self.last_blocked_sources = []
        visited_urls: set[str] = set()

        search_hits, coverage_map = await self._execute_query_batch(planned_queries, visited_urls)

        # 均衡挑选英文与中文摘要
        en_hits = [(pq, h) for pq, h in search_hits if pq.language == "en"][:5]
        zh_hits = [(pq, h) for pq, h in search_hits if pq.language == "zh"][:5]
        balanced_hits = en_hits + zh_hits

        collected: list[CollectedData] = []
        for pq, hit in balanced_hits:
            title = hit.get("title", "Search Result")
            body = hit.get("body", "")
            url = hit.get("href", "")
            if body:
                collected.append(
                    CollectedData(
                        source_url=url,
                        source_type="search_snippet",
                        title=f"[{pq.language}/{pq.angle}] {title}",
                        content=body,
                    )
                )

        to_fetch = en_hits[:2] + zh_hits[:2]
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; HarnessAnalyzer/1.0)"},
        ) as client:
            async def _grab(pq: PlannedQuery, hit: dict) -> tuple[PlannedQuery, CollectedData | None]:
                url = hit.get("href")
                if not url or self.rate_limiter.is_blocked(url):
                    return pq, None
                try:
                    p_title, p_text, _ = await fetch_clean_page(
                        client, url, max_chars=4500, rate_limiter=self.rate_limiter
                    )
                    if len(p_text) > 150:
                        return pq, CollectedData(
                            source_url=url,
                            source_type="web_page",
                            title=f"[网页正文|{pq.language}] {p_title or hit.get('title', '')}",
                            content=p_text,
                        )
                except Exception:
                    pass
                return pq, None

            page_results = await asyncio.gather(*[_grab(pq, h) for pq, h in to_fetch], return_exceptions=True)
            for res in page_results:
                if isinstance(res, tuple):
                    pq, item = res
                    if isinstance(item, CollectedData):
                        collected.append(item)
                        cov = coverage_map[pq.query]
                        cov.pages_fetched += 1
                        cov.chars_collected += len(item.content)

        self.last_coverage_items = list(coverage_map.values())
        self.last_blocked_sources.extend(self.rate_limiter.blocked_records)
        return collected

    async def refill_missing_angles(
        self,
        app_name: str,
        missing_angles: list[str],
        existing_urls: set[str] | None = None,
    ) -> tuple[list[CollectedData], list[QueryCoverageItem]]:
        """对命中为 0 的覆盖盲区角度执行一次轻量宽泛补搜"""
        refill_queries = BilingualQueryPlanner.plan_refill_queries(
            app_name, missing_angles=missing_angles, question_lang=self.question_lang
        )
        if not refill_queries:
            return [], []

        visited = set(existing_urls or ())
        hits, cov_map = await self._execute_query_batch(refill_queries, visited)
        extra_data: list[CollectedData] = []
        for pq, h in hits[:4]:
            body = h.get("body", "")
            url = h.get("href", "")
            if body and url:
                cov_map[pq.query].chars_collected += len(body)
                extra_data.append(
                    CollectedData(
                        source_url=url,
                        source_type="search_snippet",
                        title=f"[盲区补搜|{pq.language}/{pq.angle}] {h.get('title', '')}",
                        content=body,
                    )
                )
        return extra_data, list(cov_map.values())
