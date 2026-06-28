from __future__ import annotations

import json
import statistics
import uuid
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import joblib
import numpy as np
from PIL import Image, ImageOps
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, classification_report, confusion_matrix
from sklearn.preprocessing import StandardScaler

from app.config import ai_settings
from app.schemas.training import FaceCropBaselineTrainRequest


def get_training_export_root() -> Path:
    return ai_settings.dataset_root / "processed" / "face_crop_training_exports"


def get_model_root() -> Path:
    path = ai_settings.model_root / "face_crop_baseline"
    path.mkdir(parents=True, exist_ok=True)
    return path


def read_jsonl(path: Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []

    if not path.exists():
        return rows

    with path.open("r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()

            if not line:
                continue

            item = json.loads(line)

            if isinstance(item, dict):
                rows.append(item)

    return rows


def load_image(path: Path, image_size: int) -> np.ndarray:
    image = Image.open(path)
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")
    image = image.resize((image_size, image_size))

    return np.asarray(image).astype(np.float32) / 255.0


def extract_image_features(path: Path, image_size: int) -> list[float]:
    image = load_image(path, image_size)

    gray = (
        image[:, :, 0] * 0.299
        + image[:, :, 1] * 0.587
        + image[:, :, 2] * 0.114
    )

    features: list[float] = []

    for channel_index in range(3):
        channel = image[:, :, channel_index]

        features.extend(
            [
                float(np.mean(channel)),
                float(np.std(channel)),
                float(np.min(channel)),
                float(np.max(channel)),
                float(np.percentile(channel, 25)),
                float(np.percentile(channel, 50)),
                float(np.percentile(channel, 75)),
            ]
        )

    features.extend(
        [
            float(np.mean(gray)),
            float(np.std(gray)),
            float(np.min(gray)),
            float(np.max(gray)),
            float(np.percentile(gray, 25)),
            float(np.percentile(gray, 50)),
            float(np.percentile(gray, 75)),
        ]
    )

    horizontal_diff = np.abs(np.diff(gray, axis=1))
    vertical_diff = np.abs(np.diff(gray, axis=0))

    features.extend(
        [
            float(np.mean(horizontal_diff)),
            float(np.std(horizontal_diff)),
            float(np.mean(vertical_diff)),
            float(np.std(vertical_diff)),
        ]
    )

    center_crop = gray[
        image_size // 4 : (image_size * 3) // 4,
        image_size // 4 : (image_size * 3) // 4,
    ]

    features.extend(
        [
            float(np.mean(center_crop)),
            float(np.std(center_crop)),
        ]
    )

    return features


def label_to_int(label: str) -> int:
    return 1 if label.lower() == "fake" else 0


def int_to_label(value: int) -> str:
    return "fake" if int(value) == 1 else "real"


def rows_to_dataset(
    *,
    rows: list[dict[str, Any]],
    image_size: int,
) -> tuple[np.ndarray, np.ndarray, list[dict[str, Any]]]:
    features = []
    labels = []
    used_rows = []

    for row in rows:
        crop_path = Path(str(row.get("crop_path") or ""))
        label = str(row.get("label") or "").lower()

        if label not in {"real", "fake"}:
            continue

        if not crop_path.exists():
            continue

        try:
            row_features = extract_image_features(crop_path, image_size)
        except Exception:
            continue

        features.append(row_features)
        labels.append(label_to_int(label))
        used_rows.append(row)

    if not features:
        return np.empty((0, 0)), np.empty((0,)), []

    return (
        np.asarray(features, dtype=np.float32),
        np.asarray(labels, dtype=np.int64),
        used_rows,
    )


def evaluate_model(
    *,
    model: LogisticRegression,
    scaler: StandardScaler,
    rows: list[dict[str, Any]],
    image_size: int,
) -> dict[str, Any]:
    x_data, y_true, used_rows = rows_to_dataset(
        rows=rows,
        image_size=image_size,
    )

    if len(used_rows) == 0:
        return {
            "sample_count": 0,
            "accuracy": None,
            "classification_report": None,
            "confusion_matrix": None,
        }

    x_scaled = scaler.transform(x_data)
    y_pred = model.predict(x_scaled)

    return {
        "sample_count": int(len(used_rows)),
        "accuracy": float(accuracy_score(y_true, y_pred)),
        "classification_report": classification_report(
            y_true,
            y_pred,
            target_names=["real", "fake"],
            labels=[0, 1],
            zero_division=0,
            output_dict=True,
        ),
        "confusion_matrix": confusion_matrix(
            y_true,
            y_pred,
            labels=[0, 1],
        ).tolist(),
    }


def count_labels(rows: list[dict[str, Any]]) -> dict[str, int]:
    counts = {
        "total": len(rows),
        "real": 0,
        "fake": 0,
    }

    for row in rows:
        label = str(row.get("label") or "").lower()

        if label == "real":
            counts["real"] += 1
        elif label == "fake":
            counts["fake"] += 1

    return counts


def train_face_crop_baseline(
    request: FaceCropBaselineTrainRequest,
) -> dict[str, Any]:
    export_dir = get_training_export_root() / request.training_export_name

    train_path = export_dir / "train.jsonl"
    val_path = export_dir / "val.jsonl"
    test_path = export_dir / "test.jsonl"
    all_path = export_dir / "all.jsonl"

    if not all_path.exists():
        raise FileNotFoundError(
            f"Training export not found: {request.training_export_name}"
        )

    train_rows = read_jsonl(train_path)
    val_rows = read_jsonl(val_path)
    test_rows = read_jsonl(test_path)

    if len(train_rows) == 0:
        train_rows = read_jsonl(all_path)

    x_train, y_train, used_train_rows = rows_to_dataset(
        rows=train_rows,
        image_size=request.image_size,
    )

    if len(used_train_rows) < 2:
        raise ValueError(
            "At least 2 valid face crops are required for baseline training."
        )

    unique_labels = sorted(set(y_train.tolist()))

    if len(unique_labels) < 2:
        raise ValueError(
            "Training data must contain at least one real and one fake face crop."
        )

    scaler = StandardScaler()
    x_train_scaled = scaler.fit_transform(x_train)

    model = LogisticRegression(
        random_state=request.random_seed,
        max_iter=1000,
        class_weight="balanced",
    )

    model.fit(x_train_scaled, y_train)

    train_metrics = evaluate_model(
        model=model,
        scaler=scaler,
        rows=used_train_rows,
        image_size=request.image_size,
    )

    val_metrics = evaluate_model(
        model=model,
        scaler=scaler,
        rows=val_rows,
        image_size=request.image_size,
    )

    test_metrics = evaluate_model(
        model=model,
        scaler=scaler,
        rows=test_rows,
        image_size=request.image_size,
    )

    run_id = uuid.uuid4().hex[:12]
    run_name = request.run_name or f"{request.model_name}_{run_id}"

    model_dir = get_model_root() / run_name
    model_dir.mkdir(parents=True, exist_ok=True)

    model_path = model_dir / "model.joblib"
    scaler_path = model_dir / "scaler.joblib"
    metadata_path = model_dir / "metadata.json"

    joblib.dump(model, model_path)
    joblib.dump(scaler, scaler_path)

    feature_count = int(x_train.shape[1])

    metadata = {
        "run_id": run_id,
        "run_name": run_name,
        "model_name": request.model_name,
        "model_version": "baseline-logistic-v1",
        "created_at": datetime.now(timezone.utc).isoformat(),
        "training_export_name": request.training_export_name,
        "image_size": request.image_size,
        "feature_count": feature_count,
        "model_path": str(model_path),
        "scaler_path": str(scaler_path),
        "metadata_path": str(metadata_path),
        "train_counts": count_labels(used_train_rows),
        "val_counts": count_labels(val_rows),
        "test_counts": count_labels(test_rows),
        "train_metrics": train_metrics,
        "val_metrics": val_metrics,
        "test_metrics": test_metrics,
        "important_warning": (
            "This is a simple baseline model for pipeline validation. "
            "It is not production-grade deepfake detection yet."
        ),
        "recommendations": [
            "Use this only to verify the training/inference pipeline.",
            "Collect a larger balanced dataset before trusting accuracy.",
            "Later chunks will replace this with CNN/Transformer-based models.",
        ],
    }

    metadata_path.write_text(
        json.dumps(metadata, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return metadata


def list_face_crop_baseline_runs() -> list[dict[str, Any]]:
    model_root = get_model_root()
    runs = []

    for metadata_path in model_root.glob("*/metadata.json"):
        try:
            metadata = json.loads(metadata_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            continue

        runs.append(metadata)

    return sorted(
        runs,
        key=lambda item: item.get("created_at", ""),
        reverse=True,
    )


def get_face_crop_baseline_run(run_name: str) -> dict[str, Any]:
    metadata_path = get_model_root() / run_name / "metadata.json"

    if not metadata_path.exists():
        raise FileNotFoundError(f"Model run not found: {run_name}")

    return json.loads(metadata_path.read_text(encoding="utf-8"))


def get_latest_face_crop_baseline_run() -> dict[str, Any]:
    runs = list_face_crop_baseline_runs()

    if not runs:
        raise FileNotFoundError("No face crop baseline model has been trained yet.")

    return runs[0]