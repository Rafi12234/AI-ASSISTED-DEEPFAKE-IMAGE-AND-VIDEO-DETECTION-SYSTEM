from __future__ import annotations

from pydantic import BaseModel, Field


class FaceCropBaselineTrainRequest(BaseModel):
    training_export_name: str
    model_name: str = "face_crop_baseline_v1"
    run_name: str | None = None
    image_size: int = Field(default=128, ge=32, le=512)
    random_seed: int = 42


class FaceCropBaselinePredictResponse(BaseModel):
    filename: str
    model_name: str
    model_version: str
    predicted_label: str
    fake_probability: float
    real_probability: float
    confidence: float
    features_used: int