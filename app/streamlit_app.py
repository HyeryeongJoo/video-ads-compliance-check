import os
import traceback

import streamlit as st

from config import settings
from models import (
    CampaignRelevance,
    ComplianceResult,
    Decision,
    Evidence,
    PolicyViolation,
    Severity,
)
from storage import storage
from twelvelabs_client import tl_client

st.set_page_config(page_title="Video Ad Compliance Checker", layout="wide")
st.title("Video Ad Compliance & Brand Safety Checker")
st.caption("Powered by TwelveLabs | Global Makeup Brand Campaign")

SEVERITY_COLORS = {"NONE": "green", "LOW": "blue", "MEDIUM": "orange", "HIGH": "red"}
DECISION_ICONS = {"APPROVE": ":white_check_mark:", "REVIEW": ":warning:", "BLOCK": ":no_entry_sign:"}


def _build_result(request_id: str, video_id: str, analysis: dict) -> ComplianceResult:
    return ComplianceResult(
        request_id=request_id,
        video_id=video_id,
        decision=Decision(analysis.get("decision", "REVIEW")),
        video_description=analysis.get("video_description", ""),
        campaign_relevance=CampaignRelevance(**analysis["campaign_relevance"])
        if "campaign_relevance" in analysis
        else None,
        policy_violations=[
            PolicyViolation(
                category=v["category"],
                severity=Severity(v.get("severity", "NONE")),
                evidence=[Evidence(**e) for e in v.get("evidence", [])],
            )
            for v in analysis.get("policy_violations", [])
        ],
        explanation=analysis.get("explanation", ""),
        status="completed",
    )


def run_analysis(file_bytes: bytes, filename: str) -> ComplianceResult:
    request_id = storage.generate_request_id()
    status = st.empty()

    try:
        status.text("Saving video locally...")
        ext = os.path.splitext(filename)[1] or ".mp4"
        local_path = os.path.join("/tmp/videos", f"{request_id}{ext}")
        os.makedirs("/tmp/videos", exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(file_bytes)

        status.text("Uploading video to S3...")
        storage.upload_video_to_s3(local_path, request_id)

        status.text("Indexing video in TwelveLabs...")
        video_id = tl_client.index_video(local_path, callback=lambda msg: status.text(msg))

        status.text("Running compliance analysis...")
        analysis = tl_client.analyze_compliance(video_id)

        result = _build_result(request_id, video_id, analysis)
        storage.save_result(request_id, result.model_dump(mode="json"))
        status.text("Analysis complete!")
        return result

    except Exception as e:
        traceback.print_exc()
        status.error(f"Analysis failed: {e}")
        return ComplianceResult(
            request_id=request_id,
            explanation=f"Error: {e}", status="error",
        )
    finally:
        if os.path.exists(local_path):
            os.remove(local_path)


# --- Input Section ---
result = None

uploaded_file = st.file_uploader("Upload a video file", type=["mp4", "mov", "avi", "webm"])
if uploaded_file and st.button("Analyze Video"):
    result = run_analysis(uploaded_file.getvalue(), uploaded_file.name)


# --- Results Section ---
if result and result.status != "error":
    st.divider()

    decision = result.decision.value
    icon = DECISION_ICONS.get(decision, "")

    # Decision header
    st.subheader(f"{icon} Decision: {decision}")

    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Decision", decision)
    with col2:
        if result.campaign_relevance:
            st.metric(
                "Campaign Relevance",
                f"{result.campaign_relevance.score}/100",
                delta=result.campaign_relevance.label,
            )
    with col3:
        st.metric("Request ID", result.request_id[:8] + "...")

    # Video Description
    st.subheader("Video Description")
    st.write(result.video_description or "N/A")

    # Explanation
    st.subheader("Decision Explanation")
    st.info(result.explanation or "N/A")

    # Campaign Relevance Detail
    if result.campaign_relevance and result.campaign_relevance.reasoning:
        st.subheader("Relevance Reasoning")
        st.write(result.campaign_relevance.reasoning)

    # Policy Violations
    st.subheader("Policy Violations")
    if not result.policy_violations:
        st.success("No policy violations detected.")
    else:
        for v in result.policy_violations:
            severity = v.severity.value
            with st.expander(
                f"{v.category} - Severity: {severity}",
                expanded=severity != "NONE",
            ):
                if severity == "NONE":
                    st.write("No issues detected in this category.")
                else:
                    for ev in v.evidence:
                        st.markdown(
                            f"- **[{ev.timestamp}]** ({ev.modality}): {ev.description}"
                        )


# --- History Section ---
st.divider()
st.subheader("Recent Analysis History")

if st.button("Load History"):
    try:
        history = storage.list_results(limit=10)
        if not history:
            st.write("No previous analyses found.")
        else:
            for item in history:
                dec = item.get("decision", "REVIEW")
                icon = DECISION_ICONS.get(dec, "")
                rid = item.get("request_id", "")[:8]
                desc = (item.get("video_description", "") or "")[:80]
                st.write(f"{icon} **{dec}** | `{rid}...` | {desc}...")
    except Exception as e:
        st.warning(f"Could not load history: {e}")
