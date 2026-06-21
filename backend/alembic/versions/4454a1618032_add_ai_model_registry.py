"""add ai model registry

Revision ID: 4454a1618032
Revises: 0002_core_schema
Create Date: 2026-06-22
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = "4454a1618032"
down_revision: Union[str, None] = "0002_core_schema"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

    op.create_table(
        "ai_model_registry",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("model_type", sa.Text(), nullable=False),
        sa.Column("input_type", sa.Text(), nullable=False),
        sa.Column("checkpoint_path", sa.Text(), nullable=True),
        sa.Column("runtime_provider", sa.Text(), nullable=False),
        sa.Column("device", sa.Text(), nullable=False, server_default="cpu"),
        sa.Column("dataset_used", sa.Text(), nullable=True),
        sa.Column("is_trainable", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("is_enabled", sa.Boolean(), nullable=False, server_default=sa.text("true")),
        sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column(
            "training_metrics",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "evaluation_metrics",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "extra_metadata",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.UniqueConstraint(
            "model_name",
            "model_version",
            name="uq_ai_model_registry_name_version",
        ),
    )

    op.create_index(
        "ix_ai_model_registry_model_name",
        "ai_model_registry",
        ["model_name"],
    )

    op.create_index(
        "ix_ai_model_registry_model_type",
        "ai_model_registry",
        ["model_type"],
    )

    op.create_index(
        "ix_ai_model_registry_is_active",
        "ai_model_registry",
        ["is_active"],
    )

    op.create_table(
        "analysis_model_evidence",
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "analysis_result_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("analysis_results.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("model_name", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("model_type", sa.Text(), nullable=False),
        sa.Column("input_type", sa.Text(), nullable=False),
        sa.Column("score", sa.Float(), nullable=False),
        sa.Column("confidence", sa.Float(), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=True),
        sa.Column("device", sa.Text(), nullable=False, server_default="cpu"),
        sa.Column(
            "details",
            postgresql.JSONB(),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("NOW()")),
        sa.CheckConstraint("score >= 0 AND score <= 1", name="ck_analysis_model_evidence_score_range"),
        sa.CheckConstraint("confidence >= 0 AND confidence <= 1", name="ck_analysis_model_evidence_confidence_range"),
    )

    op.create_index(
        "ix_analysis_model_evidence_result_id",
        "analysis_model_evidence",
        ["analysis_result_id"],
    )

    op.create_index(
        "ix_analysis_model_evidence_model_name",
        "analysis_model_evidence",
        ["model_name"],
    )


def downgrade() -> None:
    op.drop_index("ix_analysis_model_evidence_model_name", table_name="analysis_model_evidence")
    op.drop_index("ix_analysis_model_evidence_result_id", table_name="analysis_model_evidence")
    op.drop_table("analysis_model_evidence")

    op.drop_index("ix_ai_model_registry_is_active", table_name="ai_model_registry")
    op.drop_index("ix_ai_model_registry_model_type", table_name="ai_model_registry")
    op.drop_index("ix_ai_model_registry_model_name", table_name="ai_model_registry")
    op.drop_table("ai_model_registry")