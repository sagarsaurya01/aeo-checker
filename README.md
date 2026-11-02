# AEO Readiness Checker

A free web tool that audits any website for AI visibility (AEO) and scores it out
of 100 on how well AI tools (ChatGPT, Gemini, Perplexity, Google AI) can read it.
Each audit captures a lead for paid fixing work.

## Run it locally
```
.venv\Scripts\python.exe -m uvicorn app.main:app --port 8000
```
Then open http://127.0.0.1:8000/ in a browser.

## What it checks (score out of 100)
1. Crawl access (25) - are AI bots allowed (robots.txt + real bot fetch)
2. Readable without JavaScript (25) - is the text in the raw HTML
3. Structured data (20) - JSON-LD schema (Organization, LocalBusiness, FAQ, Product...)
4. Answer-friendly content (20) - question headings, FAQ, phone, ₹ price, address
5. Discovery files (10) - sitemap.xml and llms.txt

## Layout
- app/crawler.py - fetches homepage, robots.txt, sitemap, llms.txt, a few pages
- app/checks/ - one file per bucket
- app/scoring.py - runs all checks, totals the score
- app/main.py - the web app (form + results)
- templates/ - the web pages
- leads.csv - every audit's lead (created on first run)

## Done so far
- All 5 checks, scoring, web form, results page, lead capture. Runs and tested locally.

## Not built yet
- Bucket 2 upgrade: real-browser (Playwright) fetch, so it can read JS-heavy sites and
  get past sites that block plain fetches (several real sites return 403 to the simple fetch).
- PDF report emailed to the lead.
- Deploy to an Indian server (DigitalOcean Bangalore / AWS Mumbai).
- Confirm scoring weights and per-bot weights (open decisions in the plan).
