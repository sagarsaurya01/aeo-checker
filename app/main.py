"""AEO Readiness Checker - web app.

Routes:
  GET  /              -> the URL + lead form
  POST /audit         -> runs the audit, saves the lead, shows the score
  GET  /leads         -> private page listing every lead (password protected)
  GET  /leads/download-> download all leads as a CSV (password protected)

Leads are written to LEADS_DIR (a Railway persistent volume at /data in
production) so they survive redeploys. If a SHEET_WEBHOOK_URL is also set, each
lead is additionally posted to that Google Sheet.
"""
from __future__ import annotations

import csv
import os
import secrets
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import Depends, FastAPI, Form, HTTPException, Request
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from fastapi.templating import Jinja2Templates

from .scoring import audit_site

BASE_DIR = Path(__file__).resolve().parent.parent
LEADS_DIR = Path(os.environ.get("LEADS_DIR", str(BASE_DIR)))
LEADS_FILE = LEADS_DIR / "leads.csv"
LEADS_PASSWORD = os.environ.get("LEADS_PASSWORD", "").strip()
SHEET_WEBHOOK_URL = os.environ.get("SHEET_WEBHOOK_URL", "").strip()
FIELDS = ["timestamp", "name", "phone", "email", "url", "score"]

app = FastAPI(title="AEO Readiness Checker")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
security = HTTPBasic()


def save_lead(name: str, phone: str, email: str, url: str, score: int) -> None:
    lead = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "name": name, "phone": phone, "email": email, "url": url, "score": score,
    }
    # Optional: also push to a Google Sheet if configured.
    if SHEET_WEBHOOK_URL:
        try:
            httpx.post(SHEET_WEBHOOK_URL, json=lead, timeout=8.0)
        except httpx.HTTPError:
            pass
    # Durable: append to the CSV on the persistent disk.
    try:
        LEADS_DIR.mkdir(parents=True, exist_ok=True)
        new = not LEADS_FILE.exists()
        with LEADS_FILE.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(FIELDS)
            w.writerow([lead[k] for k in FIELDS])
    except OSError:
        pass


def read_leads() -> list[dict]:
    if not LEADS_FILE.exists():
        return []
    with LEADS_FILE.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def require_admin(creds: HTTPBasicCredentials = Depends(security)) -> None:
    ok = bool(LEADS_PASSWORD) and secrets.compare_digest(creds.password, LEADS_PASSWORD)
    if not ok:
        raise HTTPException(
            status_code=401, detail="Unauthorized",
            headers={"WWW-Authenticate": "Basic"},
        )


@app.get("/", response_class=HTMLResponse)
def home(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})


@app.post("/audit", response_class=HTMLResponse)
def run_audit(
    request: Request,
    url: str = Form(...),
    name: str = Form(""),
    phone: str = Form(""),
    email: str = Form(""),
):
    audit = audit_site(url)
    if audit.ok:
        save_lead(name, phone, email, audit.url, audit.score)
    return templates.TemplateResponse(
        "results.html", {"request": request, "audit": audit, "name": name}
    )


@app.get("/leads", response_class=HTMLResponse)
def leads_page(request: Request, _: None = Depends(require_admin)):
    leads = list(reversed(read_leads()))  # newest first
    return templates.TemplateResponse(
        "leads.html", {"request": request, "leads": leads, "count": len(leads)}
    )


@app.get("/leads/download")
def leads_download(_: None = Depends(require_admin)):
    if not LEADS_FILE.exists():
        raise HTTPException(status_code=404, detail="No leads yet.")
    return FileResponse(LEADS_FILE, filename="aeo-leads.csv", media_type="text/csv")
