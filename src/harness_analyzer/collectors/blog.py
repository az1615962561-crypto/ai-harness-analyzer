"""博客与技术文档数据采集器"""
import re
from typing import Any
import httpx
from .base import BaseCollector, CollectedData


class BlogCollector(BaseCollector):
    """从官方技术博客与文档采集公开架构信息"""

    def __init__(self, timeout: float = 15.0):
        self.timeout = timeout

    @staticmethod
    def _strip_html(html_content: str) -> str:
        """使用正则表达式清洗 HTML 标签与多余空白字符"""
        # 移除 script 与 style 块
        text = re.sub(r"<(script|style)[^>]*>.*?</\1>", "", html_content, flags=re.DOTALL | re.IGNORECASE)
        # 移除通用 HTML 标签
        text = re.sub(r"<[^>]+>", " ", text)
        # 替换 HTML 转义符
        text = text.replace("&nbsp;", " ").replace("&lt;", "<").replace("&gt;", ">").replace("&amp;", "&").replace("&quot;", '"')
        # 合并空行与多余空格
        lines = [line.strip() for line in text.splitlines()]
        cleaned = "\n".join(line for line in lines if line)
        return cleaned

    async def collect(self, app: Any) -> list[CollectedData]:
        """采集 app.info_sources 中 source_type 为 blog 或 docs 的公开内容"""
        collected: list[CollectedData] = []
        sources = getattr(app, "info_sources", None)
        if sources is None and isinstance(app, dict):
            sources = app.get("info_sources", [])

        if not sources or not isinstance(sources, list):
            return collected

        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/124.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        }

        async with httpx.AsyncClient(headers=headers, timeout=self.timeout, follow_redirects=True) as client:
            for item in sources:
                stype = getattr(item, "source_type", None) or (item.get("source_type") if isinstance(item, dict) else None)
                url = getattr(item, "url", None) or (item.get("url") if isinstance(item, dict) else None)
                title = getattr(item, "title", None) or (item.get("title") if isinstance(item, dict) else None) or url or "未知标题"

                # 仅采集 blog 与 docs 类型来源
                if str(stype).lower() not in ("blog", "docs") or not url:
                    continue

                try:
                    resp = await client.get(str(url))
                    if resp.status_code == 200:
                        content_type = resp.headers.get("content-type", "").lower()
                        raw_text = resp.text
                        if "html" in content_type or "<html" in raw_text[:200].lower():
                            cleaned = self._strip_html(raw_text)
                        else:
                            cleaned = raw_text.strip()

                        if cleaned:
                            collected.append(
                                CollectedData(
                                    source_url=str(url),
                                    source_type=str(stype),
                                    title=str(title),
                                    content=cleaned,
                                )
                            )
                except Exception:
                    # 单个 URL 失败不中断整体采集流程
                    continue

        return collected
