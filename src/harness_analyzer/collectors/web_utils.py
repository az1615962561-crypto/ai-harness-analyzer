"""网页抓取、反爬虫侦测与礼貌限流公共工具 (Web Extraction & Anti-Bot Guard Utilities)
提供：
1. 反爬虫/WAF/CAPTCHA/限流特征侦测（绝不绕过验证码或反爬门禁，命中即熔断退出并如实上报）
2. 按域名速率控制与熔断器 (DomainRateLimiter)
3. 基于标准库 html.parser 剥离导航/页脚/脚本噪音并抽取链接
4. 仅对无反爬阻断的纯静态 SPA 壳页面自动降级 Jina Reader
"""
from __future__ import annotations

import asyncio
from html.parser import HTMLParser
import random
import re
import time
from typing import Mapping
from urllib.parse import urljoin, urlparse
import httpx

from harness_analyzer.models.harness import BlockedSource

_SKIP_TAGS = {"script", "style", "noscript", "svg", "nav", "footer", "header", "aside"}
_BLOCK_TAGS = {"p", "div", "section", "article", "li", "h1", "h2", "h3", "h4", "h5", "h6", "pre", "code", "blockquote", "tr"}

_ARCH_LINK_KEYWORDS = (
    "architecture", "agent", "harness", "prompt", "index", "context", "sandbox",
    "diff", "sql", "rag", "routing", "mcp", "workflow", "engine", "under-the-hood",
    "how-we-built", "technical", "engineering", "system",
    "架构", "原理", "工程", "拆解", "实践",
)

_CLOUDFLARE_MARKERS = (
    "just a moment...",
    "attention required! | cloudflare",
    "cf-browser-verification",
    "enable javascript and cookies to continue",
    "checking if the site connection is secure",
)

_CAPTCHA_MARKERS = (
    "g-recaptcha",
    "h-captcha",
    "cf-turnstile",
    "verify you are human",
    "are you a robot",
    "captcha-delivery",
    "perimeterx",
    "datadome",
)


def detect_antibot_block(status_code: int, headers: Mapping[str, str], body: str) -> str | None:
    """侦测 HTTP 响应是否触发了反爬拦截、WAF、验证码或速率限制，未触发返回 None"""
    norm_headers = {k.lower(): v.lower() for k, v in headers.items()}
    lower_body = (body or "")[:8000].lower()

    if status_code == 429 or "retry-after" in norm_headers and status_code >= 400:
        return "rate_limited_429"
    if norm_headers.get("cf-mitigated") == "challenge":
        return "cloudflare_challenge"
    if any(m in lower_body for m in _CLOUDFLARE_MARKERS):
        return "cloudflare_challenge"
    if any(m in lower_body for m in _CAPTCHA_MARKERS):
        return "captcha_or_antibot"
    if status_code == 403:
        return "forbidden_403"
    if status_code == 503 and len(lower_body.strip()) < 4000:
        return "service_unavailable_503"
    return None


