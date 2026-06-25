from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


DatasetModality = Literal["image", "video", "audio", "audio_video", "multimodal"]
DatasetStatus = Literal["recommended", "registered", "missing", "ready", "invalid"]
DatasetSplit = Literal["train", "val", "test", "unknown"]
DatasetLabel = Literal["real", "fake", "unknown"]


class DatasetCatalogItem(BaseModel):
    slug: str
    name: str
    priority: int
    modality: DatasetModality
    task_type: str
    recommended_stage: str
    official_source: str
    access_type: str
    size_note: str
    license_note: str
    why_use_it: str
    local_expected_path: str
    expected_layout: dict[str, Any] = Field(default_factory=dict)
    notes: list[str] = Field(default_factory=list)


class LocalDatasetRegistrationRequest(BaseModel):
    slug: str
    local_path: str
    enabled: bool = True
    notes: str | None = None


class LocalDatasetRegistryItem(BaseModel):
    slug: str
    name: str
    modality: DatasetModality
    local_path: str
    enabled: bool
    status: DatasetStatus
    exists: bool
    notes: str | None = None
    validation: dict[str, Any] = Field(default_factory=dict)


class DatasetValidationRequest(BaseModel):
    slug: str
    local_path: str


class DatasetManifestBuildRequest(BaseModel):
    slug: str
    local_path: str | None = None
    output_name: str | None = None
    compute_sha256: bool = False
    max_files: int | None = None
    train_ratio: float = Field(default=0.70, ge=0.1, le=0.95)
    val_ratio: float = Field(default=0.15, ge=0.01, le=0.80)
    test_ratio: float = Field(default=0.15, ge=0.01, le=0.80)


class DatasetManifestSample(BaseModel):
    sample_id: str
    dataset_slug: str
    file_path: str
    relative_path: str
    label: DatasetLabel
    media_type: str
    split: DatasetSplit
    file_size_bytes: int
    extension: str
    sha256: str | None = None
    source: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class DatasetManifestSummary(BaseModel):
    slug: str
    manifest_path: str
    summary_path: str
    total_files: int
    real_count: int
    fake_count: int
    unknown_count: int
    image_count: int
    video_count: int
    audio_count: int
    train_count: int
    val_count: int
    test_count: int
    warnings: list[str] = Field(default_factory=list)


class DatasetQualityCheckRequest(BaseModel):
    slug: str
    manifest_path: str | None = None
    max_rows: int | None = None
    verify_images: bool = True
    min_total_for_training: int = 100
    min_per_class_for_training: int = 50


class DatasetTrainingExportRequest(BaseModel):
    slug: str
    manifest_path: str | None = None
    output_name: str | None = None

    target_media_type: str | None = None
    include_unknown_labels: bool = False
    verify_files_exist: bool = True

    train_ratio: float = Field(default=0.70, ge=0.1, le=0.95)
    val_ratio: float = Field(default=0.15, ge=0.01, le=0.80)
    test_ratio: float = Field(default=0.15, ge=0.01, le=0.80)

    seed: int = 42
    copy_files: bool = False