from __future__ import annotations

import json
import random
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image

from app.config import ai_settings
from app.schemas.faces import (
    FaceCropQualityCheckRequest,
    FaceCropTrainingExportRequest,
)


def get_face_crop_root() -> Path:
    path = ai_settings.dataset_root / "processed" / "face_crops"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_face_crop_training_root() -> Path:
    path = ai_settings.dataset_root / "processed" / "face_crop_training_exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    if not path.exists():
        raise FileNotFoundError(f"File not found: {path}")

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            item = json.loads(line)

            if isinstance(item, dict):
                rows.append(item)

    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def check_image(path: Path) -> dict[str, Any]:
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


def count_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "total": len(rows),
        "real": 0,
        "fake": 0,
        "unknown": 0,
    }

    for row in rows:
        label = str(row.get("label") or "unknown").lower()

        if label == "real":
            counts["real"] += 1
        elif label == "fake":
            counts["fake"] += 1
        else:
            counts["unknown"] += 1

    return counts


def check_face_crop_quality(
    request: FaceCropQualityCheckRequest,
) -> dict[str, Any]:
    export_dir = get_face_crop_root() / request.output_name
    manifest_path = export_dir / "face_crops_manifest.jsonl"

    if not manifest_path.exists():
        raise FileNotFoundError(
            f"Face crop manifest not found: {manifest_path}"
        )

    rows = read_jsonl(manifest_path)

    issues: list[dict[str, Any]] = []
    image_details: list[dict[str, Any]] = []

    counts = {
        "total_crops": len(rows),
        "real_count": 0,
        "fake_count": 0,
        "unknown_count": 0,
        "missing_file_count": 0,
        "unreadable_image_count": 0,
        "small_crop_count": 0,
        "low_quality_count": 0,
    }

    for row in rows:
        label = str(row.get("label") or "unknown").lower()
        crop_path = Path(str(row.get("crop_path") or ""))
        quality_score = float(row.get("quality_score") or 0.0)

        if label == "real":
            counts["real_count"] += 1
        elif label == "fake":
            counts["fake_count"] += 1
        else:
            counts["unknown_count"] += 1
            issues.append(
                {
                    "level": "warning",
                    "code": "unknown_label",
                    "message": "Crop has unknown label.",
                    "crop_path": str(crop_path),
                }
            )

        if not crop_path.exists():
            counts["missing_file_count"] += 1
            issues.append(
                {
                    "level": "error",
                    "code": "missing_crop_file",
                    "message": "Crop file does not exist.",
                    "crop_path": str(crop_path),
                }
            )
            continue

        if quality_score < request.min_quality_score:
            counts["low_quality_count"] += 1
            issues.append(
                {
                    "level": "warning",
                    "code": "low_quality_crop",
                    "message": (
                        f"Crop quality score {quality_score} is below "
                        f"{request.min_quality_score}."
                    ),
                    "crop_path": str(crop_path),
                }
            )

        if request.verify_images:
            image_check = check_image(crop_path)

            image_details.append(
                {
                    "crop_path": str(crop_path),
                    "quality_score": quality_score,
                    **image_check,
                }
            )

            if not image_check["readable"]:
                counts["unreadable_image_count"] += 1
                issues.append(
                    {
                        "level": "error",
                        "code": "unreadable_crop",
                        "message": image_check["error"],
                        "crop_path": str(crop_path),
                    }
                )
                continue

            width = int(image_check["width"] or 0)
            height = int(image_check["height"] or 0)

            if width < request.min_width or height < request.min_height:
                counts["small_crop_count"] += 1
                issues.append(
                    {
                        "level": "warning",
                        "code": "small_crop",
                        "message": (
                            f"Crop size {width}x{height} is smaller than "
                            f"{request.min_width}x{request.min_height}."
                        ),
                        "crop_path": str(crop_path),
                    }
                )

    error_count = len(
        [issue for issue in issues if issue["level"] == "error"]
    )
    warning_count = len(
        [issue for issue in issues if issue["level"] == "warning"]
    )

    pipeline_ready = (
        counts["total_crops"] > 0
        and error_count == 0
        and counts["real_count"] > 0
        and counts["fake_count"] > 0
    )

    training_ready = (
        pipeline_ready
        and counts["real_count"] >= 50
        and counts["fake_count"] >= 50
        and warning_count == 0
    )

    if error_count > 0:
        status = "fail"
    elif warning_count > 0:
        status = "warning"
    else:
        status = "pass"

    recommendations: list[str] = []

    if counts["total_crops"] == 0:
        recommendations.append("No face crops found.")

    if counts["real_count"] == 0:
        recommendations.append("Add real face crops.")

    if counts["fake_count"] == 0:
        recommendations.append("Add fake/deepfake face crops.")

    if counts["real_count"] < 50:
        recommendations.append(
            "For early training, collect at least 50 real face crops."
        )

    if counts["fake_count"] < 50:
        recommendations.append(
            "For early training, collect at least 50 fake face crops."
        )

    if not recommendations:
        recommendations.append("Face crop export is ready.")

    return {
        "output_name": request.output_name,
        "export_dir": str(export_dir),
        "manifest_path": str(manifest_path),
        "status": status,
        "pipeline_ready": pipeline_ready,
        "training_ready": training_ready,
        "summary": {
            **counts,
            "error_count": error_count,
            "warning_count": warning_count,
        },
        "image_details": image_details[:50],
        "issues": issues[:100],
        "recommendations": recommendations,
    }