class DomainRateLimiter:
    """按域名实施礼貌爬取间隔控制与反爬熔断保护"""

    def __init__(self, min_interval: float = 1.0, max_concurrency: int = 4):
        self.min_interval = min_interval
        self._sem = asyncio.Semaphore(max_concurrency)
        self._domain_locks: dict[str, asyncio.Lock] = {}
        self._last_request_at: dict[str, float] = {}
        self.blocked_domains: dict[str, str] = {}
        self.blocked_records: list[BlockedSource] = []

    @staticmethod
    def _domain(url: str) -> str:
        return urlparse(url).netloc.lower()

    def is_blocked(self, url: str) -> str | None:
        return self.blocked_domains.get(self._domain(url))

    def trip_circuit(self, url: str, reason: str, status_code: int | None = None) -> None:
        """某域名触发反爬/限流后立即熔断，本次运行不再请求该域名"""
        dom = self._domain(url)
        if dom and dom not in self.blocked_domains:
            self.blocked_domains[dom] = reason
        self.blocked_records.append(BlockedSource(url=url, reason=reason, status_code=status_code))

    async def acquire(self, url: str) -> str | None:
        """等待域名礼貌间隔；若该域名已被熔断则立即返回阻断原因"""
        dom = self._domain(url)
        if dom in self.blocked_domains:
            return self.blocked_domains[dom]

        lock = self._domain_locks.setdefault(dom, asyncio.Lock())
        async with lock:
            if dom in self.blocked_domains:
                return self.blocked_domains[dom]
            now = time.monotonic()
            last = self._last_request_at.get(dom, 0.0)
            wait_sec = (last + self.min_interval + random.uniform(0.05, 0.35)) - now
            if wait_sec > 0:
                await asyncio.sleep(wait_sec)
            self._last_request_at[dom] = time.monotonic()
        return None

    @property
    def semaphore(self) -> asyncio.Semaphore:
        return self._sem


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
        self.links: list[tuple[str, str]] = []

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
    """判断 200 响应是否为无反爬拦截的纯前端 SPA 渲染壳页面"""
    if len(text.strip()) < 180:
        return True
    lowered = text.lower()
    return "enable javascript" in lowered or "you need to enable javascript" in lowered


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
        if any(parsed.path.lower().endswith(ext) for ext in (".png", ".jpg", ".svg", ".css", ".js", ".pdf", ".xml")):
            continue
        if any(bad in norm_url.lower() for bad in ("/login", "/signup", "/pricing", "/careers", "/privacy", "/terms")):
            continue

        seen.add(norm_url)
        combined = f"{parsed.path} {anchor}".lower()
        score = sum(2 for kw in _ARCH_LINK_KEYWORDS if kw in combined)
        if score == 0:
            continue
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
    rate_limiter: DomainRateLimiter | None = None,
) -> tuple[str, str, list[tuple[str, str]]]:
    """抓取网页并返回 (title, clean_text, internal_links)。
    命中反爬/验证码/限流时立即停止并熔断记录，不尝试绕过。
    """
    if rate_limiter is not None:
        blocked = await rate_limiter.acquire(url)
        if blocked:
            return "", "", []

    async def _do_get() -> httpx.Response:
        if rate_limiter is not None:
            async with rate_limiter.semaphore:
                return await client.get(url)
        return await client.get(url)

    resp = await _do_get()
    block_reason = detect_antibot_block(resp.status_code, resp.headers, resp.text)
    if block_reason:
        if rate_limiter is not None:
            rate_limiter.trip_circuit(url, block_reason, status_code=resp.status_code)
        return "", "", []

    if resp.status_code >= 400:
        if rate_limiter is not None:
            rate_limiter.blocked_records.append(
                BlockedSource(url=url, reason=f"http_{resp.status_code}", status_code=resp.status_code)
            )
        return "", "", []

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

    # 仅在确认为公开 200 状态且无反爬门禁的纯 SPA 壳页面时，才降级 Jina Reader
    if use_jina_fallback and resp.status_code == 200 and is_likely_js_shell(clean_text):
        try:
            jina_url = f"https://r.jina.ai/{url}"
            if rate_limiter is not None:
                async with rate_limiter.semaphore:
                    j_resp = await client.get(jina_url, headers={"Accept": "text/plain"})
            else:
                j_resp = await client.get(jina_url, headers={"Accept": "text/plain"})
            j_block = detect_antibot_block(j_resp.status_code, j_resp.headers, j_resp.text)
            if not j_block and j_resp.status_code == 200 and len(j_resp.text.strip()) > len(clean_text):
                clean_text = re.sub(r"\n{3,}", "\n\n", j_resp.text.strip())
        except Exception:
            pass

    return title, clean_text[:max_chars], links


def run_search_query(
    query: str,
    language: str = "en",
    max_results: int = 4,
    timeout: int = 6,
) -> list[dict]:
    """基于 ddgs 多后端按语种路由检索（英文优先 yahoo,bing；中文优先 bing,yahoo），避开失效/超时后端"""
    backend = "bing,yahoo" if language == "zh" else "yahoo,bing"
    try:
        from ddgs import DDGS
        return list(DDGS(timeout=timeout).text(query, max_results=max_results, backend=backend))
    except ImportError:
        from duckduckgo_search import DDGS as LegacyDDGS
        with LegacyDDGS() as d:
            return list(d.text(query, max_results=max_results))
