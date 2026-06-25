from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from app.config import ai_settings
from app.datasets.catalog import get_dataset_by_slug, get_recommended_datasets
from app.schemas.datasets import (
    DatasetValidationRequest,
    LocalDatasetRegistrationRequest,
)


REGISTRY_PATH = ai_settings.dataset_root / "registry.json"


def read_registry_file() -> list[dict[str, Any]]:
    if not REGISTRY_PATH.exists():
        return []

    try:
        data = json.loads(REGISTRY_PATH.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return []

    if not isinstance(data, list):
        return []

    return data


def write_registry_file(items: list[dict[str, Any]]) -> None:
    ai_settings.dataset_root.mkdir(parents=True, exist_ok=True)

    REGISTRY_PATH.write_text(
        json.dumps(items, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )


def validate_dataset_path(*, slug: str, local_path: str) -> dict[str, Any]:
    path = Path(local_path)
    catalog_item = get_dataset_by_slug(slug)

    validation: dict[str, Any] = {
        "slug": slug,
        "local_path": str(path),
        "exists": path.exists(),
        "is_dir": path.is_dir(),
        "file_count": 0,
        "video_count": 0,
        "image_count": 0,
        "audio_count": 0,
        "metadata_count": 0,
        "status": "missing",
        "warnings": [],
    }

    if not path.exists():
        validation["warnings"].append("Dataset path does not exist.")
        return validation

    if not path.is_dir():
        validation["warnings"].append("Dataset path exists but is not a directory.")
        validation["status"] = "invalid"
        return validation

    video_ext = {".mp4", ".mov", ".avi", ".mkv", ".webm"}
    image_ext = {".jpg", ".jpeg", ".png", ".webp", ".bmp"}
    audio_ext = {".wav", ".mp3", ".flac", ".m4a", ".ogg"}
    metadata_ext = {".csv", ".json", ".txt", ".yaml", ".yml"}

    for item in path.rglob("*"):
        if not item.is_file():
            continue

        validation["file_count"] += 1
        suffix = item.suffix.lower()

        if suffix in video_ext:
            validation["video_count"] += 1
        elif suffix in image_ext:
            validation["image_count"] += 1
        elif suffix in audio_ext:
            validation["audio_count"] += 1
        elif suffix in metadata_ext:
            validation["metadata_count"] += 1

    if validation["file_count"] == 0:
        validation["status"] = "invalid"
        validation["warnings"].append("Dataset folder is empty.")
        return validation

    if catalog_item:
        modality = catalog_item.modality

        if modality == "video" and validation["video_count"] == 0:
            validation["warnings"].append("This dataset is expected to contain video files.")

        if modality == "image" and validation["image_count"] == 0:
            validation["warnings"].append("This dataset is expected to contain image files.")

        if modality == "audio" and validation["audio_count"] == 0:
            validation["warnings"].append("This dataset is expected to contain audio files.")

        if modality == "audio_video" and validation["video_count"] == 0:
            validation["warnings"].append("Audio-video datasets should contain video files.")

    validation["status"] = "ready" if not validation["warnings"] else "registered"

    return validation


def list_local_dataset_registry() -> list[dict[str, Any]]:
    registry_items = read_registry_file()
    catalog_lookup = {
        item["slug"]: item
        for item in get_recommended_datasets()
    }

    output = []

    for item in registry_items:
        slug = str(item.get("slug") or "")
        catalog_item = catalog_lookup.get(slug, {})

        validation = validate_dataset_path(
            slug=slug,
            local_path=str(item.get("local_path") or ""),
        )

        output.append(
            {
                "slug": slug,
                "name": catalog_item.get("name") or item.get("name") or slug,
                "modality": catalog_item.get("modality") or "multimodal",
                "local_path": item.get("local_path"),
                "enabled": bool(item.get("enabled", True)),
                "status": validation.get("status"),
                "exists": validation.get("exists"),
                "notes": item.get("notes"),
                "validation": validation,
            }
        )

    return output


def register_local_dataset(request: LocalDatasetRegistrationRequest) -> dict[str, Any]:
    catalog_item = get_dataset_by_slug(request.slug)

    if catalog_item is None:
        raise ValueError(f"Unknown dataset slug: {request.slug}")

    registry_items = read_registry_file()

    new_item = {
        "slug": request.slug,
        "name": catalog_item.name,
        "modality": catalog_item.modality,
        "local_path": request.local_path,
        "enabled": request.enabled,
        "notes": request.notes,
    }

    updated = False

    for index, item in enumerate(registry_items):
        if item.get("slug") == request.slug:
            registry_items[index] = new_item
            updated = True
            break

    if not updated:
        registry_items.append(new_item)

    write_registry_file(registry_items)

    validation = validate_dataset_path(
        slug=request.slug,
        local_path=request.local_path,
    )

    return {
        **new_item,
        "status": validation.get("status"),
        "exists": validation.get("exists"),
        "validation": validation,
    }


def validate_local_dataset(request: DatasetValidationRequest) -> dict[str, Any]:
    return validate_dataset_path(
        slug=request.slug,
        local_path=request.local_path,
    )


def initialize_recommended_registry() -> list[dict[str, Any]]:
    current_items = read_registry_file()
    current_slugs = {item.get("slug") for item in current_items}

    for dataset in get_recommended_datasets():
        if dataset["slug"] in current_slugs:
            continue

        current_items.append(
            {
                "slug": dataset["slug"],
                "name": dataset["name"],
                "modality": dataset["modality"],
                "local_path": dataset["local_expected_path"],
                "enabled": dataset["slug"] in {
                    "faceforensics_pp",
                    "celeb_df_v2",
                    "custom_real_life",
                },
                "notes": "Auto-created by Chunk 34 dataset registry.",
            }
        )

    write_registry_file(current_items)

    return list_local_dataset_registry()