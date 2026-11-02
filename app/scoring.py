"""Run every check and combine into one score out of 100."""
from __future__ import annotations

from dataclasses import dataclass

from .checks import (
    answer_friendly,
    crawl_access,
    discovery_files,
    js_readable,
    structured_data,
)
from .checks.base import CheckResult
from .crawler import SiteData, crawl

CHECKS = [crawl_access, js_readable, structured_data, answer_friendly, discovery_files]


@dataclass
class Audit:
    url: str
    ok: bool
    error: str
    score: int
    grade: str
    results: list[CheckResult]


def _grade(score: int) -> str:
    if score >= 80:
        return "AI-ready"
    if score >= 60:
        return "Mostly ready"
    if score >= 40:
        return "Needs work"
    return "Hard for AI to read"


def audit_site(input_url: str) -> Audit:
    data: SiteData = crawl(input_url)
    if not data.ok:
        return Audit(
            url=input_url, ok=False, error=data.error or "Could not read the site.",
            score=0, grade="", results=[],
        )

    results = [mod.run(data) for mod in CHECKS]
    score = round(sum(r.points for r in results))
    # Sort worst-performing buckets first = the client's top problems.
    results_sorted = sorted(results, key=lambda r: r.pct)
    return Audit(
        url=data.homepage.url if data.homepage else input_url,
        ok=True, error="", score=score, grade=_grade(score), results=results_sorted,
    )
