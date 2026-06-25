from __future__ import annotations

from app.config import ai_settings
from app.schemas.datasets import DatasetCatalogItem


def dataset_path(*parts: str) -> str:
    return str(ai_settings.dataset_root.joinpath(*parts))


RECOMMENDED_DATASETS: list[DatasetCatalogItem] = [
    DatasetCatalogItem(
        slug="faceforensics_pp",
        name="FaceForensics++",
        priority=1,
        modality="video",
        task_type="visual_face_manipulation_detection",
        recommended_stage="starter_visual_training",
        official_source="https://github.com/ondyari/FaceForensics",
        access_type="research_dataset_request_or_official_download_script",
        size_note="Large video dataset; use C23 compressed version first if storage is limited.",
        license_note="Use according to official research/data terms. Do not redistribute.",
        why_use_it=(
            "Strong starter benchmark for facial manipulation detection. "
            "Includes Deepfakes, Face2Face, FaceSwap, and NeuralTextures."
        ),
        local_expected_path=dataset_path("raw", "faceforensics_pp"),
        expected_layout={
            "real": "original_sequences/",
            "fake": [
                "manipulated_sequences/Deepfakes/",
                "manipulated_sequences/Face2Face/",
                "manipulated_sequences/FaceSwap/",
                "manipulated_sequences/NeuralTextures/",
            ],
        },
        notes=[
            "Use for first image/video visual detector training.",
            "Extract face crops from frames in later preprocessing chunks.",
            "Recommended first dataset for visual branch.",
        ],
    ),
    DatasetCatalogItem(
        slug="celeb_df_v2",
        name="Celeb-DF v2",
        priority=2,
        modality="video",
        task_type="high_quality_deepfake_video_detection",
        recommended_stage="starter_visual_generalization",
        official_source="https://cse.buffalo.edu/~siweilyu/celeb-deepfakeforensics.html",
        access_type="official_request_or_kaggle_mirror_if_license_allows",
        size_note="Medium-sized compared with DFDC; good after FaceForensics++.",
        license_note="Check official terms before download/use.",
        why_use_it=(
            "Higher-quality celebrity deepfake videos closer to online visual quality. "
            "Useful for cross-dataset generalization."
        ),
        local_expected_path=dataset_path("raw", "celeb_df_v2"),
        expected_layout={
            "real": "Celeb-real/",
            "fake": "Celeb-synthesis/",
            "metadata": "List_of_testing_videos.txt or metadata files",
        },
        notes=[
            "Use as second visual dataset.",
            "Good for checking whether FaceForensics++ trained model generalizes.",
        ],
    ),
    DatasetCatalogItem(
        slug="dfdc",
        name="Deepfake Detection Challenge Dataset",
        priority=3,
        modality="video",
        task_type="large_scale_video_deepfake_detection",
        recommended_stage="large_scale_visual_training",
        official_source="https://ai.meta.com/datasets/dfdc/",
        access_type="Meta official dataset / Kaggle competition dataset",
        size_note="Very large. Requires significant disk space and preprocessing time.",
        license_note="Follow Meta/Kaggle dataset terms.",
        why_use_it=(
            "Large-scale dataset for production-strength visual video detection. "
            "Useful after the base pipeline is stable."
        ),
        local_expected_path=dataset_path("raw", "dfdc"),
        expected_layout={
            "videos": "train_sample_videos/ or full dataset folders",
            "metadata": "metadata.json files",
        },
        notes=[
            "Do not start with full DFDC on a weak PC.",
            "Use sample subset first, then scale.",
        ],
    ),
    DatasetCatalogItem(
        slug="deeperforensics_1",
        name="DeeperForensics-1.0",
        priority=4,
        modality="video",
        task_type="real_world_perturbation_deepfake_detection",
        recommended_stage="robustness_training_and_testing",
        official_source="https://github.com/EndlessSora/DeeperForensics-1.0",
        access_type="official dataset request/download",
        size_note="Very large: 60,000 videos and 17.6M frames according to the paper/project.",
        license_note="Follow official research usage terms.",
        why_use_it=(
            "Important for robustness because it includes real-world perturbations."
        ),
        local_expected_path=dataset_path("raw", "deeperforensics_1"),
        expected_layout={
            "real": "source videos / real videos",
            "fake": "manipulated videos",
            "perturbations": "compressed/blur/noise/real-world perturbation variants",
        },
        notes=[
            "Use after the first models and preprocessing pipeline are stable.",
            "Very useful for production robustness testing.",
        ],
    ),
    DatasetCatalogItem(
        slug="wilddeepfake",
        name="WildDeepfake",
        priority=5,
        modality="video",
        task_type="in_the_wild_deepfake_detection",
        recommended_stage="real_world_testing",
        official_source="https://github.com/OpenTAI/wild-deepfake",
        access_type="official project repository / dataset release",
        size_note="Smaller than DFDC but useful for real-world style testing.",
        license_note="Follow official repository terms.",
        why_use_it=(
            "Useful for testing real-world internet-style deepfake difficulty."
        ),
        local_expected_path=dataset_path("raw", "wilddeepfake"),
        expected_layout={
            "face_sequences": "real/fake face sequences depending on release layout",
        },
        notes=[
            "Use for generalization testing, not only training.",
            "Good for evaluating real-world performance drop.",
        ],
    ),
    DatasetCatalogItem(
        slug="fakeavceleb",
        name="FakeAVCeleb",
        priority=6,
        modality="audio_video",
        task_type="audio_video_multimodal_deepfake_detection",
        recommended_stage="audio_visual_training",
        official_source="https://sites.google.com/view/fakeavcelebdash-lab/",
        access_type="official request/project access",
        size_note="Multimodal dataset; storage and preprocessing requirements are higher.",
        license_note="Follow official research/data terms.",
        why_use_it=(
            "Contains audio-video deepfakes with cloned audio and lip-sync. "
            "Important for multimodal detection."
        ),
        local_expected_path=dataset_path("raw", "fakeavceleb"),
        expected_layout={
            "real": "real videos",
            "fake": "fake audio-video categories",
            "metadata": "labels/metadata from official release",
        },
        notes=[
            "Use after audio extraction and AV sync chunks.",
            "Important for detecting face + voice manipulation.",
        ],
    ),
    DatasetCatalogItem(
        slug="asvspoof_2021",
        name="ASVspoof 2021",
        priority=7,
        modality="audio",
        task_type="speech_deepfake_and_spoof_detection",
        recommended_stage="audio_deepfake_training",
        official_source="https://www.asvspoof.org/index2021.html",
        access_type="official challenge release / Zenodo",
        size_note="Audio-focused dataset. Use after audio pipeline is ready.",
        license_note="Released under stated ASVspoof/Zenodo terms.",
        why_use_it=(
            "Important for detecting spoofed and deepfake speech."
        ),
        local_expected_path=dataset_path("raw", "asvspoof_2021"),
        expected_layout={
            "audio": "LA/PA/DF audio files",
            "protocols": "metadata/protocol files",
        },
        notes=[
            "Use for audio model training and evaluation.",
            "Will not help visual face detection directly.",
        ],
    ),
    DatasetCatalogItem(
        slug="av_deepfake1m",
        name="AV-Deepfake1M",
        priority=8,
        modality="audio_video",
        task_type="large_scale_audio_visual_deepfake_localization",
        recommended_stage="advanced_multimodal_training",
        official_source="https://github.com/ControlNet/AV-Deepfake1M",
        access_type="official GitHub/project release",
        size_note="Very large: more than 1M videos according to the paper/project.",
        license_note="Follow official research usage terms.",
        why_use_it=(
            "Advanced dataset for video, audio, and audio-visual manipulation detection/localization."
        ),
        local_expected_path=dataset_path("raw", "av_deepfake1m"),
        expected_layout={
            "videos": "dataset videos",
            "annotations": "segment-level/audio-video manipulation annotations",
        },
        notes=[
            "Use only after core pipeline is stable.",
            "Good for next-generation audio-visual localization.",
        ],
    ),
    DatasetCatalogItem(
        slug="av_deepfake1m_pp",
        name="AV-Deepfake1M++",
        priority=9,
        modality="audio_video",
        task_type="large_scale_audio_visual_deepfake_with_perturbations",
        recommended_stage="advanced_production_robustness",
        official_source="https://huggingface.co/datasets/ControlNet/AV-Deepfake1M-PlusPlus",
        access_type="Hugging Face dataset / research license",
        size_note="Around 2M clips according to the dataset card.",
        license_note="Research-only or dataset-specific license terms may apply.",
        why_use_it=(
            "Very advanced multimodal dataset for audio-visual perturbation robustness."
        ),
        local_expected_path=dataset_path("raw", "av_deepfake1m_pp"),
        expected_layout={
            "videos": "dataset clips",
            "annotations": "labels and temporal annotations",
        },
        notes=[
            "Not recommended as the first dataset due to size.",
            "Use after GPU pipeline and evaluation pipeline are ready.",
        ],
    ),
    DatasetCatalogItem(
        slug="custom_real_life",
        name="Custom Real-Life Dataset",
        priority=10,
        modality="multimodal",
        task_type="local_real_world_training_and_testing",
        recommended_stage="continuous_improvement",
        official_source="local_project_dataset",
        access_type="user_collected_ethically_labeled_dataset",
        size_note="Starts small; grows from verified real/fake samples and human-reviewed cases.",
        license_note="Only use data you have permission to store and train on.",
        why_use_it=(
            "Most important for your actual production environment because it reflects your users, compression, language, devices, and real upload conditions."
        ),
        local_expected_path=dataset_path("custom_real_life"),
        expected_layout={
            "real_images": "real/images/",
            "real_videos": "real/videos/",
            "real_audio": "real/audio/",
            "fake_images": "fake/images/",
            "fake_videos": "fake/videos/",
            "fake_audio": "fake/audio/",
            "metadata": "metadata.csv",
        },
        notes=[
            "Must be ethically collected and labeled.",
            "Use for real-life testing and later fine-tuning.",
            "Do not include private or sensitive media without permission.",
        ],
    ),
]


def get_recommended_datasets() -> list[dict]:
    return [
        item.model_dump()
        for item in sorted(RECOMMENDED_DATASETS, key=lambda dataset: dataset.priority)
    ]


def get_dataset_by_slug(slug: str) -> DatasetCatalogItem | None:
    normalized_slug = slug.strip().lower()

    for item in RECOMMENDED_DATASETS:
        if item.slug == normalized_slug:
            return item

    return None