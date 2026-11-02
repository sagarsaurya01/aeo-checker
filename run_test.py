"""Quick command-line test of the audit engine (no web server)."""
import sys

sys.stdout.reconfigure(encoding="utf-8")

from app.scoring import audit_site

url = sys.argv[1] if len(sys.argv) > 1 else "example.com"
a = audit_site(url)
print(f"\n=== {a.url} ===")
if not a.ok:
    print("ERROR:", a.error)
else:
    print(f"SCORE: {a.score}/100  ({a.grade})\n")
    for r in a.results:
        print(f"- {r.name}: {r.points}/{int(r.max_points)}")
        for f in r.findings:
            print(f"    . {f}")
