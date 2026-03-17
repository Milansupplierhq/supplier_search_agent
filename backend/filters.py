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


# =========================================================
# TLD → COUNTRY MAPPING (for pre-LLM country filtering)
# =========================================================
TLD_COUNTRY = {
    ".cn": "China",
    ".jp": "Japan",
    ".kr": "South Korea",
    ".in": "India",
    ".br": "Brazil",
    ".mx": "Mexico",
    ".ru": "Russia",
    ".tr": "Turkey",
    ".th": "Thailand",
    ".vn": "Vietnam",
    ".id": "Indonesia",
    ".ph": "Philippines",
    ".tw": "Taiwan",
    ".pl": "Poland",
    ".cz": "Czech Republic",
    ".it": "Italy",
    ".es": "Spain",
    ".fr": "France",
    ".nl": "Netherlands",
    ".se": "Sweden",
    ".no": "Norway",
    ".dk": "Denmark",
    ".fi": "Finland",
    ".at": "Austria",
    ".ch": "Switzerland",
    ".be": "Belgium",
    ".pt": "Portugal",
    ".co.uk": "United Kingdom",
    ".uk": "United Kingdom",
    ".de": "Germany",
    ".com.au": "Australia",
    ".au": "Australia",
    ".ca": "Canada",
}


def quick_country_from_tld(domain: str) -> str | None:
    """
    Infer country from domain TLD. Returns country name or None if .com/.net/etc.
    Checks longest suffixes first so .co.uk matches before .uk.
    """
    domain = domain.lower()
    # Check compound TLDs first (e.g. .co.uk, .com.au)
    for tld, country in sorted(TLD_COUNTRY.items(), key=lambda x: -len(x[0])):
        if domain.endswith(tld):
            return country
    return None


def is_country_blocked_by_tld(domain: str, allowed_countries: list[str] | None) -> bool:
    """
    Returns True if domain TLD maps to a country NOT in allowed_countries.
    Returns False for .com/.net/generic TLDs (can't infer country).
    """
    if not allowed_countries:
        return False
    country = quick_country_from_tld(domain)
    if country is None:
        return False  # generic TLD, can't filter
    return country not in allowed_countries


# Backwards compatibility
def is_blocked_domain(domain: str) -> bool:
    return is_blocked_domain_or_url(domain)
