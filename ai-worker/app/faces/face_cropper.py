from __future__ import annotations

import io
import json
import re
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from PIL import Image, ImageOps

from app.config import ai_settings
from app.datasets.quality_checker import get_default_manifest_path
from app.faces.face_detector import detect_faces_from_image_bytes
from app.schemas.faces import DatasetFaceCropExportRequest, FaceCropResult


IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp", ".jfif"}


def safe_stem(value: str) -> str:
    cleaned = re.sub(r"[^a-zA-Z0-9_-]+", "_", value)
    return cleaned.strip("_")[:80] or "image"


def get_face_crop_root() -> Path:
    path = ai_settings.dataset_root / "processed" / "face_crops"
    path.mkdir(parents=True, exist_ok=True)
    return path


def load_pil_image(file_bytes: bytes) -> Image.Image:
    image = Image.open(io.BytesIO(file_bytes))
    image = ImageOps.exif_transpose(image)
    return image.convert("RGB")


def clip_box(
    *,
    x: int,
    y: int,
    width: int,
    height: int,
    image_width: int,
    image_height: int,
    padding_ratio: float,
) -> tuple[int, int, int, int]:
    padding_x = int(width * padding_ratio)
    padding_y = int(height * padding_ratio)

    x1 = max(0, x - padding_x)
    y1 = max(0, y - padding_y)
    x2 = min(image_width, x + width + padding_x)
    y2 = min(image_height, y + height + padding_y)

    return x1, y1, x2, y2


def crop_faces_from_image_bytes(
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    output_dir: Path,
    relative_base: Path,
    padding_ratio: float = 0.25,
    min_quality_score: float = 0.0,
    label: str | None = None,
    source_file_path: str | None = None,
) -> dict[str, Any]:
    output_dir.mkdir(parents=True, exist_ok=True)

    image = load_pil_image(file_bytes)
    image_width, image_height = image.size

    detection = detect_faces_from_image_bytes(
        file_bytes=file_bytes,
        filename=filename,
        mime_type=mime_type,
    )

    crops: list[dict[str, Any]] = []
    warnings = list(detection.get("warnings") or [])

    for index, face in enumerate(detection.get("faces") or []):
        quality_score = float(face.get("quality_score") or 0.0)

        if quality_score < min_quality_score:
            warnings.append(
                f"Skipped face {face.get('face_id')} because quality_score {quality_score} is below minimum {min_quality_score}."
            )
            continue

        x = int(face["x"])
        y = int(face["y"])
        width = int(face["width"])
        height = int(face["height"])

        padded_x1, padded_y1, padded_x2, padded_y2 = clip_box(
            x=x,
            y=y,
            width=width,
            height=height,
            image_width=image_width,
            image_height=image_height,
            padding_ratio=padding_ratio,
        )

        crop = image.crop((padded_x1, padded_y1, padded_x2, padded_y2))

        base_name = safe_stem(Path(filename).stem)
        crop_filename = f"{base_name}_face_{index + 1}_{face['face_id'][:8]}.jpg"
        crop_path = output_dir / crop_filename

        crop.save(crop_path, format="JPEG", quality=95)

        try:
            crop_relative_path = crop_path.relative_to(relative_base).as_posix()
        except ValueError:
            crop_relative_path = crop_path.as_posix()

        crops.append(
            {
                "face_id": face["face_id"],
                "crop_path": str(crop_path),
                "crop_relative_path": crop_relative_path,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "padded_x": padded_x1,
                "padded_y": padded_y1,
                "padded_width": padded_x2 - padded_x1,
                "padded_height": padded_y2 - padded_y1,
                "quality_score": quality_score,
                "label": label,
                "source_file_path": source_file_path,
                "details": {
                    "original_face": face,
                    "padding_ratio": padding_ratio,
                },
            }
        )

    result = FaceCropResult(
        filename=filename,
        mime_type=mime_type,
        image_width=image_width,
        image_height=image_height,
        face_count=int(detection.get("face_count") or 0),
        saved_crop_count=len(crops),
        output_dir=str(output_dir),
        crops=crops,
        warnings=warnings,
    )

    return result.model_dump()


def crop_uploaded_image(
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    padding_ratio: float = 0.25,
    min_quality_score: float = 0.0,
) -> dict[str, Any]:
    run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S") + "_" + uuid.uuid4().hex[:8]
    output_dir = get_face_crop_root() / "single_uploads" / run_id

    return crop_faces_from_image_bytes(
        file_bytes=file_bytes,
        filename=filename,
        mime_type=mime_type,
        output_dir=output_dir,
        relative_base=ai_settings.dataset_root,
        padding_ratio=padding_ratio,
        min_quality_score=min_quality_score,
    )


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            item = json.loads(line)

            if isinstance(item, dict):
                rows.append(item)

    return rows


