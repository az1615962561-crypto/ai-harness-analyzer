"""全网动态搜索采集器 (Web Search Collector)
用于在遇到未预置的新颖、小众 AI 应用时，通过搜索引擎自动检索技术架构、GitHub 仓库及技术博客资料。
"""
import re
import asyncio
import httpx
from datetime import datetime
from harness_analyzer.collectors.base import BaseCollector, CollectedData


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
        """针对未知小众应用执行多关键词组合搜索并抓取网页片段"""
        queries = [
            f"{app_name} AI architecture system prompt",
            f"{app_name} AI agent github technical blog",
            f"{app_name} LLM harness how it works",
        ]

        collected: list[CollectedData] = []
        visited_urls: set[str] = set()

        # 尝试通过 DuckDuckGo 搜索
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

        # 将搜索摘要本身先作为高密度信息源保存
        for hit in search_hits[:6]:
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

        # 尝试并发深度抓取 Top 2-3 个最相关的网页正文
        detail_tasks = []
        async with httpx.AsyncClient(timeout=self.timeout, follow_redirects=True) as client:
            for hit in search_hits[:3]:
                url = hit.get("href")
                if url:
                    detail_tasks.append(self._fetch_page_content(client, url, hit.get("title", "")))

            if detail_tasks:
                page_results = await asyncio.gather(*detail_tasks, return_exceptions=True)
                for res in page_results:
                    if isinstance(res, CollectedData):
                        collected.append(res)

        return collected

    async def _fetch_page_content(self, client: httpx.AsyncClient, url: str, title: str) -> CollectedData | None:
        """抓取网页正文并清洗 HTML 标签"""
        try:
            resp = await client.get(url, headers={"User-Agent": "Mozilla/5.0 (compatible; HarnessAnalyzer/1.0)"})
            if resp.status_code == 200:
                html = resp.text
                # 简单清洗 HTML 标签
                clean_text = re.sub(r"<script.*?</script>", "", html, flags=re.DOTALL | re.IGNORECASE)
                clean_text = re.sub(r"<style.*?</style>", "", clean_text, flags=re.DOTALL | re.IGNORECASE)
                clean_text = re.sub(r"<[^>]+>", " ", clean_text)
                clean_text = re.sub(r"\s+", " ", clean_text).strip()
                # 截取前 3000 字
                if len(clean_text) > 100:
                    return CollectedData(
                        source_url=url,
                        source_type="web_page",
                        title=f"[网页正文] {title}",
                        content=clean_text[:3000],
                    )
        except Exception:
            pass
        return None
