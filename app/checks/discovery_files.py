"""Bucket 5 - Discovery files (10 points).

sitemap.xml helps bots find every page. llms.txt is a proposed standard, so it
carries only a small weight (as the plan notes).
"""
from __future__ import annotations

from .base import CheckResult

MAX = 10.0
SITEMAP_PTS = 8.0
LLMS_PTS = 2.0


def run(data) -> CheckResult:
    findings = []
    earned = 0.0

    if data.sitemap_status == 200 and data.sitemap_urls:
        earned += SITEMAP_PTS
        findings.append(f"sitemap.xml found with {len(data.sitemap_urls)} URLs.")
    elif data.sitemap_status == 200:
        earned += SITEMAP_PTS * 0.5
        findings.append("A sitemap.xml exists but looks empty.")
    else:
        findings.append("No sitemap.xml found.")

    if data.llms_txt_status == 200:
        earned += LLMS_PTS
        findings.append("llms.txt is present (nice-to-have).")
    else:
        findings.append("No llms.txt (optional, small weight).")

    fix = ""
    if earned < MAX:
        fix = "Publish a sitemap.xml listing all pages (and optionally an llms.txt)."

    return CheckResult(
        key="discovery_files",
        name="Discovery files",
        points=round(earned, 1),
        max_points=MAX,
        findings=findings,
        fix=fix,
    )
