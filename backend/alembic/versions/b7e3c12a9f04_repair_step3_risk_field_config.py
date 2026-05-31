"""repair step3 risk field config

Revision ID: b7e3c12a9f04
Revises: a1d8c5f0b642
Create Date: 2026-05-31 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op


revision: str = "b7e3c12a9f04"
down_revision: Union[str, Sequence[str], None] = "a1d8c5f0b642"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _quote(value: str | None) -> str:
    if value is None:
        return "NULL"
    return "'" + value.replace("'", "''") + "'"


FACTOR_DEFINITIONS = [
    ("type_of_onboarding", "Onboarding Channel", "onboarding", "onboarding_channel", "first", 10),
    ("transactional_risk", "Expected Annual Transaction Volume", "transactional", "expected_transaction_range", "first", 100),
    ("source_of_funds_verification", "Source of Funds", "transparency", "source_of_funds", "first", 110),
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
    "transactional_risk": [
        ("BELOW_BDT_1M", "normalized_match", "below_bdt_1m", None, None, None, 1, "< BDT 1 Million"),
        ("BDT_1M_5M", "normalized_match", "bdt_1m_5m", None, None, None, 2, "BDT 1M - 5M"),
        ("BDT_5M_50M", "normalized_match", "bdt_5m_50m", None, None, None, 3, "BDT 5M - 50M"),
        ("ABOVE_BDT_50M", "normalized_match", "above_bdt_50m", None, None, None, 5, "> BDT 50M"),
    ],
    "source_of_funds_verification": [
        ("SALARY", "normalized_match", "salary", None, None, None, 1, "Salary"),
        ("BUSINESS_INCOME", "normalized_match", "business_income", None, None, None, 3, "Business Income"),
        ("INVESTMENT", "normalized_match", "investment", None, None, None, 2, "Investment"),
        ("CASH", "normalized_match", "cash", None, None, None, 5, "Cash"),
    ],
}


def upgrade() -> None:
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
        UPDATE customer_identity_profiles
        SET source_of_funds = CASE lower(trim(source_of_funds))
                WHEN 'salary' THEN 'salary'
                WHEN 'business income' THEN 'business_income'
                WHEN 'business_income' THEN 'business_income'
                WHEN 'investment' THEN 'investment'
                WHEN 'cash' THEN 'cash'
                ELSE source_of_funds
            END,
            expected_transaction_range = CASE lower(trim(expected_transaction_range))
                WHEN '< bdt 1 million' THEN 'below_bdt_1m'
                WHEN '< bdt 1m' THEN 'below_bdt_1m'
                WHEN 'below_bdt_1m' THEN 'below_bdt_1m'
                WHEN 'below bdt 1m' THEN 'below_bdt_1m'
                WHEN 'bdt 1m - 5m' THEN 'bdt_1m_5m'
                WHEN 'bdt 1m-5m' THEN 'bdt_1m_5m'
                WHEN 'bdt_1m_5m' THEN 'bdt_1m_5m'
                WHEN 'bdt 5m - 50m' THEN 'bdt_5m_50m'
                WHEN 'bdt 5m-50m' THEN 'bdt_5m_50m'
                WHEN 'bdt_5m_50m' THEN 'bdt_5m_50m'
                WHEN '> bdt 50m' THEN 'above_bdt_50m'
                WHEN 'above_bdt_50m' THEN 'above_bdt_50m'
                WHEN 'above bdt 50m' THEN 'above_bdt_50m'
                ELSE expected_transaction_range
            END,
            onboarding_channel = CASE lower(trim(onboarding_channel))
                WHEN 'branch' THEN 'branch'
                WHEN 'relationship manager' THEN 'rm'
                WHEN 'rm' THEN 'rm'
                WHEN 'direct sales agent' THEN 'direct_sales_agent'
                WHEN 'direct_sales_agent' THEN 'direct_sales_agent'
                WHEN 'walk-in' THEN 'walk_in'
                WHEN 'walk in' THEN 'walk_in'
                WHEN 'walk_in' THEN 'walk_in'
                WHEN 'internet' THEN 'internet'
                WHEN 'non-face-to-face' THEN 'non_face_to_face'
                WHEN 'non face to face' THEN 'non_face_to_face'
                WHEN 'non_face_to_face' THEN 'non_face_to_face'
                ELSE onboarding_channel
            END,
            updated_at = NOW()
        WHERE source_of_funds IS NOT NULL
           OR expected_transaction_range IS NOT NULL
           OR onboarding_channel IS NOT NULL
        """
    )


def downgrade() -> None:
    # Seed repair is intentionally not deleted on downgrade; these rows may be referenced
    # by completed, auditable customer risk assessments.
    pass
