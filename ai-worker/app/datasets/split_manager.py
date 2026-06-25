from __future__ import annotations

import json
import random
import shutil
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from app.config import ai_settings
from app.datasets.quality_checker import get_default_manifest_path
from app.schemas.datasets import DatasetTrainingExportRequest


VALID_LABELS = {"real", "fake"}
VALID_SPLITS = {"train", "val", "test"}


def get_training_export_root() -> Path:
    path = ai_settings.dataset_root / "processed" / "training_exports"
    path.mkdir(parents=True, exist_ok=True)
    return path


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


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    with path.open("w", encoding="utf-8") as file:
        for row in rows:
            file.write(json.dumps(row, ensure_ascii=False) + "\n")


def safe_filename(row: dict[str, Any]) -> str:
    sample_id = str(row.get("sample_id") or "sample").replace("-", "")
    original_path = Path(str(row.get("file_path") or "file"))
    suffix = original_path.suffix.lower()

    return f"{sample_id[:12]}_{original_path.stem}{suffix}"


def copy_export_file(
    *,
    row: dict[str, Any],
    export_dir: Path,
    split: str,
    label: str,
) -> str | None:
    source_path = Path(str(row.get("file_path") or ""))

    if not source_path.exists() or not source_path.is_file():
        return None

    target_dir = export_dir / "files" / split / label
    target_dir.mkdir(parents=True, exist_ok=True)

    target_path = target_dir / safe_filename(row)

    if not target_path.exists():
        shutil.copy2(source_path, target_path)

    return str(target_path)


def split_class_rows(
    *,
    rows: list[dict[str, Any]],
    train_ratio: float,
    val_ratio: float,
    seed: int,
) -> dict[str, list[dict[str, Any]]]:
    shuffled_rows = list(rows)
    random.Random(seed).shuffle(shuffled_rows)

    total = len(shuffled_rows)

    if total == 0:
        return {
            "train": [],
            "val": [],
            "test": [],
        }

    if total == 1:
        return {
            "train": shuffled_rows,
            "val": [],
            "test": [],
        }

    if total == 2:
        return {
            "train": shuffled_rows[:1],
            "val": [],
            "test": shuffled_rows[1:],
        }

    train_count = int(total * train_ratio)
    val_count = int(total * val_ratio)

    if train_count <= 0:
        train_count = 1

    if val_count <= 0 and total >= 5:
        val_count = 1

    if train_count + val_count >= total:
        val_count = max(0, total - train_count - 1)

    train_rows = shuffled_rows[:train_count]
    val_rows = shuffled_rows[train_count : train_count + val_count]
    test_rows = shuffled_rows[train_count + val_count :]

    return {
        "train": train_rows,
        "val": val_rows,
        "test": test_rows,
    }


def count_rows(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "total": len(rows),
        "real": 0,
        "fake": 0,
        "image": 0,
        "video": 0,
        "audio": 0,
    }

    for row in rows:
        label = str(row.get("label") or "").lower()
        media_type = str(row.get("media_type") or "").lower()

        if label in {"real", "fake"}:
            counts[label] += 1

        if media_type in {"image", "video", "audio"}:
            counts[media_type] += 1

    return counts


