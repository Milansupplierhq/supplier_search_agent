import json
import logging
from typing import Dict

from openai import OpenAI
from backend.brand_utils import infer_supplier_name
from backend.config import OPENAI_API_KEY, OPENAI_MODEL, NO_TEMPERATURE_MODELS, COUNTRY_ALIASES
from backend.web_fetcher import fetch_website_text, fetch_contact_text
from backend.intent_agent import analyze_intent_with_llm

logger = logging.getLogger(__name__)
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

Also extract:
- The official company/business name as displayed on the website
- Minimum product price (number or null)
- Country of operation (best guess)
- Contact email address if visible on the website (null if not found)
- Contact phone number if visible on the website (null if not found)
- Estimated retail margin percentage. Match the product to the closest category below and return that margin. If the product spans multiple categories, pick the best match. If no category fits, return null.

MARGIN REFERENCE TABLE:
Fire Pit: 40% | Fireplace: 40% | Indoor furniture (couch, chair, etc.): 30%
Patio furniture: 30% | Mattress: 40% | Golf Simulator: 25%
Sauna: 25% | Cold Plunge: 20% | Hot Tub: 17%
Farm/Industrial equipment (loader, snow plow, etc.): 30% | 3D printer: 25%
Power tools (CNC machine, sawmill, table saw, etc.): 25%
Exercise equipment (squat rack, treadmill): 40%
Air Conditioner/Air Purifier/HVAC/Heater (radiator, towel warmer): 30%
Safe (gun safe, media safe, etc.): 20% | Lighting (chandelier, etc.): 25%
Massage Chair: 40% | Kid Stuff (stroller, crib): 25%
Bathroom stuff (sink, toilet, shower, vanity): 20%
Backyard structures (pergola, shed, gazebo): 20% | Espresso Machine: 30%
Pool equipment (pool heater, pool cleaner): 30% | Hyperbaric chamber: 17%
Red light therapy bed: 17% | Sleep Pod: 20%
Elderly stuff (mobility scooter, wheelchair): 40%
Bar Games (pool table, foosball table, poker table): 20%
ATV/UTV/E-Bike: 15% | Trailers (boat trailer, dump trailer, etc.): 25%
Wine Cooler: 20% | Grill: 35% | Smoker: 35% | Oven Range: 25%
Pizza Oven: 30% | Humidor: 20%
Generator, batteries, solar panel, solar kits: 20%
Appliances (fridge, freezer, oven, etc.): 25%
Lawn equipment (mower, trimmer, etc.): 25% | Garage Cabinet/Storage: 15%
Technology (computers, smartphones, drones, etc.): 20%
Commercial Cooking Equipment (deli slicers, commercial ovens, etc.): 25%
Construction Materials (doors, windows, floors, stones, pvc): 25%
Art: 25% | Camping Equipment (tents, hammocks, etc.): 25%
Sports Equipment (batting cage, pitching machine, etc.): 20%
PEMF Machine: 20% | Automotive products (truck tool bed, etc.): 25%
Boats and fishing equipment (pond, aerator, etc.): 20%
Water treatment/filtration systems: 30%
Healing, medical and biofeedback device, CPAP machine: 35%
Sleep Mask, White Noise Machine, Anti-Snoring Device: 35%
EMP Shield/Electricity: 35%
E-Bike, Bicycle, E-Scooter, E-Tricycle, E-Wheel: 20%
Water Sports Equipment (SUP, Paddleboard, Canoe, Kayak, etc.): 25%
Fishing/Hunting Equipment (Fishing Rod, Fishing Bag): 15%
Pool Table, Poker Table, Snooker Table, Foosball Table: 20%
Game Machines, Pinball Machines, Arcade Game Cabinet: 50%
Chicken Coop: 15% | Floor Scrubber: 25%
Music Instruments (Amplifiers, Piano, Guitar, Speakers, Home Theater): 40%
Pets Equipment: 30% | Metal Detectors: 20% | Slot Machines: 15%
Optics (Scope, Rangefinder, Binoculars): 22% | CCTV, Smart Home: 30%
EV Charger, EV Charging Station: 25% | Skis, Snowboard: 40%
Golf Cart: 15% | Chess Set: 20%

