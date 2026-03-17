import os
import time
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
BACKEND_SCHEME = os.getenv("BACKEND_SCHEME", "http")
BASE_URL = f"{BACKEND_SCHEME}://{BACKEND_HOST}:{BACKEND_PORT}"

COUNTRY_OPTIONS = [
    "United States",
    "Canada",
    "United Kingdom",
    "Germany",
    "Australia",
]

STATUS_LABELS = {
    "running": "Searching for suppliers...",
    "completed": "Research complete",
    "stopped": "Research stopped",
    "failed": "Research failed",
    "not_found": "Job not found",
}

# ----------------------------
# PAGE CONFIG & STYLING
# ----------------------------
st.set_page_config(page_title="Supplier Agent", layout="wide")

st.markdown("""
<style>
    .block-container { padding-top: 2rem; padding-bottom: 1rem; }

    .supplier-table { overflow-x: auto; }
    .supplier-table table {
        width: 100%;
        border-collapse: collapse;
        font-size: 0.85rem;
    }
    .supplier-table th {
        background: #f1f5f9;
        padding: 10px 12px;
        text-align: left;
        font-weight: 600;
        color: #334155;
        border-bottom: 2px solid #e2e8f0;
    }
    .supplier-table td {
        padding: 8px 12px;
        border-bottom: 1px solid #f1f5f9;
        color: #475569;
    }
    .supplier-table tr:hover td { background: #f8fafc; }
    .supplier-table a { color: #2563eb; text-decoration: none; }
    .supplier-table a:hover { text-decoration: underline; }

    [data-testid="stMetric"] {
        background: #f8fafc;
        border: 1px solid #e2e8f0;
        border-radius: 8px;
        padding: 12px 16px;
    }

    .stTabs [data-baseweb="tab-list"] { gap: 8px; }
    .stTabs [data-baseweb="tab"] {
        border-radius: 6px 6px 0 0;
        padding: 8px 20px;
    }

    .disclaimer {
        text-align: center;
        color: #94a3b8;
        font-size: 0.75rem;
        padding: 8px 0;
    }

    /* Primary button styling (Run Research) */
    .stButton > button[kind="primary"],
    .run-btn button {
        background: #0ea5e9 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        padding: 0.5rem 2rem !important;
        font-weight: 600 !important;
    }
    .stButton > button[kind="primary"]:hover,
    .run-btn button:hover {
        background: #0284c7 !important;
    }

    /* Multiselect tag pills */
    [data-baseweb="tag"] {
        background-color: #e0f2fe !important;
        color: #0369a1 !important;
        border-radius: 6px !important;
    }
    [data-baseweb="tag"] span:first-child {
        color: #0369a1 !important;
    }

    /* Download button styling */
    .stDownloadButton > button {
        background: #059669 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .stDownloadButton > button:hover {
        background: #047857 !important;
    }

    /* Stop button styling */
    .stop-btn button {
        background: #ef4444 !important;
        color: white !important;
        border: none !important;
        border-radius: 8px !important;
        font-weight: 600 !important;
    }
    .stop-btn button:hover {
        background: #dc2626 !important;
    }

    /* Spinner animation */
    @keyframes pulse {
        0%, 100% { opacity: 1; }
        50% { opacity: 0.4; }
    }
    .searching-indicator {
        display: flex;
        align-items: center;
        gap: 10px;
        padding: 12px 16px;
        background: #eff6ff;
        border: 1px solid #bfdbfe;
        border-radius: 8px;
        margin-bottom: 1rem;
    }
    .searching-dot {
        width: 10px;
        height: 10px;
        border-radius: 50%;
        background: #2563eb;
        animation: pulse 1.5s ease-in-out infinite;
    }
    .searching-dot:nth-child(2) { animation-delay: 0.3s; }
    .searching-dot:nth-child(3) { animation-delay: 0.6s; }
    .searching-text {
        color: #1e40af;
        font-weight: 500;
        font-size: 0.9rem;
    }
</style>
""", unsafe_allow_html=True)

ACCEPTED_COLS = {
    "supplier_name": "Supplier Name",
    "url": "Website",
    "product": "Product Type",
    "country": "Country",
    "estimated_price_min": "Est. Price Min",
    "supplier_type": "Supplier Type",
    "confidence": "Confidence",
    "email": "Email",
    "phone": "Phone",
    "estimated_margin_pct": "Est. Margin % (AI)",
    "notes": "Notes",
}

