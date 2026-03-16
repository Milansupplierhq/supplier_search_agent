from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel, Field
from typing import List, Optional
import uuid
import traceback
from backend.job_store import init_job, get_job
from backend.research_runner import run_research_job
from backend.utils import domain_from_url
from backend.apify_runner import run_serp_discovery, run_serp_brand_lookup
from backend.google_shopping_runner import run_google_shopping_discovery
from backend.supplier_validator import process_supplier
from backend.filters import is_blocked_domain
from backend.sheets import append_supplier_row
from backend.config import MAX_CANDIDATE_DOMAINS, BATCH_SIZE

app = FastAPI(title="Supplier Agent – Phase 1 Discovery")


# =========================================================
# REQUEST MODEL
# =========================================================
class ResearchRequest(BaseModel):
    product: str = Field(..., min_length=2)
    candidate_urls: Optional[List[str]] = None
    use_apify: bool = True
    max_candidate_domains: Optional[int] = None


# =========================================================
# BRAND → DOMAIN RESOLUTION
# =========================================================

def resolve_brand_domains(brand: str, max_domains: int = 2) -> List[str]:
    results = run_serp_brand_lookup(brand)
    domains = []

    for item in results:
        domain = item.get("domain")
        if not domain:
            continue
        if is_blocked_domain(domain):
            continue

        domains.append(domain)

        if len(domains) >= max_domains:
            break

    return domains

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
        "error": job.get("error"),
    }

@app.get("/research/result/{job_id}")
def research_result(job_id: str):
    job = get_job(job_id)
    if not job:
        return {"status": "not_found"}

    if job["status"] != "completed":
        return {"status": job["status"]}

    return {
        "job_id": job_id,
        "accepted": job["accepted"],
        "rejected": job["rejected"][:50],
        "accepted_count": len(job["accepted"]),
        "rejected_count": len(job["rejected"]),
    }
