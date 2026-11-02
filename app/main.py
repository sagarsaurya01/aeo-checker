"""AEO Readiness Checker - web app.

Routes:
  GET  /        -> the URL + lead form
  POST /audit   -> runs the audit, saves the lead, shows the score
"""
from __future__ import annotations

import csv
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, Form, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from .scoring import audit_site

BASE_DIR = Path(__file__).resolve().parent.parent
LEADS_FILE = BASE_DIR / "leads.csv"

app = FastAPI(title="AEO Readiness Checker")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def save_lead(name: str, phone: str, email: str, url: str, score: int) -> None:
    new = not LEADS_FILE.exists()
    with LEADS_FILE.open("a", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        if new:
            w.writerow(["timestamp", "name", "phone", "email", "url", "score"])
        w.writerow([datetime.now().isoformat(timespec="seconds"), name, phone, email, url, score])


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
