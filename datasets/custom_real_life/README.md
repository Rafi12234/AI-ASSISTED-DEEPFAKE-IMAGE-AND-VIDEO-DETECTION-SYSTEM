# Custom Real-Life Deepfake Dataset

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
