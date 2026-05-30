"""enforce one active onboarding session per user

Revision ID: f8c4d2a1b9e7
Revises: 9a1f3d7c4b20
Create Date: 2026-05-26 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = "f8c4d2a1b9e7"
down_revision: Union[str, Sequence[str], None] = "9a1f3d7c4b20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        WITH ranked_sessions AS (
            SELECT
                id,
                ROW_NUMBER() OVER (
                    PARTITION BY user_id
                    ORDER BY updated_at DESC, id DESC
                ) AS rn
            FROM onboarding_session
            WHERE status <> 'completed'
        )
        UPDATE onboarding_session AS s
        SET
            status = 'completed',
            current_step = 'complete',
            completed_at = COALESCE(s.completed_at, s.updated_at, NOW()),
            updated_at = NOW()
        FROM ranked_sessions AS r
        WHERE s.id = r.id
          AND r.rn > 1
        """
    )

    op.create_index(
        "uq_onboarding_session_active_user_id",
        "onboarding_session",
        ["user_id"],
        unique=True,
        postgresql_where=sa.text("status <> 'completed'"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_onboarding_session_active_user_id",
        table_name="onboarding_session",
    )
