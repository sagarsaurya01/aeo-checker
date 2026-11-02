"""Fetch the pages and files the checks need.

The crawler is deliberately light: it fetches the homepage, robots.txt, the
sitemap and llms.txt, and a few extra pages from the sitemap. Every check reads
from the SiteData object this builds, so no check does its own fetching.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urljoin, urlparse

import httpx

# A normal browser-like user agent for the "human" fetch.
HUMAN_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
)
# One AI-bot user agent, used to see whether bots get blocked (403/challenge).
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
    base_url: str = ""          # scheme + host, e.g. https://example.com
    ok: bool = False
    error: str = ""
    homepage: Page | None = None
    bot_fetch_status: int | None = None   # homepage fetched AS a bot
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
            # Homepage (as a human/browser).
            r = client.get(url)
            data.homepage = Page(url=str(r.url), status=r.status_code, html=r.text)
            data.base_url = f"{urlparse(str(r.url)).scheme}://{urlparse(str(r.url)).netloc}"

            # Homepage fetched AS an AI bot, to detect hard blocks.
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

            # sitemap.xml (from robots.txt if named there, else the default path)
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
            seen = {data.homepage.url}
            for loc in data.sitemap_urls:
                if len(data.extra_pages) >= MAX_EXTRA_PAGES:
                    break
                if urlparse(loc).netloc != host or loc in seen:
                    continue
                seen.add(loc)
                try:
                    rp = client.get(loc)
                    data.extra_pages.append(
                        Page(url=loc, status=rp.status_code, html=rp.text)
                    )
                except httpx.HTTPError:
                    continue

        data.ok = data.homepage is not None and data.homepage.status < 400
        if not data.ok and not data.error:
            code = data.homepage.status if data.homepage else "no response"
            data.error = f"The site did not load correctly (status {code})."
    except httpx.HTTPError as exc:
        data.error = f"Could not reach the site: {exc.__class__.__name__}."
    return data
