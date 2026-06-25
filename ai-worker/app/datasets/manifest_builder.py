from __future__ import annotations

import csv
import hashlib
import json
import random
import uuid
from pathlib import Path
from typing import Any

from app.config import ai_settings
from app.datasets.catalog import get_dataset_by_slug
from app.datasets.local_registry import read_registry_file
from app.schemas.datasets import DatasetManifestBuildRequest


VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
AUDIO_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
SUPPORTED_EXTENSIONS = VIDEO_EXTENSIONS | IMAGE_EXTENSIONS | AUDIO_EXTENSIONS


def get_manifest_dir() -> Path:
    path = ai_settings.dataset_root / "manifests"
    path.mkdir(parents=True, exist_ok=True)
    return path


def get_registered_dataset_path(slug: str) -> str | None:
    for item in read_registry_file():
        if item.get("slug") == slug:
            local_path = item.get("local_path")
            if local_path:
                return str(local_path)

    return None


def get_media_type(path: Path) -> str:
    suffix = path.suffix.lower()

    if suffix in IMAGE_EXTENSIONS:
        return "image"

    if suffix in VIDEO_EXTENSIONS:
        return "video"

    if suffix in AUDIO_EXTENSIONS:
        return "audio"

    return "unknown"


def normalize_label(value: str | None) -> str:
    if not value:
        return "unknown"

    cleaned = str(value).strip().lower()

    if cleaned in {"real", "original", "authentic", "bonafide", "genuine", "0"}:
        return "real"

    if cleaned in {"fake", "deepfake", "manipulated", "spoof", "synthetic", "1"}:
        return "fake"

    return "unknown"


def infer_label_from_path(path: Path, dataset_slug: str) -> str:
    parts = [part.lower() for part in path.parts]
    path_text = str(path).lower()

    if dataset_slug == "faceforensics_pp":
        if "original_sequences" in parts:
            return "real"

        if "manipulated_sequences" in parts:
            return "fake"

    if dataset_slug == "celeb_df_v2":
        if "celeb-real" in parts or "youtube-real" in parts:
            return "real"

        if "celeb-synthesis" in parts:
            return "fake"

    if dataset_slug == "custom_real_life":
        if "real" in parts:
            return "real"

        if "fake" in parts:
            return "fake"

    if "\\real\\" in path_text or "/real/" in path_text:
        return "real"

    if "\\fake\\" in path_text or "/fake/" in path_text:
        return "fake"

    if "bonafide" in path_text:
        return "real"

    if "spoof" in path_text or "deepfake" in path_text or "manipulated" in path_text:
        return "fake"

    return "unknown"


def calculate_sha256(path: Path) -> str:
    sha256 = hashlib.sha256()

    with path.open("rb") as file:
        for chunk in iter(lambda: file.read(1024 * 1024), b""):
            sha256.update(chunk)

    return sha256.hexdigest()


def read_custom_metadata(dataset_root: Path) -> dict[str, dict[str, Any]]:
    metadata_path = dataset_root / "metadata.csv"

    if not metadata_path.exists():
        return {}

    metadata: dict[str, dict[str, Any]] = {}

    with metadata_path.open("r", encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)

        for row in reader:
            relative_path = str(row.get("file_path") or "").replace("\\", "/").strip()

            if not relative_path:
                continue

            metadata[relative_path] = dict(row)

    return metadata


def read_dfdc_metadata(dataset_root: Path) -> dict[str, dict[str, Any]]:
    metadata: dict[str, dict[str, Any]] = {}

    for metadata_path in dataset_root.rglob("metadata.json"):
        try:
            payload = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        if not isinstance(payload, dict):
            continue

        for filename, item in payload.items():
            if not isinstance(item, dict):
                continue

            label = normalize_label(item.get("label"))

            metadata[filename] = {
                "file_path": filename,
                "label": label,
                "source": "dfdc_metadata",
                "original": item.get("original"),
                "split": item.get("split"),
            }

    return metadata


def get_metadata_lookup(dataset_root: Path, dataset_slug: str) -> dict[str, dict[str, Any]]:
    if dataset_slug == "custom_real_life":
        return read_custom_metadata(dataset_root)

    if dataset_slug == "dfdc":
        return read_dfdc_metadata(dataset_root)

    return {}


def infer_split(
    *,
    index: int,
    total: int,
    train_ratio: float,
    val_ratio: float,
) -> str:
    if total <= 0:
        return "unknown"

    train_cutoff = int(total * train_ratio)
    val_cutoff = int(total * (train_ratio + val_ratio))

    if index < train_cutoff:
        return "train"

    if index < val_cutoff:
        return "val"

    return "test"


def find_supported_files(dataset_root: Path, max_files: int | None) -> list[Path]:
    files: list[Path] = []

    for path in dataset_root.rglob("*"):
        if not path.is_file():
            continue

        if path.suffix.lower() not in SUPPORTED_EXTENSIONS:
            continue

        files.append(path)

        if max_files and len(files) >= max_files:
            break

    return files


