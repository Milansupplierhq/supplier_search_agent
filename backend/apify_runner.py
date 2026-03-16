from typing import List, Dict
from apify_client import ApifyClient

from backend.config import APIFY_TOKEN, APIFY_SERP_ACTOR_ID
from backend.utils import normalize_url, domain_from_url


def run_serp_discovery(product: str) -> List[Dict]:
    """
    High-recall SERP discovery.
    Returns a list of {domain, url, title, snippet}
    """

    if not APIFY_TOKEN:
        raise ValueError("Missing APIFY_TOKEN")

    client = ApifyClient(APIFY_TOKEN)

    print(f"[APIFY] Running SERP for: {product}")

    run_input = {
        "queries": product,
        "countryCode": "us",
        "languageCode": "en",
        "maxPagesPerQuery": 15,
        "mobileResults": False,
        "includeUnfilteredResults": False,
        "saveHtml": False,
    }

    run = client.actor(APIFY_SERP_ACTOR_ID).call(run_input=run_input)
    dataset_id = run["defaultDatasetId"]

    items = list(client.dataset(dataset_id).iterate_items())

    results: List[Dict] = []
    seen_domains = set()

    for page in items:
        for r in page.get("organicResults", []):
            url = r.get("url")
            if not url:
                continue

            url = normalize_url(url)
            domain = domain_from_url(url)

            if not domain or domain in seen_domains:
                continue

            seen_domains.add(domain)

            results.append({
                "url": url,
                "domain": domain,
                "title": r.get("title", ""),
                "snippet": r.get("description", ""),
            })

    print(f"[APIFY] Unique domains discovered: {len(results)}")
    return results


def run_serp_brand_lookup(brand: str, limit: int = 1) -> List[str]:
    """
    LOW-recall, HIGH-precision SERP lookup.
    Returns up to `limit` unique domains for a brand.
    """
    client = ApifyClient(APIFY_TOKEN)

    print(f"[APIFY] Brand SERP lookup: {brand}")

    run_input = {
        "queries": brand,
        "countryCode": "us",
        "languageCode": "en",
        "maxPagesPerQuery": 1,   # brand search → first page only
        "mobileResults": False,
        "includeUnfilteredResults": False,
        "saveHtml": False,
    }

    run = client.actor(APIFY_SERP_ACTOR_ID).call(run_input=run_input)
    dataset_id = run.get("defaultDatasetId")

    if not dataset_id:
        return []

    items = list(client.dataset(dataset_id).iterate_items())

    results: List[str] = []
    seen_domains = set()

    for page in items:
        for r in page.get("organicResults", []):
            url = r.get("url")
            if not url:
                continue

            url = normalize_url(url)
            domain = domain_from_url(url)

            if not domain or domain in seen_domains:
                continue

            seen_domains.add(domain)
            results.append(domain)

            if len(results) >= limit:
                print(f"[APIFY] Brand domains capped at {limit}")
                return results   # ⬅️ HARD STOP

    print(f"[APIFY] Brand domains found: {len(results)}")
    return results

