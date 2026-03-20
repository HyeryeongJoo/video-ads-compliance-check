import os
import traceback

from fastapi import APIRouter, File, Form, UploadFile

from models import (
    AnalyzeRequest,
    CampaignRelevance,
    ComplianceResult,
    Decision,
    Evidence,
    PolicyViolation,
    Severity,
    VideoSource,
)
from services.storage import storage_service
from services.twelvelabs_client import twelvelabs_client
from services.video_input import video_input_router

router = APIRouter()


@router.post("/analyze/upload", response_model=ComplianceResult)
async def analyze_upload(file: UploadFile = File(...)):
    request_id = storage_service.generate_request_id()
    try:
        file_bytes = await file.read()
        local_path = await video_input_router.process_upload(file_bytes, file.filename or "video.mp4")
        return await _run_analysis(request_id, local_path, VideoSource.UPLOAD)
    except Exception as e:
        return _error_result(request_id, VideoSource.UPLOAD, str(e))


@router.post("/analyze/url", response_model=ComplianceResult)
async def analyze_url(req: AnalyzeRequest):
    request_id = storage_service.generate_request_id()
    try:
        local_path, meta = await video_input_router.process_url(req.url)
        source = VideoSource.YOUTUBE if "youtu" in (req.url or "") else VideoSource.DIRECT_URL
        return await _run_analysis(request_id, local_path, source, meta)
    except Exception as e:
        return _error_result(request_id, VideoSource.DIRECT_URL, str(e))


@router.get("/results/{request_id}", response_model=ComplianceResult)
async def get_result(request_id: str):
    item = storage_service.get_result(request_id)
    if not item:
        return ComplianceResult(request_id=request_id, video_source=VideoSource.UPLOAD, status="not_found")
    return ComplianceResult(**item)


@router.get("/results", response_model=list[ComplianceResult])
async def list_results():
    items = storage_service.list_results()
    return [ComplianceResult(**item) for item in items]


async def _run_analysis(
    request_id: str,
    local_path: str,
    source: VideoSource,
    meta: dict | None = None,
) -> ComplianceResult:
    try:
        # Upload to S3
        s3_key = storage_service.upload_video_to_s3(local_path, request_id)

        # Index video in TwelveLabs
        video_id = twelvelabs_client.index_video(local_path)

        # Run compliance analysis
        analysis = twelvelabs_client.analyze_compliance(video_id)

        # Build result
        result = ComplianceResult(
            request_id=request_id,
            video_id=video_id,
            video_source=source,
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

        # Save to DynamoDB
        storage_service.save_result(request_id, result.model_dump(mode="json"))

        return result
    finally:
        # Cleanup temp file
        if os.path.exists(local_path):
            os.remove(local_path)


def _error_result(request_id: str, source: VideoSource, error: str) -> ComplianceResult:
    traceback.print_exc()
    return ComplianceResult(
        request_id=request_id,
        video_source=source,
        decision=Decision.REVIEW,
        explanation=f"Analysis failed: {error}",
        status="error",
    )
