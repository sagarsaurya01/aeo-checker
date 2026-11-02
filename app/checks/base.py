"""Shared result shape for every check (one 'bucket' from the plan)."""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class CheckResult:
    key: str                 # e.g. "crawl_access"
    name: str                # human title
    points: float            # points earned
    max_points: float        # points possible for this bucket
    findings: list[str] = field(default_factory=list)   # what we saw
    fix: str = ""            # plain-English how to fix it

    @property
    def pct(self) -> int:
        return round(100 * self.points / self.max_points) if self.max_points else 0
