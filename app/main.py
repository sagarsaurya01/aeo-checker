"""AEO Readiness Checker - web app.

Routes:
  GET  /        -> the URL + lead form
  POST /audit   -> runs the audit, saves the lead, shows the score
"""
from __future__ import annotations

import csv
import os
from datetime import datetime
from pathlib import Path

import httpx
from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .scoring import audit_site

BASE_DIR = Path(__file__).resolve().parent.parent
LEADS_FILE = BASE_DIR / "leads.csv"
# Google Sheet webhook (an Apps Script web-app URL). Set in Railway variables.
SHEET_WEBHOOK_URL = os.environ.get("SHEET_WEBHOOK_URL", "").strip()

app = FastAPI(title="AEO Readiness Checker")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def save_lead(name: str, phone: str, email: str, url: str, score: int) -> None:
    lead = {
        "timestamp": datetime.now().isoformat(timespec="seconds"),
        "name": name,
        "phone": phone,
        "email": email,
        "url": url,
        "score": score,
    }
    # 1) Durable: send to the Google Sheet if a webhook is configured.
    if SHEET_WEBHOOK_URL:
        try:
            httpx.post(SHEET_WEBHOOK_URL, json=lead, timeout=8.0)
        except httpx.HTTPError:
            pass  # never let a sheet hiccup break the audit
    # 2) Local fallback copy (wiped on Railway redeploys, kept for local runs).
    new = not LEADS_FILE.exists()
    try:
        with LEADS_FILE.open("a", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            if new:
                w.writerow(list(lead.keys()))
            w.writerow(list(lead.values()))
    except OSError:
        pass


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
