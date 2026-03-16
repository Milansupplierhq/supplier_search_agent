# Supplier Agent (MVP)

## What it does
- Streamlit UI: enter a product -> runs supplier discovery via Apify SERP -> validates suppliers via LLM -> stores golden suppliers to Google Sheets.
- FastAPI backend: provides /research/run endpoint.

## Setup
1) Create a venv, install deps:
   - python -m venv .venv
   - source .venv/bin/activate
   - pip install -r requirements.txt

2) Create .env from .env.example and fill keys.
3) Put your Google service account key at project root:
   - service_account.json
   - Share the Google Sheet with the service account email.

## Run backend
uvicorn backend.main:app --reload --host 127.0.0.1 --port 8000

## Run UI
streamlit run ui/streamlit_app.py