REJECTED_COLS = {
    "supplier_name": "Supplier Name",
    "url": "Website",
    "product": "Product Type",
    "country": "Country",
    "confidence": "Confidence",
    "reason": "Rejection Reason",
    "notes": "Notes",
}


def _render_results(accepted, rejected):
    tab_accepted, tab_rejected = st.tabs(["Accepted Suppliers", "Rejected Suppliers"])

    with tab_accepted:
        if accepted:
            df_a = pd.DataFrame(accepted)
            for col in ACCEPTED_COLS:
                if col not in df_a.columns:
                    df_a[col] = None
            df_a = df_a[[c for c in ACCEPTED_COLS if c in df_a.columns]]
            df_a = df_a.rename(columns=ACCEPTED_COLS)
            df_a = df_a.fillna("\u2014")
            df_a = df_a.replace("None", "\u2014")
            df_a["Website"] = df_a["Website"].apply(
                lambda x: f'<a href="{x}" target="_blank">{x}</a>' if x and x != "\u2014" else "\u2014"
            )
            st.markdown(
                '<div class="supplier-table">' + df_a.to_html(escape=False, index=False) + '</div>',
                unsafe_allow_html=True,
            )
            df_csv = pd.DataFrame(accepted)
            for col in ACCEPTED_COLS:
                if col not in df_csv.columns:
                    df_csv[col] = None
            df_csv = df_csv[[c for c in ACCEPTED_COLS if c in df_csv.columns]]
            df_csv = df_csv.rename(columns=ACCEPTED_COLS)
            st.download_button("Download Accepted CSV", df_csv.to_csv(index=False), file_name="accepted_suppliers.csv", mime="text/csv")
        else:
            st.info("No accepted suppliers found.")

    with tab_rejected:
        if rejected:
            df_r = pd.DataFrame(rejected)
            for col in REJECTED_COLS:
                if col not in df_r.columns:
                    df_r[col] = None
            df_r = df_r[[c for c in REJECTED_COLS if c in df_r.columns]]
            df_r = df_r.rename(columns=REJECTED_COLS)
            df_r = df_r.fillna("\u2014")
            df_r = df_r.replace("None", "\u2014")
            df_r["Website"] = df_r["Website"].apply(
                lambda x: f'<a href="{x}" target="_blank">{x}</a>' if x and x != "\u2014" else "\u2014"
            )
            st.markdown(
                '<div class="supplier-table">' + df_r.to_html(escape=False, index=False) + '</div>',
                unsafe_allow_html=True,
            )
            st.download_button("Download Rejected CSV", df_r.to_csv(index=False), file_name="rejected_suppliers.csv", mime="text/csv")
        else:
            st.info("No rejected suppliers.")


st.title("Supplier Research Agent")
st.caption("Google Shopping \u2192 Google Search \u2192 Validation LLM \u2192 Table")

# ----------------------------
# SESSION STATE
# ----------------------------
if "job_id" not in st.session_state:
    st.session_state.job_id = None
if "is_running" not in st.session_state:
    st.session_state.is_running = False

is_running = st.session_state.is_running

# ----------------------------
# INPUTS (disabled while running)
# ----------------------------
col_input1, col_input2 = st.columns([2, 1])

with col_input1:
    product = st.text_input("Product", placeholder="e.g., Cold Plunge, Outdoor Sauna", disabled=is_running)

with col_input2:
    target_suppliers = st.slider("Suppliers to find", 1, 40, 20, step=1, disabled=is_running)

selected_countries = st.multiselect(
    "Supplier countries",
    COUNTRY_OPTIONS,
    default=COUNTRY_OPTIONS,
    disabled=is_running,
)

