from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from PIL import Image

from app.config import ai_settings
from app.schemas.datasets import DatasetQualityCheckRequest


VALID_LABELS = {"real", "fake", "unknown"}
VALID_SPLITS = {"train", "val", "test", "unknown"}
VALID_MEDIA_TYPES = {"image", "video", "audio", "unknown"}

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".jfif"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
SUPPORTED_EXTENSIONS = IMAGE_EXTENSIONS | VIDEO_EXTENSIONS | AUDIO_EXTENSIONS


def get_default_manifest_path(slug: str) -> Path:
    manifest_dir = ai_settings.dataset_root / "manifests"

    exact_path = manifest_dir / f"{slug}_manifest.jsonl"

    if exact_path.exists():
        return exact_path

    matches = list(manifest_dir.glob(f"{slug}*.jsonl"))

    if matches:
        return matches[0]

    return exact_path


def safe_float_ratio(part: int, total: int) -> float:
    if total <= 0:
        return 0.0

    return round(part / total, 4)


def check_image_readable(path: Path) -> dict[str, Any]:
    try:
        with Image.open(path) as image:
            image.verify()

        with Image.open(path) as image:
            width, height = image.size
            mode = image.mode

        return {
            "readable": True,
            "width": width,
            "height": height,
            "mode": mode,
            "error": None,
        }

    except Exception as exc:
        return {
            "readable": False,
            "width": None,
            "height": None,
            "mode": None,
            "error": str(exc),
        }


