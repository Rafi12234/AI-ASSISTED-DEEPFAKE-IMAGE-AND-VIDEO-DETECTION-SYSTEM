from __future__ import annotations

import os
import tempfile
import time
from typing import Any

import cv2
import numpy as np
from PIL import Image

from app.services.image_analyzer import (
    analyze_image_bytes,
    get_explanation,
    get_risk_level,
    round_score,
    severity_from_score,
)


def frame_to_jpeg_bytes(frame_bgr: np.ndarray) -> bytes:
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    image = Image.fromarray(frame_rgb)

    with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as temp_file:
        temp_path = temp_file.name

    try:
        image.save(temp_path, format="JPEG", quality=92)

        with open(temp_path, "rb") as file:
            return file.read()
    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)


def get_sample_indices(total_frames: int, max_samples: int = 12) -> list[int]:
    if total_frames <= 0:
        return []

    sample_count = min(total_frames, max_samples)

    if sample_count <= 1:
        return [0]

    return sorted(
        set(
            int(index)
            for index in np.linspace(
                0,
                total_frames - 1,
                sample_count,
            )
        )
    )


def analyze_video_bytes(
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> dict[str, Any]:
    started_at = time.perf_counter()

    suffix = ".mp4"

    if filename.lower().endswith(".mov"):
        suffix = ".mov"
    elif filename.lower().endswith(".avi"):
        suffix = ".avi"

    with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temp_file:
        temp_path = temp_file.name
        temp_file.write(file_bytes)

    try:
        capture = cv2.VideoCapture(temp_path)

        if not capture.isOpened():
            raise ValueError("Could not open video file.")

        total_frames = int(capture.get(cv2.CAP_PROP_FRAME_COUNT) or 0)
        fps = float(capture.get(cv2.CAP_PROP_FPS) or 0.0)
        width = int(capture.get(cv2.CAP_PROP_FRAME_WIDTH) or 0)
        height = int(capture.get(cv2.CAP_PROP_FRAME_HEIGHT) or 0)

        duration_seconds = 0.0

        if fps > 0 and total_frames > 0:
            duration_seconds = total_frames / fps

        sample_indices = get_sample_indices(total_frames=total_frames)

        frame_results: list[dict[str, Any]] = []

        for frame_number in sample_indices:
            capture.set(cv2.CAP_PROP_POS_FRAMES, frame_number)

            success, frame = capture.read()

            if not success or frame is None:
                continue

            jpeg_bytes = frame_to_jpeg_bytes(frame)

            frame_result = analyze_image_bytes(
                file_bytes=jpeg_bytes,
                filename=f"{filename}_frame_{frame_number}.jpg",
                mime_type="image/jpeg",
            )

            frame_results.append(
                {
                    "frame_number": frame_number,
                    "timestamp_seconds": round(
                        frame_number / fps,
                        3,
                    )
                    if fps > 0
                    else None,
                    "final_score": frame_result["final_score"],
                    "risk_level": frame_result["risk_level"],
                    "confidence": frame_result["confidence"],
                }
            )

        capture.release()

        if not frame_results:
            raise ValueError("No readable frames found in video.")

        frame_scores = [float(item["final_score"]) for item in frame_results]

        mean_score = float(np.mean(frame_scores))
        max_score = float(np.max(frame_scores))
        min_score = float(np.min(frame_scores))
        score_std = float(np.std(frame_scores))

        final_score = round_score((mean_score * 0.65) + (max_score * 0.35))
        confidence = round_score(1.0 - min(score_std, 0.5))
        risk_level = get_risk_level(final_score)

        video_metadata_risk = round_score(
            0.15 if width > 0 and height > 0 and fps > 0 else 0.45
        )

        frame_mean_risk = round_score(mean_score)
        frame_max_risk = round_score(max_score)
        temporal_variance_risk = round_score(score_std * 2.0)

        forensic_signals = [
            {
                "signal_type": "video_metadata",
                "signal_name": "video_readability",
                "score": video_metadata_risk,
                "severity": severity_from_score(video_metadata_risk),
                "description": "Video metadata and readability check completed.",
                "raw_data": {
                    "width": width,
                    "height": height,
                    "fps": round(fps, 3),
                    "total_frames": total_frames,
                    "duration_seconds": round(duration_seconds, 3),
                },
            },
            {
                "signal_type": "frame_analysis",
                "signal_name": "mean_frame_risk",
                "score": frame_mean_risk,
                "severity": severity_from_score(frame_mean_risk),
                "description": "Average risk score across sampled video frames.",
                "raw_data": {
                    "sampled_frames": len(frame_results),
                    "mean_score": round_score(mean_score),
                },
            },
            {
                "signal_type": "frame_analysis",
                "signal_name": "max_frame_risk",
                "score": frame_max_risk,
                "severity": severity_from_score(frame_max_risk),
                "description": "Highest risk score found among sampled video frames.",
                "raw_data": {
                    "sampled_frames": len(frame_results),
                    "max_score": round_score(max_score),
                    "min_score": round_score(min_score),
                },
            },
            {
                "signal_type": "temporal",
                "signal_name": "frame_score_variance",
                "score": temporal_variance_risk,
                "severity": severity_from_score(temporal_variance_risk),
                "description": "Estimated variation of risk scores between sampled frames.",
                "raw_data": {
                    "score_std": round_score(score_std),
                },
            },
        ]

        model_predictions = [
            {
                "model_name": "foundation_video_frame_analyzer",
                "model_version": "foundation-v1",
                "raw_score": final_score,
                "calibrated_score": final_score,
                "prediction_label": risk_level,
                "target_region": "sampled_frames",
                "inference_time_ms": int((time.perf_counter() - started_at) * 1000),
            }
        ]

        processing_time_ms = int((time.perf_counter() - started_at) * 1000)

        return {
            "engine": "ai-service-video-foundation-v1",
            "media_type": "video",
            "filename": filename,
            "mime_type": mime_type,
            "video": {
                "width": width,
                "height": height,
                "fps": round(fps, 3),
                "total_frames": total_frames,
                "duration_seconds": round(duration_seconds, 3),
                "sampled_frames": len(frame_results),
            },
            "sampled_frame_results": frame_results,
            "final_score": final_score,
            "risk_level": risk_level,
            "confidence": confidence,
            "explanation": (
                get_explanation(risk_level, final_score)
                + " This video result is based on sampled frame analysis, not a trained deepfake video model yet."
            ),
            "processing_time_ms": processing_time_ms,
            "model_predictions": model_predictions,
            "forensic_signals": forensic_signals,
            "model_versions": {
                "engine": "ai-service-video-foundation-v1",
                "models": [
                    {
                        "model_name": "foundation_video_frame_analyzer",
                        "model_version": "foundation-v1",
                    }
                ],
            },
            "signals_summary": {
                "summary": (
                    "Foundation video frame analysis completed. "
                    "The service sampled frames from the video and analyzed frame-level visual signals."
                ),
                "prediction_count": len(model_predictions),
                "forensic_signal_count": len(forensic_signals),
                "sampled_frames": frame_results,
                "signals": forensic_signals,
            },
        }

    finally:
        if os.path.exists(temp_path):
            os.remove(temp_path)