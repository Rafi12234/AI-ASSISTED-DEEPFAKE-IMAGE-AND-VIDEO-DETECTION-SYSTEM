# Deepfake Detection System

## Overview

Deepfake Detection System is a production-grade, localhost-first, cloud-deployable AI-assisted platform for detecting suspicious AI-generated and manipulated images or videos. The system is designed for public safety, privacy protection, and digital media verification by combining AI model predictions, forensic signals, metadata analysis, risk scoring, and human review workflows.

The goal of this project is not to claim 100% certainty. Deepfake generation technology evolves quickly, so the system provides evidence-based risk assessment instead of absolute judgments. Uploaded media is analyzed through multiple layers, and the final result is presented as a confidence-based risk level such as likely authentic, uncertain, suspicious, or high-risk.

## Core Philosophy

This project follows a responsible AI-assisted detection approach:

* Never claim perfect accuracy.
* Use risk scores and evidence instead of absolute verdicts.
* Send suspicious and high-risk cases for human review.
* Keep the architecture modular so models, storage, scoring, and frontend components can be replaced independently.
* Protect uploaded media as sensitive user data.
* Maintain auditability through logs, model versioning, and review history.

## Technology Stack

### Frontend

* Next.js
* TypeScript
* Tailwind CSS
* ShadCN UI
* Lucide Icons
* React Hook Form
* Zod
* TanStack Query
* Recharts

### Backend

* Python
* FastAPI
* Pydantic Settings
* SQLAlchemy
* Alembic
* AsyncPG
* JWT Authentication
* Role-Based Access Control

### Database and Storage

* PostgreSQL
* pgvector
* Redis
* MinIO
* Docker Compose

### AI and Media Processing

* PyTorch
* OpenCV
* FFmpeg
* Pillow
* Metadata extraction
* Image analysis pipeline
* Video frame extraction pipeline
* Future support for audio deepfake detection and lip-sync mismatch analysis

## Main Features

### User Features

* Upload image or video files.
* Validate supported media types before processing.
* Store uploaded files securely in object storage.
* Track analysis status.
* View deepfake risk score.
* View confidence level.
* View forensic and AI-based signals.
* View result explanation.
* Download analysis reports in future versions.

### Admin and Reviewer Features

* View suspicious and high-risk cases.
* Inspect media analysis results.
* Review AI predictions and forensic signals.
* Add human review decisions.
* Add reviewer notes.
* Track audit logs.
* Manage model registry in future versions.

### AI Analysis Features

* Image preprocessing.
* Metadata extraction.
* Face detection support.
* AI-generated image detection.
* Face manipulation detection.
* Frequency/artifact analysis.
* Video frame extraction.
* Per-frame analysis for videos.
* Risk-level classification.
* Evidence-based explanation generation.

## Risk Classification

The system uses a score-based risk classification approach:

* 0.00 - 0.30: Likely Authentic
* 0.31 - 0.60: Uncertain
* 0.61 - 0.85: Suspicious
* 0.86 - 1.00: High Risk

High-risk and suspicious cases are designed to be reviewed by humans before any serious conclusion is made.

## System Architecture

The system follows a modular production-style architecture:

1. User uploads an image or video from the frontend.
2. FastAPI backend validates the file.
3. The file is stored in MinIO.
4. Upload metadata is stored in PostgreSQL.
5. An analysis job is created.
6. Redis queue sends the job to the AI worker.
7. The AI worker processes the media.
8. AI predictions and forensic signals are saved in the database.
9. Final score, risk level, and explanation are generated.
10. Frontend displays the result.
11. Suspicious cases are sent to the admin review dashboard.

## Database Modules

The project database includes the following major tables:

* users
* media_uploads
* analysis_jobs
* analysis_results
* model_predictions
* forensic_signals
* video_frames
* review_cases
* review_decisions
* audit_logs
* model_registry
* case_embeddings

The system also uses pgvector for future case similarity search and RAG-based investigation support.

## Local Development Goal

This project is designed to be built and tested completely on localhost using free and open-source tools. The first development target is a full local production-style system with:

* Frontend running on Next.js
* Backend running on FastAPI
* PostgreSQL and pgvector for database and vector support
* Redis for background job queue
* MinIO for local object storage
* Alembic for database migrations
* Docker Compose for local services

## Current Development Roadmap

### Completed / Foundation

* Project folder structure
* Next.js frontend setup
* Docker foundation
* PostgreSQL container
* Redis container
* MinIO container
* pgvector extension
* FastAPI backend skeleton
* Backend health check
* Alembic migration setup
* Initial database extension migration

### Upcoming

* Full core database schema
* Authentication and role system
* File upload API
* MinIO upload service
* Redis queue integration
* AI worker skeleton
* Mock analysis result system
* Image detection pipeline
* Video frame extraction pipeline
* Result UI
* Admin review dashboard
* Security hardening
* Report generation
* Advanced AI modules

## Important Disclaimer

This system is an AI-assisted media analysis tool. It does not provide legal or forensic certainty. The system is designed to support investigation and review by providing risk scores, confidence levels, model signals, and explainable evidence. Final decisions, especially in high-risk or sensitive cases, should involve human review.

## Project Purpose

This project is being developed as a serious AI, full-stack, and machine learning engineering project focused on real-world public safety and privacy challenges. It demonstrates modern web engineering, backend architecture, database design, media processing, AI integration, and responsible AI system design.
