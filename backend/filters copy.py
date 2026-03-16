# ---------------------------------------------
# SERP-stage domain blocking
# Only obvious NON-suppliers
# ---------------------------------------------

BLOCKED_DOMAINS_CONTAINS = (
    # ------------------
    # Marketplaces
    # ------------------
    "amazon.",
    "ebay.",
    "alibaba.",
    "aliexpress.",
    "walmart.",
    "etsy.",
    "wayfair.",
    "overstock.",
    "rakuten.",
    "flipkart.",

    # ------------------
    # Big-box retailers
    # ------------------
    "homedepot.",
    "lowes.",
    "costco.",
    "samsclub.",
    "target.",
    "bestbuy.",
    "menards.",
    "ikea.",
    "acehardware.",
    "canadiantire.",
    "bunnings.",
    "homehardware.",
    "tractorsupply.",
    "harborfreight.",
    "fleetfarm.",
    "northerntool.",

    # ------------------
    # Social / UGC
    # ------------------
    "youtube.",
    "facebook.",
    "instagram.",
    "tiktok.",
    "pinterest.",
    "reddit.",
    "linkedin.",

    # ------------------
    # Reviews / forums
    # ------------------
    "trustpilot.",
    "yelp.",
    "glassdoor.",
    "quora.",

    # ------------------
    # Media / publishers
    # ------------------
    "wikipedia.org",
    "forbes.com",
    "fortune.com",
    "bloomberg.com",
    "wsj.com",
    "nytimes.com",
    "cnn.com",
    "bbc.",
    "reuters.com",
    "techcrunch.com",
    "cnet.com",
    "theverge.com",
    "thespruce.com",
    "healthline.com",
    "verywellhealth.com",
    "everydayhealth.com",

    # ------------------
    # Design / inspiration
    # ------------------
    "dribbble.com",
    "behance.net",
    "webflow.com",
)

def is_blocked_domain(domain: str) -> bool:
    """
    SERP-stage filter ONLY.

    Blocks:
    - marketplaces
    - big-box retailers
    - social platforms
    - review sites
    - pure media

    DOES NOT block:
    - brands
    - manufacturers
    - distributors
    - DTC companies
    """
    d = (domain or "").lower()
    return any(x in d for x in BLOCKED_DOMAINS_CONTAINS)
