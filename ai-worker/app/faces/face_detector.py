from __future__ import annotations

import uuid
from typing import Any

import cv2
import numpy as np

from app.schemas.faces import FaceDetectionResult


DETECTOR_NAME = "opencv_haar_frontalface"
DETECTOR_VERSION = "haar-frontalface-v1"


def calculate_quality_score(
    gray_image: np.ndarray,
    x: int,
    y: int,
    width: int,
    height: int,
) -> float:
    face_region = gray_image[y:y + height, x:x + width]

    if face_region.size == 0:
        return 0.0

    sharpness = cv2.Laplacian(
        face_region,
        cv2.CV_64F,
    ).var()

    sharpness_score = min(float(sharpness) / 500.0, 1.0)

    brightness = float(np.mean(face_region))
    brightness_score = max(
        0.0,
        1.0 - abs(brightness - 127.5) / 127.5,
    )

    quality_score = (
        sharpness_score * 0.7
        + brightness_score * 0.3
    )

    return round(max(0.0, min(quality_score, 1.0)), 4)


def detect_faces_from_image_bytes(
    *,
    file_bytes: bytes,
    filename: str,
    mime_type: str,
) -> dict[str, Any]:
    if not file_bytes:
        raise ValueError("Image data is empty.")

    image_array = np.frombuffer(file_bytes, dtype=np.uint8)
    image = cv2.imdecode(image_array, cv2.IMREAD_COLOR)

    if image is None:
        raise ValueError(
            "The uploaded file could not be decoded as an image."
        )

    image_height, image_width = image.shape[:2]
    gray_image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    gray_image = cv2.equalizeHist(gray_image)

    cascade_path = (
        cv2.data.haarcascades
        + "haarcascade_frontalface_default.xml"
    )

    detector = cv2.CascadeClassifier(cascade_path)

    if detector.empty():
        raise RuntimeError(
            "OpenCV Haar face detector could not be loaded."
        )

    detected_faces = detector.detectMultiScale(
        gray_image,
        scaleFactor=1.1,
        minNeighbors=5,
        minSize=(40, 40),
    )

    faces: list[dict[str, Any]] = []
    warnings: list[str] = []

    image_area = max(image_width * image_height, 1)

    for index, (x, y, width, height) in enumerate(
        detected_faces
    ):
        x = int(x)
        y = int(y)
        width = int(width)
        height = int(height)

        area_ratio = round(
            (width * height) / image_area,
            6,
        )

        quality_score = calculate_quality_score(
            gray_image,
            x,
            y,
            width,
            height,
        )

        face_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                (
                    f"{filename}:{index}:{x}:{y}:"
                    f"{width}:{height}"
                ),
            )
        )

        faces.append(
            {
                "face_id": face_id,
                "x": x,
                "y": y,
                "width": width,
                "height": height,
                "center_x": round(x + width / 2, 2),
                "center_y": round(y + height / 2, 2),
                "confidence": None,
                "area_ratio": area_ratio,
                "quality_score": quality_score,
                "crop_recommended": (
                    quality_score >= 0.2
                    and width >= 60
                    and height >= 60
                ),
                "details": {
                    "index": index,
                    "detector": DETECTOR_NAME,
                },
            }
        )

    faces = sorted(
        faces,
        key=lambda item: item["area_ratio"],
        reverse=True,
    )

    if not faces:
        warnings.append(
            "No frontal face was detected. Try a clear, "
            "well-lit, front-facing image."
        )

    if len(faces) > 1:
        warnings.append(
            "Multiple faces were detected in the image."
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