def split_rows_by_label(
    *,
    rows: list[dict[str, Any]],
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> dict[str, list[dict[str, Any]]]:
    grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in rows:
        label = str(row.get("label") or "unknown").lower()

        if label in {"real", "fake"}:
            grouped[label].append(row)

    split_rows = {
        "train": [],
        "val": [],
        "test": [],
    }

    for label_rows in grouped.values():
        shuffled = list(label_rows)
        random.Random(seed).shuffle(shuffled)

        total = len(shuffled)

        if total == 1:
            split_rows["train"].extend(shuffled)
            continue

        if total == 2:
            split_rows["train"].append(shuffled[0])
            split_rows["test"].append(shuffled[1])
            continue

        train_count = int(total * train_ratio)
        val_count = int(total * val_ratio)

        if train_count <= 0:
            train_count = 1

        if val_count <= 0 and total >= 5:
            val_count = 1

        if train_count + val_count >= total:
            val_count = max(0, total - train_count - 1)

        split_rows["train"].extend(shuffled[:train_count])
        split_rows["val"].extend(
            shuffled[train_count: train_count + val_count]
        )
        split_rows["test"].extend(
            shuffled[train_count + val_count:]
        )

    for split_name in split_rows:
        random.Random(seed).shuffle(split_rows[split_name])

    return split_rows


def copy_crop_file(
    *,
    row: dict[str, Any],
    export_dir: Path,
    split: str,
) -> str | None:
    source_path = Path(str(row.get("crop_path") or ""))
    label = str(row.get("label") or "unknown").lower()

    if not source_path.exists():
        return None

    target_dir = export_dir / "files" / split / label
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / source_path.name

    if not target_path.exists():
        shutil.copy2(source_path, target_path)

    return str(target_path)


def export_face_crop_training_split(
    request: FaceCropTrainingExportRequest,
) -> dict[str, Any]:
    if abs(
        (
            request.train_ratio
            + request.val_ratio
            + request.test_ratio
        )
        - 1.0
    ) > 0.001:
        raise ValueError(
            "train_ratio + val_ratio + test_ratio must equal 1.0"
        )

    source_export_dir = get_face_crop_root() / request.crop_export_name
    source_manifest_path = source_export_dir / "face_crops_manifest.jsonl"

    if not source_manifest_path.exists():
        raise FileNotFoundError(
            f"Face crop manifest not found: {source_manifest_path}"
        )

    rows = read_jsonl(source_manifest_path)

    valid_rows = []

    for row in rows:
        crop_path = Path(str(row.get("crop_path") or ""))
        label = str(row.get("label") or "unknown").lower()

        if label not in {"real", "fake"}:
            continue

        if not crop_path.exists():
            continue

        valid_rows.append(row)

    split_rows = split_rows_by_label(
        rows=valid_rows,
        train_ratio=request.train_ratio,
        val_ratio=request.val_ratio,
        seed=request.seed,
    )

    output_name = (
        request.output_name
        or f"{request.crop_export_name}_training_v1"
    )

    export_dir = get_face_crop_training_root() / output_name
    export_dir.mkdir(parents=True, exist_ok=True)

    if request.copy_files:
        for split_name, rows_for_split in split_rows.items():
            for row in rows_for_split:
                copied_path = copy_crop_file(
                    row=row,
                    export_dir=export_dir,
                    split=split_name,
                )

                row["export_file_path"] = copied_path

    all_rows = (
        split_rows["train"]
        + split_rows["val"]
        + split_rows["test"]
    )

    train_path = export_dir / "train.jsonl"
    val_path = export_dir / "val.jsonl"
    test_path = export_dir / "test.jsonl"
    all_path = export_dir / "all.jsonl"
    summary_path = export_dir / "summary.json"

    write_jsonl(train_path, split_rows["train"])
    write_jsonl(val_path, split_rows["val"])
    write_jsonl(test_path, split_rows["test"])
    write_jsonl(all_path, all_rows)

    summary = {
        "output_name": output_name,
        "crop_export_name": request.crop_export_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest_path": str(source_manifest_path),
        "export_dir": str(export_dir),
        "train_path": str(train_path),
        "val_path": str(val_path),
        "test_path": str(test_path),
        "all_path": str(all_path),
        "summary_path": str(summary_path),
        "copy_files": request.copy_files,
        "counts": {
            "all": count_rows(all_rows),
            "train": count_rows(split_rows["train"]),
            "val": count_rows(split_rows["val"]),
            "test": count_rows(split_rows["test"]),
        },
        "recommendations": [],
    }

    if summary["counts"]["all"]["total"] < 100:
        summary["recommendations"].append(
            "This export is okay for pipeline testing, but too small for real model training."
        )

    if summary["counts"]["val"]["total"] == 0:
        summary["recommendations"].append(
            "Validation split is empty. Add more face crops."
        )

    if summary["counts"]["test"]["total"] == 0:
        summary["recommendations"].append(
            "Test split is empty. Add more face crops."
        )

    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    readme = f"""# Face Crop Training Export

Source face crop export: {request.crop_export_name}

Use:
- train.jsonl for training
- val.jsonl for validation
- test.jsonl for final testing

Do not move test samples into train.
"""

    (export_dir / "README.md").write_text(
        readme,
        encoding="utf-8",
    )

    return summary


def list_face_crop_training_exports() -> list[dict[str, Any]]:
    root = get_face_crop_training_root()
    exports: list[dict[str, Any]] = []

    for summary_path in root.glob("*/summary.json"):
        try:
            exports.append(
                json.loads(summary_path.read_text(encoding="utf-8"))
            )
        except json.JSONDecodeError:
            continue

    return sorted(
        exports,
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )


def get_face_crop_training_export_summary(
    output_name: str,
) -> dict[str, Any]:
    summary_path = (
        get_face_crop_training_root()
        / output_name
        / "summary.json"
    )

    if not summary_path.exists():
        raise FileNotFoundError(
            f"Face crop training export not found: {output_name}"
        )

    return json.loads(summary_path.read_text(encoding="utf-8"))