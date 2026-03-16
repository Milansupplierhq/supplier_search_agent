from typing import Dict, Any

JOBS: Dict[str, Dict[str, Any]] = {}

def init_job(job_id: str):
    JOBS[job_id] = {
        "status": "running",
        "progress": 0,
        "accepted": [],
        "rejected": [],
        "meta": {},
        "total": 0,
        "processed": 0,
        "error": None,
    }

def update_job(job_id: str, **kwargs):
    JOBS[job_id].update(kwargs)

def get_job(job_id: str):
    return JOBS.get(job_id)
