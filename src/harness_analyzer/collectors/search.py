"""全网动态搜索采集器 (Web Search Collector)
用于在遇到未预置的新颖、小众 AI 应用时，通过搜索引擎自动检索技术架构、GitHub 仓库及技术博客资料。
"""
import asyncio
import httpx
from harness_analyzer.collectors.base import BaseCollector, CollectedData
from harness_analyzer.collectors.web_utils import fetch_clean_page


class WebSearchCollector(BaseCollector):
    """自动通过全网搜索引擎检索 AI 应用的技术架构线索"""

    def __init__(self, max_results: int = 5, timeout: float = 10.0):
        self.max_results = max_results
        self.timeout = timeout

    async def collect(self, app) -> list[CollectedData]:
        """采集指定应用的公开互联网技术线索"""
        app_name = getattr(app, "display_name", None) or getattr(app, "name", "")
        return await self.search_app(app_name)

    async def search_app(self, app_name: str) -> list[CollectedData]:
        """针对未知或已知应用执行多关键词组合搜索并抓取网页正文"""
        queries = [
            f"{app_name} AI architecture system prompt",
            f"{app_name} AI agent github technical blog",
            f"{app_name} LLM harness how it works",
            f"{app_name} AI 架构 原理 拆解",
        ]

        collected: list[CollectedData] = []
        visited_urls: set[str] = set()
        search_hits = []

        try:
            from duckduckgo_search import DDGS
            with DDGS() as ddgs:
                for q in queries:
                    try:
                        hits = list(ddgs.text(q, max_results=self.max_results))
                        for h in hits:
                            url = h.get("href")
                            if url and url not in visited_urls:
                                visited_urls.add(url)
                                search_hits.append(h)
                    except Exception:
                        continue
        except Exception:
            pass

        for hit in search_hits[:8]:
            title = hit.get("title", "Search Result")
            body = hit.get("body", "")
            url = hit.get("href", "")
            if body:
                collected.append(
                    CollectedData(
                        source_url=url,
                        source_type="search_snippet",
                        title=f"[搜索摘要] {title}",
                        content=body,
                    )
                )

        async with httpx.AsyncClient(
            timeout=self.timeout,
            follow_redirects=True,
            headers={"User-Agent": "Mozilla/5.0 (compatible; HarnessAnalyzer/1.0)"},
        ) as client:
            async def _grab(hit: dict) -> CollectedData | None:
                url = hit.get("href")
                if not url:
                    return None
                try:
                    p_title, p_text, _ = await fetch_clean_page(client, url, max_chars=4500)
                    if len(p_text) > 150:
                        return CollectedData(
                            source_url=url,
                            source_type="web_page",
                            title=f"[网页正文] {p_title or hit.get('title', '')}",
                            content=p_text,
                        )
                except Exception:
                    pass
                return None

            page_results = await asyncio.gather(*[_grab(h) for h in search_hits[:4]], return_exceptions=True)
            for res in page_results:
                if isinstance(res, CollectedData):
                    collected.append(res)

        return collected
