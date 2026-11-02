"""Bucket 4 - Answer-friendly content (20 points).

AI tools quote pages that give clear, direct facts: question-style headings,
FAQs, a phone number, a price, a city/address.
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import CheckResult

MAX = 20.0

PHONE_RE = re.compile(r"(?:\+?91[\-\s]?)?[6-9]\d{9}\b")
PRICE_RE = re.compile(r"(?:₹|\bRs\.?\b|\bINR\b)\s?\d", re.IGNORECASE)
QWORDS = ("how", "what", "why", "when", "where", "who", "which", "can", "do", "is", "are")


def run(data) -> CheckResult:
    html = data.homepage.html if data.homepage else ""
    soup = BeautifulSoup(html or "", "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    text = soup.get_text(" ", strip=True)
    low = text.lower()

    findings = []
    earned = 0.0

    # Question-style headings (6)
    headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
    q_headings = [
        h for h in headings
        if "?" in h or h.lower().split(" ")[0] in QWORDS
    ]
    if q_headings:
        earned += 6
        findings.append(f"{len(q_headings)} question-style heading(s) found.")
    else:
        findings.append("No question-style headings (e.g. 'How do I...?').")

    # FAQ presence (4)
    if "faq" in low or "frequently asked" in low:
        earned += 4
        findings.append("FAQ section detected.")
    else:
        findings.append("No FAQ section found.")

    # Phone (4)
    if PHONE_RE.search(text):
        earned += 4
        findings.append("A phone number is present on the page.")
    else:
        findings.append("No phone number found in the page text.")

    # Price in rupees (3)
    if PRICE_RE.search(text):
        earned += 3
        findings.append("Clear pricing (₹) present.")
    else:
        findings.append("No clear ₹ price on the page.")

    # Address / city hint (3)
    if re.search(r"\b(address|pin\s?code|\d{6})\b", low):
        earned += 3
        findings.append("An address / PIN code is present.")
    else:
        findings.append("No clear address or city on the page.")

    earned = min(earned, MAX)
    fix = ""
    if earned < MAX:
        fix = (
            "Add question-style headings with short, direct answers, an FAQ, and clear facts "
            "(phone, ₹ price, city/address) in plain text."
        )

    return CheckResult(
        key="answer_friendly",
        name="Answer-friendly content",
        points=round(earned, 1),
        max_points=MAX,
        findings=findings,
        fix=fix,
    )
