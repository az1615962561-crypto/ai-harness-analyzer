"""博客与技术文档数据采集器（支持索引页自动下钻至技术文章正文 + SPA 降级提取）"""
import asyncio
from typing import Any
from urllib.parse import urlparse
import httpx
from .base import BaseCollector, CollectedData
from .web_utils import fetch_clean_page, rank_article_links


class BlogCollector(BaseCollector):
    """从官方技术博客与文档采集公开架构信息"""

    def __init__(self, timeout: float = 15.0, max_drilldown: int = 3):
        self.timeout = timeout
        self.max_drilldown = max_drilldown

    @staticmethod
    def _is_index_page(url: str) -> bool:
        """判断 URL 是否更像是博客列表页/文档首页"""
        path = urlparse(url).path.rstrip("/").lower()
        return path in ("", "/blog", "/news", "/docs", "/changelog", "/engineering", "/research")

    async def collect(self, app: Any) -> list[CollectedData]:
        """采集 app.info_sources 中的 blog / docs / documentation / product_page 内容并追踪子文章"""
        collected: list[CollectedData] = []
        sources = getattr(app, "info_sources", None)
        if sources is None and isinstance(app, dict):
            sources = app.get("info_sources", [])

        if not sources or not isinstance(sources, list):
            return collected

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(headers=headers, timeout=self.timeout, follow_redirects=True) as client:
            visited: set[str] = set()
            drilldown_candidates: list[tuple[str, str]] = []

            for item in sources:
                stype = getattr(item, "source_type", None) or (item.get("source_type") if isinstance(item, dict) else None)
                url = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else None)
                desc = getattr(item, "description", None) or (item.get("description") if isinstance(item, dict) else None)
                title = getattr(item, "title", None) or (item.get("title") if isinstance(item, dict) else None) or desc or url or "未知标题"

                if str(stype).lower() not in ("blog", "docs", "documentation", "product_page") or not url:
                    continue

                url_str = str(url)
                visited.add(url_str.rstrip("/"))
                try:
                    page_title, cleaned, links = await fetch_clean_page(client, url_str, max_chars=5000)
                    if cleaned:
                        collected.append(
                            CollectedData(
                                source_url=url_str,
                                source_type=str(stype),
                                title=page_title or str(title),
                                content=cleaned,
                            )
                        )
                    # 如果是索引/列表页，收集高质量技术子文章链接
                    if links and self._is_index_page(url_str):
                        drilldown_candidates.extend(rank_article_links(url_str, links, limit=self.max_drilldown))
                except Exception:
                    continue

            # 并发深抓筛选出来的具体技术文章
            unique_sub_links = []
            for sub_url, sub_title in drilldown_candidates:
                norm = sub_url.rstrip("/")
                if norm not in visited:
                    visited.add(norm)
                    unique_sub_links.append((sub_url, sub_title))

            if unique_sub_links:
                async def _fetch_sub(sub_url: str, sub_title: str) -> CollectedData | None:
                    try:
                        p_title, p_text, _ = await fetch_clean_page(client, sub_url, max_chars=5000)
                        if p_text and len(p_text) > 150:
                            return CollectedData(
                                source_url=sub_url,
                                source_type="blog_article",
                                title=f"[深度文章] {p_title or sub_title}",
                                content=p_text,
                            )
                    except Exception:
                        pass
                    return None

                sub_results = await asyncio.gather(
                    *[_fetch_sub(u, t) for u, t in unique_sub_links[:self.max_drilldown]],
                    return_exceptions=True,
                )
                for res in sub_results:
                    if isinstance(res, CollectedData):
                        collected.append(res)

        return collected
