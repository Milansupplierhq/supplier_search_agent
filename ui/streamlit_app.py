import os
import time
import requests
import pandas as pd
import streamlit as st
from dotenv import load_dotenv

load_dotenv()

BACKEND_HOST = os.getenv("BACKEND_HOST", "127.0.0.1")
BACKEND_PORT = os.getenv("BACKEND_PORT", "8000")
BASE_URL = f"http://{BACKEND_HOST}:{BACKEND_PORT}"

st.set_page_config(page_title="Supplier Agent", layout="wide")

st.title("Supplier Research Agent")
st.caption("Google Shopping -> Google Search -> Validation LLM -> Table")

# ----------------------------
# INPUTS
# ----------------------------
product = st.text_input("Product", placeholder="e.g., Cold Plunge, Outdoor Sauna")
use_apify = st.toggle("Use Apify discovery", value=True)
max_domains = st.slider("Max candidate domains", 10, 200, 60, step=10)

run = st.button("Run Research")

# ----------------------------
# SESSION STATE
# ----------------------------
if "job_id" not in st.session_state:
    st.session_state.job_id = None

# ----------------------------
# START JOB
# ----------------------------
if run:
    if not product.strip():
        st.error("Please enter a product.")
        st.stop()

    payload = {
        "product": product.strip(),
        "use_apify": use_apify,
        "max_candidate_domains": int(max_domains),
    }

    with st.spinner("Starting research job..."):
        resp = requests.post(f"{BASE_URL}/research/start", json=payload)
        resp.raise_for_status()
        data = resp.json()

    st.session_state.job_id = data["job_id"]
    st.success(f"Job started: {st.session_state.job_id}")

# ----------------------------
# POLLING
# ----------------------------
job_id = st.session_state.job_id

if job_id:
    status_placeholder = st.empty()
    progress_bar = st.progress(0)
    metrics_placeholder = st.empty()

    while True:
        resp = requests.get(f"{BASE_URL}/research/status/{job_id}")
        resp.raise_for_status()
        status = resp.json()

        state = status.get("status")
        processed = status.get("processed", 0)
        total = status.get("total", max_domains)
        percent = status.get("progress_pct", 0)

        accepted = status.get("accepted_count", 0)
        rejected = status.get("rejected_count", 0)

        progress_bar.progress(int(percent))

        status_placeholder.info(f"Status: **{state}**")

        metrics_placeholder.markdown(
            f"""
            **Progress:** {percent}%  
            **Processed:** {processed} / {total}  
            **Accepted:** {accepted}  
            **Rejected:** {rejected}
            """
        )

        if state == "completed":
            break

        if state == "failed":
            st.error(status.get("error", "Job failed"))
            st.stop()

        time.sleep(4)

    # ----------------------------
    # FETCH RESULTS
    # ----------------------------
    with st.spinner("Fetching results..."):
        resp = requests.get(f"{BASE_URL}/research/result/{job_id}")
        resp.raise_for_status()
        result = resp.json()

    st.success(
        f"Done! Accepted: {result['accepted_count']} | "
        f"Rejected: {result['rejected_count']}"
    )

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Accepted Suppliers")
        accepted = result.get("accepted", [])
        if accepted:
            df_a = pd.json_normalize(accepted)
            st.dataframe(df_a, use_container_width=True)
        else:
            st.write("No accepted suppliers.")

    with col2:
        st.subheader("Rejected Suppliers")
        rejected = result.get("rejected", [])
        if rejected:
            df_r = pd.json_normalize(rejected)
            st.dataframe(df_r, use_container_width=True)
        else:
            st.write("No rejected suppliers.")
