"""customer identity form tables

Revision ID: c4a2f6e8d901
Revises: b2d6c9e41f20
Create Date: 2026-05-30 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "c4a2f6e8d901"
down_revision: Union[str, Sequence[str], None] = "b2d6c9e41f20"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "customer_identity_profiles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("session_id", sa.Integer(), nullable=False),
        sa.Column("form_type", sa.String(), nullable=False),
        sa.Column("risk_category", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=False),
        sa.Column("applicant_name", sa.String(), nullable=True),
        sa.Column("account_number", sa.String(), nullable=True),
        sa.Column("unique_account_number", sa.String(), nullable=True),
        sa.Column("nid_number", sa.String(), nullable=True),
        sa.Column("father_name", sa.String(), nullable=True),
        sa.Column("mother_name", sa.String(), nullable=True),
        sa.Column("spouse_name", sa.String(), nullable=True),
        sa.Column("date_of_birth", sa.String(), nullable=True),
        sa.Column("gender", sa.String(), nullable=True),
        sa.Column("profession", sa.String(), nullable=True),
        sa.Column("mobile_number", sa.String(), nullable=True),
        sa.Column("monthly_income", sa.String(), nullable=True),
        sa.Column("nationality", sa.String(), nullable=True),
        sa.Column("source_of_funds", sa.String(), nullable=True),
        sa.Column("tin", sa.String(), nullable=True),
        sa.Column("expected_transaction_range", sa.String(), nullable=True),
        sa.Column("expected_transaction_pattern", sa.String(), nullable=True),
        sa.Column("existing_customer_review", sa.String(), nullable=True),
        sa.Column("additional_documents_obtained", sa.String(), nullable=True),
        sa.Column("additional_remarks", sa.String(), nullable=True),
        sa.Column("beneficial_owner_different", sa.Boolean(), nullable=False),
        sa.Column("beneficial_owner_name", sa.String(), nullable=True),
        sa.Column("beneficial_owner_nationality", sa.String(), nullable=True),
        sa.Column("beneficial_owner_identification_number", sa.String(), nullable=True),
        sa.Column("beneficial_owner_relationship", sa.String(), nullable=True),
        sa.Column("ocr_snapshot", sa.JSON(), nullable=False),
        sa.Column("ocr_corrections", sa.JSON(), nullable=False),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("submitted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["session_id"], ["onboarding_session.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index(op.f("ix_customer_identity_profiles_session_id"), "customer_identity_profiles", ["session_id"], unique=True)
    op.create_index(op.f("ix_customer_identity_profiles_form_type"), "customer_identity_profiles", ["form_type"], unique=False)
    op.create_index(op.f("ix_customer_identity_profiles_risk_category"), "customer_identity_profiles", ["risk_category"], unique=False)
    op.create_index(op.f("ix_customer_identity_profiles_status"), "customer_identity_profiles", ["status"], unique=False)

    op.create_table(
        "customer_addresses",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("address_type", sa.String(), nullable=False),
        sa.Column("address_line", sa.String(), nullable=True),
        sa.Column("city", sa.String(), nullable=True),
        sa.Column("district", sa.String(), nullable=True),
        sa.Column("postal_code", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["customer_identity_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_customer_addresses_profile_id"), "customer_addresses", ["profile_id"], unique=False)
    op.create_index(op.f("ix_customer_addresses_address_type"), "customer_addresses", ["address_type"], unique=False)
    op.create_index("uq_customer_address_profile_type", "customer_addresses", ["profile_id", "address_type"], unique=True)

    op.create_table(
        "customer_nominees",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("profile_id", sa.Integer(), nullable=False),
        sa.Column("nominee_name", sa.String(), nullable=True),
        sa.Column("relationship", sa.String(), nullable=True),
        sa.Column("photograph_file_path", sa.String(), nullable=True),
        sa.Column("photograph_file_name", sa.String(), nullable=True),
        sa.Column("metadata", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["profile_id"], ["customer_identity_profiles.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("profile_id"),
    )
    op.create_index(op.f("ix_customer_nominees_profile_id"), "customer_nominees", ["profile_id"], unique=True)


def downgrade() -> None:
    op.drop_index(op.f("ix_customer_nominees_profile_id"), table_name="customer_nominees")
    op.drop_table("customer_nominees")
    op.drop_index("uq_customer_address_profile_type", table_name="customer_addresses")
    op.drop_index(op.f("ix_customer_addresses_address_type"), table_name="customer_addresses")
    op.drop_index(op.f("ix_customer_addresses_profile_id"), table_name="customer_addresses")
    op.drop_table("customer_addresses")
    op.drop_index(op.f("ix_customer_identity_profiles_status"), table_name="customer_identity_profiles")
    op.drop_index(op.f("ix_customer_identity_profiles_risk_category"), table_name="customer_identity_profiles")
    op.drop_index(op.f("ix_customer_identity_profiles_form_type"), table_name="customer_identity_profiles")
    op.drop_index(op.f("ix_customer_identity_profiles_session_id"), table_name="customer_identity_profiles")
    op.drop_table("customer_identity_profiles")
