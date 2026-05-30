"""risk assessment engine tables

Revision ID: d7b0f2a6c914
Revises: c4a2f6e8d901
Create Date: 2026-05-30 00:00:00.000000

"""
from datetime import datetime
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d7b0f2a6c914"
down_revision: Union[str, Sequence[str], None] = "c4a2f6e8d901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    now = datetime.utcnow()
    op.create_table(
        "risk_rule_versions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("version", sa.String(), nullable=False),
        sa.Column("effective_date", sa.DateTime(timezone=True), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("thresholds", sa.JSON(), nullable=False),
        sa.Column("rules_snapshot", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("version"),
    )
    op.create_index(op.f("ix_risk_rule_versions_version"), "risk_rule_versions", ["version"], unique=True)
    op.create_index(op.f("ix_risk_rule_versions_status"), "risk_rule_versions", ["status"], unique=False)

    op.create_table(
        "risk_business_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("category", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("category"),
    )
    op.create_index(op.f("ix_risk_business_categories_category"), "risk_business_categories", ["category"], unique=True)
    op.create_index(op.f("ix_risk_business_categories_status"), "risk_business_categories", ["status"], unique=False)

    op.create_table(
        "risk_profession_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profession", sa.String(), nullable=False),
        sa.Column("score", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profession"),
    )
    op.create_index(op.f("ix_risk_profession_categories_profession"), "risk_profession_categories", ["profession"], unique=True)
    op.create_index(op.f("ix_risk_profession_categories_status"), "risk_profession_categories", ["status"], unique=False)

    op.create_table(
        "customer_risk_assessments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("screening_request_id", sa.Integer(), nullable=True),
        sa.Column("assessment_type", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("total_score", sa.Integer(), nullable=False),
        sa.Column("risk_category", sa.String(), nullable=False),
        sa.Column("rule_version", sa.String(), nullable=False),
        sa.Column("edd_required", sa.Boolean(), nullable=False),
        sa.Column("edd_status", sa.String(), nullable=True),
        sa.Column("edd_reasons", sa.JSON(), nullable=False),
        sa.Column("rules_snapshot", sa.JSON(), nullable=False),
        sa.Column("calculated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["screening_request_id"], ["screening_request.id"]),
        sa.ForeignKeyConstraint(["session_id"], ["onboarding_session.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customer_risk_assessments_session_id"), "customer_risk_assessments", ["session_id"], unique=False)
    op.create_index(op.f("ix_customer_risk_assessments_screening_request_id"), "customer_risk_assessments", ["screening_request_id"], unique=False)
    op.create_index(op.f("ix_customer_risk_assessments_assessment_type"), "customer_risk_assessments", ["assessment_type"], unique=False)
    op.create_index(op.f("ix_customer_risk_assessments_status"), "customer_risk_assessments", ["status"], unique=False)
    op.create_index(op.f("ix_customer_risk_assessments_risk_category"), "customer_risk_assessments", ["risk_category"], unique=False)
    op.create_index(op.f("ix_customer_risk_assessments_rule_version"), "customer_risk_assessments", ["rule_version"], unique=False)
    op.create_index(op.f("ix_customer_risk_assessments_edd_required"), "customer_risk_assessments", ["edd_required"], unique=False)
    op.create_index(op.f("ix_customer_risk_assessments_edd_status"), "customer_risk_assessments", ["edd_status"], unique=False)

    op.create_table(
        "customer_risk_factor_scores",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("assessment_id", sa.Integer(), nullable=False),
        sa.Column("factor_name", sa.String(), nullable=False),
        sa.Column("factor_score", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(), nullable=False),
        sa.Column("source_value", sa.JSON(), nullable=False),
        sa.Column("rule_version", sa.String(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["assessment_id"], ["customer_risk_assessments.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customer_risk_factor_scores_assessment_id"), "customer_risk_factor_scores", ["assessment_id"], unique=False)
    op.create_index(op.f("ix_customer_risk_factor_scores_factor_name"), "customer_risk_factor_scores", ["factor_name"], unique=False)
    op.create_index(op.f("ix_customer_risk_factor_scores_source"), "customer_risk_factor_scores", ["source"], unique=False)
    op.create_index(op.f("ix_customer_risk_factor_scores_rule_version"), "customer_risk_factor_scores", ["rule_version"], unique=False)

    op.bulk_insert(
        sa.table(
            "risk_rule_versions",
            sa.column("version", sa.String),
            sa.column("effective_date", sa.DateTime),
            sa.column("status", sa.String),
            sa.column("thresholds", sa.JSON),
            sa.column("rules_snapshot", sa.JSON),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        ),
        [
            {
                "version": "v1",
                "effective_date": now,
                "status": "ACTIVE",
                "thresholds": {"low_max": 9, "medium_max": 14},
                "rules_snapshot": {"source": "03-risk-assessment-engine", "unknown_matrix_fallback_score": 3},
                "created_at": now,
                "updated_at": now,
            }
        ],
    )
    op.bulk_insert(
        sa.table(
            "risk_business_categories",
            sa.column("category", sa.String),
            sa.column("score", sa.Integer),
            sa.column("status", sa.String),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        ),
        [
            {"category": "default", "score": 3, "status": "ACTIVE", "created_at": now, "updated_at": now},
            {"category": "individual_investor", "score": 2, "status": "ACTIVE", "created_at": now, "updated_at": now},
        ],
    )
    op.bulk_insert(
        sa.table(
            "risk_profession_categories",
            sa.column("profession", sa.String),
            sa.column("score", sa.Integer),
            sa.column("status", sa.String),
            sa.column("created_at", sa.DateTime),
            sa.column("updated_at", sa.DateTime),
        ),
        [
            {"profession": "default", "score": 3, "status": "ACTIVE", "created_at": now, "updated_at": now},
            {"profession": "student", "score": 1, "status": "ACTIVE", "created_at": now, "updated_at": now},
            {"profession": "service", "score": 2, "status": "ACTIVE", "created_at": now, "updated_at": now},
            {"profession": "business", "score": 3, "status": "ACTIVE", "created_at": now, "updated_at": now},
        ],
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_customer_risk_factor_scores_rule_version"), table_name="customer_risk_factor_scores")
    op.drop_index(op.f("ix_customer_risk_factor_scores_source"), table_name="customer_risk_factor_scores")
    op.drop_index(op.f("ix_customer_risk_factor_scores_factor_name"), table_name="customer_risk_factor_scores")
    op.drop_index(op.f("ix_customer_risk_factor_scores_assessment_id"), table_name="customer_risk_factor_scores")
    op.drop_table("customer_risk_factor_scores")
    op.drop_index(op.f("ix_customer_risk_assessments_edd_status"), table_name="customer_risk_assessments")
    op.drop_index(op.f("ix_customer_risk_assessments_edd_required"), table_name="customer_risk_assessments")
    op.drop_index(op.f("ix_customer_risk_assessments_rule_version"), table_name="customer_risk_assessments")
    op.drop_index(op.f("ix_customer_risk_assessments_risk_category"), table_name="customer_risk_assessments")
    op.drop_index(op.f("ix_customer_risk_assessments_status"), table_name="customer_risk_assessments")
    op.drop_index(op.f("ix_customer_risk_assessments_assessment_type"), table_name="customer_risk_assessments")
    op.drop_index(op.f("ix_customer_risk_assessments_screening_request_id"), table_name="customer_risk_assessments")
    op.drop_index(op.f("ix_customer_risk_assessments_session_id"), table_name="customer_risk_assessments")
    op.drop_table("customer_risk_assessments")
    op.drop_index(op.f("ix_risk_profession_categories_status"), table_name="risk_profession_categories")
    op.drop_index(op.f("ix_risk_profession_categories_profession"), table_name="risk_profession_categories")
    op.drop_table("risk_profession_categories")
    op.drop_index(op.f("ix_risk_business_categories_status"), table_name="risk_business_categories")
    op.drop_index(op.f("ix_risk_business_categories_category"), table_name="risk_business_categories")
    op.drop_table("risk_business_categories")
    op.drop_index(op.f("ix_risk_rule_versions_status"), table_name="risk_rule_versions")
    op.drop_index(op.f("ix_risk_rule_versions_version"), table_name="risk_rule_versions")
    op.drop_table("risk_rule_versions")
