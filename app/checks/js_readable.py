"""Bucket 2 - Readable without JavaScript (25 points).

Most AI bots read the RAW HTML and do not run JavaScript. If the main content
only appears after JS runs (React/Wix/etc.), bots see an almost empty page.

Without a browser we use a strong heuristic: how much real text is in the raw
HTML, and whether the page looks like an empty JS 'shell'.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import CheckResult

MAX = 25.0

# Common empty-shell containers used by JS frameworks.
SHELL_IDS = ("root", "__next", "app", "app-root", "___gatsby")


def _visible_words(html: str) -> int:
    soup = BeautifulSoup(html or "", "html.parser")
    for tag in soup(["script", "style", "noscript", "template"]):
        tag.decompose()
    text = soup.get_text(" ", strip=True)
    return len(re.findall(r"\w+", text))


def run(data) -> CheckResult:
    html = data.homepage.html if data.homepage else ""
    words = _visible_words(html)
    soup = BeautifulSoup(html or "", "html.parser")

    shell = False
    for el in soup.find_all(id=True):
        if el.get("id") in SHELL_IDS and _visible_words(str(el)) < 20:
            shell = True
            break

    # Score from the amount of readable text (300+ words = full marks).
    ratio = min(words / 300.0, 1.0)
    earned = MAX * ratio
    findings = [f"Raw HTML (what bots see) has about {words} words of real text."]

    if shell and words < 100:
        earned = min(earned, MAX * 0.2)
        findings.append(
            "The page looks like an empty JavaScript shell - bots likely see almost nothing."
        )
    elif words >= 300:
        findings.append("Plenty of text is readable without JavaScript.")
    else:
        findings.append("Thin text in the raw HTML - some content may need JavaScript to show.")

    fix = ""
    if earned < MAX:
        fix = (
            "Make the main text available in the server HTML (server-side rendering / "
            "pre-rendering), so bots read it without running JavaScript."
        )

    return CheckResult(
        key="js_readable",
        name="Readable without JavaScript",
        points=round(earned, 1),
        max_points=MAX,
        findings=findings,
        fix=fix,
    )
