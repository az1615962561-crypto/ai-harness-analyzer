"""网页抓取与清洗公共工具 (Web Extraction Utilities)
使用 Python 标准库 html.parser 精确剔除导航/页脚/脚本噪音，提取正文与站内技术文章链接，
并在遇到 SPA/JS 渲染壳页面时自动降级调用 Jina Reader 获取纯文本。
"""
from __future__ import annotations

from html.parser import HTMLParser
import re
from urllib.parse import urljoin, urlparse
import httpx


_SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside"}
_BLOCK_TAGS = {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "code", "blockquote", "tr"}

_ARCH_LINK_KEYWORDS = (
    "architecture", "agent", "harness", "prompt", "index", "context", "sandbox",
    "diff", "sql", "rag", "routing", "mcp", "workflow", "engine", "under-the-hood",
    "how-we-built", "technical", "engineering", "system",
    "架构", "原理", "工程", "拆解", "实践",
)


class _CleanHTMLParser(HTMLParser):
    """提取干净正文文本、页面标题与站内链接"""

    def __init__(self, base_url: str = "") -> None:
        super().__init__(convert_charrefs=True)
        self.base_url = base_url
        self._skip_depth = 0
        self._in_title = False
        self._in_a = False
        self._current_href = ""
        self._current_a_text: list[str] = []
        self.title = ""
        self._text_parts: list[str] = []
        self.links: list[tuple[str, str]] = []  # (url, anchor_text)

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        t = tag.lower()
        if t in _SKIP_TAGS:
            self._skip_depth += 1
            return
        if self._skip_depth > 0:
            return
        if t == "title":
            self._in_title = True
        elif t in _BLOCK_TAGS:
            self._text_parts.append("\n")
        elif t == "a":
            attr_map = dict(attrs)
            href = attr_map.get("href") or ""
            if href and not href.startswith(("#", "javascript:", "mailto:")):
                self._in_a = True
                self._current_href = urljoin(self.base_url, href) if self.base_url else href
                self._current_a_text = []

    def handle_endtag(self, tag: str) -> None:
        t = tag.lower()
        if t in _SKIP_TAGS:
            if self._skip_depth > 0:
                self._skip_depth -= 1
            return
        if self._skip_depth > 0:
            return
        if t == "title":
            self._in_title = False
        elif t in _BLOCK_TAGS:
            self._text_parts.append("\n")
        elif t == "a" and self._in_a:
            anchor = " ".join("".join(self._current_a_text).split()).strip()
            if self._current_href:
                self.links.append((self._current_href, anchor))
            self._in_a = False
            self._current_href = ""
            self._current_a_text = []

    def handle_data(self, data: str) -> None:
        if self._skip_depth > 0:
            return
        if self._in_title and not self.title:
            self.title = data.strip()
        if self._in_a:
            self._current_a_text.append(data)
        self._text_parts.append(data)

    def get_clean_text(self) -> str:
        raw = "".join(self._text_parts)
        lines = [" ".join(line.split()) for line in raw.splitlines()]
        return "\n".join(line for line in lines if line)


def parse_html(html_content: str, base_url: str = "") -> tuple[str, str, list[tuple[str, str]]]:
    """解析 HTML，返回 (title, clean_text, links)"""
    parser = _CleanHTMLParser(base_url=base_url)
    parser.feed(html_content)
    parser.close()
    return parser.title, parser.get_clean_text(), parser.links


def is_likely_js_shell(text: str) -> bool:
    """判断抓取到的内容是否为 JS 渲染空壳页或被挑战拦截页"""
    if len(text.strip()) < 180:
        return True
    lowered = text.lower()
    js_markers = ("enable javascript", "you need to enable javascript", "just a moment...", "checking your browser")
    return any(m in lowered for m in js_markers)


def rank_article_links(base_url: str, links: list[tuple[str, str]], limit: int = 3) -> list[tuple[str, str]]:
    """从索引页/列表页链接中筛选最可能包含架构技术细节的子文章链接"""
    base_parsed = urlparse(base_url)
    base_domain = base_parsed.netloc.lower()
    seen: set[str] = {base_url.rstrip("/")}
    scored: list[tuple[int, str, str]] = []

    for href, anchor in links:
        parsed = urlparse(href)
        if parsed.scheme not in ("http", "https"):
            continue
        if parsed.netloc.lower() != base_domain:
            continue
        norm_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
        if norm_url in seen or len(parsed.path.strip("/")) < 3:
            continue
        # 跳过纯资源或登录/定价页
        if any(parsed.path.lower().endswith(ext) for ext in (".png", ".jpg", ".svg", ".css", ".js", ".pdf", ".xml")):
            continue
        if any(bad in norm_url.lower() for bad in ("/login", "/signup", "/pricing", "/careers", "/privacy", "/terms")):
            continue

        seen.add(norm_url)
        combined = f"{parsed.path} {anchor}".lower()
        score = sum(2 for kw in _ARCH_LINK_KEYWORDS if kw in combined)
        if score == 0:
            continue
        # 路径层级越深（如 /blog/how-we-built-x），越可能是具体文章而非顶层菜单
        depth = len([seg for seg in parsed.path.split("/") if seg])
        if depth >= 2:
            score += 2
        if len(anchor) >= 12:
            score += 1
        scored.append((score, href, anchor or href))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [(href, anchor) for _, href, anchor in scored[:limit]]


async def fetch_clean_page(
    client: httpx.AsyncClient,
    url: str,
    max_chars: int = 6000,
    use_jina_fallback: bool = True,
) -> tuple[str, str, list[tuple[str, str]]]:
    """抓取网页并返回 (title, clean_text, internal_links)，必要时降级到 Jina Reader"""
    resp = await client.get(url)
    title = ""
    clean_text = ""
    links: list[tuple[str, str]] = []

    if resp.status_code == 200:
        content_type = resp.headers.get("content-type", "").lower()
        raw_text = resp.text
        if "html" in content_type or "<html" in raw_text[:300].lower():
            title, clean_text, links = parse_html(raw_text, base_url=url)
        else:
            clean_text = raw_text.strip()

    if use_jina_fallback and is_likely_js_shell(clean_text):
        try:
            jina_url = f"https://r.jina.ai/{url}"
            j_resp = await client.get(jina_url, headers={"Accept": "text/plain"})
            if j_resp.status_code == 200 and len(j_resp.text.strip()) > len(clean_text):
                jina_text = re.sub(r"\n{3,}", "\n\n", j_resp.text.strip())
                clean_text = jina_text
        except Exception:
            pass

    return title, clean_text[:max_chars], links
