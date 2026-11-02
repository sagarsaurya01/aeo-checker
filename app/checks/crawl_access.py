"""Bucket 1 - Crawl access (25 points).

Can AI bots reach the site at all? Two ways a site blocks them:
  1. robots.txt disallows the bot.
  2. The server / Cloudflare returns 403 to the bot's user agent.
"""
from __future__ import annotations

import io
from urllib.robotparser import RobotFileParser

from .base import CheckResult

MAX = 25.0

# The 8 bots from the plan. Equal weight for now (an open decision in the plan).
BOTS = [
    "GPTBot",
    "OAI-SearchBot",
    "ChatGPT-User",
    "ClaudeBot",
    "PerplexityBot",
    "Google-Extended",
    "Googlebot",
    "Bingbot",
]


def run(data) -> CheckResult:
    findings: list[str] = []
    per_bot = MAX / len(BOTS)
    earned = 0.0

    # Parse robots.txt (missing robots.txt = everything allowed).
    rp = RobotFileParser()
    if data.robots_txt:
        rp.parse(io.StringIO(data.robots_txt).read().splitlines())
    else:
        rp.parse([])  # empty => allow all

    blocked = []
    for bot in BOTS:
        allowed = rp.can_fetch(bot, data.base_url + "/")
        if allowed:
            earned += per_bot
        else:
            blocked.append(bot)

    if not data.robots_txt:
        findings.append("No robots.txt found - all bots are allowed by default.")
    if blocked:
        findings.append("Blocked in robots.txt: " + ", ".join(blocked) + ".")
    else:
        findings.append("robots.txt allows all 8 AI/search bots.")

    # Hard block check: did the homepage refuse an AI-bot user agent?
    if data.bot_fetch_status is not None and data.bot_fetch_status in (401, 403, 429, 503):
        earned *= 0.4  # most of the credit is lost if bots are hard-blocked
        findings.append(
            f"The server returned {data.bot_fetch_status} to an AI bot - "
            "likely Cloudflare or a firewall blocking bots."
        )

    fix = ""
    if earned < MAX:
        fix = (
            "Allow AI bots in robots.txt and in your Cloudflare/hosting bot settings. "
            "Add explicit 'User-agent: <bot>' / 'Allow: /' lines and turn off 'block AI bots'."
        )

    return CheckResult(
        key="crawl_access",
        name="Crawl access",
        points=round(earned, 1),
        max_points=MAX,
        findings=findings,
        fix=fix,
    )
