import json
from openai import OpenAI
from backend.config import OPENAI_API_KEY, OPENAI_MODEL, NO_TEMPERATURE_MODELS

client = OpenAI(api_key=OPENAI_API_KEY)

INTENT_SYSTEM_PROMPT = """
You are classifying the PRIMARY business intent of a company.

IMPORTANT DEFINITIONS:
- product_company = sells PHYSICAL, tangible products (manufactured goods)
- service_company = services, consulting, agencies, SaaS, software, platforms
- hospitality_medical = hotels, clinics, spas, medical services
- content_media = blogs, news, review sites, directories

CRITICAL RULES:
- SaaS, software tools, platforms, apps are NOT product companies
- If the product is digital → service_company
- Only physical goods qualify as product_company
- Be strict and conservative

Respond ONLY with valid JSON:
{
  "intent": "",
  "confidence": 0.0-1.0,
  "evidence": ""
}
"""


def analyze_intent_with_llm(website_text: str) -> dict:
    try:
        messages = [
            {"role": "system", "content": INTENT_SYSTEM_PROMPT},
            {"role": "user", "content": website_text[:8000]},
        ]

        kwargs = {
            "model": OPENAI_MODEL,
            "messages": messages,
        }

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
        import logging
        logging.error(f"[INTENT LLM ERROR] {type(e).__name__}: {e}")
        return {"error": f"intent_llm_failed: {type(e).__name__}: {str(e)}"}

    return {"error": "intent_llm_no_json"}
