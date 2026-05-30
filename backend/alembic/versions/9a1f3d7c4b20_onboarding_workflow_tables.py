"""onboarding workflow tables

Revision ID: 9a1f3d7c4b20
Revises: ab7a905e0ded
Create Date: 2026-05-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "9a1f3d7c4b20"
down_revision: Union[str, Sequence[str], None] = "ab7a905e0ded"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "onboarding_session",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("current_step", sa.String(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_onboarding_session_user_id"), "onboarding_session", ["user_id"], unique=False)
    op.create_index(op.f("ix_onboarding_session_status"), "onboarding_session", ["status"], unique=False)
    op.create_index(op.f("ix_onboarding_session_current_step"), "onboarding_session", ["current_step"], unique=False)

    op.create_table(
        "onboarding_face_verification",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("result", sa.String(), nullable=False),
        sa.Column("distance", sa.Float(), nullable=False),
        sa.Column("threshold", sa.Float(), nullable=False),
        sa.Column("error_message", sa.String(), nullable=True),
        sa.Column("captured_file_path", sa.String(), nullable=False),
        sa.Column("reference_file_path", sa.String(), nullable=True),
        sa.Column("captured_file_name", sa.String(), nullable=True),
        sa.Column("reference_file_name", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["onboarding_session.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )

    op.create_table(
        "onboarding_ocr_extraction",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("front_file_path", sa.String(), nullable=False),
        sa.Column("back_file_path", sa.String(), nullable=True),
        sa.Column("front_file_name", sa.String(), nullable=True),
        sa.Column("back_file_name", sa.String(), nullable=True),
        sa.Column("front_text", sa.String(), nullable=False),
        sa.Column("back_text", sa.String(), nullable=True),
        sa.Column("merged_text", sa.String(), nullable=False),
        sa.Column("fields", sa.JSON(), nullable=False),
        sa.Column("front_detection", sa.JSON(), nullable=False),
        sa.Column("back_detection", sa.JSON(), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["onboarding_session.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )

    op.create_table(
        "onboarding_signature_capture",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("signature_method", sa.String(), nullable=False),
        sa.Column("verification_method", sa.String(), nullable=False),
        sa.Column("account_risk", sa.String(), nullable=False),
        sa.Column("signer_name", sa.String(), nullable=True),
        sa.Column("signature_file_path", sa.String(), nullable=True),
        sa.Column("signature_file_name", sa.String(), nullable=True),
        sa.Column("signature_record", sa.JSON(), nullable=False),
        sa.Column("audit_log", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("integrity_hash", sa.String(), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["onboarding_session.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )


def downgrade() -> None:
    op.drop_table("onboarding_signature_capture")
    op.drop_table("onboarding_ocr_extraction")
    op.drop_table("onboarding_face_verification")
    op.drop_index(op.f("ix_onboarding_session_current_step"), table_name="onboarding_session")
    op.drop_index(op.f("ix_onboarding_session_status"), table_name="onboarding_session")
    op.drop_index(op.f("ix_onboarding_session_user_id"), table_name="onboarding_session")
    op.drop_table("onboarding_session")