Respond ONLY with valid JSON in this schema:
{
  "company_name": "",
  "supplier_type": "",
  "owns_brand": true/false/null,
  "estimated_price_min": number or null,
  "country": "",
  "email": null,
  "phone": null,
  "estimated_margin_pct": null,
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
        logger.error(f"[SUPPLIER LLM ERROR] {type(e).__name__}: {e}")
        return {"error": f"llm_failed:{type(e).__name__}: {str(e)}"}

    return {"error": "llm_no_json"}


def _extract_contact_with_llm(contact_text: str) -> Dict:
    """Extract email and phone from a contact page via LLM."""
    try:
        messages = [
            {"role": "system", "content": (
                "Extract the company contact email and phone number from this webpage content. "
                "Look for general/sales/wholesale contact info, not personal emails. "
                "Respond ONLY with JSON: {\"email\": null, \"phone\": null}"
            )},
            {"role": "user", "content": contact_text[:4000]},
        ]

        kwargs = {"model": OPENAI_MODEL, "messages": messages}
        if OPENAI_MODEL not in NO_TEMPERATURE_MODELS:
            kwargs["temperature"] = 0.0

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
        logger.error(f"[CONTACT LLM ERROR] {type(e).__name__}: {e}")

    return {"email": None, "phone": None}


def process_supplier(
            product: str,
            url: str,
            brand_hint: str | None = None,
            discovery_source: str | None = None,
            price_hint: float | None = None,
            allowed_countries: list[str] | None = None,
        ) -> Dict:
    # -------------------------------------------------
    # 1) Fetch website content
    # -------------------------------------------------
    logger.info(f"[PIPELINE] Processing {url}")
    website_text = fetch_website_text(url)

    if not website_text:
        logger.warning(f"[PIPELINE] {url} — website unavailable")
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

    logger.info(f"[PIPELINE] {url} — intent: {intent_result}")

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

    logger.info(f"[PIPELINE] {url} — supplier LLM: {llm_result}")

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
        "email": llm_result.get("email"),
        "phone": llm_result.get("phone"),
        "estimated_margin_pct": llm_result.get("estimated_margin_pct"),
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
    # 5b) Country filter
    # -------------------------------------------------
    if allowed_countries:
        raw_country = (supplier.get("country") or "").strip()
        normalized = COUNTRY_ALIASES.get(raw_country, raw_country)
        if normalized not in allowed_countries:
            supplier["status"] = "rejected"
            supplier["needs_manual_review"] = False
            supplier["reason"] = f"country_filtered:{raw_country}"
            return supplier

    # -------------------------------------------------
    # 6) Supplier identity enrichment (NO rejection here)
    # -------------------------------------------------
    supplier_name = llm_result.get("company_name") or infer_supplier_name(brand_hint, url)

    supplier.update({
        "supplier_name": supplier_name,
        "brand_names": [brand_hint] if brand_hint else [],
        "discovery_source": [discovery_source] if discovery_source else [],
        "price_hint": price_hint,
    })

    # -------------------------------------------------
    # 6b) Contact info enrichment (only for accepted suppliers)
    # -------------------------------------------------
    if not supplier.get("email") or not supplier.get("phone"):
        contact_text = fetch_contact_text(url)
        if contact_text:
            contact_result = _extract_contact_with_llm(contact_text)
            if not supplier.get("email") and contact_result.get("email"):
                supplier["email"] = contact_result["email"]
            if not supplier.get("phone") and contact_result.get("phone"):
                supplier["phone"] = contact_result["phone"]

    # -------------------------------------------------
    # 7) Final status
    # -------------------------------------------------
    supplier["status"] = "probable"
    supplier["needs_manual_review"] = True
    return supplier

