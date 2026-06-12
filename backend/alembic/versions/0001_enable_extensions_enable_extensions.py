"""enable extensions

Revision ID: 0001_enable_extensions
Revises:
Create Date: 2026-06-13
"""

from typing import Sequence, Union

from alembic import op


revision: str = "0001_enable_extensions"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")
    op.execute("CREATE EXTENSION IF NOT EXISTS vector;")


def downgrade() -> None:
    # We intentionally do not drop extensions on downgrade because
    # other tables or systems may depend on them.
    pass