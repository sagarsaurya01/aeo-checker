"""Bucket 3 - Structured data (20 points).

JSON-LD schema tells AI exactly what the business is, instead of guessing.
We reward the schema types the plan lists.
"""
from __future__ import annotations

import json

from bs4 import BeautifulSoup

from .base import CheckResult

MAX = 20.0

# type -> points (capped at MAX overall)
VALUABLE = {
    "Organization": 8,
    "LocalBusiness": 8,
    "FAQPage": 5,
    "Product": 5,
    "Article": 4,
    "BlogPosting": 4,
    "WebSite": 3,
    "BreadcrumbList": 2,
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

    earned = 0.0
    for t, pts in VALUABLE.items():
        if t in found:
            earned += pts
    earned = min(earned, MAX)

    findings = []
    if not blocks:
        findings.append("No JSON-LD structured data found.")
    else:
        findings.append(f"Found {parsed_ok} JSON-LD block(s).")
        if found:
            findings.append("Schema types present: " + ", ".join(sorted(found)) + ".")

    fix = ""
    if earned < MAX:
        missing = [t for t in ("Organization", "LocalBusiness", "FAQPage", "Product") if t not in found]
        fix = (
            "Add JSON-LD schema so AI knows your business name, city and services. "
            "Start with: " + ", ".join(missing[:3]) + "."
        )

    return CheckResult(
        key="structured_data",
        name="Structured data",
        points=round(earned, 1),
        max_points=MAX,
        findings=findings,
        fix=fix,
    )