def get_mime_type_from_path(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in {".jpg", ".jpeg", ".jfif"}:
        return "image/jpeg"

    if suffix == ".png":
        return "image/png"

    if suffix == ".webp":
        return "image/webp"

    if suffix == ".bmp":
        return "image/bmp"

    return "application/octet-stream"


def export_dataset_face_crops(request: DatasetFaceCropExportRequest) -> dict[str, Any]:
    slug = request.slug.strip().lower()

    manifest_path = (
        Path(request.manifest_path)
        if request.manifest_path
        else get_default_manifest_path(slug)
    )

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file does not exist: {manifest_path}")

    output_name = request.output_name or f"{slug}_face_crops_v1"
    export_root = get_face_crop_root() / output_name
    export_root.mkdir(parents=True, exist_ok=True)

    rows = read_jsonl(manifest_path)

    if request.max_files is not None:
        rows = rows[: request.max_files]

    crop_manifest_path = export_root / "face_crops_manifest.jsonl"
    no_face_report_path = export_root / "no_face_report.jsonl"
    summary_path = export_root / "summary.json"

    summary = {
        "slug": slug,
        "output_name": output_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest_path": str(manifest_path),
        "export_root": str(export_root),
        "crop_manifest_path": str(crop_manifest_path),
        "no_face_report_path": str(no_face_report_path),
        "total_manifest_rows": len(rows),
        "processed_images": 0,
        "skipped_rows": 0,
        "images_with_faces": 0,
        "images_without_faces": 0,
        "saved_crop_count": 0,
        "real_crop_count": 0,
        "fake_crop_count": 0,
        "warnings": [],
    }

    with crop_manifest_path.open("w", encoding="utf-8") as crop_file, no_face_report_path.open(
        "w", encoding="utf-8"
    ) as no_face_file:
        for row in rows:
            media_type = str(row.get("media_type") or "").lower()
            label = str(row.get("label") or "unknown").lower()
            file_path = Path(str(row.get("file_path") or ""))

            if request.target_media_type and media_type != request.target_media_type:
                summary["skipped_rows"] += 1
                continue

            if label not in {"real", "fake"}:
                summary["skipped_rows"] += 1
                continue

            if not file_path.exists() or not file_path.is_file():
                summary["skipped_rows"] += 1
                summary["warnings"].append(f"Missing file: {file_path}")
                continue

            if file_path.suffix.lower() not in IMAGE_EXTENSIONS:
                summary["skipped_rows"] += 1
                continue

            summary["processed_images"] += 1

            label_output_dir = export_root / label

            file_bytes = file_path.read_bytes()

            crop_result = crop_faces_from_image_bytes(
                file_bytes=file_bytes,
                filename=file_path.name,
                mime_type=get_mime_type_from_path(file_path),
                output_dir=label_output_dir,
                relative_base=ai_settings.dataset_root,
                padding_ratio=request.padding_ratio,
                min_quality_score=request.min_quality_score,
                label=label,
                source_file_path=str(file_path),
            )

            if crop_result["saved_crop_count"] <= 0:
                summary["images_without_faces"] += 1

                if request.save_no_face_report:
                    no_face_file.write(
                        json.dumps(
                            {
                                "sample_id": row.get("sample_id"),
                                "file_path": str(file_path),
                                "label": label,
                                "warnings": crop_result.get("warnings") or [],
                            },
                            ensure_ascii=False,
                        )
                        + "\n"
                    )

                continue

            summary["images_with_faces"] += 1
            summary["saved_crop_count"] += int(crop_result["saved_crop_count"])

            if label == "real":
                summary["real_crop_count"] += int(crop_result["saved_crop_count"])

            if label == "fake":
                summary["fake_crop_count"] += int(crop_result["saved_crop_count"])

            for crop in crop_result["crops"]:
                crop_file.write(
                    json.dumps(
                        {
                            "crop_id": str(uuid.uuid5(uuid.NAMESPACE_URL, crop["crop_path"])),
                            "source_sample_id": row.get("sample_id"),
                            "dataset_slug": slug,
                            "label": label,
                            "media_type": "face_crop",
                            "crop_path": crop["crop_path"],
                            "crop_relative_path": crop["crop_relative_path"],
                            "source_file_path": str(file_path),
                            "quality_score": crop["quality_score"],
                            "bbox": {
                                "x": crop["x"],
                                "y": crop["y"],
                                "width": crop["width"],
                                "height": crop["height"],
                                "padded_x": crop["padded_x"],
                                "padded_y": crop["padded_y"],
                                "padded_width": crop["padded_width"],
                                "padded_height": crop["padded_height"],
                            },
                            "details": crop["details"],
                        },
                        ensure_ascii=False,
                    )
                    + "\n"
                )

    summary["status"] = "ready" if summary["saved_crop_count"] > 0 else "no_faces_detected"

    if summary["saved_crop_count"] == 0:
        summary["warnings"].append("No face crops were saved. Try clearer frontal face images.")

    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return summary


def list_face_crop_exports() -> list[dict[str, Any]]:
    root = get_face_crop_root()
    exports: list[dict[str, Any]] = []

    for summary_path in root.glob("*/summary.json"):
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        exports.append(summary)

    return sorted(
        exports,
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )


def get_face_crop_export_summary(output_name: str) -> dict[str, Any]:
    summary_path = get_face_crop_root() / output_name / "summary.json"

    if not summary_path.exists():
        raise FileNotFoundError(f"Face crop export not found: {output_name}")

    return json.loads(summary_path.read_text(encoding="utf-8"))