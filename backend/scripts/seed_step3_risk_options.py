from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlmodel import Session, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings
from model.models import CustomerIdentityProfile, RiskFactorDefinition, RiskFactorRule, RiskRuleVersion


@dataclass(frozen=True)
class FactorSeed:
    code: str
    name: str
    group: str
    source_key: str
    aggregation_mode: str
    display_order: int


@dataclass(frozen=True)
class RuleSeed:
    factor_code: str
    rule_code: str
    rule_type: str
    match_value: str | None
    risk_score: int
    description: str


FACTOR_SEEDS = [
    FactorSeed("type_of_onboarding", "Onboarding Channel", "onboarding", "onboarding_channel", "first", 10),
    FactorSeed("transactional_risk", "Expected Annual Transaction Volume", "transactional", "expected_transaction_range", "first", 100),
    FactorSeed("source_of_funds_verification", "Source of Funds", "transparency", "source_of_funds", "first", 110),
]

RULE_SEEDS = [
    RuleSeed("type_of_onboarding", "BRANCH", "normalized_match", "branch", 2, "Branch"),
    RuleSeed("type_of_onboarding", "RM", "normalized_match", "rm", 2, "Relationship Manager"),
    RuleSeed("type_of_onboarding", "DIRECT_SALES_AGENT", "normalized_match", "direct_sales_agent", 2, "Direct Sales Agent"),
    RuleSeed("type_of_onboarding", "WALK_IN", "normalized_match", "walk_in", 3, "Walk-in"),
    RuleSeed("type_of_onboarding", "INTERNET", "normalized_match", "internet", 2, "Internet"),
    RuleSeed("type_of_onboarding", "NON_FACE_TO_FACE", "normalized_match", "non_face_to_face", 2, "Non-face-to-face"),
    RuleSeed("transactional_risk", "BELOW_BDT_1M", "normalized_match", "below_bdt_1m", 1, "< BDT 1 Million"),
    RuleSeed("transactional_risk", "BDT_1M_5M", "normalized_match", "bdt_1m_5m", 2, "BDT 1M - 5M"),
    RuleSeed("transactional_risk", "BDT_5M_50M", "normalized_match", "bdt_5m_50m", 3, "BDT 5M - 50M"),
    RuleSeed("transactional_risk", "ABOVE_BDT_50M", "normalized_match", "above_bdt_50m", 5, "> BDT 50M"),
    RuleSeed("source_of_funds_verification", "SALARY", "normalized_match", "salary", 1, "Salary"),
    RuleSeed("source_of_funds_verification", "BUSINESS_INCOME", "normalized_match", "business_income", 3, "Business Income"),
    RuleSeed("source_of_funds_verification", "INVESTMENT", "normalized_match", "investment", 2, "Investment"),
    RuleSeed("source_of_funds_verification", "CASH", "normalized_match", "cash", 5, "Cash"),
]

NORMALIZED_PROFILE_VALUES = {
    "source_of_funds": {
        "salary": "salary",
        "business income": "business_income",
        "business_income": "business_income",
        "investment": "investment",
        "cash": "cash",
    },
    "expected_transaction_range": {
        "< bdt 1 million": "below_bdt_1m",
        "< bdt 1m": "below_bdt_1m",
        "below bdt 1m": "below_bdt_1m",
        "below_bdt_1m": "below_bdt_1m",
        "bdt 1m - 5m": "bdt_1m_5m",
        "bdt 1m-5m": "bdt_1m_5m",
        "bdt_1m_5m": "bdt_1m_5m",
        "bdt 5m - 50m": "bdt_5m_50m",
        "bdt 5m-50m": "bdt_5m_50m",
        "bdt_5m_50m": "bdt_5m_50m",
        "> bdt 50m": "above_bdt_50m",
        "above bdt 50m": "above_bdt_50m",
        "above_bdt_50m": "above_bdt_50m",
    },
    "onboarding_channel": {
        "branch": "branch",
        "relationship manager": "rm",
        "rm": "rm",
        "direct sales agent": "direct_sales_agent",
        "direct_sales_agent": "direct_sales_agent",
        "walk-in": "walk_in",
        "walk in": "walk_in",
        "walk_in": "walk_in",
        "internet": "internet",
        "non-face-to-face": "non_face_to_face",
        "non face to face": "non_face_to_face",
        "non_face_to_face": "non_face_to_face",
    },
}


