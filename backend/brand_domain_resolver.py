from backend.apify_runner import run_serp_discovery
from backend.filters import is_blocked_domain

def resolve_brand_domains(brand: str, max_domains: int = 3):
    """
    Uses SERP to resolve official domains for a brand.
    """
    results = run_serp_discovery(brand)
    domains = []

    for item in results:
        domain = item.get("domain")
        if not domain:
            continue
        if is_blocked_domain(domain):
            continue
        if domain in domains:
            continue

        domains.append(domain)

        if len(domains) >= max_domains:
            break

    return domains