def build_manifest(request: DatasetManifestBuildRequest) -> dict[str, Any]:
    slug = request.slug.strip().lower()
    catalog_item = get_dataset_by_slug(slug)

    if catalog_item is None:
        raise ValueError(f"Unknown dataset slug: {slug}")

    local_path = request.local_path or get_registered_dataset_path(slug) or catalog_item.local_expected_path
    dataset_root = Path(local_path)

    if not dataset_root.exists():
        raise FileNotFoundError(f"Dataset path does not exist: {dataset_root}")

    if not dataset_root.is_dir():
        raise NotADirectoryError(f"Dataset path is not a directory: {dataset_root}")

    if abs((request.train_ratio + request.val_ratio + request.test_ratio) - 1.0) > 0.001:
        raise ValueError("train_ratio + val_ratio + test_ratio must equal 1.0")

    metadata_lookup = get_metadata_lookup(dataset_root, slug)

    files = find_supported_files(
        dataset_root=dataset_root,
        max_files=request.max_files,
    )

    random.Random(42).shuffle(files)

    warnings: list[str] = []

    if not files:
        warnings.append("No supported image/video/audio files found.")

    output_base_name = request.output_name or f"{slug}_manifest"
    manifest_dir = get_manifest_dir()
    manifest_path = manifest_dir / f"{output_base_name}.jsonl"
    summary_path = manifest_dir / f"{output_base_name}_summary.json"

    counts = {
        "total_files": 0,
        "real_count": 0,
        "fake_count": 0,
        "unknown_count": 0,
        "image_count": 0,
        "video_count": 0,
        "audio_count": 0,
        "train_count": 0,
        "val_count": 0,
        "test_count": 0,
    }

    with manifest_path.open("w", encoding="utf-8") as output_file:
        for index, path in enumerate(files):
            relative_path = path.relative_to(dataset_root).as_posix()
            media_type = get_media_type(path)

            metadata = (
                metadata_lookup.get(relative_path)
                or metadata_lookup.get(path.name)
                or {}
            )

            metadata_label = normalize_label(metadata.get("label"))
            inferred_label = infer_label_from_path(path, slug)
            label = metadata_label if metadata_label != "unknown" else inferred_label

            split = metadata.get("split")

            if split not in {"train", "val", "test"}:
                split = infer_split(
                    index=index,
                    total=len(files),
                    train_ratio=request.train_ratio,
                    val_ratio=request.val_ratio,
                )

            sha256 = calculate_sha256(path) if request.compute_sha256 else None

            sample = {
                "sample_id": str(uuid.uuid5(uuid.NAMESPACE_URL, f"{slug}:{relative_path}")),
                "dataset_slug": slug,
                "file_path": str(path),
                "relative_path": relative_path,
                "label": label,
                "media_type": media_type,
                "split": split,
                "file_size_bytes": path.stat().st_size,
                "extension": path.suffix.lower(),
                "sha256": sha256,
                "source": metadata.get("source") or slug,
                "metadata": metadata,
            }

            output_file.write(json.dumps(sample, ensure_ascii=False) + "\n")

            counts["total_files"] += 1
            counts[f"{label}_count"] = counts.get(f"{label}_count", 0) + 1

            if media_type in {"image", "video", "audio"}:
                counts[f"{media_type}_count"] += 1

            if split in {"train", "val", "test"}:
                counts[f"{split}_count"] += 1

    if counts["unknown_count"] > 0:
        warnings.append(
            f"{counts['unknown_count']} files have unknown labels. They should not be used for supervised training until labeled."
        )

    if counts["real_count"] == 0:
        warnings.append("No real samples detected.")

    if counts["fake_count"] == 0:
        warnings.append("No fake samples detected.")

    summary = {
        "slug": slug,
        "dataset_name": catalog_item.name,
        "dataset_root": str(dataset_root),
        "manifest_path": str(manifest_path),
        "summary_path": str(summary_path),
        "compute_sha256": request.compute_sha256,
        "ratios": {
            "train": request.train_ratio,
            "val": request.val_ratio,
            "test": request.test_ratio,
        },
        "counts": counts,
        "warnings": warnings,
    }

    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return summary


def list_manifests() -> list[dict[str, Any]]:
    manifest_dir = get_manifest_dir()
    items: list[dict[str, Any]] = []

    for summary_path in manifest_dir.glob("*_summary.json"):
        try:
            summary = json.loads(summary_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        items.append(summary)

    return sorted(items, key=lambda item: item.get("slug", ""))


def read_manifest_preview(
    *,
    slug: str,
    limit: int = 20,
) -> dict[str, Any]:
    manifest_dir = get_manifest_dir()

    matching_paths = list(manifest_dir.glob(f"{slug}_manifest.jsonl"))

    if not matching_paths:
        matching_paths = list(manifest_dir.glob(f"{slug}*.jsonl"))

    if not matching_paths:
        raise FileNotFoundError(f"No manifest found for slug: {slug}")

    manifest_path = matching_paths[0]
    rows: list[dict[str, Any]] = []

    with manifest_path.open("r", encoding="utf-8") as file:
        for index, line in enumerate(file):
            if index >= limit:
                break

            line = line.strip()

            if not line:
                continue

            rows.append(json.loads(line))

    return {
        "slug": slug,
        "manifest_path": str(manifest_path),
        "preview_count": len(rows),
        "rows": rows,
    }