def _active_rule_version(session: Session) -> RiskRuleVersion:
    row = session.exec(
        select(RiskRuleVersion)
        .where(RiskRuleVersion.status == "ACTIVE")
        .order_by(RiskRuleVersion.effective_date.desc())
    ).first()
    if row is not None:
        return row
    row = RiskRuleVersion(
        version="v1",
        status="ACTIVE",
        thresholds={"low_max": 9, "medium_max": 14},
        rules_snapshot={"source": "seed_step3_risk_options"},
        change_notes="Seeded active risk rule version for Step-3 risk options.",
    )
    session.add(row)
    session.flush()
    session.refresh(row)
    return row


def seed_step3_risk_options(session: Session) -> dict[str, int]:
    now = datetime.utcnow()
    version = _active_rule_version(session)
    counts = {
        "definitions_created": 0,
        "definitions_repaired": 0,
        "rules_created": 0,
        "rules_repaired": 0,
        "profiles_normalized": 0,
    }
    definitions_by_code = {
        row.factor_code: row
        for row in session.exec(
            select(RiskFactorDefinition).where(
                RiskFactorDefinition.factor_code.in_([seed.code for seed in FACTOR_SEEDS])
            )
        ).all()
    }

    for seed in FACTOR_SEEDS:
        if seed.code in definitions_by_code:
            row = definitions_by_code[seed.code]
            changed = False
            if row.factor_name != seed.name:
                row.factor_name = seed.name
                changed = True
            if row.factor_group != seed.group:
                row.factor_group = seed.group
                changed = True
            if row.source_key != seed.source_key:
                row.source_key = seed.source_key
                changed = True
            if row.aggregation_mode != seed.aggregation_mode:
                row.aggregation_mode = seed.aggregation_mode
                changed = True
            if row.display_order != seed.display_order:
                row.display_order = seed.display_order
                changed = True
            if changed:
                row.updated_at = now
                session.add(row)
                counts["definitions_repaired"] += 1
            continue
        row = RiskFactorDefinition(
            factor_code=seed.code,
            factor_name=seed.name,
            factor_group=seed.group,
            source_key=seed.source_key,
            aggregation_mode=seed.aggregation_mode,
            is_active=True,
            display_order=seed.display_order,
            created_at=now,
            updated_at=now,
        )
        session.add(row)
        session.flush()
        definitions_by_code[seed.code] = row
        counts["definitions_created"] += 1

    existing_rules = {
        (definition.factor_code, rule.rule_code): rule
        for rule, definition in session.exec(
            select(RiskFactorRule, RiskFactorDefinition)
            .join(RiskFactorDefinition, RiskFactorDefinition.id == RiskFactorRule.factor_definition_id)
            .where(RiskFactorRule.rule_version_id == version.id)
            .where(RiskFactorDefinition.factor_code.in_([seed.code for seed in FACTOR_SEEDS]))
        ).all()
    }

    for seed in RULE_SEEDS:
        definition = definitions_by_code.get(seed.factor_code)
        if definition is None or definition.id is None:
            continue
        existing = existing_rules.get((seed.factor_code, seed.rule_code))
        if existing is not None:
            changed = False
            if existing.rule_type != seed.rule_type:
                existing.rule_type = seed.rule_type
                changed = True
            if existing.match_value != seed.match_value:
                existing.match_value = seed.match_value
                changed = True
            if not str(existing.description or "").strip():
                existing.description = seed.description
                changed = True
            if changed:
                existing.updated_at = now
                session.add(existing)
                counts["rules_repaired"] += 1
            continue
        session.add(
            RiskFactorRule(
                rule_version_id=version.id,
                factor_definition_id=definition.id,
                rule_code=seed.rule_code,
                rule_type=seed.rule_type,
                match_value=seed.match_value,
                risk_score=seed.risk_score,
                description=seed.description,
                is_active=True,
                effective_date=now,
                created_at=now,
                updated_at=now,
            )
        )
        counts["rules_created"] += 1

    for profile in session.exec(select(CustomerIdentityProfile)).all():
        changed = False
        for field_name, values in NORMALIZED_PROFILE_VALUES.items():
            current = getattr(profile, field_name)
            normalized = values.get(str(current or "").strip().lower())
            if normalized is not None and normalized != current:
                setattr(profile, field_name, normalized)
                changed = True
        if changed:
            profile.updated_at = now
            session.add(profile)
            counts["profiles_normalized"] += 1

    session.commit()
    return counts


def main() -> None:
    engine = create_engine(settings.DATABASE_SYNC_URL)
    with Session(engine) as session:
        counts = seed_step3_risk_options(session)
    print(
        "Seeded Step-3 risk options: "
        f"definitions_created={counts['definitions_created']}, "
        f"definitions_repaired={counts['definitions_repaired']}, "
        f"rules_created={counts['rules_created']}, "
        f"rules_repaired={counts['rules_repaired']}, "
        f"profiles_normalized={counts['profiles_normalized']}"
    )


if __name__ == "__main__":
    main()
