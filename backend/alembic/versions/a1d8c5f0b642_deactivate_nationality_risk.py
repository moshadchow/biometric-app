"""deactivate nationality risk factor

Revision ID: a1d8c5f0b642
Revises: f2a9d4c8b731
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "a1d8c5f0b642"
down_revision: Union[str, Sequence[str], None] = "f2a9d4c8b731"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute(
        """
        UPDATE risk_factor_definitions
        SET is_active = FALSE,
            updated_at = NOW()
        WHERE factor_code = 'nationality_risk'
        """
    )


def downgrade() -> None:
    op.execute(
        """
        UPDATE risk_factor_definitions
        SET is_active = TRUE,
            updated_at = NOW()
        WHERE factor_code = 'nationality_risk'
        """
    )
