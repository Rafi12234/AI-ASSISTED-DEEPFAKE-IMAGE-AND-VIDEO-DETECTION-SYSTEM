"""create core schema

Revision ID: 0002_core_schema
Revises: 0001_enable_extensions
Create Date: 2026-06-13
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0002_core_schema"
down_revision: Union[str, None] = "0001_enable_extensions"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        CREATE TABLE IF NOT EXISTS users (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            role TEXT NOT NULL DEFAULT 'user'
                CHECK (role IN ('user', 'reviewer', 'admin')),
            is_active BOOLEAN NOT NULL DEFAULT true,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_users_email ON users (email);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS media_uploads (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE SET NULL,
            original_filename TEXT NOT NULL,
            stored_path TEXT NOT NULL,
            file_type TEXT NOT NULL CHECK (file_type IN ('image', 'video')),
            mime_type TEXT NOT NULL,
            file_size_bytes BIGINT NOT NULL CHECK (file_size_bytes > 0),
            duration_seconds DOUBLE PRECISION,
            resolution TEXT,
            upload_status TEXT NOT NULL DEFAULT 'pending'
                CHECK (upload_status IN ('pending', 'stored', 'failed', 'deleted')),
            is_deleted BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_media_uploads_user_id ON media_uploads (user_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_media_uploads_file_type ON media_uploads (file_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_media_uploads_created_at ON media_uploads (created_at);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_jobs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            media_upload_id UUID NOT NULL REFERENCES media_uploads(id) ON DELETE CASCADE,
            status TEXT NOT NULL DEFAULT 'queued'
                CHECK (status IN ('queued', 'processing', 'completed', 'failed', 'dead_letter')),
            worker_id TEXT,
            queued_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            started_at TIMESTAMPTZ,
            completed_at TIMESTAMPTZ,
            retry_count INT NOT NULL DEFAULT 0 CHECK (retry_count >= 0),
            error_message TEXT,
            job_metadata JSONB NOT NULL DEFAULT '{}'::jsonb
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_analysis_jobs_media_upload_id ON analysis_jobs (media_upload_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_analysis_jobs_status ON analysis_jobs (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_analysis_jobs_queued_at ON analysis_jobs (queued_at);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS analysis_results (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            media_upload_id UUID NOT NULL REFERENCES media_uploads(id) ON DELETE CASCADE,
            analysis_job_id UUID REFERENCES analysis_jobs(id) ON DELETE SET NULL,
            final_score DOUBLE PRECISION NOT NULL CHECK (final_score >= 0 AND final_score <= 1),
            risk_level TEXT NOT NULL
                CHECK (risk_level IN ('likely_authentic', 'uncertain', 'suspicious', 'high_risk')),
            confidence DOUBLE PRECISION NOT NULL CHECK (confidence >= 0 AND confidence <= 1),
            explanation TEXT NOT NULL,
            signals_summary JSONB NOT NULL,
            model_versions JSONB NOT NULL,
            processing_time_ms INT CHECK (processing_time_ms IS NULL OR processing_time_ms >= 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_analysis_results_media_upload_id ON analysis_results (media_upload_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_analysis_results_analysis_job_id ON analysis_results (analysis_job_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_analysis_results_risk_level ON analysis_results (risk_level);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_analysis_results_final_score ON analysis_results (final_score);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS model_predictions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            analysis_result_id UUID NOT NULL REFERENCES analysis_results(id) ON DELETE CASCADE,
            model_name TEXT NOT NULL,
            model_version TEXT NOT NULL,
            raw_score DOUBLE PRECISION NOT NULL CHECK (raw_score >= 0 AND raw_score <= 1),
            calibrated_score DOUBLE PRECISION NOT NULL CHECK (calibrated_score >= 0 AND calibrated_score <= 1),
            prediction_label TEXT,
            target_region TEXT,
            inference_time_ms INT CHECK (inference_time_ms IS NULL OR inference_time_ms >= 0),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_model_predictions_analysis_result_id ON model_predictions (analysis_result_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_predictions_model_name ON model_predictions (model_name);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS forensic_signals (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            analysis_result_id UUID NOT NULL REFERENCES analysis_results(id) ON DELETE CASCADE,
            signal_type TEXT NOT NULL,
            signal_value TEXT,
            risk_contribution DOUBLE PRECISION
                CHECK (risk_contribution IS NULL OR (risk_contribution >= 0 AND risk_contribution <= 1)),
            details JSONB NOT NULL DEFAULT '{}'::jsonb,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_forensic_signals_analysis_result_id ON forensic_signals (analysis_result_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_forensic_signals_signal_type ON forensic_signals (signal_type);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS video_frames (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            media_upload_id UUID NOT NULL REFERENCES media_uploads(id) ON DELETE CASCADE,
            analysis_result_id UUID REFERENCES analysis_results(id) ON DELETE CASCADE,
            frame_index INT NOT NULL CHECK (frame_index >= 0),
            timestamp_seconds DOUBLE PRECISION NOT NULL CHECK (timestamp_seconds >= 0),
            stored_path TEXT,
            face_detected BOOLEAN NOT NULL DEFAULT false,
            frame_score DOUBLE PRECISION CHECK (frame_score IS NULL OR (frame_score >= 0 AND frame_score <= 1)),
            is_suspicious BOOLEAN NOT NULL DEFAULT false,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_video_frames_media_upload_id ON video_frames (media_upload_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_video_frames_analysis_result_id ON video_frames (analysis_result_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_video_frames_timestamp_seconds ON video_frames (timestamp_seconds);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_video_frames_is_suspicious ON video_frames (is_suspicious);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS review_cases (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            analysis_result_id UUID NOT NULL REFERENCES analysis_results(id) ON DELETE CASCADE,
            media_upload_id UUID NOT NULL REFERENCES media_uploads(id) ON DELETE CASCADE,
            assigned_to UUID REFERENCES users(id) ON DELETE SET NULL,
            status TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'in_review', 'resolved')),
            priority TEXT NOT NULL DEFAULT 'normal'
                CHECK (priority IN ('low', 'normal', 'high')),
            triggered_by TEXT NOT NULL
                CHECK (triggered_by IN ('auto_score', 'user_report', 'admin')),
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_review_cases_analysis_result_id ON review_cases (analysis_result_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_review_cases_media_upload_id ON review_cases (media_upload_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_review_cases_status ON review_cases (status);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_review_cases_priority ON review_cases (priority);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS review_decisions (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            review_case_id UUID NOT NULL REFERENCES review_cases(id) ON DELETE CASCADE,
            reviewer_id UUID REFERENCES users(id) ON DELETE SET NULL,
            decision TEXT NOT NULL
                CHECK (decision IN ('confirmed_fake', 'confirmed_authentic', 'uncertain', 'insufficient_data')),
            reviewer_notes TEXT,
            override_score DOUBLE PRECISION CHECK (override_score IS NULL OR (override_score >= 0 AND override_score <= 1)),
            decided_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_review_decisions_review_case_id ON review_decisions (review_case_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_review_decisions_reviewer_id ON review_decisions (reviewer_id);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS audit_logs (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            actor_id UUID REFERENCES users(id) ON DELETE SET NULL,
            action TEXT NOT NULL,
            resource_type TEXT,
            resource_id UUID,
            details JSONB NOT NULL DEFAULT '{}'::jsonb,
            ip_address TEXT,
            user_agent TEXT,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_actor_id ON audit_logs (actor_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_action ON audit_logs (action);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_resource_id ON audit_logs (resource_id);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_audit_logs_created_at ON audit_logs (created_at);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS model_registry (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            model_name TEXT NOT NULL,
            model_version TEXT NOT NULL,
            model_type TEXT NOT NULL,
            architecture TEXT,
            training_dataset TEXT,
            weights_path TEXT,
            is_active BOOLEAN NOT NULL DEFAULT true,
            performance_metrics JSONB,
            registered_at TIMESTAMPTZ NOT NULL DEFAULT now(),
            registered_by UUID REFERENCES users(id) ON DELETE SET NULL,
            UNIQUE (model_name, model_version)
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_model_registry_model_name ON model_registry (model_name);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_registry_model_type ON model_registry (model_type);")
    op.execute("CREATE INDEX IF NOT EXISTS ix_model_registry_is_active ON model_registry (is_active);")

    op.execute(
        """
        CREATE TABLE IF NOT EXISTS case_embeddings (
            id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            analysis_result_id UUID NOT NULL REFERENCES analysis_results(id) ON DELETE CASCADE,
            embedding vector(512) NOT NULL,
            created_at TIMESTAMPTZ NOT NULL DEFAULT now()
        );
        """
    )

    op.execute("CREATE INDEX IF NOT EXISTS ix_case_embeddings_analysis_result_id ON case_embeddings (analysis_result_id);")


def downgrade() -> None:
    op.execute("DROP TABLE IF EXISTS case_embeddings CASCADE;")
    op.execute("DROP TABLE IF EXISTS model_registry CASCADE;")
    op.execute("DROP TABLE IF EXISTS audit_logs CASCADE;")
    op.execute("DROP TABLE IF EXISTS review_decisions CASCADE;")
    op.execute("DROP TABLE IF EXISTS review_cases CASCADE;")
    op.execute("DROP TABLE IF EXISTS video_frames CASCADE;")
    op.execute("DROP TABLE IF EXISTS forensic_signals CASCADE;")
    op.execute("DROP TABLE IF EXISTS model_predictions CASCADE;")
    op.execute("DROP TABLE IF EXISTS analysis_results CASCADE;")
    op.execute("DROP TABLE IF EXISTS analysis_jobs CASCADE;")
    op.execute("DROP TABLE IF EXISTS media_uploads CASCADE;")
    op.execute("DROP TABLE IF EXISTS users CASCADE;")