"""Bucket 3 - Structured data (20 points).

JSON-LD schema tells AI exactly what a page is, instead of guessing. We credit
ANY valid, recognised schema (news, article, product, local business, etc.) -
not just one site type.

Scoring:
  - valid JSON-LD present ................. 10 (base)
  - each distinct recognised @type ....... +4 (capped at 20 total)
"""
from __future__ import annotations

import json

from bs4 import BeautifulSoup

from .base import CheckResult

MAX = 20.0
BASE = 10.0
PER_TYPE = 4.0

# A broad set of legitimate schema.org types worth crediting.
RECOGNISED = {
    "Organization", "LocalBusiness", "Corporation", "NewsMediaOrganization",
    "ProfessionalService", "Store", "Restaurant",
    "WebSite", "WebPage", "SearchAction", "BreadcrumbList",
    "FAQPage", "QAPage", "HowTo", "Question",
    "Product", "Offer", "Service",
    "Article", "NewsArticle", "BlogPosting", "Blog",
    "VideoObject", "ImageObject", "Recipe", "Event", "Course",
    "Person", "Review", "AggregateRating", "PostalAddress",
}


def _types_in(obj, found: set):
    if isinstance(obj, dict):
        t = obj.get("@type")
        if isinstance(t, str):
            found.add(t)
        elif isinstance(t, list):
            found.update(x for x in t if isinstance(x, str))
        for v in obj.values():
            _types_in(v, found)
    elif isinstance(obj, list):
        for v in obj:
            _types_in(v, found)


def run(data) -> CheckResult:
    html = data.homepage.html if data.homepage else ""
    soup = BeautifulSoup(html or "", "html.parser")
    blocks = soup.find_all("script", attrs={"type": "application/ld+json"})

    found: set[str] = set()
    parsed_ok = 0
    for b in blocks:
        raw = b.string or b.get_text() or ""
        try:
            _types_in(json.loads(raw), found)
            parsed_ok += 1
        except (json.JSONDecodeError, TypeError):
            continue

    recognised = found & RECOGNISED
    findings = []
    if not parsed_ok:
        earned = 0.0
        findings.append("No JSON-LD structured data found.")
    else:
        earned = min(BASE + PER_TYPE * len(recognised), MAX)
        findings.append(f"Found {parsed_ok} JSON-LD block(s).")
        if found:
            findings.append("Schema types present: " + ", ".join(sorted(found)) + ".")

    fix = ""
    if earned < MAX:
        if not parsed_ok:
            fix = ("Add JSON-LD schema so AI knows what your pages are. "
                   "For a business start with Organization or LocalBusiness and FAQPage.")
        else:
            fix = "Add more schema (e.g. FAQPage, Product/Service, or Article) to describe your pages fully."

    return CheckResult(
        key="structured_data", name="Structured data",
        points=round(earned, 1), max_points=MAX, findings=findings, fix=fix,
    )
