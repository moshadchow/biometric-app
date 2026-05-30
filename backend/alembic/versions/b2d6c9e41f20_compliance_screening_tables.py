"""compliance screening tables

Revision ID: b2d6c9e41f20
Revises: f8c4d2a1b9e7
Create Date: 2026-05-29 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "b2d6c9e41f20"
down_revision: Union[str, Sequence[str], None] = "f8c4d2a1b9e7"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "onboarding_session",
        sa.Column("activation_status", sa.String(), nullable=False, server_default="blocked"),
    )
    op.create_index(
        op.f("ix_onboarding_session_activation_status"),
        "onboarding_session",
        ["activation_status"],
        unique=False,
    )

    op.create_table(
        "screening_request",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("trigger_source", sa.String(), nullable=False),
        sa.Column("workflow_id", sa.String(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["onboarding_session.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_screening_request_session_id"), "screening_request", ["session_id"], unique=False)
    op.create_index(op.f("ix_screening_request_user_id"), "screening_request", ["user_id"], unique=False)
    op.create_index(op.f("ix_screening_request_status"), "screening_request", ["status"], unique=False)
    op.create_index(op.f("ix_screening_request_workflow_id"), "screening_request", ["workflow_id"], unique=False)

    op.create_table(
        "screening_job",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("screening_request_id", sa.Integer(), nullable=False),
        sa.Column("job_name", sa.String(), nullable=False),
        sa.Column("celery_task_id", sa.String(), nullable=True),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("retry_count", sa.Integer(), nullable=False),
        sa.Column("last_error", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["screening_request_id"], ["screening_request.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_screening_job_screening_request_id"), "screening_job", ["screening_request_id"], unique=False)
    op.create_index(op.f("ix_screening_job_job_name"), "screening_job", ["job_name"], unique=False)
    op.create_index(op.f("ix_screening_job_celery_task_id"), "screening_job", ["celery_task_id"], unique=False)
    op.create_index(op.f("ix_screening_job_status"), "screening_job", ["status"], unique=False)

    op.create_table(
        "screening_result",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("screening_request_id", sa.Integer(), nullable=False),
        sa.Column("screening_type", sa.String(), nullable=False),
        sa.Column("provider_name", sa.String(), nullable=False),
        sa.Column("list_name", sa.String(), nullable=True),
        sa.Column("outcome", sa.String(), nullable=False),
        sa.Column("confidence_score", sa.Float(), nullable=False),
        sa.Column("matched_fields", sa.JSON(), nullable=False),
        sa.Column("risk_factors", sa.JSON(), nullable=False),
        sa.Column("evidence_summary", sa.String(), nullable=True),
        sa.Column("raw_payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["screening_request_id"], ["screening_request.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_screening_result_screening_request_id"), "screening_result", ["screening_request_id"], unique=False)
    op.create_index(op.f("ix_screening_result_screening_type"), "screening_result", ["screening_type"], unique=False)
    op.create_index(op.f("ix_screening_result_outcome"), "screening_result", ["outcome"], unique=False)

    op.create_table(
        "risk_assessment",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("screening_request_id", sa.Integer(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("risk_category", sa.String(), nullable=False),
        sa.Column("factors", sa.JSON(), nullable=False),
        sa.Column("rules_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["screening_request_id"], ["screening_request.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("screening_request_id"),
    )
    op.create_index(op.f("ix_risk_assessment_risk_category"), "risk_assessment", ["risk_category"], unique=False)

    op.create_table(
        "compliance_case",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("screening_request_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("queue_name", sa.String(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("opened_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolution_note", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reviewer_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["screening_request_id"], ["screening_request.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("screening_request_id"),
    )
    op.create_index(op.f("ix_compliance_case_status"), "compliance_case", ["status"], unique=False)

    op.create_table(
        "screening_decision",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("screening_request_id", sa.Integer(), nullable=False),
        sa.Column("decision", sa.String(), nullable=False),
        sa.Column("decision_source", sa.String(), nullable=False),
        sa.Column("reviewer_id", sa.Integer(), nullable=True),
        sa.Column("previous_decision", sa.String(), nullable=True),
        sa.Column("reason", sa.String(), nullable=True),
        sa.Column("notes", sa.String(), nullable=True),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["reviewer_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["screening_request_id"], ["screening_request.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("screening_request_id"),
    )
    op.create_index(op.f("ix_screening_decision_decision"), "screening_decision", ["decision"], unique=False)
    op.create_index(op.f("ix_screening_decision_decision_source"), "screening_decision", ["decision_source"], unique=False)

    op.create_table(
        "audit_log",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("screening_request_id", sa.Integer(), nullable=True),
        sa.Column("session_id", sa.Integer(), nullable=True),
        sa.Column("actor_user_id", sa.Integer(), nullable=True),
        sa.Column("event_type", sa.String(), nullable=False),
        sa.Column("event_status", sa.String(), nullable=False),
        sa.Column("message", sa.String(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["actor_user_id"], ["user.id"]),
        sa.ForeignKeyConstraint(["screening_request_id"], ["screening_request.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["onboarding_session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_audit_log_screening_request_id"), "audit_log", ["screening_request_id"], unique=False)
    op.create_index(op.f("ix_audit_log_session_id"), "audit_log", ["session_id"], unique=False)
    op.create_index(op.f("ix_audit_log_actor_user_id"), "audit_log", ["actor_user_id"], unique=False)
    op.create_index(op.f("ix_audit_log_event_type"), "audit_log", ["event_type"], unique=False)
    op.create_index(op.f("ix_audit_log_event_status"), "audit_log", ["event_status"], unique=False)

    op.alter_column("onboarding_session", "activation_status", server_default=None)


def downgrade() -> None:
    op.drop_index(op.f("ix_audit_log_event_status"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_event_type"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_actor_user_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_session_id"), table_name="audit_log")
    op.drop_index(op.f("ix_audit_log_screening_request_id"), table_name="audit_log")
    op.drop_table("audit_log")

    op.drop_index(op.f("ix_screening_decision_decision_source"), table_name="screening_decision")
    op.drop_index(op.f("ix_screening_decision_decision"), table_name="screening_decision")
    op.drop_table("screening_decision")

    op.drop_index(op.f("ix_compliance_case_status"), table_name="compliance_case")
    op.drop_table("compliance_case")

    op.drop_index(op.f("ix_risk_assessment_risk_category"), table_name="risk_assessment")
    op.drop_table("risk_assessment")

    op.drop_index(op.f("ix_screening_result_outcome"), table_name="screening_result")
    op.drop_index(op.f("ix_screening_result_screening_type"), table_name="screening_result")
    op.drop_index(op.f("ix_screening_result_screening_request_id"), table_name="screening_result")
    op.drop_table("screening_result")

    op.drop_index(op.f("ix_screening_job_status"), table_name="screening_job")
    op.drop_index(op.f("ix_screening_job_celery_task_id"), table_name="screening_job")
    op.drop_index(op.f("ix_screening_job_job_name"), table_name="screening_job")
    op.drop_index(op.f("ix_screening_job_screening_request_id"), table_name="screening_job")
    op.drop_table("screening_job")

    op.drop_index(op.f("ix_screening_request_workflow_id"), table_name="screening_request")
    op.drop_index(op.f("ix_screening_request_status"), table_name="screening_request")
    op.drop_index(op.f("ix_screening_request_user_id"), table_name="screening_request")
    op.drop_index(op.f("ix_screening_request_session_id"), table_name="screening_request")
    op.drop_table("screening_request")

    op.drop_index(op.f("ix_onboarding_session_activation_status"), table_name="onboarding_session")
    op.drop_column("onboarding_session", "activation_status")
