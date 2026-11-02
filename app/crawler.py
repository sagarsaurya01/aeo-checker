"""Fetch the pages and files the checks need.

Two views of the homepage are gathered:
  - RAW HTML via httpx (what most AI bots see - no JavaScript).
  - RENDERED HTML via a real browser (Playwright) - runs JavaScript and gets
    past most Cloudflare/bot blocks.

Comparing the two is exactly how we judge "readable without JavaScript", and the
browser render also lets us still score sites that return 403 to a plain fetch.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx

HUMAN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
BOT_UA = "GPTBot/1.0 (+https://openai.com/gptbot)"

TIMEOUT = 15.0
MAX_EXTRA_PAGES = 8


@dataclass
class Page:
    url: str
    status: int
    html: str = ""


@dataclass
class SiteData:
    input_url: str
    base_url: str = ""
    ok: bool = False
    error: str = ""
    homepage: Page | None = None      # best HTML available (for generic checks)
    raw_html: str = ""                # httpx (no-JS) homepage body
    raw_status: int | None = None
    rendered_html: str | None = None  # Playwright (browser) homepage body
    used_browser: bool = False        # True if we fell back to the browser render
    bot_fetch_status: int | None = None
    robots_txt: str | None = None
    robots_status: int | None = None
    sitemap_url: str | None = None
    sitemap_status: int | None = None
    sitemap_urls: list[str] = field(default_factory=list)
    llms_txt_status: int | None = None
    extra_pages: list[Page] = field(default_factory=list)


def _normalise(url: str) -> str:
    url = url.strip()
    if not url.startswith(("http://", "https://")):
        url = "https://" + url
    return url


def _words(html: str) -> int:
    # Rough visible-word count (strip tags).
    text = re.sub(r"(?is)<(script|style|noscript).*?</\1>", " ", html or "")
    text = re.sub(r"(?s)<[^>]+>", " ", text)
    return len(re.findall(r"\w+", text))


def render_with_browser(url: str) -> tuple[int | None, str | None]:
    """Load the page in a real headless browser. Returns (status, html) or (None, None)."""
    try:
        from playwright.sync_api import sync_playwright
    except Exception:
        return None, None
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                headless=True,
                args=[
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-gpu",
                    "--single-process",
                ],
            )
            page = browser.new_page(user_agent=HUMAN_UA, viewport={"width": 1366, "height": 900})
            status = None
            try:
                resp = page.goto(url, wait_until="domcontentloaded", timeout=25000)
                status = resp.status if resp else None
                try:
                    page.wait_for_load_state("networkidle", timeout=5000)
                except Exception:
                    pass
                html = page.content()
            finally:
                browser.close()
            return status, html
    except Exception:
        return None, None


def crawl(input_url: str) -> SiteData:
    data = SiteData(input_url=input_url)
    url = _normalise(input_url)
    parsed = urlparse(url)
    if not parsed.netloc:
        data.error = "That does not look like a valid website address."
        return data
    data.base_url = f"{parsed.scheme}://{parsed.netloc}"

    try:
        with httpx.Client(
            timeout=TIMEOUT, follow_redirects=True, headers={"User-Agent": HUMAN_UA}
        ) as client:
            # RAW homepage (httpx, no JavaScript).
            try:
                r = client.get(url)
                data.raw_status = r.status_code
                data.raw_html = r.text
                data.base_url = f"{urlparse(str(r.url)).scheme}://{urlparse(str(r.url)).netloc}"
                final_url = str(r.url)
            except httpx.HTTPError:
                data.raw_status = None
                final_url = url

            # Homepage as an AI bot, to detect hard blocks.
            try:
                rb = client.get(data.base_url + "/", headers={"User-Agent": BOT_UA})
                data.bot_fetch_status = rb.status_code
            except httpx.HTTPError:
                data.bot_fetch_status = None

            # robots.txt
            try:
                rr = client.get(urljoin(data.base_url, "/robots.txt"))
                data.robots_status = rr.status_code
                if rr.status_code == 200:
                    data.robots_txt = rr.text
            except httpx.HTTPError:
                data.robots_status = None

            # sitemap.xml
            sitemap_url = urljoin(data.base_url, "/sitemap.xml")
            if data.robots_txt:
                m = re.search(r"(?im)^\s*sitemap:\s*(\S+)", data.robots_txt)
                if m:
                    sitemap_url = m.group(1).strip()
            data.sitemap_url = sitemap_url
            try:
                rs = client.get(sitemap_url)
                data.sitemap_status = rs.status_code
                if rs.status_code == 200:
                    data.sitemap_urls = re.findall(r"<loc>\s*([^<\s]+)\s*</loc>", rs.text)
            except httpx.HTTPError:
                data.sitemap_status = None

            # llms.txt
            try:
                rl = client.get(urljoin(data.base_url, "/llms.txt"))
                data.llms_txt_status = rl.status_code
            except httpx.HTTPError:
                data.llms_txt_status = None

            # A few extra pages from the sitemap (same host only).
            host = urlparse(data.base_url).netloc
            seen = {final_url}
            for loc in data.sitemap_urls:
                if len(data.extra_pages) >= MAX_EXTRA_PAGES:
                    break
                if urlparse(loc).netloc != host or loc in seen:
                    continue
                seen.add(loc)
                try:
                    rp = client.get(loc)
                    data.extra_pages.append(Page(url=loc, status=rp.status_code, html=rp.text))
                except httpx.HTTPError:
                    continue

        # RENDERED homepage (real browser) - also the fallback when raw is blocked/thin.
        raw_ok = data.raw_status is not None and data.raw_status < 400 and _words(data.raw_html) >= 50
        if not raw_ok or _words(data.raw_html) < 300:
            status, html = render_with_browser(final_url)
            if html:
                data.rendered_html = html
                if not raw_ok:
                    data.used_browser = True

        # Pick the best HTML for the generic checks.
        if raw_ok:
            best = data.raw_html
            best_status = data.raw_status
        elif data.rendered_html:
            best = data.rendered_html
            best_status = 200
        else:
            best = data.raw_html
            best_status = data.raw_status or 0

        data.homepage = Page(url=final_url, status=best_status or 0, html=best)
        data.ok = bool(best) and _words(best) >= 20
        if not data.ok and not data.error:
            code = data.raw_status if data.raw_status else "no response"
            data.error = f"The site did not load correctly (status {code})."
    except httpx.HTTPError as exc:
        data.error = f"Could not reach the site: {exc.__class__.__name__}."
    return data
