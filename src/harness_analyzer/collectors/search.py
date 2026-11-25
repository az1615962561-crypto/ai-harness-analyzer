"""全网动态搜索采集器 (Web Search Collector)
支持「提问语言 + 英语」双语问题式检索，并追踪每条检索词的命中覆盖度。
"""
import asyncio
import httpx
from harness_analyzer.collectors.base import BaseCollector, CollectedData
from harness_analyzer.collectors.query_planner import BilingualQueryPlanner, PlannedQuery
from harness_analyzer.collectors.web_utils import fetch_clean_page
from harness_analyzer.models.harness import QueryCoverageItem


class WebSearchCollector(BaseCollector):
    """自动通过全网搜索引擎执行双语多角度检索，并统计搜索覆盖度"""

    def __init__(self, max_results: int = 4, timeout: float = 10.0, question_lang: str = "zh"):
        self.max_results = max_results
        self.timeout = timeout
        self.question_lang = question_lang
        self.last_coverage_items: list[QueryCoverageItem] = []
        self.last_bilingual_names: dict[str, str] = {}

    async def collect(self, app) -> list[CollectedData]:
        """采集指定应用的公开互联网技术线索（自动执行提问语言 + 英语双语检索）"""
        app_name = getattr(app, "display_name", None) or getattr(app, "name", "")
        return await self.search_app(app_name)

    async def search_app(
        self,
        app_name: str,
        planned_queries: list[PlannedQuery] | None = None,
    ) -> list[CollectedData]:
        """执行双语多角度搜索、抓取正文并记录每条 query 的内容覆盖情况"""
        if planned_queries is None:
            names, planned_queries = BilingualQueryPlanner.plan_search_queries(
                app_name, question_lang=self.question_lang
            )
            self.last_bilingual_names = names

        collected: list[CollectedData] = []
        visited_urls: set[str] = set()
        search_hits: list[tuple[PlannedQuery, dict]] = []
        coverage_map: dict[str, QueryCoverageItem] = {
            pq.query: QueryCoverageItem(query=pq.query, language=pq.language, angle=pq.angle)
            for pq in planned_queries
        }

        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                for pq in planned_queries:
                    try:
                        hits = list(ddgs.text(pq.query, max_results=self.max_results))
                        coverage_map[pq.query].hits_count = len(hits)
                        for h in hits:
                            url = h.get("href")
                            if url and url not in visited_urls:
                                visited_urls.add(url)
                                search_hits.append((pq, h))
                    except Exception:
                        continue
        except Exception:
            pass

        # 均衡挑选英文与中文摘要，避免单语种霸屏
        en_hits = [(pq, h) for pq, h in search_hits if pq.language == "en"][:5]
        zh_hits = [(pq, h) for pq, h in search_hits if pq.language == "zh"][:5]
        balanced_hits = en_hits + zh_hits

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

        # 中英文各挑前 2 个高质量页面深抓正文
        to_fetch = en_hits[:2] + zh_hits[:2]
        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; HarnessAnalyzer/1.0)"},
        ) as client:
            async def _grab(pq: PlannedQuery, hit: dict) -> tuple[PlannedQuery, CollectedData | None]:
                url = hit.get("href")
                if not url:
                    return pq, None
                try:
                    p_title, p_text, _ = await fetch_clean_page(client, url, max_chars=4500)
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
        return collected
