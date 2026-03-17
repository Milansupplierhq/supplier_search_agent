import logging
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
from backend.job_store import init_job, get_job, update_job
from backend.research_runner import run_research_job

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s | %(message)s")

app = FastAPI(title="Supplier Agent – Phase 1 Discovery")


@app.get("/health")
def health_check():
    """Quick check that env vars are loaded."""
    from backend.config import OPENAI_API_KEY, APIFY_TOKEN, OPENAI_MODEL
    return {
        "openai_key_set": bool(OPENAI_API_KEY),
        "openai_key_prefix": OPENAI_API_KEY[:8] + "..." if OPENAI_API_KEY else "MISSING",
        "openai_model": OPENAI_MODEL,
        "apify_token_set": bool(APIFY_TOKEN),
    }


@app.get("/test-llm")
def test_llm():
    """Test if OpenAI API is reachable."""
    try:
        from openai import OpenAI
        from backend.config import OPENAI_API_KEY, OPENAI_MODEL
        client = OpenAI(api_key=OPENAI_API_KEY)
        response = client.chat.completions.create(
            model=OPENAI_MODEL,
            messages=[{"role": "user", "content": "Say hello in one word."}],
        )
        return {"status": "ok", "response": response.choices[0].message.content}
    except Exception as e:
        return {"status": "error", "error_type": type(e).__name__, "detail": str(e)}


@app.get("/test-apify")
def test_apify():
    """Test if Apify can fetch a website."""
    try:
        from backend.web_fetcher import fetch_website_text
        text = fetch_website_text("https://realflame.com")
        return {
            "status": "ok" if text else "empty",
            "chars": len(text),
            "preview": text[:300] if text else "NO TEXT RETURNED",
        }
    except Exception as e:
        return {"status": "error", "error_type": type(e).__name__, "detail": str(e)}


# =========================================================
# REQUEST MODEL
# =========================================================
class ResearchRequest(BaseModel):
    product: str = Field(..., min_length=2)
    candidate_urls: Optional[List[str]] = None
    use_apify: bool = True
    max_candidate_domains: Optional[int] = None
    target_suppliers: Optional[int] = 20
    allowed_countries: Optional[List[str]] = None


@app.post("/research/start")
def start_research(req: ResearchRequest, background_tasks: BackgroundTasks):
    job_id = str(uuid.uuid4())

    init_job(job_id)

    background_tasks.add_task(
        run_research_job,
        job_id,
        req
    )

    return {
        "job_id": job_id,
        "status": "started",
    }

@app.get("/research/status/{job_id}")
def research_status(job_id: str):
    job = get_job(job_id)
    if not job:
        return {"status": "not_found"}

    processed = job.get("processed", 0)
    total = job.get("total", 0)

    progress_pct = round((processed / total) * 100, 1) if total else 0.0

    return {
        "status": job["status"],
        "processed": processed,
        "total": total,
        "progress_pct": progress_pct,
        "accepted_count": len(job.get("accepted", [])),
        "rejected_count": len(job.get("rejected", [])),
        "target_suppliers": job.get("target_suppliers", 0),
        "error": job.get("error"),
    }

@app.post("/research/stop/{job_id}")
def stop_research(job_id: str):
    job = get_job(job_id)
    if not job:
        return {"status": "not_found"}
    if job["status"] == "running":
        update_job(job_id, status="stopped")
        return {"status": "stopped"}
    return {"status": job["status"]}


@app.get("/research/result/{job_id}")
def research_result(job_id: str):
    job = get_job(job_id)
    if not job:
        return {"status": "not_found"}

    accepted = job.get("accepted", [])
    rejected = job.get("rejected", [])

    # Allow fetching results even mid-run (e.g. when target is met)
    if job["status"] not in ("completed", "stopped", "running"):
        return {"status": job["status"]}

    return {
        "job_id": job_id,
        "status": job["status"],
        "accepted": accepted,
        "rejected": rejected[:50],
        "accepted_count": len(accepted),
        "rejected_count": len(rejected),
    }
