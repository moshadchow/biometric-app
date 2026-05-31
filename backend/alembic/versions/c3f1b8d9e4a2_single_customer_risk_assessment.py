"""collapse customer risk assessments to one row per session

Revision ID: c3f1b8d9e4a2
Revises: b7e3c12a9f04
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c3f1b8d9e4a2"
down_revision: Union[str, Sequence[str], None] = "b7e3c12a9f04"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                session_id,
                ROW_NUMBER() OVER (
                    PARTITION BY session_id
                    ORDER BY
                        CASE WHEN assessment_type = 'final' THEN 0 ELSE 1 END,
                        calculated_at DESC,
                        id DESC
                ) AS rn
            FROM customer_risk_assessments
        ),
        doomed AS (
            SELECT id FROM ranked WHERE rn > 1
        )
        DELETE FROM customer_risk_factor_scores
        WHERE assessment_id IN (SELECT id FROM doomed)
        """
    )
    op.execute(
        """
        WITH ranked AS (
            SELECT
                id,
                session_id,
                ROW_NUMBER() OVER (
                    PARTITION BY session_id
                    ORDER BY
                        CASE WHEN assessment_type = 'final' THEN 0 ELSE 1 END,
                        calculated_at DESC,
                        id DESC
                ) AS rn
            FROM customer_risk_assessments
        )
        DELETE FROM customer_risk_assessments
        WHERE id IN (SELECT id FROM ranked WHERE rn > 1)
        """
    )
    op.drop_index(op.f("ix_customer_risk_assessments_session_id"), table_name="customer_risk_assessments")
    op.create_index(
        op.f("ix_customer_risk_assessments_session_id"),
        "customer_risk_assessments",
        ["session_id"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_customer_risk_assessments_session_id"), table_name="customer_risk_assessments")
    op.create_index(
        op.f("ix_customer_risk_assessments_session_id"),
        "customer_risk_assessments",
        ["session_id"],
        unique=False,
    )
