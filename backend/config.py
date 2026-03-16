import os
from dotenv import load_dotenv

load_dotenv()

def env_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, default))
    except Exception:
        return default

def env_float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, default))
    except Exception:
        return default

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5")
NO_TEMPERATURE_MODELS = {
    "gpt-5",
    "gpt-5-mini",
}

APIFY_TOKEN = os.getenv("APIFY_TOKEN", "")
APIFY_SERP_ACTOR_ID = os.getenv("APIFY_SERP_ACTOR_ID", "apify/google-search-scraper")
APIFY_WEBSITE_CRAWLER_ACTOR_ID = os.getenv("APIFY_WEBSITE_CRAWLER_ACTOR_ID", "apify/website-content-crawler")
RAG_BROWSER_ACTOR_ID = os.getenv("RAG_BROWSER_ACTOR_ID", "apify/rag-web-browser")
APIFY_MAX_RESULTS_PER_QUERY = env_int("APIFY_MAX_RESULTS_PER_QUERY", 20)
APIFY_GOOGLE_SHOPPING_ACTOR_ID = os.getenv("APIFY_GOOGLE_SHOPPING_ACTOR_ID", "burbn/google-shopping-scraper")

MAX_CANDIDATE_DOMAINS = env_int("MAX_CANDIDATE_DOMAINS", 200)
DEFAULT_TARGET_SUPPLIERS = env_int("DEFAULT_TARGET_SUPPLIERS", 20)
BATCH_SIZE = env_int("BATCH_SIZE", 10)
REQUEST_TIMEOUT_SEC = env_int("REQUEST_TIMEOUT_SEC", 12)
MAX_RETRIES = env_int("MAX_RETRIES", 3)
SLEEP_BETWEEN_DOMAINS_SEC = env_float("SLEEP_BETWEEN_DOMAINS_SEC", 0.5)

GOOGLE_SHEET_ID="12jzffHna_C-ouJj9iptRCwVTPvnXHdj8zrRV-S2wR2E"
GOOGLE_SHEET_TAB="Supplier"
# --- Supplier rules ---
COUNTRY_OPTIONS = [
    "United States",
    "Canada",
    "United Kingdom",
    "Germany",
    "Australia",
]

COUNTRY_ALIASES = {
    "US": "United States", "USA": "United States", "United States": "United States",
    "America": "United States",
    "CA": "Canada", "Canada": "Canada",
    "UK": "United Kingdom", "United Kingdom": "United Kingdom",
    "Great Britain": "United Kingdom", "England": "United Kingdom",
    "DE": "Germany", "Germany": "Germany", "Deutschland": "Germany",
    "AU": "Australia", "Australia": "Australia",
}

ALLOWED_COUNTRIES = {
    "United States",
    "USA",
    "US",
    "Canada",
    "CA",
    "United Kingdom",
    "UK",
    "Germany",
    "DE",
    "Australia",
    "AU",
}
