from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class FaceBox(BaseModel):
    face_id: str
    x: int
    y: int
    width: int
    height: int
    center_x: float
    center_y: float
    confidence: float | None = None
    area_ratio: float
    quality_score: float
    crop_recommended: bool
    details: dict[str, Any] = Field(default_factory=dict)


class FaceDetectionResult(BaseModel):
    filename: str
    mime_type: str
    image_width: int
    image_height: int
    face_count: int
    faces: list[FaceBox]
    detector: str
    detector_version: str
    warnings: list[str] = Field(default_factory=list)


class FaceCropItem(BaseModel):
    face_id: str
    crop_path: str
    crop_relative_path: str
    x: int
    y: int
    width: int
    height: int
    padded_x: int
    padded_y: int
    padded_width: int
    padded_height: int
    quality_score: float
    label: str | None = None
    source_file_path: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class FaceCropResult(BaseModel):
    filename: str
    mime_type: str
    image_width: int
    image_height: int
    face_count: int
    saved_crop_count: int
    output_dir: str
    crops: list[FaceCropItem]
    warnings: list[str] = Field(default_factory=list)


class DatasetFaceCropExportRequest(BaseModel):
    slug: str
    manifest_path: str | None = None
    output_name: str | None = None
    target_media_type: str = "image"
    max_files: int | None = None
    padding_ratio: float = 0.25
    min_quality_score: float = 0.0
    save_no_face_report: bool = True