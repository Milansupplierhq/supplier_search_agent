import traceback
from typing import List

from backend.job_store import update_job
from backend.apify_runner import run_serp_discovery
from backend.google_shopping_runner import run_google_shopping_discovery
from backend.supplier_validator import process_supplier
from backend.filters import is_blocked_domain
from backend.sheets import append_supplier_row
from backend.config import MAX_CANDIDATE_DOMAINS, BATCH_SIZE
from backend.utils import domain_from_url


def run_research_job(job_id: str, req):
    """
    Runs supplier research in the background.
    NEVER raises — always updates job_store.
    """
    try:
        update_job(job_id, status="running")

        max_domains = req.max_candidate_domains or MAX_CANDIDATE_DOMAINS

        candidates: list[dict] = []
        seen_domains: set[str] = set()

        # =================================================
        # PHASE 0 — GOOGLE SHOPPING → BRAND ANCHORS
        # =================================================
        shopping_brands = run_google_shopping_discovery(req.product)

        for item in shopping_brands:
            if len(candidates) >= max_domains:
                break

            brand = item.get("brand")
            price_hint = item.get("price_hint")
            product_url = item.get("example_product_url")

            if not brand or not product_url:
                continue

            domain = domain_from_url(product_url)
            if not domain or domain in seen_domains or is_blocked_domain(domain):
                continue

            seen_domains.add(domain)

            candidates.append({
                "url": f"https://{domain}",
                "brand_name": brand,
                "discovery_source": "google_shopping",
                "price_hint": price_hint,
            })

        # =================================================
        # PHASE 1 — SERP FALLBACK
        # =================================================
        remaining = max_domains - len(candidates)

        if remaining > 0 and req.use_apify:
            serp_results = run_serp_discovery(req.product)

            for item in serp_results:
                if remaining <= 0:
                    break

                domain = item.get("domain")
                if not domain or domain in seen_domains:
                    continue

                if is_blocked_domain(domain):
                    continue

                seen_domains.add(domain)

                candidates.append({
                    "url": f"https://{domain}",
                    "brand_name": None,
                    "discovery_source": "serp",
                    "price_hint": None,
                })

                remaining -= 1

        total_candidates = len(candidates)

        # 🔑 initialize counters ONCE
        update_job(
            job_id,
            total=total_candidates,
            processed=0,
            accepted=[],
            rejected=[],
        )

        # =================================================
        # PHASE 2 — VALIDATION
        # =================================================
        accepted, rejected = [], []
        processed = 0

        for i in range(0, total_candidates, BATCH_SIZE):
            batch = candidates[i:i + BATCH_SIZE]

            for item in batch:
                try:
                    supplier = process_supplier(
                        product=req.product,
                        url=item["url"],
                        brand_hint=item.get("brand_name"),
                        discovery_source=item.get("discovery_source"),
                        price_hint=item.get("price_hint"),
                    )

                    if supplier.get("status") == "rejected":
                        rejected.append(supplier)
                    else:
                        append_supplier_row(job_id, req.product, supplier)
                        accepted.append(supplier)

                except Exception as e:
                    rejected.append({
                        "url": item["url"],
                        "reason": f"runtime_error:{type(e).__name__}",
                    })

                processed += 1

                # ✅ update COUNTS only
                update_job(
                    job_id,
                    processed=processed,
                    accepted=accepted,
                    rejected=rejected,
                )

        update_job(
            job_id,
            status="completed",
            processed=processed,
            accepted=accepted,
            rejected=rejected,
        )

    except Exception as e:
        update_job(
            job_id,
            status="failed",
            error=str(e),
            traceback=traceback.format_exc(),
        )