# ----------------------------
# BUTTONS
# ----------------------------
if is_running:
    _, col_btn, col_stop, _ = st.columns([3, 1, 1, 3])
    with col_btn:
        st.markdown('<div class="run-btn">', unsafe_allow_html=True)
        run = st.button("Run Research", type="primary", use_container_width=True, disabled=True)
        st.markdown('</div>', unsafe_allow_html=True)
    with col_stop:
        st.markdown('<div class="stop-btn">', unsafe_allow_html=True)
        stop = st.button("Stop Research", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
else:
    _, col_btn, _ = st.columns([3, 1, 3])
    with col_btn:
        st.markdown('<div class="run-btn">', unsafe_allow_html=True)
        run = st.button("Run Research", type="primary", use_container_width=True)
        st.markdown('</div>', unsafe_allow_html=True)
    stop = False

# ----------------------------
# STOP HANDLER
# ----------------------------
if stop and st.session_state.job_id:
    try:
        requests.post(f"{BASE_URL}/research/stop/{st.session_state.job_id}")
    except Exception:
        pass

# ----------------------------
# START JOB
# ----------------------------
if run and not is_running:
    if not product.strip():
        st.error("Please enter a product.")
        st.stop()

    payload = {
        "product": product.strip(),
        "use_apify": True,
        "max_candidate_domains": 200,
        "target_suppliers": int(target_suppliers),
        "allowed_countries": selected_countries,
    }

    with st.spinner("Starting research job..."):
        resp = requests.post(f"{BASE_URL}/research/start", json=payload)
        resp.raise_for_status()
        data = resp.json()

    st.session_state.job_id = data["job_id"]
    st.session_state.is_running = True
    st.rerun()

# ----------------------------
# POLLING
# ----------------------------
job_id = st.session_state.job_id

if job_id and is_running:
    # Animated searching indicator
    anim_placeholder = st.empty()
    anim_placeholder.markdown("""
    <div class="searching-indicator">
        <div class="searching-dot"></div>
        <div class="searching-dot"></div>
        <div class="searching-dot"></div>
        <span class="searching-text">Analyzing supplier websites...</span>
    </div>
    """, unsafe_allow_html=True)

    progress_bar = st.progress(0)
    metrics_placeholder = st.empty()

    while True:
        resp = requests.get(f"{BASE_URL}/research/status/{job_id}")
        resp.raise_for_status()
        status = resp.json()

        state = status.get("status")
        processed = status.get("processed", 0)
        total = status.get("total", 1)

        accepted_count = status.get("accepted_count", 0)
        rejected_count = status.get("rejected_count", 0)
        target = status.get("target_suppliers", target_suppliers)

        supplier_pct = min(int((accepted_count / target) * 100), 100) if target else 0

        progress_bar.progress(supplier_pct)

        m1, m2, m3 = metrics_placeholder.columns(3)
        m1.metric("Suppliers Found", f"{accepted_count} / {target}")
        m2.metric("Candidates Processed", f"{processed} / {total}")
        m3.metric("Rejected", rejected_count)

        if state in ("completed", "stopped", "failed"):
            break

        # Target reached — stop polling immediately
        if accepted_count >= target:
            break

        time.sleep(4)

    # Clear animation
    anim_placeholder.empty()
    st.session_state.is_running = False

    if state == "failed":
        st.session_state.last_error = status.get("error", "Unknown error")
    else:
        # Fetch final results and store in session
        resp = requests.get(f"{BASE_URL}/research/result/{job_id}")
        resp.raise_for_status()
        result = resp.json()
        st.session_state.last_result = result
        st.session_state.last_state = state

    # Rerun to reset buttons (Run Research centered, no Stop button)
    st.rerun()

elif job_id and not is_running:
    # Check for error from just-finished run
    if st.session_state.get("last_error"):
        st.error(f"Research failed: {st.session_state.last_error}")
        st.session_state.last_error = None
    else:
        # Use cached result from session or fetch from backend
        result = st.session_state.get("last_result")
        if not result:
            resp = requests.get(f"{BASE_URL}/research/result/{job_id}")
            if resp.ok:
                result = resp.json()

        if result:
            accepted = result.get("accepted", [])
            rejected = result.get("rejected", [])
            a_count = result.get("accepted_count", len(accepted))
            r_count = result.get("rejected_count", len(rejected))

            last_state = st.session_state.get("last_state", "completed")

            if a_count or r_count:
                if last_state == "stopped":
                    st.warning(f"Research stopped early \u2014 found **{a_count}** suppliers ({r_count} rejected)")
                else:
                    st.success(f"Research complete \u2014 found **{a_count}** suppliers ({r_count} rejected)")
                _render_results(accepted, rejected)
            else:
                st.info("No suppliers found. Try a different product or broader country selection.")

else:
    st.markdown(
        '<p style="text-align:center; color:#94a3b8; padding:2rem 0;">Enter a product and click <b>Run Research</b> to get started.</p>',
        unsafe_allow_html=True,
    )

# ----------------------------
# DISCLAIMER
# ----------------------------
st.markdown(
    '<p class="disclaimer">Supplier Research Agent can make mistakes. Always verify supplier information independently.</p>',
    unsafe_allow_html=True,
)