def build_recommendations(summary: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []

    total = summary["counts"]["all"]["total"]
    real_count = summary["counts"]["all"]["real"]
    fake_count = summary["counts"]["all"]["fake"]
    val_count = summary["counts"]["val"]["total"]
    test_count = summary["counts"]["test"]["total"]

    if total < 100:
        recommendations.append(
            "This export is okay for pipeline testing, but it is too small for real model training. Collect at least 100 labeled samples first."
        )

    if real_count < 50:
        recommendations.append("Add more real samples. Minimum early target: 50 real samples.")

    if fake_count < 50:
        recommendations.append("Add more fake/deepfake samples. Minimum early target: 50 fake samples.")

    if val_count == 0:
        recommendations.append("Validation split is empty. Add more samples before training.")

    if test_count == 0:
        recommendations.append("Test split is empty. Add more samples before evaluation.")

    if not recommendations:
        recommendations.append("Training export is ready for the configured threshold.")

    return recommendations


def create_export_readme(
    *,
    export_dir: Path,
    summary: dict[str, Any],
) -> None:
    text = f"""# Training Dataset Export

Dataset slug: {summary["slug"]}

Created at: {summary["created_at"]}

Files:
- train.jsonl
- val.jsonl
- test.jsonl
- all.jsonl
- summary.json

Use this folder as the input for future model training chunks.

Important:
1. Do not train directly from random folders.
2. Use train.jsonl for training.
3. Use val.jsonl for validation during training.
4. Use test.jsonl only for final testing.
5. Do not manually move test samples into train.
6. Keep this export unchanged for reproducible experiments.
"""

    (export_dir / "README.md").write_text(text, encoding="utf-8")


def export_training_split(request: DatasetTrainingExportRequest) -> dict[str, Any]:
    slug = request.slug.strip().lower()

    if abs((request.train_ratio + request.val_ratio + request.test_ratio) - 1.0) > 0.001:
        raise ValueError("train_ratio + val_ratio + test_ratio must equal 1.0")

    manifest_path = (
        Path(request.manifest_path)
        if request.manifest_path
        else get_default_manifest_path(slug)
    )

    if not manifest_path.exists():
        raise FileNotFoundError(f"Manifest file does not exist: {manifest_path}")

    rows = read_jsonl(manifest_path)

    filtered_rows: list[dict[str, Any]] = []
    skipped_rows: list[dict[str, Any]] = []

    for row in rows:
        label = str(row.get("label") or "unknown").lower()
        media_type = str(row.get("media_type") or "unknown").lower()
        file_path = Path(str(row.get("file_path") or ""))

        if not request.include_unknown_labels and label not in VALID_LABELS:
            skipped_rows.append(
                {
                    "reason": "unknown_or_invalid_label",
                    "sample_id": row.get("sample_id"),
                    "file_path": row.get("file_path"),
                }
            )
            continue

        if request.target_media_type and media_type != request.target_media_type:
            skipped_rows.append(
                {
                    "reason": "media_type_filtered_out",
                    "sample_id": row.get("sample_id"),
                    "file_path": row.get("file_path"),
                }
            )
            continue

        if request.verify_files_exist and not file_path.exists():
            skipped_rows.append(
                {
                    "reason": "file_missing",
                    "sample_id": row.get("sample_id"),
                    "file_path": row.get("file_path"),
                }
            )
            continue

        filtered_rows.append(row)

    grouped_by_label: dict[str, list[dict[str, Any]]] = defaultdict(list)

    for row in filtered_rows:
        label = str(row.get("label") or "unknown").lower()
        grouped_by_label[label].append(row)

    split_rows = {
        "train": [],
        "val": [],
        "test": [],
    }

    for label, label_rows in grouped_by_label.items():
        class_splits = split_class_rows(
            rows=label_rows,
            train_ratio=request.train_ratio,
            val_ratio=request.val_ratio,
            seed=request.seed,
        )

        for split_name in VALID_SPLITS:
            for row in class_splits[split_name]:
                updated_row = dict(row)
                updated_row["split"] = split_name
                updated_row["export_label"] = label
                split_rows[split_name].append(updated_row)

    for split_name in VALID_SPLITS:
        random.Random(request.seed).shuffle(split_rows[split_name])

    output_name = request.output_name or f"{slug}_training_export"
    export_dir = get_training_export_root() / output_name
    export_dir.mkdir(parents=True, exist_ok=True)

    if request.copy_files:
        for split_name in VALID_SPLITS:
            for row in split_rows[split_name]:
                label = str(row.get("label") or "unknown").lower()

                copied_path = copy_export_file(
                    row=row,
                    export_dir=export_dir,
                    split=split_name,
                    label=label,
                )

                row["export_file_path"] = copied_path

    all_rows = split_rows["train"] + split_rows["val"] + split_rows["test"]

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
        "slug": slug,
        "output_name": output_name,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "source_manifest_path": str(manifest_path),
        "export_dir": str(export_dir),
        "train_path": str(train_path),
        "val_path": str(val_path),
        "test_path": str(test_path),
        "all_path": str(all_path),
        "summary_path": str(summary_path),
        "copy_files": request.copy_files,
        "target_media_type": request.target_media_type,
        "include_unknown_labels": request.include_unknown_labels,
        "ratios": {
            "train": request.train_ratio,
            "val": request.val_ratio,
            "test": request.test_ratio,
        },
        "counts": {
            "all": count_rows(all_rows),
            "train": count_rows(split_rows["train"]),
            "val": count_rows(split_rows["val"]),
            "test": count_rows(split_rows["test"]),
            "skipped": len(skipped_rows),
        },
        "skipped_preview": skipped_rows[:50],
    }

    summary["recommendations"] = build_recommendations(summary)

    summary_path.write_text(
        json.dumps(summary, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    create_export_readme(
        export_dir=export_dir,
        summary=summary,
    )

    return summary


def list_training_exports() -> list[dict[str, Any]]:
    export_root = get_training_export_root()
    exports: list[dict[str, Any]] = []

    for summary_path in export_root.glob("*/summary.json"):
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


def get_training_export_summary(output_name: str) -> dict[str, Any]:
    export_root = get_training_export_root()
    summary_path = export_root / output_name / "summary.json"

    if not summary_path.exists():
        raise FileNotFoundError(f"Training export not found: {output_name}")

    return json.loads(summary_path.read_text(encoding="utf-8"))