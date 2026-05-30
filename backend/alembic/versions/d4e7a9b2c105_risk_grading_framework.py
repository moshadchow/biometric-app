"""risk grading framework

Revision ID: d4e7a9b2c105
Revises: c6d2f8a4b901
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "d4e7a9b2c105"
down_revision: Union[str, Sequence[str], None] = "c6d2f8a4b901"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("risk_rule_versions", sa.Column("created_by", sa.Integer(), nullable=True))
    op.add_column("risk_rule_versions", sa.Column("change_notes", sa.String(), nullable=True))
    op.add_column("risk_rule_versions", sa.Column("activated_at", sa.DateTime(), nullable=True))
    op.add_column("risk_rule_versions", sa.Column("retired_at", sa.DateTime(), nullable=True))
    op.create_foreign_key("fk_risk_rule_versions_created_by_user", "risk_rule_versions", "user", ["created_by"], ["id"])

    op.create_table(
        "risk_factor_definitions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("factor_code", sa.String(), nullable=False),
        sa.Column("factor_name", sa.String(), nullable=False),
        sa.Column("factor_group", sa.String(), nullable=False),
        sa.Column("source_key", sa.String(), nullable=False),
        sa.Column("aggregation_mode", sa.String(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("display_order", sa.Integer(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("factor_code"),
    )
    op.create_index(op.f("ix_risk_factor_definitions_factor_code"), "risk_factor_definitions", ["factor_code"], unique=True)
    op.create_index(op.f("ix_risk_factor_definitions_factor_group"), "risk_factor_definitions", ["factor_group"], unique=False)
    op.create_index(op.f("ix_risk_factor_definitions_source_key"), "risk_factor_definitions", ["source_key"], unique=False)
    op.create_index(op.f("ix_risk_factor_definitions_is_active"), "risk_factor_definitions", ["is_active"], unique=False)
    op.create_index(op.f("ix_risk_factor_definitions_display_order"), "risk_factor_definitions", ["display_order"], unique=False)

    op.create_table(
        "risk_factor_rules",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_version_id", sa.Integer(), nullable=False),
        sa.Column("factor_definition_id", sa.Integer(), nullable=False),
        sa.Column("rule_code", sa.String(), nullable=False),
        sa.Column("rule_type", sa.String(), nullable=False),
        sa.Column("match_value", sa.String(), nullable=True),
        sa.Column("min_value", sa.Float(), nullable=True),
        sa.Column("max_value", sa.Float(), nullable=True),
        sa.Column("boolean_value", sa.Boolean(), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("description", sa.String(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("effective_date", sa.DateTime(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["factor_definition_id"], ["risk_factor_definitions.id"]),
        sa.ForeignKeyConstraint(["rule_version_id"], ["risk_rule_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_factor_rules_rule_version_id"), "risk_factor_rules", ["rule_version_id"], unique=False)
    op.create_index(op.f("ix_risk_factor_rules_factor_definition_id"), "risk_factor_rules", ["factor_definition_id"], unique=False)
    op.create_index(op.f("ix_risk_factor_rules_rule_code"), "risk_factor_rules", ["rule_code"], unique=False)
    op.create_index(op.f("ix_risk_factor_rules_rule_type"), "risk_factor_rules", ["rule_type"], unique=False)
    op.create_index(op.f("ix_risk_factor_rules_match_value"), "risk_factor_rules", ["match_value"], unique=False)
    op.create_index(op.f("ix_risk_factor_rules_is_active"), "risk_factor_rules", ["is_active"], unique=False)

    op.create_table(
        "risk_threshold_bands",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_version_id", sa.Integer(), nullable=False),
        sa.Column("category_code", sa.String(), nullable=False),
        sa.Column("category_name", sa.String(), nullable=False),
        sa.Column("min_score", sa.Integer(), nullable=False),
        sa.Column("max_score", sa.Integer(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["rule_version_id"], ["risk_rule_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_threshold_bands_rule_version_id"), "risk_threshold_bands", ["rule_version_id"], unique=False)
    op.create_index(op.f("ix_risk_threshold_bands_category_code"), "risk_threshold_bands", ["category_code"], unique=False)
    op.create_index(op.f("ix_risk_threshold_bands_category_name"), "risk_threshold_bands", ["category_name"], unique=False)
    op.create_index(op.f("ix_risk_threshold_bands_is_active"), "risk_threshold_bands", ["is_active"], unique=False)

    op.create_table(
        "risk_transaction_ranges",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_version_id", sa.Integer(), nullable=False),
        sa.Column("range_code", sa.String(), nullable=False),
        sa.Column("range_name", sa.String(), nullable=False),
        sa.Column("min_amount", sa.Float(), nullable=True),
        sa.Column("max_amount", sa.Float(), nullable=True),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["rule_version_id"], ["risk_rule_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_transaction_ranges_rule_version_id"), "risk_transaction_ranges", ["rule_version_id"], unique=False)
    op.create_index(op.f("ix_risk_transaction_ranges_range_code"), "risk_transaction_ranges", ["range_code"], unique=False)
    op.create_index(op.f("ix_risk_transaction_ranges_range_name"), "risk_transaction_ranges", ["range_name"], unique=False)
    op.create_index(op.f("ix_risk_transaction_ranges_is_active"), "risk_transaction_ranges", ["is_active"], unique=False)

    op.create_table(
        "risk_product_categories",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rule_version_id", sa.Integer(), nullable=False),
        sa.Column("product_code", sa.String(), nullable=False),
        sa.Column("product_name", sa.String(), nullable=False),
        sa.Column("product_category", sa.String(), nullable=False),
        sa.Column("risk_score", sa.Integer(), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("created_by", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["created_by"], ["user.id"]),
        sa.ForeignKeyConstraint(["rule_version_id"], ["risk_rule_versions.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_risk_product_categories_rule_version_id"), "risk_product_categories", ["rule_version_id"], unique=False)
    op.create_index(op.f("ix_risk_product_categories_product_code"), "risk_product_categories", ["product_code"], unique=False)
    op.create_index(op.f("ix_risk_product_categories_product_name"), "risk_product_categories", ["product_name"], unique=False)
    op.create_index(op.f("ix_risk_product_categories_product_category"), "risk_product_categories", ["product_category"], unique=False)
    op.create_index(op.f("ix_risk_product_categories_is_active"), "risk_product_categories", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_risk_product_categories_is_active"), table_name="risk_product_categories")
    op.drop_index(op.f("ix_risk_product_categories_product_category"), table_name="risk_product_categories")
    op.drop_index(op.f("ix_risk_product_categories_product_name"), table_name="risk_product_categories")
    op.drop_index(op.f("ix_risk_product_categories_product_code"), table_name="risk_product_categories")
    op.drop_index(op.f("ix_risk_product_categories_rule_version_id"), table_name="risk_product_categories")
    op.drop_table("risk_product_categories")
    op.drop_index(op.f("ix_risk_transaction_ranges_is_active"), table_name="risk_transaction_ranges")
    op.drop_index(op.f("ix_risk_transaction_ranges_range_name"), table_name="risk_transaction_ranges")
    op.drop_index(op.f("ix_risk_transaction_ranges_range_code"), table_name="risk_transaction_ranges")
    op.drop_index(op.f("ix_risk_transaction_ranges_rule_version_id"), table_name="risk_transaction_ranges")
    op.drop_table("risk_transaction_ranges")
    op.drop_index(op.f("ix_risk_threshold_bands_is_active"), table_name="risk_threshold_bands")
    op.drop_index(op.f("ix_risk_threshold_bands_category_name"), table_name="risk_threshold_bands")
    op.drop_index(op.f("ix_risk_threshold_bands_category_code"), table_name="risk_threshold_bands")
    op.drop_index(op.f("ix_risk_threshold_bands_rule_version_id"), table_name="risk_threshold_bands")
    op.drop_table("risk_threshold_bands")
    op.drop_index(op.f("ix_risk_factor_rules_is_active"), table_name="risk_factor_rules")
    op.drop_index(op.f("ix_risk_factor_rules_match_value"), table_name="risk_factor_rules")
    op.drop_index(op.f("ix_risk_factor_rules_rule_type"), table_name="risk_factor_rules")
    op.drop_index(op.f("ix_risk_factor_rules_rule_code"), table_name="risk_factor_rules")
    op.drop_index(op.f("ix_risk_factor_rules_factor_definition_id"), table_name="risk_factor_rules")
    op.drop_index(op.f("ix_risk_factor_rules_rule_version_id"), table_name="risk_factor_rules")
    op.drop_table("risk_factor_rules")
    op.drop_index(op.f("ix_risk_factor_definitions_display_order"), table_name="risk_factor_definitions")
    op.drop_index(op.f("ix_risk_factor_definitions_is_active"), table_name="risk_factor_definitions")
    op.drop_index(op.f("ix_risk_factor_definitions_source_key"), table_name="risk_factor_definitions")
    op.drop_index(op.f("ix_risk_factor_definitions_factor_group"), table_name="risk_factor_definitions")
    op.drop_index(op.f("ix_risk_factor_definitions_factor_code"), table_name="risk_factor_definitions")
    op.drop_table("risk_factor_definitions")
    op.drop_constraint("fk_risk_rule_versions_created_by_user", "risk_rule_versions", type_="foreignkey")
    op.drop_column("risk_rule_versions", "retired_at")
    op.drop_column("risk_rule_versions", "activated_at")
    op.drop_column("risk_rule_versions", "change_notes")
    op.drop_column("risk_rule_versions", "created_by")
