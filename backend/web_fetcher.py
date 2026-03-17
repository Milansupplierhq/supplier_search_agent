import time
import logging
import requests
from urllib.parse import urljoin, urlparse

from backend.config import APIFY_TOKEN

logger = logging.getLogger(__name__)

# -----------------------
# RAG CONFIG
# -----------------------
RAG_ENDPOINT = "https://rag-web-browser.apify.actor/search"

MAX_PAGES_PER_DOMAIN = 5
MAX_CHARS_TOTAL = 8000
REQUEST_TIMEOUT = 25

# -----------------------
# IN-MEMORY FETCH CACHE
# -----------------------
_fetch_cache: dict[str, tuple[str, float]] = {}  # url → (text, timestamp)
CACHE_TTL = 3600  # 1 hour

# -----------------------
# SMART PATHS TO TRY
# -----------------------
COMMON_PATHS = [
    "",                 # homepage
    "/about",
    "pages/about",
    "/about-us",
    "pages/about-us",
    "/company",
    "/who-we-are",
    "/what-we-do",
    "/products",
    "/solutions",
    "/our-story",
]

CONTACT_PATHS = [
    "/contact",
    "/contact-us",
    "/pages/contact",
    "/pages/contact-us",
    "/get-in-touch",
    "/reach-us",
    "/support",
    "/customer-service",
    "/help",
]


def _build_candidate_urls(base_url: str) -> list[str]:
    """
    Generate up to N candidate URLs for a domain.
    """
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"

    urls = []
    for path in COMMON_PATHS:
        full = urljoin(root, path)
        if full not in urls:
            urls.append(full)

    return urls[:MAX_PAGES_PER_DOMAIN]


def fetch_url(url: str) -> str:
    """
    Fetch ONE page via RAG Web Browser (URL mode).
    Uses in-memory cache to avoid duplicate Apify calls.
    HARD SAFETY NET: never raises; returns "" on any failure.
    """
    # Check cache first
    now = time.time()
    cached = _fetch_cache.get(url)
    if cached:
        text, ts = cached
        if now - ts < CACHE_TTL:
            logger.debug(f"[RAG CACHE HIT] {url}")
            return text
        else:
            del _fetch_cache[url]

    params = {
        "token": APIFY_TOKEN,
        "query": url,                 # URL MODE (no Google search)
        "maxResults": 1,
        "scrapingTool": "raw-http",   # fast, static
        "requestTimeoutSecs": 20,
        "removeCookieWarnings": True,
    }

    try:
        resp = requests.get(RAG_ENDPOINT, params=params, timeout=REQUEST_TIMEOUT)
        resp.raise_for_status()

        items = resp.json()
        if not items:
            _fetch_cache[url] = ("", now)
            return ""

        content = items[0].get("markdown") or items[0].get("text") or ""
        result = content.strip()
        _fetch_cache[url] = (result, now)
        return result

    except Exception as e:
        logger.warning(f"[RAG ERROR] {url} → {e}")
        return ""


def fetch_contact_text(base_url: str, max_chars: int = 4000) -> str:
    """
    Fetch contact-specific pages to find email/phone.
    Tries multiple contact URL patterns, returns first hit.
    """
    parsed = urlparse(base_url)
    root = f"{parsed.scheme}://{parsed.netloc}"

    for path in CONTACT_PATHS:
        url = urljoin(root, path)
        page_text = fetch_url(url)
        if page_text:
            return page_text[:max_chars]

    return ""


def fetch_website_text(base_url: str) -> str:
    """
    Fetch homepage + key informational pages (NO crawling).
    Returns combined text capped at MAX_CHARS_TOTAL.
    """
    texts: list[str] = []
    total_chars = 0

    candidate_urls = _build_candidate_urls(base_url)

    for url in candidate_urls:
        if total_chars >= MAX_CHARS_TOTAL:
            break

        page_text = fetch_url(url)  # ✅ use the safe fetcher
        if not page_text:
            continue

        remaining = MAX_CHARS_TOTAL - total_chars
        if remaining <= 0:
            break

        # ✅ avoid overshooting total limit
        page_text = page_text[:remaining]

        texts.append(page_text)
        total_chars += len(page_text)

    return "\n\n".join(texts)
