from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field
from pydantic import BaseModel


DatasetModality = Literal["image", "video", "audio", "audio_video", "multimodal"]
DatasetStatus = Literal["recommended", "registered", "missing", "ready", "invalid"]


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

class DatasetQualityCheckRequest(BaseModel):
    slug: str
    manifest_path: str | None = None
    max_files: int | None = None