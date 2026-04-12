# Amazon Tracker MVP

Standalone Python backend service that scrapes Amazon product pages (AE, SA, AU), stores time-series snapshots in PostgreSQL, detects changes, and exposes data via FastAPI REST API and CSV export.

## Setup

```bash
pip install -r requirements.txt
playwright install chromium
```

## Configuration

Copy `.env.example` to `.env` and adjust values as needed. All settings use the `TRACKER_` prefix.

## Running

```bash
uvicorn app.main:app --reload
```
