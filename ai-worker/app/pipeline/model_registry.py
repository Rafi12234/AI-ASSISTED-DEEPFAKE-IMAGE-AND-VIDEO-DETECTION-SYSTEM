from __future__ import annotations

from dataclasses import dataclass, asdict
from typing import Any

from app.config import ai_settings


@dataclass(frozen=True)
class RegisteredModel:
    model_name: str
    model_version: str
    model_type: str
    input_type: str
    checkpoint_path: str | None
    runtime_provider: str
    device: str
    is_trainable: bool
    is_enabled: bool
    description: str


def get_registered_models() -> list[RegisteredModel]:
    return [
        RegisteredModel(
            model_name="heuristic_image_foundation_v1",
            model_version="foundation-v1",
            model_type="forensic_heuristic",
            input_type="image",
            checkpoint_path=None,
            runtime_provider="python-opencv-pillow-numpy",
            device=ai_settings.default_device,
            is_trainable=False,
            is_enabled=True,
            description="Current image forensic foundation detector using pixel, noise, contrast, sharpness, color, and metadata signals.",
        ),
        RegisteredModel(
            model_name="heuristic_video_foundation_v1",
            model_version="foundation-v1",
            model_type="video_frame_heuristic",
            input_type="video",
            checkpoint_path=None,
            runtime_provider="python-opencv-pillow-numpy",
            device=ai_settings.default_device,
            is_trainable=False,
            is_enabled=True,
            description="Current video foundation detector using sampled-frame image forensic analysis.",
        ),
        RegisteredModel(
            model_name="image_dl_ensemble_future",
            model_version="planned-v1",
            model_type="deep_learning_ensemble",
            input_type="face_image",
            checkpoint_path=str(ai_settings.model_root / "image" / "best.pt"),
            runtime_provider="pytorch",
            device=ai_settings.default_device,
            is_trainable=True,
            is_enabled=False,
            description="Planned real image deepfake ensemble using CNN, transformer, frequency, and landmark branches.",
        ),
        RegisteredModel(
            model_name="video_temporal_ensemble_future",
            model_version="planned-v1",
            model_type="video_temporal_deep_learning",
            input_type="face_track_video",
            checkpoint_path=str(ai_settings.model_root / "video" / "best.pt"),
            runtime_provider="pytorch",
            device=ai_settings.default_device,
            is_trainable=True,
            is_enabled=False,
            description="Planned video temporal detector using face tracks and spatiotemporal modeling.",
        ),
        RegisteredModel(
            model_name="audio_avsync_ensemble_future",
            model_version="planned-v1",
            model_type="audio_visual_multimodal",
            input_type="audio_video",
            checkpoint_path=str(ai_settings.model_root / "audio_visual" / "best.pt"),
            runtime_provider="pytorch-ffmpeg",
            device=ai_settings.default_device,
            is_trainable=True,
            is_enabled=False,
            description="Planned audio fake and audio-video lip-sync inconsistency detector.",
        ),
    ]


def get_model_registry_payload() -> list[dict[str, Any]]:
    return [asdict(model) for model in get_registered_models()]


def get_active_model_names() -> dict[str, str]:
    return {
        "image": ai_settings.active_image_model,
        "video": ai_settings.active_video_model,
        "audio": ai_settings.active_audio_model,
        "audio_video": ai_settings.active_av_sync_model,
    }