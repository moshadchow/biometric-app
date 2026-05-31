"""config driven risk alignment

Revision ID: f2a9d4c8b731
Revises: e6b4a21c7d93
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "f2a9d4c8b731"
down_revision: Union[str, Sequence[str], None] = "e6b4a21c7d93"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


FACTOR_DEFINITIONS = [
    ("type_of_onboarding", "Onboarding Channel", "onboarding", "onboarding_channel", "first", 10),
    ("geographic_risk", "Residency Status", "geographic", "residency_status", "first", 20),
    ("nationality_risk", "Nationality", "geographic", "nationality", "first", 21),
    ("pep", "PEP Screening", "screening", "pep_match", "max", 30),
    ("pep_close_associate", "PEP Associate Screening", "screening", "pep_associate_match", "max", 31),
    ("influential_person", "Influential Person Screening", "screening", "ip_risk_match", "max", 40),
    ("high_risk_ip_result", "High Risk IP Result", "screening", "high_risk_ip_result", "max", 41),
    ("adverse_media_risk", "Adverse Media Screening", "screening", "adverse_media_match", "max", 50),
    ("sanctions_risk", "Sanctions Screening", "screening", "sanctions_match", "max", 60),
    ("exit_list_risk", "Exit List Screening", "screening", "exit_list_match", "max", 61),
    ("product_risk", "Product Type", "product", "product_type", "first", 70),
    ("business_activity_risk", "Business Category", "business", "business_category", "first", 80),
    ("profession_risk", "Profession", "profession", "profession", "first", 90),
    ("transactional_risk", "Expected Annual Transaction Volume", "transactional", "expected_transaction_range", "first", 100),
    ("source_of_funds_verification", "Source of Funds", "transparency", "source_of_funds", "first", 110),
    ("beneficial_ownership_risk", "Beneficial Ownership", "transparency", "beneficial_owner_different", "first", 120),
]


FACTOR_RULES = {
    "type_of_onboarding": [
        ("BRANCH", "normalized_match", "branch", None, None, None, 2, "Branch"),
        ("RM", "normalized_match", "rm", None, None, None, 2, "Relationship Manager"),
        ("DIRECT_SALES_AGENT", "normalized_match", "direct_sales_agent", None, None, None, 2, "Direct Sales Agent"),
        ("WALK_IN", "normalized_match", "walk_in", None, None, None, 3, "Walk-in"),
        ("INTERNET", "normalized_match", "internet", None, None, None, 2, "Internet"),
        ("NON_FACE_TO_FACE", "normalized_match", "non_face_to_face", None, None, None, 2, "Non-face-to-face"),
    ],
    "geographic_risk": [
        ("RESIDENT_BANGLADESHI", "normalized_match", "resident_bangladeshi", None, None, None, 1, "Resident Bangladeshi"),
        ("NON_RESIDENT_BANGLADESHI", "normalized_match", "non_resident_bangladeshi", None, None, None, 3, "Non-resident Bangladeshi"),
    ],
    "nationality_risk": [
        ("BANGLADESHI", "normalized_match", "bangladeshi", None, None, None, 1, "Bangladeshi"),
        ("NON_BANGLADESHI", "normalized_match", "non_bangladeshi", None, None, None, 3, "Non-Bangladeshi"),
    ],
    "source_of_funds_verification": [
        ("SALARY", "normalized_match", "salary", None, None, None, 1, "Salary"),
        ("BUSINESS_INCOME", "normalized_match", "business_income", None, None, None, 3, "Business Income"),
        ("INVESTMENT", "normalized_match", "investment", None, None, None, 2, "Investment"),
        ("CASH", "normalized_match", "cash", None, None, None, 5, "Cash"),
    ],
    "transactional_risk": [
        ("BELOW_BDT_1M", "normalized_match", "below_bdt_1m", None, None, None, 1, "< BDT 1 Million"),
        ("BDT_1M_5M", "normalized_match", "bdt_1m_5m", None, None, None, 2, "BDT 1M - 5M"),
        ("BDT_5M_50M", "normalized_match", "bdt_5m_50m", None, None, None, 3, "BDT 5M - 50M"),
        ("ABOVE_BDT_50M", "normalized_match", "above_bdt_50m", None, None, None, 5, "> BDT 50M"),
    ],
    "beneficial_ownership_risk": [
        ("SAME_OWNER", "boolean", None, None, None, False, 0, "Beneficial owner is the customer"),
        ("DIFFERENT_OWNER", "boolean", None, None, None, True, 3, "Different beneficial owner"),
    ],
    "pep": [
        ("MATCH", "boolean", None, None, None, True, 5, "PEP match"),
        ("NO_MATCH", "boolean", None, None, None, False, 0, "No PEP match"),
    ],
    "pep_close_associate": [
        ("MATCH", "boolean", None, None, None, True, 5, "PEP associate match"),
        ("NO_MATCH", "boolean", None, None, None, False, 0, "No PEP associate match"),
    ],
    "influential_person": [
        ("MATCH", "boolean", None, None, None, True, 5, "Influential person match"),
        ("NO_MATCH", "boolean", None, None, None, False, 0, "No influential person match"),
    ],
    "high_risk_ip_result": [
        ("MATCH", "boolean", None, None, None, True, 5, "High risk IP result"),
        ("NO_MATCH", "boolean", None, None, None, False, 0, "No high risk IP result"),
    ],
    "adverse_media_risk": [
        ("MATCH", "boolean", None, None, None, True, 5, "Adverse media match"),
        ("NO_MATCH", "boolean", None, None, None, False, 0, "No adverse media match"),
    ],
    "sanctions_risk": [
        ("MATCH", "boolean", None, None, None, True, 5, "Sanctions match"),
        ("NO_MATCH", "boolean", None, None, None, False, 0, "No sanctions match"),
    ],
    "exit_list_risk": [
        ("MATCH", "boolean", None, None, None, True, 5, "Exit list match"),
        ("NO_MATCH", "boolean", None, None, None, False, 0, "No exit list match"),
    ],
}


def _quote(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


def upgrade() -> None:
    op.add_column("customer_identity_profiles", sa.Column("product_type", sa.String(), nullable=True))
    op.add_column("customer_identity_profiles", sa.Column("business_category", sa.String(), nullable=True))
    op.add_column("customer_identity_profiles", sa.Column("residency_status", sa.String(), nullable=True))
    op.add_column("customer_identity_profiles", sa.Column("onboarding_channel", sa.String(), nullable=True))

    op.add_column("customer_risk_factor_scores", sa.Column("factor_code", sa.String(), nullable=True))
    op.add_column("customer_risk_factor_scores", sa.Column("source_table", sa.String(), nullable=True))
    op.add_column("customer_risk_factor_scores", sa.Column("selected_value", sa.String(), nullable=True))
    op.add_column("customer_risk_factor_scores", sa.Column("rule_id", sa.Integer(), nullable=True))
    op.add_column("customer_risk_factor_scores", sa.Column("match_status", sa.String(), nullable=False, server_default="matched"))
    op.create_index(op.f("ix_customer_risk_factor_scores_factor_code"), "customer_risk_factor_scores", ["factor_code"], unique=False)
    op.create_index(op.f("ix_customer_risk_factor_scores_source_table"), "customer_risk_factor_scores", ["source_table"], unique=False)
    op.create_index(op.f("ix_customer_risk_factor_scores_selected_value"), "customer_risk_factor_scores", ["selected_value"], unique=False)
    op.create_index(op.f("ix_customer_risk_factor_scores_rule_id"), "customer_risk_factor_scores", ["rule_id"], unique=False)
    op.create_index(op.f("ix_customer_risk_factor_scores_match_status"), "customer_risk_factor_scores", ["match_status"], unique=False)

    op.execute("UPDATE customer_risk_factor_scores SET factor_code = factor_name WHERE factor_code IS NULL")

    for code, name, group, source_key, aggregation, display_order in FACTOR_DEFINITIONS:
        op.execute(
            f"""
            INSERT INTO risk_factor_definitions
                (factor_code, factor_name, factor_group, source_key, aggregation_mode, description, is_active, display_order, created_at, updated_at)
            VALUES
                ({_quote(code)}, {_quote(name)}, {_quote(group)}, {_quote(source_key)}, {_quote(aggregation)}, NULL, TRUE, {display_order}, NOW(), NOW())
            ON CONFLICT (factor_code) DO UPDATE
            SET factor_name = EXCLUDED.factor_name,
                factor_group = EXCLUDED.factor_group,
                source_key = EXCLUDED.source_key,
                aggregation_mode = EXCLUDED.aggregation_mode,
                is_active = TRUE,
                display_order = EXCLUDED.display_order,
                updated_at = NOW()
            """
        )

    for factor_code, rules in FACTOR_RULES.items():
        for rule_code, rule_type, match_value, min_value, max_value, boolean_value, score, description in rules:
            boolean_sql = "NULL" if boolean_value is None else ("TRUE" if boolean_value else "FALSE")
            min_sql = "NULL" if min_value is None else str(min_value)
            max_sql = "NULL" if max_value is None else str(max_value)
            op.execute(
                f"""
                INSERT INTO risk_factor_rules
                    (rule_version_id, factor_definition_id, rule_code, rule_type, match_value, min_value, max_value, boolean_value, risk_score, description, is_active, effective_date, created_at, updated_at)
                SELECT rv.id, fd.id, {_quote(rule_code)}, {_quote(rule_type)}, {_quote(match_value)}, {min_sql}, {max_sql}, {boolean_sql}, {score}, {_quote(description)}, TRUE, NOW(), NOW(), NOW()
                FROM risk_rule_versions rv
                JOIN risk_factor_definitions fd ON fd.factor_code = {_quote(factor_code)}
                WHERE rv.status = 'ACTIVE'
                  AND NOT EXISTS (
                    SELECT 1
                    FROM risk_factor_rules existing
                    WHERE existing.rule_version_id = rv.id
                      AND existing.factor_definition_id = fd.id
                      AND existing.rule_code = {_quote(rule_code)}
                  )
                """
            )

    op.execute(
        """
        INSERT INTO risk_factor_rules
            (rule_version_id, factor_definition_id, rule_code, rule_type, match_value, min_value, max_value, boolean_value, risk_score, description, is_active, effective_date, created_at, updated_at)
        SELECT tr.rule_version_id, fd.id, tr.range_code, 'normalized_match', lower(tr.range_code), NULL, NULL, NULL, tr.risk_score, tr.range_name, tr.is_active, NOW(), NOW(), NOW()
        FROM risk_transaction_ranges tr
        JOIN risk_factor_definitions fd ON fd.factor_code = 'transactional_risk'
        WHERE NOT EXISTS (
            SELECT 1
            FROM risk_factor_rules existing
            WHERE existing.rule_version_id = tr.rule_version_id
              AND existing.factor_definition_id = fd.id
              AND existing.rule_code = tr.range_code
        )
        """
    )


def downgrade() -> None:
    op.drop_index(op.f("ix_customer_risk_factor_scores_match_status"), table_name="customer_risk_factor_scores")
    op.drop_index(op.f("ix_customer_risk_factor_scores_rule_id"), table_name="customer_risk_factor_scores")
    op.drop_index(op.f("ix_customer_risk_factor_scores_selected_value"), table_name="customer_risk_factor_scores")
    op.drop_index(op.f("ix_customer_risk_factor_scores_source_table"), table_name="customer_risk_factor_scores")
    op.drop_index(op.f("ix_customer_risk_factor_scores_factor_code"), table_name="customer_risk_factor_scores")
    op.drop_column("customer_risk_factor_scores", "match_status")
    op.drop_column("customer_risk_factor_scores", "rule_id")
    op.drop_column("customer_risk_factor_scores", "selected_value")
    op.drop_column("customer_risk_factor_scores", "source_table")
    op.drop_column("customer_risk_factor_scores", "factor_code")

    op.drop_column("customer_identity_profiles", "onboarding_channel")
    op.drop_column("customer_identity_profiles", "residency_status")
    op.drop_column("customer_identity_profiles", "business_category")
    op.drop_column("customer_identity_profiles", "product_type")
