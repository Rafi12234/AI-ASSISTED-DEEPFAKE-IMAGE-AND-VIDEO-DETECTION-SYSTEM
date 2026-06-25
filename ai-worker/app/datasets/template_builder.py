from __future__ import annotations

from pathlib import Path

from app.config import ai_settings


CUSTOM_METADATA_TEMPLATE = """file_path,label,media_type,source,consent,notes
real/images/example_real.jpg,real,image,local_collection,yes,Replace this row
fake/images/example_fake.jpg,fake,image,generated_or_verified_fake,yes,Replace this row
real/videos/example_real.mp4,real,video,local_collection,yes,Replace this row
fake/videos/example_fake.mp4,fake,video,generated_or_verified_fake,yes,Replace this row
real/audio/example_real.wav,real,audio,local_collection,yes,Replace this row
fake/audio/example_fake.wav,fake,audio,generated_or_verified_fake,yes,Replace this row
"""


CUSTOM_README_TEMPLATE = """# Custom Real-Life Deepfake Dataset

Use this folder for your own ethically collected real/fake media.

Expected structure:

custom_real_life/
├── real/
│   ├── images/
│   ├── videos/
│   └── audio/
├── fake/
│   ├── images/
│   ├── videos/
│   └── audio/
└── metadata.csv

Rules:
1. Only use media you have permission to store and train on.
2. Keep labels correct: real or fake.
3. Keep source notes.
4. Do not include private sensitive media without permission.
5. Keep separate test data that is never used for training.
"""


def create_custom_dataset_template() -> dict[str, str]:
    root = ai_settings.dataset_root / "custom_real_life"

    folders = [
        root / "real" / "images",
        root / "real" / "videos",
        root / "real" / "audio",
        root / "fake" / "images",
        root / "fake" / "videos",
        root / "fake" / "audio",
    ]

    for folder in folders:
        folder.mkdir(parents=True, exist_ok=True)

    metadata_path = root / "metadata.csv"
    readme_path = root / "README.md"

    if not metadata_path.exists():
        metadata_path.write_text(CUSTOM_METADATA_TEMPLATE, encoding="utf-8")

    if not readme_path.exists():
        readme_path.write_text(CUSTOM_README_TEMPLATE, encoding="utf-8")

    return {
        "custom_dataset_root": str(root),
        "metadata_path": str(metadata_path),
        "readme_path": str(readme_path),
    }