from typing import List, Dict, Optional
import re
from apify_client import ApifyClient
from backend.config import APIFY_TOKEN, APIFY_GOOGLE_SHOPPING_ACTOR_ID


# -----------------------------------
# CONFIG
# -----------------------------------
MAX_RESULTS = 50

# absolute junk we never want here
HARD_BLOCK_DOMAINS = (
    "amazon.",
    "ebay.",
    "walmart.",
    "aliexpress.",
)


# -----------------------------------
# BRAND NORMALIZATION
# -----------------------------------
def _normalize_brand(name: str) -> str:
    return re.sub(r"\s+", " ", name.strip()).title()


def _extract_brand_from_title(title: str) -> Optional[str]:
    """
    Fallback brand extraction from product title.
    Example:
    'Almost Heaven Saunas Harmony Infrared Sauna'
    → 'Almost Heaven Saunas'
    """
    if not title:
        return None

    # heuristic: first 2–4 capitalized words
    words = title.split()
    if len(words) < 2:
        return None

    return " ".join(words[:3])


# -----------------------------------
# MAIN RUNNER
# -----------------------------------
def run_google_shopping_discovery(product: str) -> List[Dict]:
    """
    Phase 0: Brand discovery via Google Shopping.

    Returns:
    [
        {
            "brand": "Almost Heaven Saunas",
            "price_hint": 8634.99,
            "example_product_url": "...",
            "merchant": "Almost Heaven Saunas",
            "discovery_source": "google_shopping"
        }
    ]
    """

    if not APIFY_TOKEN:
        print("[SHOPPING] Missing APIFY_TOKEN — skipping")
        return []

    client = ApifyClient(APIFY_TOKEN)

    print(f"[APIFY] Google Shopping discovery for: {product}")

    run_input = {
        "searchQuery": product,
        "country": "us",
        "language": "en",
        "limit": MAX_RESULTS,
        "sortBy": "HIGHEST_PRICE",
    }

    try:
        run = client.actor(APIFY_GOOGLE_SHOPPING_ACTOR_ID).call(
            run_input=run_input
        )
    except Exception as e:
        print(f"[SHOPPING ERROR] Actor failed → {e}")
        return []

    dataset_id = run.get("defaultDatasetId")
    if not dataset_id:
        return []

    items = list(client.dataset(dataset_id).iterate_items())

    brands: Dict[str, Dict] = {}

    for item in items:
        # ----------------------------
        # basic fields (actor-dependent)
        # ----------------------------
        title = item.get("title") or ""
        price = item.get("price")
        product_url = item.get("productUrl") or item.get("url") or ""
        merchant = item.get("merchant") or item.get("storeName") or ""

        # hard junk filter
        if any(bad in product_url.lower() for bad in HARD_BLOCK_DOMAINS):
            continue

        # ----------------------------
        # BRAND EXTRACTION (fallback chain)
        # ----------------------------
        brand = (
            item.get("brand")
            or _extract_brand_from_title(title)
            or merchant
        )

        if not brand:
            continue

        brand = _normalize_brand(brand)

        # ----------------------------
        # DEDUP BY BRAND
        # ----------------------------
        if brand not in brands:
            brands[brand] = {
                "brand": brand,
                "price_hint": price,
                "example_product_url": product_url,
                "merchant": merchant,
                "discovery_source": "google_shopping",
            }

    results = list(brands.values())

    print(f"[APIFY] Shopping brands discovered: {len(results)}")

    return results
