from __future__ import annotations

import io
import uuid
from typing import Any

import cv2
import numpy as np
from PIL import Image, ImageOps

from app.schemas.faces import FaceDetectionResult


DETECTOR_NAME = "opencv_haar_frontalface"
DETECTOR_VERSION = "haar-frontalface-v2"


AVAILABLE_DETECTORS = [
    {
        "detector_id": "opencv_haar",
        "name": "OpenCV Haar Cascade",
        "version": DETECTOR_VERSION,
        "status": "enabled",
        "backend": "opencv",
        "supports_confidence": False,
        "supports_landmarks": False,
        "notes": "Fast CPU fallback detector. Good for pipeline testing, but can produce false positives.",
    },
    {
        "detector_id": "retinaface_future",
        "name": "RetinaFace",
        "version": "planned",
        "status": "planned",
        "backend": "deep_learning",
        "supports_confidence": True,
        "supports_landmarks": True,
        "notes": "Recommended future production detector for accurate face boxes and landmarks.",
    },
    {
        "detector_id": "yolo_face_future",
        "name": "YOLO-Face",
        "version": "planned",
        "status": "planned",
        "backend": "deep_learning",
        "supports_confidence": True,
        "supports_landmarks": False,
        "notes": "Recommended future high-speed detector for video and batch inference.",
    },
    {
        "detector_id": "mediapipe_future",
        "name": "MediaPipe Face Detection",
        "version": "planned",
        "status": "planned",
        "backend": "mediapipe",
        "supports_confidence": True,
        "supports_landmarks": True,
        "notes": "Good lightweight detector, but package support depends on Python version.",
    },
]


def list_available_face_detectors() -> list[dict[str, Any]]:
    return AVAILABLE_DETECTORS


def load_image_from_bytes(file_bytes: bytes) -> tuple[np.ndarray, int, int]:
    image = Image.open(io.BytesIO(file_bytes))
    image = ImageOps.exif_transpose(image)
    image = image.convert("RGB")

    width, height = image.size
    rgb_array = np.array(image)
    bgr_array = cv2.cvtColor(rgb_array, cv2.COLOR_RGB2BGR)

    return bgr_array, width, height


def get_face_cascade() -> cv2.CascadeClassifier:
    cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    cascade = cv2.CascadeClassifier(cascade_path)

    if cascade.empty():
        raise RuntimeError(f"Could not load OpenCV Haar cascade: {cascade_path}")

    return cascade


def calculate_iou(box_a: dict[str, Any], box_b: dict[str, Any]) -> float:
    ax1 = int(box_a["x"])
    ay1 = int(box_a["y"])
    ax2 = ax1 + int(box_a["width"])
    ay2 = ay1 + int(box_a["height"])

    bx1 = int(box_b["x"])
    by1 = int(box_b["y"])
    bx2 = bx1 + int(box_b["width"])
    by2 = by1 + int(box_b["height"])

    inter_x1 = max(ax1, bx1)
    inter_y1 = max(ay1, by1)
    inter_x2 = min(ax2, bx2)
    inter_y2 = min(ay2, by2)

    inter_width = max(0, inter_x2 - inter_x1)
    inter_height = max(0, inter_y2 - inter_y1)
    inter_area = inter_width * inter_height

    area_a = max(1, (ax2 - ax1) * (ay2 - ay1))
    area_b = max(1, (bx2 - bx1) * (by2 - by1))

    union_area = area_a + area_b - inter_area

    return inter_area / union_area


def remove_overlapping_faces(
    faces: list[dict[str, Any]],
    iou_threshold: float = 0.35,
) -> list[dict[str, Any]]:
    sorted_faces = sorted(
        faces,
        key=lambda item: (
            float(item.get("quality_score") or 0.0),
            float(item.get("area_ratio") or 0.0),
        ),
        reverse=True,
    )

    kept_faces: list[dict[str, Any]] = []

    for face in sorted_faces:
        overlaps_existing = False

        for kept_face in kept_faces:
            if calculate_iou(face, kept_face) >= iou_threshold:
                overlaps_existing = True
                break

        if not overlaps_existing:
            kept_faces.append(face)

    return kept_faces


