from backend.apify_runner import ApifyClient
from urllib.parse import urlparse

from backend.config import APIFY_TOKEN, APIFY_WEBSITE_CRAWLER_ACTOR_ID

MAX_CHARS = 8000
MAX_PAGES_QUICK = 3
MAX_PAGES_DEEP = 3

# Pages we never want
NOISE_PATHS = (
    "/blog",
    "/news",
    "/policy",
    "/privacy",
    "/terms",
    "/careers",
    "/jobs",
    "/press",
)

# Pages we want first
PRIORITY_PATHS = (
    "/",                # homepage
    "/about",
    "/company",
    "/who-we-are",
    "/products",
    "/collections",
    "/shop",
    "/catalog",
)


def _path_priority(url: str) -> int:
    """
    Lower number = higher priority
    """
    path = urlparse(url).path.lower()

    if path in ("", "/"):
        return 0

    for i, p in enumerate(PRIORITY_PATHS, start=1):
        if p != "/" and p in path:
            return i

    return 99


def fetch_website_text(url: str, mode: str = "quick") -> str:
    """
    Two-phase crawler.

    quick:
        homepage + about + 1 product page
    deep:
        up to 3 strongest pages
    """

    max_pages = MAX_PAGES_QUICK if mode == "quick" else MAX_PAGES_DEEP

    client = ApifyClient(APIFY_TOKEN)

    run_input = {
        "startUrls": [{"url": url}],
        "maxDepth": 1,
        "maxPagesPerCrawl": max_pages,
        "removeCookieWarnings": True,
        "removeNavigation": True,
        "removeFooter": True,
        "saveFiles": False,
        "saveHtml": False,
        "saveMarkdown": False,
    }

    run = client.actor(APIFY_WEBSITE_CRAWLER_ACTOR_ID).call(run_input=run_input)
    dataset_id = run.get("defaultDatasetId")

    items = list(client.dataset(dataset_id).iterate_items())

    # Remove noise pages
    cleaned = []
    for item in items:
        page_url = (item.get("url") or "").lower()
        if any(p in page_url for p in NOISE_PATHS):
            continue
        cleaned.append(item)

    # Sort by priority
    cleaned.sort(key=lambda x: _path_priority(x.get("url", "")))

    texts = []
    for item in cleaned:
        if len(texts) >= max_pages:
            break

        text = (item.get("text") or "").strip()
        if text:
            texts.append(text)

    merged = "\n\n".join(texts)
    return merged[:MAX_CHARS]
