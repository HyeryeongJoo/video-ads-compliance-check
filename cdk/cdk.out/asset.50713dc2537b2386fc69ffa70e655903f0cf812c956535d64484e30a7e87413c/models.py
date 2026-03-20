from __future__ import annotations

from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Decision(str, Enum):
    APPROVE = "APPROVE"
    REVIEW = "REVIEW"
    BLOCK = "BLOCK"


class Severity(str, Enum):
    NONE = "NONE"
    LOW = "LOW"
    MEDIUM = "MEDIUM"
    HIGH = "HIGH"


class VideoSource(str, Enum):
    UPLOAD = "upload"
    YOUTUBE = "youtube"
    DIRECT_URL = "direct_url"


class Evidence(BaseModel):
    timestamp: str = Field(..., description="e.g. '01:23 - 01:28'")
    description: str
    modality: str = Field(..., description="visual, speech, or text_on_screen")
    confidence: Optional[float] = None


class PolicyViolation(BaseModel):
    category: str
    severity: Severity
    evidence: list[Evidence] = []


class CampaignRelevance(BaseModel):
    score: int = Field(..., ge=0, le=100)
    label: str = Field(..., description="ON-BRIEF or OFF-BRIEF")
    reasoning: str = ""


class AnalyzeRequest(BaseModel):
    url: Optional[str] = None


class ComplianceResult(BaseModel):
    request_id: str
    video_id: str = ""
    video_source: VideoSource
    decision: Decision = Decision.REVIEW
    video_description: str = ""
    campaign_relevance: Optional[CampaignRelevance] = None
    policy_violations: list[PolicyViolation] = []
    explanation: str = ""
    status: str = "processing"