def classify_file_type_from_extension(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        return "image"

    if suffix in VIDEO_EXTENSIONS:
        return "video"

    if suffix in AUDIO_EXTENSIONS:
        return "audio"

    return "unknown"


def make_issue(
    *,
    level: str,
    code: str,
    message: str,
    sample: dict[str, Any] | None = None,
) -> dict[str, Any]:
    return {
        "level": level,
        "code": code,
        "message": message,
        "sample_id": sample.get("sample_id") if sample else None,
        "file_path": sample.get("file_path") if sample else None,
    }


def read_manifest_rows(
    *,
    manifest_path: Path,
    max_rows: int | None = None,
) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    rows: list[dict[str, Any]] = []
    issues: list[dict[str, Any]] = []

    with manifest_path.open("r", encoding="utf-8") as file:
        for line_number, line in enumerate(file, start=1):
            if max_rows is not None and len(rows) >= max_rows:
                break

            line = line.strip()

            if not line:
                continue

            try:
                item = json.loads(line)
            except json.JSONDecodeError as exc:
                issues.append(
                    {
                        "level": "error",
                        "code": "invalid_json_line",
                        "message": f"Invalid JSON at line {line_number}: {exc}",
                        "sample_id": None,
                        "file_path": None,
                    }
                )
                continue

            if isinstance(item, dict):
                rows.append(item)
            else:
                issues.append(
                    {
                        "level": "error",
                        "code": "invalid_manifest_row",
                        "message": f"Manifest line {line_number} is not a JSON object.",
                        "sample_id": None,
                        "file_path": None,
                    }
                )

    return rows, issues


def calculate_quality_score(
    *,
    total_rows: int,
    error_count: int,
    warning_count: int,
    unknown_label_count: int,
    missing_file_count: int,
    unreadable_image_count: int,
) -> int:
    if total_rows == 0:
        return 0

    score = 100

    score -= error_count * 10
    score -= warning_count * 3
    score -= unknown_label_count * 5
    score -= missing_file_count * 15
    score -= unreadable_image_count * 15

    return max(0, min(100, score))


def check_manifest_quality(request: DatasetQualityCheckRequest) -> dict[str, Any]:
    slug = request.slug.strip().lower()

    manifest_path = (
        Path(request.manifest_path)
        if request.manifest_path
        else get_default_manifest_path(slug)
    )

    if not manifest_path.exists():
        return {
            "slug": slug,
            "manifest_path": str(manifest_path),
            "status": "fail",
            "pipeline_test_ready": False,
            "real_training_ready": False,
            "quality_score": 0,
            "summary": {},
            "issues": [
                {
                    "level": "error",
                    "code": "manifest_missing",
                    "message": "Manifest file does not exist.",
                    "sample_id": None,
                    "file_path": None,
                }
            ],
            "recommendations": [
                "Build the manifest first using POST /datasets/build-manifest."
            ],
        }

    rows, issues = read_manifest_rows(
        manifest_path=manifest_path,
        max_rows=request.max_rows,
    )

    seen_sample_ids: set[str] = set()
    seen_file_paths: set[str] = set()

    counts = {
        "total_rows": len(rows),
        "real_count": 0,
        "fake_count": 0,
        "unknown_label_count": 0,
        "train_count": 0,
        "val_count": 0,
        "test_count": 0,
        "unknown_split_count": 0,
        "image_count": 0,
        "video_count": 0,
        "audio_count": 0,
        "unknown_media_count": 0,
        "missing_file_count": 0,
        "zero_byte_count": 0,
        "small_file_count": 0,
        "invalid_label_count": 0,
        "invalid_split_count": 0,
        "invalid_media_type_count": 0,
        "unsupported_extension_count": 0,
        "duplicate_sample_id_count": 0,
        "duplicate_file_path_count": 0,
        "unreadable_image_count": 0,
    }

    image_details: list[dict[str, Any]] = []

    for row in rows:
        sample_id = str(row.get("sample_id") or "")
        file_path_text = str(row.get("file_path") or "")
        label = str(row.get("label") or "unknown").lower()
        split = str(row.get("split") or "unknown").lower()
        media_type = str(row.get("media_type") or "unknown").lower()

        if sample_id:
            if sample_id in seen_sample_ids:
                counts["duplicate_sample_id_count"] += 1
                issues.append(
                    make_issue(
                        level="error",
                        code="duplicate_sample_id",
                        message="Duplicate sample_id found.",
                        sample=row,
                    )
                )
            seen_sample_ids.add(sample_id)

        if file_path_text:
            normalized_path = file_path_text.lower()

            if normalized_path in seen_file_paths:
                counts["duplicate_file_path_count"] += 1
                issues.append(
                    make_issue(
                        level="warning",
                        code="duplicate_file_path",
                        message="Same file path appears more than once.",
                        sample=row,
                    )
                )

            seen_file_paths.add(normalized_path)

        if label not in VALID_LABELS:
            counts["invalid_label_count"] += 1
            issues.append(
                make_issue(
                    level="error",
                    code="invalid_label",
                    message=f"Invalid label: {label}",
                    sample=row,
                )
            )
        elif label == "real":
            counts["real_count"] += 1
        elif label == "fake":
            counts["fake_count"] += 1
        else:
            counts["unknown_label_count"] += 1

        if split not in VALID_SPLITS:
            counts["invalid_split_count"] += 1
            issues.append(
                make_issue(
                    level="error",
                    code="invalid_split",
                    message=f"Invalid split: {split}",
                    sample=row,
                )
            )
        elif split == "train":
            counts["train_count"] += 1
        elif split == "val":
            counts["val_count"] += 1
        elif split == "test":
            counts["test_count"] += 1
        else:
            counts["unknown_split_count"] += 1

        if media_type not in VALID_MEDIA_TYPES:
            counts["invalid_media_type_count"] += 1
            issues.append(
                make_issue(
                    level="error",
                    code="invalid_media_type",
                    message=f"Invalid media_type: {media_type}",
                    sample=row,
                )
            )
        elif media_type == "image":
            counts["image_count"] += 1
        elif media_type == "video":
            counts["video_count"] += 1
        elif media_type == "audio":
            counts["audio_count"] += 1
        else:
            counts["unknown_media_count"] += 1

        path = Path(file_path_text)

        if not file_path_text or not path.exists():
            counts["missing_file_count"] += 1
            issues.append(
                make_issue(
                    level="error",
                    code="missing_file",
                    message="File path does not exist.",
                    sample=row,
                )
            )
            continue

        extension = path.suffix.lower()

        if extension not in SUPPORTED_EXTENSIONS:
            counts["unsupported_extension_count"] += 1
            issues.append(
                make_issue(
                    level="warning",
                    code="unsupported_extension",
                    message=f"Unsupported file extension: {extension}",
                    sample=row,
                )
            )

        file_size = path.stat().st_size

        if file_size == 0:
            counts["zero_byte_count"] += 1
            issues.append(
                make_issue(
                    level="error",
                    code="zero_byte_file",
                    message="File size is zero bytes.",
                    sample=row,
                )
            )

        if 0 < file_size < 1024:
            counts["small_file_count"] += 1
            issues.append(
                make_issue(
                    level="warning",
                    code="very_small_file",
                    message="File is smaller than 1 KB. It may be invalid or too small.",
                    sample=row,
                )
            )

        actual_media_type = classify_file_type_from_extension(path)

        if media_type != "unknown" and actual_media_type != "unknown" and media_type != actual_media_type:
            issues.append(
                make_issue(
                    level="warning",
                    code="media_type_mismatch",
                    message=f"Manifest media_type is {media_type}, but extension suggests {actual_media_type}.",
                    sample=row,
                )
            )

        if request.verify_images and actual_media_type == "image":
            image_check = check_image_readable(path)

            image_details.append(
                {
                    "sample_id": sample_id,
                    "file_path": file_path_text,
                    **image_check,
                }
            )

            if not image_check["readable"]:
                counts["unreadable_image_count"] += 1
                issues.append(
                    make_issue(
                        level="error",
                        code="unreadable_image",
                        message=f"Image could not be opened: {image_check['error']}",
                        sample=row,
                    )
                )

    if counts["total_rows"] == 0:
        issues.append(
            make_issue(
                level="error",
                code="empty_manifest",
                message="Manifest has zero valid rows.",
            )
        )

    if counts["real_count"] == 0:
        issues.append(
            make_issue(
                level="error",
                code="no_real_samples",
                message="No real samples found.",
            )
        )

    if counts["fake_count"] == 0:
        issues.append(
            make_issue(
                level="error",
                code="no_fake_samples",
                message="No fake samples found.",
            )
        )

    if counts["val_count"] == 0:
        issues.append(
            make_issue(
                level="warning",
                code="empty_validation_split",
                message="Validation split has zero samples.",
            )
        )

    if counts["test_count"] == 0:
        issues.append(
            make_issue(
                level="warning",
                code="empty_test_split",
                message="Test split has zero samples.",
            )
        )

    total_labeled = counts["real_count"] + counts["fake_count"]

    label_balance = {
        "real_ratio": safe_float_ratio(counts["real_count"], total_labeled),
        "fake_ratio": safe_float_ratio(counts["fake_count"], total_labeled),
    }

    if total_labeled > 0:
        minority_ratio = min(label_balance["real_ratio"], label_balance["fake_ratio"])

        if minority_ratio < 0.25:
            issues.append(
                make_issue(
                    level="warning",
                    code="class_imbalance",
                    message="Dataset is highly imbalanced between real and fake samples.",
                )
            )

    if counts["total_rows"] < request.min_total_for_training:
        issues.append(
            make_issue(
                level="warning",
                code="dataset_too_small_for_training",
                message=(
                    f"Dataset has {counts['total_rows']} samples. "
                    f"Recommended minimum is {request.min_total_for_training} for early real training."
                ),
            )
        )

    if counts["real_count"] < request.min_per_class_for_training:
        issues.append(
            make_issue(
                level="warning",
                code="not_enough_real_samples",
                message=(
                    f"Real samples: {counts['real_count']}. "
                    f"Recommended minimum is {request.min_per_class_for_training}."
                ),
            )
        )

    if counts["fake_count"] < request.min_per_class_for_training:
        issues.append(
            make_issue(
                level="warning",
                code="not_enough_fake_samples",
                message=(
                    f"Fake samples: {counts['fake_count']}. "
                    f"Recommended minimum is {request.min_per_class_for_training}."
                ),
            )
        )

    error_count = len([issue for issue in issues if issue["level"] == "error"])
    warning_count = len([issue for issue in issues if issue["level"] == "warning"])

    quality_score = calculate_quality_score(
        total_rows=counts["total_rows"],
        error_count=error_count,
        warning_count=warning_count,
        unknown_label_count=counts["unknown_label_count"],
        missing_file_count=counts["missing_file_count"],
        unreadable_image_count=counts["unreadable_image_count"],
    )

    pipeline_test_ready = (
        counts["total_rows"] > 0
        and counts["missing_file_count"] == 0
        and counts["zero_byte_count"] == 0
        and counts["unreadable_image_count"] == 0
        and counts["invalid_label_count"] == 0
        and counts["real_count"] > 0
        and counts["fake_count"] > 0
    )

    real_training_ready = (
        pipeline_test_ready
        and counts["total_rows"] >= request.min_total_for_training
        and counts["real_count"] >= request.min_per_class_for_training
        and counts["fake_count"] >= request.min_per_class_for_training
        and counts["train_count"] > 0
        and counts["val_count"] > 0
        and counts["test_count"] > 0
        and warning_count == 0
    )

    if error_count > 0:
        status = "fail"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "pass"

    recommendations: list[str] = []

    if not pipeline_test_ready:
        recommendations.append("Fix blocking errors before using this manifest.")

    if counts["val_count"] == 0:
        recommendations.append("Add more files so validation split is not empty.")

    if counts["test_count"] == 0:
        recommendations.append("Add more files so test split is not empty.")

    if counts["total_rows"] < request.min_total_for_training:
        recommendations.append("For early real training, collect at least 100 labeled samples.")

    if counts["real_count"] < request.min_per_class_for_training:
        recommendations.append("Add more real samples.")

    if counts["fake_count"] < request.min_per_class_for_training:
        recommendations.append("Add more fake/deepfake samples.")

    if not recommendations:
        recommendations.append("Dataset quality is acceptable for the configured threshold.")

    return {
        "slug": slug,
        "manifest_path": str(manifest_path),
        "status": status,
        "pipeline_test_ready": pipeline_test_ready,
        "real_training_ready": real_training_ready,
        "quality_score": quality_score,
        "summary": {
            **counts,
            "error_count": error_count,
            "warning_count": warning_count,
            "label_balance": label_balance,
        },
        "image_details": image_details[:50],
        "issues": issues[:100],
        "recommendations": recommendations,
    }