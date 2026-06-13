from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class UploadResponse(BaseModel):
    upload_id: UUID
    job_id: UUID
    original_filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    upload_status: str
    analysis_status: str


class UploadDetailResponse(BaseModel):
    id: UUID
    original_filename: str
    file_type: str
    mime_type: str
    file_size_bytes: int
    upload_status: str
    is_deleted: bool
    created_at: datetime

    model_config = {
        "from_attributes": True
    }


class UploadListResponse(BaseModel):
    uploads: list[UploadDetailResponse]