def estimate_face_quality(
    *,
    gray_image: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
    image_width: int,
    image_height: int,
) -> tuple[float, dict[str, Any]]:
    face_region = gray_image[y : y + height, x : x + width]

    if face_region.size == 0:
        return 0.0, {
            "sharpness": 0.0,
            "brightness": 0.0,
            "face_area_ratio": 0.0,
        }

    sharpness = float(cv2.Laplacian(face_region, cv2.CV_64F).var())
    brightness = float(np.mean(face_region))

    image_area = max(1, image_width * image_height)
    face_area_ratio = float((width * height) / image_area)

    sharpness_score = min(1.0, sharpness / 250.0)

    if brightness < 35:
        brightness_score = brightness / 35.0
    elif brightness > 220:
        brightness_score = max(0.0, (255.0 - brightness) / 35.0)
    else:
        brightness_score = 1.0

    if face_area_ratio < 0.005:
        size_score = face_area_ratio / 0.005
    elif face_area_ratio > 0.70:
        size_score = max(0.0, 1.0 - ((face_area_ratio - 0.70) / 0.30))
    else:
        size_score = 1.0

    aspect_ratio = width / max(1, height)

    if 0.75 <= aspect_ratio <= 1.35:
        aspect_score = 1.0
    else:
        aspect_score = 0.5

    quality_score = round(
        max(
            0.0,
            min(
                1.0,
                (sharpness_score * 0.40)
                + (brightness_score * 0.30)
                + (size_score * 0.20)
                + (aspect_score * 0.10),
            ),
        ),
        4,
    )

    return quality_score, {
        "sharpness": round(sharpness, 4),
        "brightness": round(brightness, 4),
        "face_area_ratio": round(face_area_ratio, 6),
        "aspect_ratio": round(aspect_ratio, 4),
        "sharpness_score": round(sharpness_score, 4),
        "brightness_score": round(brightness_score, 4),
        "size_score": round(size_score, 4),
        "aspect_score": round(aspect_score, 4),
    }


def detect_faces_from_image_bytes(
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
    detector_id: str = "opencv_haar",
    min_quality_score: float = 0.0,
    min_area_ratio: float = 0.0,
    max_faces: int = 50,
    remove_overlaps: bool = False,
) -> dict[str, Any]:
    warnings: list[str] = []

    if detector_id != "opencv_haar":
        warnings.append(
            f"Detector '{detector_id}' is not enabled yet. Falling back to opencv_haar."
        )

    if not file_bytes:
        raise ValueError("Image file is empty.")

    image_bgr, image_width, image_height = load_image_from_bytes(file_bytes)

    gray = cv2.cvtColor(image_bgr, cv2.COLOR_BGR2GRAY)
    gray = cv2.equalizeHist(gray)

    cascade = get_face_cascade()

    detected_faces = cascade.detectMultiScale(
        gray,
        scaleFactor=1.08,
        minNeighbors=5,
        minSize=(40, 40),
        flags=cv2.CASCADE_SCALE_IMAGE,
    )

    faces: list[dict[str, Any]] = []
    image_area = max(1, image_width * image_height)

    for index, face in enumerate(detected_faces):
        x, y, width, height = [int(value) for value in face]

        area_ratio = round((width * height) / image_area, 6)
        # Reject likely false positives near image edge or too small for portrait analysis
        edge_margin_x = int(image_width * 0.03)
        edge_margin_y = int(image_height * 0.03)
        
        is_near_edge = (
            x <= edge_margin_x
            or y <= edge_margin_y
            or (x + width) >= (image_width - edge_margin_x)
            or (y + height) >= (image_height - edge_margin_y)
        )
        
        if is_near_edge and area_ratio < 0.08:
            continue
        
        quality_score, quality_details = estimate_face_quality(
            gray_image=gray,
            x=x,
            y=y,
            width=width,
            height=height,
            image_width=image_width,
            image_height=image_height,
        )

        if quality_score < min_quality_score:
            continue

        if area_ratio < min_area_ratio:
            continue

        crop_recommended = quality_score >= 0.2 and area_ratio >= 0.005

        faces.append(
            {
                "face_id": str(
                    uuid.uuid5(
                        uuid.NAMESPACE_URL,
                        f"{filename}:{index}:{x}:{y}:{width}:{height}",
                    )
                ),
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "center_x": round(x + (width / 2), 2),
                "center_y": round(y + (height / 2), 2),
                "confidence": None,
                "area_ratio": area_ratio,
                "quality_score": quality_score,
                "crop_recommended": crop_recommended,
                "details": {
                    "detector": DETECTOR_NAME,
                    "detector_id": "opencv_haar",
                    "quality": quality_details,
                    "raw_index": index,
                },
            }
        )

    if remove_overlaps:
        faces = remove_overlapping_faces(faces)

    faces = sorted(
        faces,
        key=lambda item: (
            float(item.get("quality_score") or 0.0),
            float(item.get("area_ratio") or 0.0),
        ),
        reverse=True,
    )

    if max_faces > 0:
        faces = faces[:max_faces]

    if len(faces) == 0:
        warnings.append(
            "No usable frontal face was detected. This can happen with side faces, low resolution, heavy blur, masks, dark images, or non-face images."
        )

    if len(faces) > 1:
        warnings.append(
            "Multiple usable faces detected. Later chunks will add identity tracking and per-person analysis."
        )

    result = FaceDetectionResult(
        filename=filename,
        mime_type=mime_type,
        image_width=image_width,
        image_height=image_height,
        face_count=len(faces),
        faces=faces,
        detector=DETECTOR_NAME,
        detector_version=DETECTOR_VERSION,
        warnings=warnings,
    )

    return result.model_dump()