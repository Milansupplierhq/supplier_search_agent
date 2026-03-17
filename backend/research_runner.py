import traceback

from backend.job_store import update_job, get_job
from backend.apify_runner import run_serp_discovery
from backend.google_shopping_runner import run_google_shopping_discovery
from backend.supplier_validator import process_supplier
from backend.filters import is_blocked_domain, is_country_blocked_by_tld
from backend.sheets import append_supplier_row
from backend.config import MAX_CANDIDATE_DOMAINS, DEFAULT_TARGET_SUPPLIERS
from backend.utils import domain_from_url


def _validate_candidates(
    candidates: list[dict],
    target: int,
    accepted: list[dict],
    rejected: list[dict],
    job_id: str,
    req,
    processed: int,
) -> int:
    """
    Validate candidates one by one. Stops early when target accepted count is met.
    Returns updated processed count.
    """
    for item in candidates:
        if len(accepted) >= target:
            break

        # Check if user stopped the job
        job = get_job(job_id)
        if job and job.get("status") == "stopped":
            break

        try:
            supplier = process_supplier(
                product=req.product,
                url=item["url"],
                brand_hint=item.get("brand_name"),
                discovery_source=item.get("discovery_source"),
                price_hint=item.get("price_hint"),
                allowed_countries=req.allowed_countries,
            )

            if supplier.get("status") == "rejected":
                rejected.append(supplier)
            else:
                accepted.append(supplier)
                try:
                    append_supplier_row(job_id, req.product, supplier)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(
                        f"[SHEETS] Failed to write {supplier.get('url')}: {e}"
                    )

        except Exception as e:
            rejected.append({
                "url": item["url"],
                "reason": f"runtime_error:{type(e).__name__}",
            })

        processed += 1

        update_job(
            job_id,
            processed=processed,
            accepted=accepted,
            rejected=rejected,
        )

    return processed


def run_research_job(job_id: str, req):
    """
    Runs supplier research in the background.
    Target-driven: stops when enough accepted suppliers are found.
    NEVER raises — always updates job_store.
    """
    try:
        target = req.target_suppliers or DEFAULT_TARGET_SUPPLIERS
        max_domains = req.max_candidate_domains or MAX_CANDIDATE_DOMAINS

        update_job(job_id, status="running", target_suppliers=target)

        accepted: list[dict] = []
        rejected: list[dict] = []
        seen_domains: set[str] = set()
        processed = 0

        # =================================================
        # PHASE 0 — GOOGLE SHOPPING → BRAND ANCHORS
        # =================================================
        shopping_brands = run_google_shopping_discovery(req.product)
        shopping_candidates: list[dict] = []

        for item in shopping_brands:
            if len(shopping_candidates) + len(seen_domains) >= max_domains:
                break

            brand = item.get("brand")
            price_hint = item.get("price_hint")
            product_url = item.get("example_product_url")

            if not brand or not product_url:
                continue

            domain = domain_from_url(product_url)
            if not domain or domain in seen_domains or is_blocked_domain(domain):
                continue
            if is_country_blocked_by_tld(domain, req.allowed_countries):
                continue

            seen_domains.add(domain)

            shopping_candidates.append({
                "url": f"https://{domain}",
                "brand_name": brand,
                "discovery_source": "google_shopping",
                "price_hint": price_hint,
            })

        # Batch-limit: only validate target × 3 candidates (accounts for ~30% acceptance)
        shopping_budget = min(len(shopping_candidates), target * 3)
        shopping_candidates = shopping_candidates[:shopping_budget]

        update_job(job_id, total=len(shopping_candidates))

        # Validate shopping candidates (stop early if target met)
        processed = _validate_candidates(
            shopping_candidates, target, accepted, rejected,
            job_id, req, processed,
        )

        # =================================================
        # PHASE 1 — SERP FALLBACK (only if target not met)
        # =================================================
        job = get_job(job_id)
        is_stopped = job and job.get("status") == "stopped"

        if not is_stopped and len(accepted) < target and req.use_apify:
            # Batch-limit: only validate enough to fill the gap (× 4 for lower SERP acceptance)
            still_needed = target - len(accepted)
            serp_budget = still_needed * 4

            if serp_budget > 0:
                serp_results = run_serp_discovery(req.product)
                serp_candidates: list[dict] = []

                for item in serp_results:
                    if len(serp_candidates) >= serp_budget:
                        break

                    domain = item.get("domain")
                    if not domain or domain in seen_domains:
                        continue

                    if is_blocked_domain(domain):
                        continue
                    if is_country_blocked_by_tld(domain, req.allowed_countries):
                        continue

                    seen_domains.add(domain)

                    serp_candidates.append({
                        "url": f"https://{domain}",
                        "brand_name": None,
                        "discovery_source": "serp",
                        "price_hint": None,
                    })

                # Update total to include SERP candidates
                update_job(job_id, total=processed + len(serp_candidates))

                # Validate SERP candidates (stop early if target met)
                processed = _validate_candidates(
                    serp_candidates, target, accepted, rejected,
                    job_id, req, processed,
                )

        job = get_job(job_id)
        final_status = "stopped" if (job and job.get("status") == "stopped") else "completed"

        update_job(
            job_id,
            status=final_status,
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
