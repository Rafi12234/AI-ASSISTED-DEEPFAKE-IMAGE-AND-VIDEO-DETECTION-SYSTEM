from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


MediaType = Literal["image", "video", "audio", "audio_video", "unknown"]
RiskLevel = Literal["likely_authentic", "uncertain", "suspicious", "high_risk"]


class ModelEvidence(BaseModel):
    model_name: str
    model_version: str
    model_type: str
    input_type: str
    score: float = Field(ge=0.0, le=1.0)
    confidence: float = Field(ge=0.0, le=1.0)
    latency_ms: int | None = None
    device: str = "cpu"
    details: dict[str, Any] = Field(default_factory=dict)


class ForensicEvidence(BaseModel):
    signal_type: str
    signal_name: str
    score: float = Field(ge=0.0, le=1.0)
    severity: str
    description: str
    raw_data: dict[str, Any] = Field(default_factory=dict)


class FaceEvidence(BaseModel):
    face_id: str
    bbox: list[float] = Field(default_factory=list)
    detection_confidence: float | None = None
    face_score: float | None = None
    frame_number: int | None = None
    timestamp_seconds: float | None = None
    crop_path: str | None = None
    heatmap_path: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class FrameEvidence(BaseModel):
    frame_number: int
    timestamp_seconds: float | None = None
    frame_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    faces: list[FaceEvidence] = Field(default_factory=list)
    details: dict[str, Any] = Field(default_factory=dict)


class AudioEvidence(BaseModel):
    audio_fake_score: float | None = None
    av_sync_score: float | None = None
    speech_segments_analyzed: int = 0
    details: dict[str, Any] = Field(default_factory=dict)


class AnalysisPipelineResult(BaseModel):
    media_type: MediaType
    engine: str
    final_score: float = Field(ge=0.0, le=1.0)
    risk_level: RiskLevel
    confidence: float = Field(ge=0.0, le=1.0)
    explanation: str

    model_evidence: list[ModelEvidence] = Field(default_factory=list)
    forensic_evidence: list[ForensicEvidence] = Field(default_factory=list)
    face_evidence: list[FaceEvidence] = Field(default_factory=list)
    frame_evidence: list[FrameEvidence] = Field(default_factory=list)
    audio_evidence: AudioEvidence | None = None

    signals_summary: dict[str, Any] = Field(default_factory=dict)
    model_versions: dict[str, Any] = Field(default_factory=dict)
    processing_time_ms: int | None = None
    raw_result: dict[str, Any] = Field(default_factory=dict)