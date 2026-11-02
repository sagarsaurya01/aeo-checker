"""Bucket 2 - Readable without JavaScript (25 points).

Most AI bots read the RAW HTML and do not run JavaScript. We compare:
  - raw HTML (httpx, no JS)      = what bots see
  - rendered HTML (real browser) = what a human sees
If the real content only shows up after JavaScript, bots miss it.

If the browser render is unavailable, we fall back to a raw-text heuristic.
"""
from __future__ import annotations

from bs4 import BeautifulSoup

from .base import CheckResult

MAX = 25.0
SHELL_IDS = ("root", "__next", "app", "app-root", "___gatsby")


def _visible_words(html: str) -> int:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    return len(soup.get_text(" ", strip=True).split())


def run(data) -> CheckResult:
    raw_words = _visible_words(data.raw_html)
    rendered = getattr(data, "rendered_html", None)

    # Preferred path: we have both views, so compare them directly.
    if rendered:
        rendered_words = _visible_words(rendered)
        if rendered_words >= 150:
            coverage = min(raw_words / rendered_words, 1.0)
            earned = MAX * coverage
            findings = [
                f"A human sees about {rendered_words} words; AI bots (raw HTML) see about {raw_words}.",
            ]
            if coverage >= 0.8:
                findings.append("Almost all the content is readable without JavaScript.")
            elif coverage >= 0.4:
                findings.append("Some content needs JavaScript - bots see only part of the page.")
            else:
                findings.append("Most content needs JavaScript or is bot-blocked - bots see very little.")
            fix = "" if coverage >= 0.8 else (
                "Serve the main text in the server HTML (server-side rendering / pre-rendering) "
                "so bots read it without running JavaScript."
            )
            return CheckResult(
                key="js_readable", name="Readable without JavaScript",
                points=round(earned, 1), max_points=MAX, findings=findings, fix=fix,
            )

    # Fallback heuristic: no browser render available.
    soup = BeautifulSoup(data.raw_html or "", "html.parser")
    shell = any(
        el.get("id") in SHELL_IDS and _visible_words(str(el)) < 20
        for el in soup.find_all(id=True)
    )
    ratio = min(raw_words / 300.0, 1.0)
    earned = MAX * ratio
    findings = [f"Raw HTML (what bots see) has about {raw_words} words of real text."]
    if shell and raw_words < 100:
        earned = min(earned, MAX * 0.2)
        findings.append("The page looks like an empty JavaScript shell - bots likely see almost nothing.")
    elif raw_words >= 300:
        findings.append("Plenty of text is readable without JavaScript.")
    else:
        findings.append("Thin text in the raw HTML - some content may need JavaScript.")
    fix = "" if earned >= MAX else (
        "Serve the main text in the server HTML (server-side rendering / pre-rendering)."
    )
    return CheckResult(
        key="js_readable", name="Readable without JavaScript",
        points=round(earned, 1), max_points=MAX, findings=findings, fix=fix,
    )
