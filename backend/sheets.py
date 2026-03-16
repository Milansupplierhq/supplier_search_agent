from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials
from backend.config import GOOGLE_SHEET_ID, GOOGLE_SHEET_TAB

HEADERS = [
    "job_id",
    "product",
    "supplier_name",
    "url",
    "supplier_type",
    "country",
    "status",
    "needs_manual_review",
    "price_min",
    "price_max",
    "currency",
    "confidence",
    "reason",
    "created_at",
]

def _get_sheet():
    if not GOOGLE_SHEET_ID:
        raise ValueError("Missing GOOGLE_SHEET_ID")

    scope = ["https://www.googleapis.com/auth/spreadsheets"]
    creds = Credentials.from_service_account_file(
        "service_account.json",
        scopes=scope
    )
    gc = gspread.authorize(creds)

    sh = gc.open_by_key(GOOGLE_SHEET_ID)

    try:
        ws = sh.worksheet(GOOGLE_SHEET_TAB)
    except gspread.WorksheetNotFound:
        ws = sh.add_worksheet(title=GOOGLE_SHEET_TAB, rows=1000, cols=20)

    # ✅ Robust header check
    existing_headers = ws.row_values(1)
    if not existing_headers or existing_headers[0] != "job_id":
        ws.update("A1", [HEADERS])

    return ws


def append_supplier_row(job_id: str, product: str, s: dict):
    ws = _get_sheet()

    next_row = len(ws.get_all_values()) + 1

    row = [
        job_id,
        product,
        s.get("supplier_name", ""),
        s.get("url", ""),
        s.get("supplier_type", ""),
        s.get("country", ""),
        s.get("status", ""),
        s.get("needs_manual_review", ""),
        s.get("estimated_price_min", ""),
        s.get("estimated_price_max", ""),
        s.get("currency", ""),
        s.get("confidence", ""),
        s.get("reason", ""),
        datetime.utcnow().isoformat(),
    ]

    ws.update(f"A{next_row}", [row])
