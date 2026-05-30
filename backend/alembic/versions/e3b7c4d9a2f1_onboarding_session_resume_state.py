"""onboarding session resume state

Revision ID: e3b7c4d9a2f1
Revises: d7b0f2a6c914
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "e3b7c4d9a2f1"
down_revision: Union[str, Sequence[str], None] = "d7b0f2a6c914"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_index("uq_onboarding_session_active_user_id", table_name="onboarding_session")
    op.add_column(
        "onboarding_session",
        sa.Column("workflow_state", sa.String(), nullable=False, server_default="ONBOARDING_STARTED"),
    )
    op.add_column(
        "onboarding_session",
        sa.Column("completed_steps", sa.JSON(), nullable=False, server_default="[]"),
    )
    op.add_column("onboarding_session", sa.Column("last_resumed_at", sa.DateTime(), nullable=True))
    op.add_column(
        "onboarding_session",
        sa.Column("resume_count", sa.Integer(), nullable=False, server_default="0"),
    )
    op.create_index(op.f("ix_onboarding_session_workflow_state"), "onboarding_session", ["workflow_state"], unique=False)
    op.create_index(
        "uq_onboarding_session_active_user_id",
        "onboarding_session",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status NOT IN ('completed', 'rejected')"),
    )

    op.execute(
        """
        UPDATE onboarding_session AS s
        SET workflow_state = CASE
            WHEN s.status = 'completed' THEN 'ONBOARDING_COMPLETED'
            WHEN sr.status = 'REJECTED' THEN 'ONBOARDING_REJECTED'
            WHEN cra.edd_required = TRUE AND cc.status = 'OPEN' THEN 'EDD_IN_REVIEW'
            WHEN cra.edd_required = TRUE THEN 'EDD_REQUIRED'
            WHEN sr.status = 'REVIEW_REQUIRED' THEN 'EDD_IN_REVIEW'
            WHEN sr.status = 'SCREENING_IN_PROGRESS' THEN 'SCREENING_IN_PROGRESS'
            WHEN sr.status = 'SCREENING_PENDING' THEN 'SCREENING_PENDING'
            WHEN sr.status = 'APPROVED' THEN 'SCREENING_COMPLETED'
            WHEN sig.id IS NOT NULL THEN 'SIGNATURE_COMPLETED'
            WHEN cip.status = 'IDENTITY_FORM_COMPLETED' THEN 'IDENTITY_FORM_COMPLETED'
            WHEN cip.status IN ('IDENTITY_FORM_DRAFT_SAVED', 'IDENTITY_FORM_IN_PROGRESS') THEN 'IDENTITY_FORM_IN_PROGRESS'
            WHEN cip.status = 'IDENTITY_FORM_PENDING' THEN 'IDENTITY_FORM_PENDING'
            WHEN ocr.id IS NOT NULL THEN 'OCR_COMPLETED'
            WHEN face.id IS NOT NULL THEN 'FACE_VERIFICATION_COMPLETED'
            ELSE 'ONBOARDING_STARTED'
        END,
        completed_steps = CASE
            WHEN s.status = 'completed' THEN '["face_verification", "ocr_extraction", "identity_form", "signature_capture", "screening"]'::json
            WHEN sig.id IS NOT NULL THEN '["face_verification", "ocr_extraction", "identity_form", "signature_capture"]'::json
            WHEN cip.status = 'IDENTITY_FORM_COMPLETED' THEN '["face_verification", "ocr_extraction", "identity_form"]'::json
            WHEN ocr.id IS NOT NULL THEN '["face_verification", "ocr_extraction"]'::json
            WHEN face.id IS NOT NULL THEN '["face_verification"]'::json
            ELSE '[]'::json
        END
        FROM onboarding_session AS base
        LEFT JOIN onboarding_face_verification AS face ON face.session_id = base.id
        LEFT JOIN onboarding_ocr_extraction AS ocr ON ocr.session_id = base.id
        LEFT JOIN customer_identity_profiles AS cip ON cip.session_id = base.id
        LEFT JOIN onboarding_signature_capture AS sig ON sig.session_id = base.id
        LEFT JOIN LATERAL (
            SELECT *
            FROM screening_request AS sr_inner
            WHERE sr_inner.session_id = base.id
            ORDER BY sr_inner.created_at DESC, sr_inner.id DESC
            LIMIT 1
        ) AS sr ON TRUE
        LEFT JOIN LATERAL (
            SELECT *
            FROM customer_risk_assessments AS cra_inner
            WHERE cra_inner.session_id = base.id
            ORDER BY cra_inner.calculated_at DESC, cra_inner.id DESC
            LIMIT 1
        ) AS cra ON TRUE
        LEFT JOIN compliance_case AS cc ON cc.screening_request_id = sr.id
        WHERE s.id = base.id
        """
    )

    op.alter_column("onboarding_session", "workflow_state", server_default=None)
    op.alter_column("onboarding_session", "completed_steps", server_default=None)
    op.alter_column("onboarding_session", "resume_count", server_default=None)


def downgrade() -> None:
    op.drop_index("uq_onboarding_session_active_user_id", table_name="onboarding_session")
    op.drop_index(op.f("ix_onboarding_session_workflow_state"), table_name="onboarding_session")
    op.drop_column("onboarding_session", "resume_count")
    op.drop_column("onboarding_session", "last_resumed_at")
    op.drop_column("onboarding_session", "completed_steps")
    op.drop_column("onboarding_session", "workflow_state")
    op.create_index(
        "uq_onboarding_session_active_user_id",
        "onboarding_session",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'completed'"),
    )
