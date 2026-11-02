"""Bucket 4 - Answer-friendly content (20 points).

AI tools quote pages that are clear and well structured. We reward good structure
for ANY site, with local-business facts (phone, price, address) as a bonus rather
than a requirement.

  - Clear, descriptive headings ............ up to 6
  - Scannable structure (lists/paragraphs) . up to 5
  - Questions / FAQ (direct answers) ........ up to 3
  - Concrete facts (phone, ₹, address, email) up to 6  (bonus)
"""
from __future__ import annotations

import re

from bs4 import BeautifulSoup

from .base import CheckResult

MAX = 20.0
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\-\s]?)?(?:\(?\d{2,4}\)?[\-\s]?)?\d{3}[\-\s]?\d{4}\b")
PRICE_RE = re.compile(r"(?:₹|\bRs\.?\b|\bINR\b|\$|€|£)\s?\d", re.IGNORECASE)
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
QWORDS = ("how", "what", "why", "when", "where", "who", "which", "can", "do", "is", "are", "should")


def run(data) -> CheckResult:
    html = data.homepage.html if data.homepage else ""
    soup = BeautifulSoup(html or "", "html.parser")
    for t in soup(["script", "style", "noscript"]):
        t.decompose()
    text = soup.get_text(" ", strip=True)
    low = text.lower()
    findings = []
    earned = 0.0

    # 1. Clear, descriptive headings (6)
    headings = [h.get_text(" ", strip=True) for h in soup.find_all(["h1", "h2", "h3"])]
    headings = [h for h in headings if len(h) >= 3]
    if len(headings) >= 2:
        earned += 6
        findings.append(f"{len(headings)} clear headings structure the page.")
    elif headings:
        earned += 3
        findings.append("Only one heading - add more to structure the page.")
    else:
        findings.append("No headings found - AI can't see the page's structure.")

    # 2. Scannable structure: lists or real paragraphs (5)
    lists = soup.find_all(["ul", "ol"])
    paras = [p for p in soup.find_all("p") if len(p.get_text(strip=True)) > 40]
    if lists or len(paras) >= 5:
        earned += 5
        findings.append("Content is scannable (lists / clear paragraphs).")
    else:
        findings.append("Little scannable structure (few lists or paragraphs).")

    # 3. Questions / FAQ (3)
    q_headings = [h for h in headings if "?" in h or h.lower().split(" ")[0] in QWORDS]
    if q_headings or "faq" in low or "frequently asked" in low:
        earned += 3
        findings.append("Has question-style headings or an FAQ (great for AI answers).")
    else:
        findings.append("No FAQ or question-style headings - add some direct Q&A.")

    # 4. Concrete facts - bonus (6)
    facts = []
    fact_pts = 0.0
    if PHONE_RE.search(text):
        fact_pts += 2; facts.append("phone")
    if PRICE_RE.search(text):
        fact_pts += 1.5; facts.append("price")
    if re.search(r"\b(address|pin\s?code|\d{6})\b", low):
        fact_pts += 1.5; facts.append("address")
    if EMAIL_RE.search(text):
        fact_pts += 1; facts.append("email")
    earned += min(fact_pts, 6)
    if facts:
        findings.append("Concrete facts present: " + ", ".join(facts) + ".")
    else:
        findings.append("No concrete facts (phone, price, address) - add them if relevant.")

    earned = min(earned, MAX)
    fix = "" if earned >= MAX else (
        "Use clear descriptive headings, short direct answers and lists; add an FAQ "
        "and concrete facts (phone, price, city) where they fit your business."
    )
    return CheckResult(
        key="answer_friendly", name="Answer-friendly content",
        points=round(earned, 1), max_points=MAX, findings=findings, fix=fix,
    )
