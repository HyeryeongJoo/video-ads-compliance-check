import os

import httpx
import streamlit as st

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

st.set_page_config(page_title="Video Ad Compliance Checker", layout="wide")
st.title("Video Ad Compliance & Brand Safety Checker")
st.caption("Powered by TwelveLabs - Global Makeup Brand Campaign")

SEVERITY_COLORS = {"NONE": "green", "LOW": "blue", "MEDIUM": "orange", "HIGH": "red"}
DECISION_COLORS = {"APPROVE": "green", "REVIEW": "orange", "BLOCK": "red"}
DECISION_ICONS = {"APPROVE": "white_check_mark", "REVIEW": "warning", "BLOCK": "no_entry_sign"}


# --- Input Section ---
tab_upload, tab_url = st.tabs(["File Upload", "Video URL"])

result = None

with tab_upload:
    uploaded_file = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi", "webm"])
    if uploaded_file and st.button("Analyze Video", key="btn_upload"):
        with st.spinner("Uploading and analyzing video... This may take a few minutes."):
            try:
                files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                resp = httpx.post(f"{BACKEND_URL}/api/analyze/upload", files=files, timeout=600)
                resp.raise_for_status()
                result = resp.json()
            except Exception as e:
                st.error(f"Error: {e}")

with tab_url:
    url_input = st.text_input("Enter video URL (YouTube, Vimeo, TikTok, or direct .mp4 link)")
    if url_input and st.button("Analyze Video", key="btn_url"):
        with st.spinner("Downloading and analyzing video... This may take a few minutes."):
            try:
                resp = httpx.post(
                    f"{BACKEND_URL}/api/analyze/url",
                    json={"url": url_input},
                    timeout=600,
                )
                resp.raise_for_status()
                result = resp.json()
            except Exception as e:
                st.error(f"Error: {e}")


# --- Results Section ---
if result:
    st.divider()
    status = result.get("status", "unknown")

    if status == "error":
        st.error(f"Analysis failed: {result.get('explanation', 'Unknown error')}")
    else:
        decision = result.get("decision", "REVIEW")
        icon = DECISION_ICONS.get(decision, "question")
        color = DECISION_COLORS.get(decision, "gray")

        # Decision header
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Decision", decision)
        with col2:
            relevance = result.get("campaign_relevance") or {}
            score = relevance.get("score", "N/A")
            label = relevance.get("label", "N/A")
            st.metric("Campaign Relevance", f"{score}/100", delta=label)
        with col3:
            st.metric("Request ID", result.get("request_id", "")[:8] + "...")

        # Video Description
        st.subheader("Video Description")
        st.write(result.get("video_description", "N/A"))

        # Explanation
        st.subheader("Decision Explanation")
        st.info(result.get("explanation", "N/A"))

        # Campaign Relevance Detail
        if relevance.get("reasoning"):
            st.subheader("Relevance Reasoning")
            st.write(relevance["reasoning"])

        # Policy Violations
        st.subheader("Policy Violations")
        violations = result.get("policy_violations", [])

        if not violations:
            st.success("No policy violations detected.")
        else:
            for v in violations:
                severity = v.get("severity", "NONE")
                sev_color = SEVERITY_COLORS.get(severity, "gray")

                with st.expander(f"{v['category']} - Severity: {severity}", expanded=severity != "NONE"):
                    if severity == "NONE":
                        st.write("No issues detected in this category.")
                    else:
                        for ev in v.get("evidence", []):
                            st.markdown(
                                f"- **[{ev.get('timestamp', 'N/A')}]** ({ev.get('modality', 'N/A')}): "
                                f"{ev.get('description', 'N/A')}"
                            )


# --- History Section ---
st.divider()
st.subheader("Recent Analysis History")

if st.button("Refresh History"):
    try:
        resp = httpx.get(f"{BACKEND_URL}/api/results", timeout=30)
        resp.raise_for_status()
        history = resp.json()
        if not history:
            st.write("No previous analyses found.")
        else:
            for item in history[:10]:
                dec = item.get("decision", "REVIEW")
                icon = DECISION_ICONS.get(dec, "question")
                rid = item.get("request_id", "")[:8]
                desc = (item.get("video_description", "") or "")[:80]
                st.write(f":{icon}: **{dec}** | `{rid}...` | {desc}...")
    except Exception as e:
        st.warning(f"Could not load history: {e}")
