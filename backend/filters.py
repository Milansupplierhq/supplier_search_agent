from urllib.parse import urlparse

# =========================================================
# BLOCKED DOMAIN SUBSTRINGS
# =========================================================
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
    "medium.com",

    # ------------------
    # Design / inspiration
    # ------------------
    "dribbble.com",
    "behance.net",
    "webflow.com",
)

# =========================================================
# BLOCKED TLDS (institutional)
# =========================================================
BLOCKED_TLDS = (
    ".gov",
    ".edu",
    ".mil",
)

# =========================================================
# BLOCKED ORG KEYWORDS (non-commercial orgs)
# =========================================================
BLOCKED_ORG_KEYWORDS = (
    "university",
    "college",
    "school",
    "institute",
    "research",
    "extension",
    "foundation",
    "association",
    "council",
    "regional",
)

# =========================================================
# PUBLIC API
# =========================================================
def is_blocked_domain_or_url(value: str) -> bool:
    """
    Returns True if domain or URL should be excluded entirely.
    Safe for SERP filtering and supplier validation.
    """
    if not value:
        return True

    v = value.lower().strip()

    # Normalize to domain if URL
    if "://" in v:
        parsed = urlparse(v)
        domain = parsed.netloc.lower()
    else:
        domain = v

    # ------------------
    # TLD block (.gov, .edu, etc)
    # ------------------
    for tld in BLOCKED_TLDS:
        if domain.endswith(tld):
            return True

    # ------------------
    # Domain substring block
    # ------------------
    for blocked in BLOCKED_DOMAINS_CONTAINS:
        if blocked in domain:
            return True

    # ------------------
    # Institutional org keywords
    # ------------------
    if domain.endswith(".org"):
        for kw in BLOCKED_ORG_KEYWORDS:
            if kw in domain:
                return True

    return False


# Backwards compatibility
def is_blocked_domain(domain: str) -> bool:
    return is_blocked_domain_or_url(domain)
