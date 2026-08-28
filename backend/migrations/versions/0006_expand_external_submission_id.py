"""Expand external submission ID length for multi-provider ingestion."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa


revision: str = "0006_external_submission_id_255"
down_revision: str | Sequence[str] | None = "0005_neetcode_integration"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.alter_column(
            "external_submission_id",
            existing_type=sa.String(length=64),
            type_=sa.String(length=255),
            existing_nullable=False,
        )


def downgrade() -> None:
    with op.batch_alter_table("submissions") as batch_op:
        batch_op.alter_column(
            "external_submission_id",
            existing_type=sa.String(length=255),
            type_=sa.String(length=64),
            existing_nullable=False,
        )
