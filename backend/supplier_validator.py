import json
from typing import Dict

from openai import OpenAI
from backend.brand_utils import infer_supplier_name
from backend.config import OPENAI_API_KEY, OPENAI_MODEL, NO_TEMPERATURE_MODELS
from backend.web_fetcher import fetch_website_text
from backend.intent_agent import analyze_intent_with_llm

client = OpenAI(api_key=OPENAI_API_KEY)


SYSTEM_PROMPT = """
You are a supplier research analyst.

Classify the company based ONLY on the website content provided.

Choose EXACTLY ONE supplier_type from:
- Manufacturer
- Brand owner
- Distributor
- Retailer
- Marketplace
- Media / Blog
- Unknown

Definitions:
- Manufacturer: designs, produces, or owns branded products
- Brand owner: sells products under its own brand (even if outsourced manufacturing)
- Distributor: sells products B2B, often wholesale, not direct-to-consumer focused
- Retailer: resells multiple third-party brands to consumers
- Marketplace: multi-vendor platform
- Media / Blog: content-only site
- Unknown: insufficient evidence

Rules:
- If evidence is weak or unclear → Unknown
- Unknown companies MUST NOT be treated as suppliers
- Be decisive, do not hedge

Estimate best-effort:
- Minimum product price (number or null)
- Country of operation (best guess)

Respond ONLY with valid JSON in this schema:
{
  "supplier_type": "",
  "owns_brand": true/false/null,
  "estimated_price_min": number or null,
  "country": "",
  "confidence": 0.0-1.0,
  "notes": ""
}
"""


def analyze_supplier_with_llm(website_text: str) -> Dict:
    try:
        messages = [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": website_text[:12000]},
        ]

        kwargs = {
            "model": OPENAI_MODEL,
            "messages": messages,
        }

        if OPENAI_MODEL not in NO_TEMPERATURE_MODELS:
            kwargs["temperature"] = 0.1

        response = client.chat.completions.create(**kwargs)
        raw = response.choices[0].message.content.strip()

        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            start = raw.find("{")
            end = raw.rfind("}")
            if start != -1 and end != -1:
                return json.loads(raw[start:end + 1])

    except Exception as e:
        return {"error": f"llm_failed:{str(e)}"}

    return {"error": "llm_no_json"}


def process_supplier(
            product: str,
            url: str,
            brand_hint: str | None = None,
            discovery_source: str | None = None,
            price_hint: float | None = None,
        ) -> Dict:
    # -------------------------------------------------
    # 1) Fetch website content
    # -------------------------------------------------
    website_text = fetch_website_text(url)

    if not website_text:
        return {
            "product": product,
            "url": url,
            "status": "rejected",
            "needs_manual_review": False,
            "reason": "website_unavailable",
            "confidence": 0.6,
        }

    # -------------------------------------------------
    # 2) Intent classification (LLM)
    # -------------------------------------------------
    intent_result = analyze_intent_with_llm(website_text)

    if "error" in intent_result or "intent" not in intent_result:
        return {
            "product": product,
            "url": url,
            "status": "rejected",
            "needs_manual_review": False,
            "reason": intent_result.get("error", "intent_missing"),
            "confidence": 0.4,
        }

    intent = intent_result["intent"].strip().lower()

    if intent not in {"product_company"}:
        return {
            "product": product,
            "url": url,
            "status": "rejected",
            "needs_manual_review": False,
            "reason": f"intent:{intent}",
            "confidence": intent_result.get("confidence", 0.8),
            "notes": intent_result.get("evidence", ""),
        }

    # -------------------------------------------------
    # 3) Supplier classification (LLM)
    # -------------------------------------------------
    llm_result = analyze_supplier_with_llm(website_text)

    if "error" in llm_result:
        return {
            "product": product,
            "url": url,
            "status": "rejected",
            "needs_manual_review": False,
            "reason": llm_result["error"],
            "confidence": 0.4,
        }

    supplier = {
        "product": product,
        "url": url,
        "intent": intent,
        "intent_confidence": intent_result.get("confidence"),
        "intent_evidence": intent_result.get("evidence"),
        "supplier_type": llm_result.get("supplier_type"),
        "owns_brand": llm_result.get("owns_brand"),
        "estimated_price_min": llm_result.get("estimated_price_min"),
        "country": llm_result.get("country"),
        "confidence": llm_result.get("confidence", 0.5),
        "notes": llm_result.get("notes", ""),
    }

    supplier_type = (supplier.get("supplier_type") or "").strip().lower()

    # -------------------------------------------------
    # 4) Hard rejects
    # -------------------------------------------------
    HARD_REJECT_TYPES = {
        "unknown",
        "retailer",
        "marketplace",
        "media / blog",
        "media",
        "blog",
        "news",
        "directory",
    }

    if supplier_type in HARD_REJECT_TYPES:
        supplier["status"] = "rejected"
        supplier["needs_manual_review"] = False
        supplier["reason"] = f"hard_reject:{supplier_type}"
        return supplier

    # -------------------------------------------------
    # 5) Allow-list
    # -------------------------------------------------
    if supplier_type not in {"manufacturer", "brand owner", "distributor"}:
        supplier["status"] = "rejected"
        supplier["needs_manual_review"] = False
        supplier["reason"] = f"unsupported_type:{supplier_type}"
        return supplier

        # -------------------------------------------------
    # 6) Supplier identity enrichment (NO rejection here)
    # -------------------------------------------------
    supplier_name = infer_supplier_name(brand_hint, url)

    supplier.update({
        "supplier_name": supplier_name,
        "brand_names": [brand_hint] if brand_hint else [],
        "discovery_source": [discovery_source] if discovery_source else [],
        "price_hint": price_hint,
    })

    # -------------------------------------------------
    # 7) Final status
    # -------------------------------------------------
    supplier["status"] = "probable"
    supplier["needs_manual_review"] = True
    return supplier

