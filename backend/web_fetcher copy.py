from apify_client import ApifyClient
from backend.config import APIFY_TOKEN, APIFY_WEBSITE_CRAWLER_ACTOR_ID

ACTOR_ID = APIFY_WEBSITE_CRAWLER_ACTOR_ID

MAX_PAGES = 3
MAX_CHARS = 8000

def fetch_website_text(url: str) -> str:
    client = ApifyClient(APIFY_TOKEN)

    run_input = {
        "startUrls": [{"url": url}],
        "crawlerType": "cheerio",  # FAST, static HTML
        "maxDepth": 0,             # 👈 DO NOT FOLLOW LINKS
        "maxPagesPerCrawl": MAX_PAGES,
        "sameDomainOnly": True,

        # Kill navigation noise
        "removeCookieWarnings": True,
        "removeNavigation": True,
        "removeFooter": True,

        # Critical: no crawling explosion
        "enqueueLinks": False,     # 👈 IMPORTANT
        "maxRequestsPerMinute": 20,

        "saveHtml": False,
        "saveMarkdown": False,
        "saveFiles": False,
    }

    run = client.actor(ACTOR_ID).call(run_input=run_input)
    dataset_id = run["defaultDatasetId"]

    texts = []
    for item in client.dataset(dataset_id).iterate_items():
        text = (item.get("text") or "").strip()
        if text:
            texts.append(text)

        if len("\n".join(texts)) >= MAX_CHARS:
            break

    return "\n\n".join(texts)[:MAX_CHARS]
