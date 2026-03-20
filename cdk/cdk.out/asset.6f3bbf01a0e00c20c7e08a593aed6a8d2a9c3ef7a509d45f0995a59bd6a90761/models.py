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
    timestamp: str = ""
    description: str = ""
    modality: str = ""
    confidence: Optional[float] = None


class PolicyViolation(BaseModel):
    category: str
    severity: Severity = Severity.NONE
    evidence: list[Evidence] = []


class CampaignRelevance(BaseModel):
    score: int = Field(default=0, ge=0, le=100)
    label: str = "ON-BRIEF"
    reasoning: str = ""


class ComplianceResult(BaseModel):
    request_id: str
    video_id: str = ""
    video_source: VideoSource = VideoSource.UPLOAD
    decision: Decision = Decision.REVIEW
    video_description: str = ""
    campaign_relevance: Optional[CampaignRelevance] = None
    policy_violations: list[PolicyViolation] = []
    explanation: str = ""
    status: str = "processing"
