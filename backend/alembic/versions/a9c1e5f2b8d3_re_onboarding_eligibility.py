"""re onboarding eligibility

Revision ID: a9c1e5f2b8d3
Revises: e3b7c4d9a2f1
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "a9c1e5f2b8d3"
down_revision: Union[str, Sequence[str], None] = "e3b7c4d9a2f1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("user", sa.Column("re_onboarding_allowed", sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column("user", sa.Column("re_onboarding_allowed_at", sa.DateTime(), nullable=True))
    op.add_column("user", sa.Column("re_onboarding_allowed_by", sa.Integer(), nullable=True))
    op.add_column("user", sa.Column("re_onboarding_reason", sa.String(), nullable=True))
    op.create_index(op.f("ix_user_re_onboarding_allowed"), "user", ["re_onboarding_allowed"], unique=False)
    op.create_foreign_key(
        "fk_user_re_onboarding_allowed_by_user",
        "user",
        "user",
        ["re_onboarding_allowed_by"],
        ["id"],
    )
    op.alter_column("user", "re_onboarding_allowed", server_default=None)


def downgrade() -> None:
    op.drop_constraint("fk_user_re_onboarding_allowed_by_user", "user", type_="foreignkey")
    op.drop_index(op.f("ix_user_re_onboarding_allowed"), table_name="user")
    op.drop_column("user", "re_onboarding_reason")
    op.drop_column("user", "re_onboarding_allowed_by")
    op.drop_column("user", "re_onboarding_allowed_at")
    op.drop_column("user", "re_onboarding_allowed")
