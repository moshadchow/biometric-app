from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, desc
from sqlmodel import Session, select
from sqlmodel.ext.asyncio.session import AsyncSession

from model.models import (
    AuditLog,
    ComplianceCase,
    CustomerAddress,
    CustomerIdentityProfile,
    CustomerNominee,
    CustomerRiskAssessment,
    CustomerRiskFactorScore,
    OnboardingOCRExtraction,
    OnboardingSession,
    RiskBusinessCategory,
    RiskFactorDefinition,
    RiskFactorRule,
    RiskProductCategory,
    RiskProfessionCategory,
    RiskRuleVersion,
    RiskThresholdBand,
    RiskTransactionRange,
    ScreeningRequest,
    ScreeningResult,
)


DEFAULT_THRESHOLDS = {"low_max": 9, "medium_max": 14}
DEFAULT_RULE_SNAPSHOT = {"source": "03-risk-assessment-engine", "unknown_matrix_fallback_score": 3}

DEFAULT_THRESHOLD_BANDS = [
    {"category_code": "LOW", "category_name": "LOW", "min_score": 0, "max_score": 9},
    {"category_code": "MEDIUM", "category_name": "MEDIUM", "min_score": 10, "max_score": 14},
    {"category_code": "HIGH", "category_name": "HIGH", "min_score": 15, "max_score": None},
]

DEFAULT_FACTOR_DEFINITIONS = [
    ("type_of_onboarding", "Type of Onboarding", "onboarding", "onboarding_type", "first", 10),
    ("geographic_risk", "Geographic Risk", "geographic", "residency_status", "first", 20),
    ("pep", "PEP", "customer_type", "pep_match", "max", 30),
    ("pep_family_member", "PEP Family Member", "customer_type", "pep_family_member", "max", 31),
    ("pep_close_associate", "PEP Close Associate", "customer_type", "pep_associate", "max", 32),
    ("influential_person", "Influential Person", "customer_type", "ip_match", "max", 40),
    ("ip_family_member", "IP Family Member", "customer_type", "ip_family_member", "max", 41),
    ("ip_close_associate", "IP Close Associate", "customer_type", "ip_associate", "max", 42),
    ("product_risk", "Product Risk", "product", "product_type", "first", 50),
    ("transactional_risk", "Transactional Risk", "transactional", "transaction_amount", "first", 80),
    ("source_of_funds_verification", "Source of Funds Verification", "transparency", "source_of_funds_verified", "first", 90),
]

DEFAULT_FACTOR_RULES = {
    "type_of_onboarding": [
        ("BRANCH", "normalized_match", "branch", None, None, None, 2),
        ("RM", "normalized_match", "rm", None, None, None, 2),
        ("DIRECT_SALES_AGENT", "normalized_match", "direct_sales_agent", None, None, None, 2),
        ("WALK_IN", "normalized_match", "walk_in", None, None, None, 3),
        ("INTERNET", "normalized_match", "internet", None, None, None, 2),
        ("NON_FACE_TO_FACE", "normalized_match", "non_face_to_face", None, None, None, 2),
        ("DEFAULT", "fallback", None, None, None, None, 2),
    ],
    "geographic_risk": [
        ("RESIDENT_BANGLADESHI", "normalized_match", "resident_bangladeshi", None, None, None, 1),
        ("NON_RESIDENT_BANGLADESHI", "normalized_match", "non_resident_bangladeshi", None, None, None, 3),
        ("DEFAULT", "fallback", None, None, None, None, 1),
    ],
    "pep": [("MATCH", "boolean", None, None, None, True, 5), ("NO_MATCH", "fallback", None, None, None, None, 0)],
    "pep_family_member": [("MATCH", "boolean", None, None, None, True, 5), ("NO_MATCH", "fallback", None, None, None, None, 0)],
    "pep_close_associate": [("MATCH", "boolean", None, None, None, True, 5), ("NO_MATCH", "fallback", None, None, None, None, 0)],
    "influential_person": [("MATCH", "boolean", None, None, None, True, 5), ("NO_MATCH", "fallback", None, None, None, None, 1)],
    "ip_family_member": [("MATCH", "boolean", None, None, None, True, 5), ("NO_MATCH", "fallback", None, None, None, None, 0)],
    "ip_close_associate": [("MATCH", "boolean", None, None, None, True, 5), ("NO_MATCH", "fallback", None, None, None, None, 0)],
    "product_risk": [("INDIVIDUAL_BO_ACCOUNT", "normalized_match", "individual_bo_account", None, None, None, 2), ("DEFAULT", "fallback", None, None, None, None, 2)],
    "transactional_risk": [
        ("BELOW_BDT_1M", "range", None, None, 999999, None, 1),
        ("BDT_1M_5M", "range", None, 1000000, 5000000, None, 2),
        ("BDT_5M_50M", "range", None, 5000000, 50000000, None, 3),
        ("ABOVE_BDT_50M", "range", None, 50000000, None, None, 5),
        ("DEFAULT", "fallback", None, None, None, None, 2),
    ],
    "source_of_funds_verification": [
        ("VERIFIED", "boolean", None, None, None, True, 1),
        ("NOT_VERIFIED", "boolean", None, None, None, False, 5),
    ],
}


@dataclass
class RiskFactor:
    name: str
    score: int
    source: str
    value: dict[str, Any]


def utc_now() -> datetime:
    return datetime.utcnow()


def classify_score(score: int, thresholds: dict[str, Any]) -> str:
    low_max = int(thresholds.get("low_max", DEFAULT_THRESHOLDS["low_max"]))
    medium_max = int(thresholds.get("medium_max", DEFAULT_THRESHOLDS["medium_max"]))
    if score <= low_max:
        return "LOW"
    if score <= medium_max:
        return "MEDIUM"
    return "HIGH"


def classify_score_with_bands(score: int, bands: list[dict[str, Any]], thresholds: dict[str, Any]) -> str:
    if not bands:
        return classify_score(score, thresholds)
    for band in sorted(bands, key=lambda item: int(item.get("min_score", 0))):
        minimum = int(band.get("min_score", 0))
        maximum = band.get("max_score")
        if score >= minimum and (maximum is None or score <= int(maximum)):
            return str(band.get("category_code") or band.get("category_name") or "HIGH")
    return "HIGH"


def form_type_for_category(category: str) -> str:
    return "simplified" if category == "LOW" else "regular"


def _normalized(value: Any) -> str:
    return str(value or "").strip().lower()


def _screening_match(results: list[ScreeningResult], screening_type: str) -> bool:
    return any(
        result.screening_type == screening_type and result.outcome != "NO_MATCH"
        for result in results
    )


def _transaction_amount(value: str | None) -> float | None:
    text = _normalized(value)
    if not text:
        return None
    if "> bdt 50m" in text or ">50" in text or "50m+" in text:
        return 50000001
    if "5m" in text and "50m" in text:
        return 5000000
    if "1m" in text and "5m" in text:
        return 1000000
    if "< bdt 1m" in text or "<1" in text:
        return 0
    return None


def _transaction_score(value: str | None) -> int:
    text = _normalized(value)
    if not text:
        return 1
    if "> bdt 50m" in text or ">50" in text or "50m+" in text:
        return 5
    if "5m" in text and "50m" in text:
        return 3
    if "1m" in text and "5m" in text:
        return 2
    if "< bdt 1m" in text or "<1" in text:
        return 1
    return 2


def _residency_status(nationality: str | None) -> str:
    normalized = _normalized(nationality)
    if "non-resident" in normalized or "nrb" in normalized:
        return "non_resident_bangladeshi"
    return "resident_bangladeshi"


def _rule_matches(rule: dict[str, Any], value: Any) -> bool:
    rule_type = rule.get("rule_type")
    if rule_type == "fallback":
        return False
    if rule_type == "boolean":
        return bool(value) is bool(rule.get("boolean_value"))
    if rule_type == "normalized_match":
        return _normalized(value) == _normalized(rule.get("match_value"))
    if rule_type == "contains":
        return _normalized(rule.get("match_value")) in _normalized(value)
    if rule_type == "range":
        try:
            numeric = float(value)
        except (TypeError, ValueError):
            return False
        minimum = rule.get("min_value")
        maximum = rule.get("max_value")
        return (minimum is None or numeric >= float(minimum)) and (maximum is None or numeric <= float(maximum))
    return False


def _evaluate_rule_set(factor: dict[str, Any], rules: list[dict[str, Any]], value: Any) -> RiskFactor:
    active_rules = [rule for rule in rules if rule.get("is_active", True)]
    matches = [rule for rule in active_rules if _rule_matches(rule, value)]
    fallback = next((rule for rule in active_rules if rule.get("rule_type") == "fallback"), None)
    selected = None
    if matches:
        selected = max(matches, key=lambda item: int(item.get("risk_score", 0))) if factor.get("aggregation_mode") == "max" else matches[0]
    elif fallback:
        selected = fallback
    score = int(selected.get("risk_score", 0)) if selected else 0
    return RiskFactor(
        str(factor["factor_code"]),
        score,
        str(factor.get("source_key") or "configured_rule"),
        {
            "submitted_value": value,
            "matched_rule_id": selected.get("id") if selected else None,
            "matched_rule_code": selected.get("rule_code") if selected else None,
            "rule_type": selected.get("rule_type") if selected else None,
            "fallback_used": bool(selected and selected.get("rule_type") == "fallback"),
            "risk_score": score,
        },
    )


def _build_factor_inputs(
    *,
    assessment_type: str,
    identity_profile: CustomerIdentityProfile | None,
    screening_results: list[ScreeningResult],
) -> dict[str, Any]:
    metadata = identity_profile.payload_metadata if identity_profile else {}
    has_source_of_funds = bool(identity_profile and identity_profile.source_of_funds)
    source_verified = bool(metadata.get("source_of_funds_verified")) or assessment_type == "preliminary" or not has_source_of_funds
    return {
        "onboarding_type": _normalized(metadata.get("onboarding_type") or "internet"),
        "residency_status": _residency_status(identity_profile.nationality if identity_profile else None),
        "pep_match": _screening_match(screening_results, "pep"),
        "pep_family_member": bool(metadata.get("pep_family_member")),
        "pep_associate": bool(metadata.get("pep_associate")),
        "ip_match": _screening_match(screening_results, "ip_risk"),
        "ip_family_member": bool(metadata.get("ip_family_member")),
        "ip_associate": bool(metadata.get("ip_associate")),
        "product_type": _normalized(metadata.get("product_type") or "individual_bo_account"),
        "transaction_amount": _transaction_amount(identity_profile.expected_transaction_range if identity_profile else None),
        "source_of_funds_verified": source_verified,
    }


def _lookup_score(key: str | None, lookup: dict[str, Any], fallback: int = 3) -> int:
    normalized = _normalized(key)
    if normalized in lookup:
        match = lookup[normalized]
        return match.get("risk_score", fallback) if isinstance(match, dict) else match
    default_match = lookup.get("default", fallback)
    return default_match.get("risk_score", fallback) if isinstance(default_match, dict) else default_match


def _lookup_score_snapshot(key: str | None, lookup: dict[str, Any], fallback: int = 3) -> dict[str, Any]:
    normalized = _normalized(key)
    match = lookup.get(normalized)
    fallback_used = False
    if match is None:
        match = lookup.get("default")
        fallback_used = True
    if isinstance(match, dict):
        snapshot = dict(match)
        snapshot["fallback_used"] = fallback_used
        snapshot["submitted_value"] = key
        return snapshot
    return {
        "risk_score": match if isinstance(match, int) else fallback,
        "fallback_used": fallback_used,
        "submitted_value": key,
    }


def calculate_assessment_payload(
    *,
    assessment_type: str,
    rule_version: RiskRuleVersion,
    identity_profile: CustomerIdentityProfile | None,
    addresses: list[CustomerAddress],
    nominee: CustomerNominee | None,
    ocr: OnboardingOCRExtraction | None,
    screening_results: list[ScreeningResult],
    business_scores: dict[str, Any],
    profession_scores: dict[str, Any],
    configured_model: dict[str, Any] | None = None,
    screening_request_id: int | None = None,
) -> dict[str, Any]:
    thresholds = rule_version.thresholds or DEFAULT_THRESHOLDS
    configured_model = configured_model or {}
    metadata = identity_profile.payload_metadata if identity_profile else {}
    nationality = identity_profile.nationality if identity_profile else None
    profession = identity_profile.profession if identity_profile else None
    business_category = metadata.get("business_category") or "individual_investor"
    onboarding_type = _normalized(metadata.get("onboarding_type") or "internet")
    source_verified = bool(metadata.get("source_of_funds_verified"))
    has_source_of_funds = bool(identity_profile and identity_profile.source_of_funds)

    pep_match = _screening_match(screening_results, "pep")
    adverse_media_match = _screening_match(screening_results, "adverse_media")
    ip_match = _screening_match(screening_results, "ip_risk")
    sanctions_match = _screening_match(screening_results, "sanctions")
    internal_match = _screening_match(screening_results, "internal_watchlist")
    exit_match = _screening_match(screening_results, "exit_list")
    beneficial_owner_concern = bool(
        identity_profile
        and identity_profile.beneficial_owner_different
        and (
            not identity_profile.beneficial_owner_name
            or not identity_profile.beneficial_owner_identification_number
        )
    )

    configured_factors: list[RiskFactor] = []
    factor_inputs = _build_factor_inputs(
        assessment_type=assessment_type,
        identity_profile=identity_profile,
        screening_results=screening_results,
    )
    factor_definitions = configured_model.get("factor_definitions") or []
    factor_rules = configured_model.get("factor_rules") or {}
    if factor_definitions:
        for definition in sorted(factor_definitions, key=lambda item: int(item.get("display_order", 0))):
            if not definition.get("is_active", True):
                continue
            value = factor_inputs.get(str(definition.get("source_key")))
            configured_factors.append(_evaluate_rule_set(definition, factor_rules.get(definition.get("factor_code"), []), value))

    factors = configured_factors or [
        RiskFactor("type_of_onboarding", 2, "identity_metadata", {"onboarding_type": onboarding_type, "fallback_used": True}),
        RiskFactor("geographic_risk", 3 if "non-resident" in _normalized(nationality) or "nrb" in _normalized(nationality) else 1, "identity_profile", {"nationality": nationality, "fallback_used": True}),
        RiskFactor("pep", 5 if pep_match else 0, "screening_result", {"matched": pep_match, "fallback_used": True}),
        RiskFactor("pep_close_associate", 5 if metadata.get("pep_associate") else 0, "identity_metadata", {"matched": bool(metadata.get("pep_associate")), "fallback_used": True}),
        RiskFactor("influential_person", 5 if ip_match else 1, "screening_result", {"matched": ip_match, "fallback_used": True}),
        RiskFactor("product_risk", 2, "product", {"product": "Individual BO Account", "fallback_used": True}),
        RiskFactor(
            "transactional_risk",
            _transaction_score(
                identity_profile.expected_transaction_range
                if identity_profile
                else None
            ),
            "identity_profile",
            {"expected_transaction_range": identity_profile.expected_transaction_range if identity_profile else None, "fallback_used": True},
        ),
        RiskFactor(
            "source_of_funds_verification",
            1 if assessment_type == "preliminary" or source_verified or not has_source_of_funds else 5,
            "identity_profile",
            {
                "source_of_funds": identity_profile.source_of_funds if identity_profile else None,
                "verified": source_verified,
                "assessed": assessment_type != "preliminary" and has_source_of_funds,
                "fallback_used": True,
            },
        ),
    ]
    factors.extend(
        [
            RiskFactor(
            "business_activity_risk",
            _lookup_score(business_category, business_scores) if metadata.get("business_category") else 0,
            "risk_business_categories",
            {
                "category": business_category,
                "provided": bool(metadata.get("business_category")),
                **(_lookup_score_snapshot(business_category, business_scores) if metadata.get("business_category") else {}),
            },
            ),
            RiskFactor(
            "profession_risk",
            _lookup_score(profession, profession_scores) if profession else 0,
            "risk_profession_categories",
            {
                "profession": profession,
                "provided": bool(profession),
                **(_lookup_score_snapshot(profession, profession_scores) if profession else {}),
            },
            ),
        ]
    )
    total_score = sum(factor.score for factor in factors)
    category = classify_score_with_bands(total_score, configured_model.get("threshold_bands") or [], thresholds)

    edd_reasons: list[str] = []
    if category == "HIGH":
        edd_reasons.append("risk_category_high")
    if pep_match:
        edd_reasons.append("pep_match_found")
    if ip_match:
        edd_reasons.append("ip_match_found")
    if adverse_media_match:
        edd_reasons.append("adverse_media_match_found")
    if assessment_type != "preliminary" and has_source_of_funds and not source_verified:
        edd_reasons.append("source_of_funds_not_verified")
    if beneficial_owner_concern:
        edd_reasons.append("beneficial_ownership_concern")
    if metadata.get("compliance_escalation"):
        edd_reasons.append("compliance_officer_escalation")

    hard_reject = sanctions_match or internal_match or exit_match
    if hard_reject:
        category = "HIGH"
        edd_reasons.append("hard_reject_screening_match")

    edd_required = bool(edd_reasons)
    status = "EDD_REQUIRED" if edd_required else "RISK_COMPLETED"
    decision = "REJECTED" if hard_reject else ("REVIEW_REQUIRED" if category != "LOW" or edd_required else "APPROVED")

    return {
        "assessment_type": assessment_type,
        "screening_request_id": screening_request_id,
        "status": status,
        "total_score": total_score,
        "risk_category": category,
        "rule_version": rule_version.version,
        "edd_required": edd_required,
        "edd_status": "EDD_REQUIRED" if edd_required else None,
        "edd_reasons": sorted(set(edd_reasons)),
        "decision": decision,
        "factors": factors,
        "rules_snapshot": {
            **(rule_version.rules_snapshot or DEFAULT_RULE_SNAPSHOT),
            "thresholds": thresholds,
            "threshold_bands": configured_model.get("threshold_bands") or [],
            "factor_definitions": configured_model.get("factor_definitions") or [],
            "factor_rules": configured_model.get("factor_rules") or {},
        },
    }


def _sync_active_rule_version(session: Session) -> RiskRuleVersion:
    rule = session.exec(
        select(RiskRuleVersion)
        .where(RiskRuleVersion.status == "ACTIVE")
        .order_by(desc(RiskRuleVersion.effective_date))
    ).first()
    if rule is None:
        rule = RiskRuleVersion(
            version="v1",
            thresholds=DEFAULT_THRESHOLDS,
            rules_snapshot=DEFAULT_RULE_SNAPSHOT,
        )
        session.add(rule)
        session.flush()
        session.refresh(rule)
    _sync_ensure_default_grading_config(session, rule)
    return rule


async def _async_active_rule_version(db: AsyncSession) -> RiskRuleVersion:
    result = await db.exec(
        select(RiskRuleVersion)
        .where(RiskRuleVersion.status == "ACTIVE")
        .order_by(desc(RiskRuleVersion.effective_date))
    )
    rule = result.first()
    if rule is None:
        rule = RiskRuleVersion(
            version="v1",
            thresholds=DEFAULT_THRESHOLDS,
            rules_snapshot=DEFAULT_RULE_SNAPSHOT,
        )
        db.add(rule)
        await db.flush()
        await db.refresh(rule)
    await _async_ensure_default_grading_config(db, rule)
    return rule


def _rule_snapshot(rule: RiskFactorRule) -> dict[str, Any]:
    return {
        "id": rule.id,
        "rule_code": rule.rule_code,
        "rule_type": rule.rule_type,
        "match_value": rule.match_value,
        "min_value": rule.min_value,
        "max_value": rule.max_value,
        "boolean_value": rule.boolean_value,
        "risk_score": rule.risk_score,
        "description": rule.description,
        "is_active": rule.is_active,
    }


def _definition_snapshot(definition: RiskFactorDefinition) -> dict[str, Any]:
    return {
        "id": definition.id,
        "factor_code": definition.factor_code,
        "factor_name": definition.factor_name,
        "factor_group": definition.factor_group,
        "source_key": definition.source_key,
        "aggregation_mode": definition.aggregation_mode,
        "description": definition.description,
        "is_active": definition.is_active,
        "display_order": definition.display_order,
    }


def _threshold_snapshot(band: RiskThresholdBand) -> dict[str, Any]:
    return {
        "id": band.id,
        "category_code": band.category_code,
        "category_name": band.category_name,
        "min_score": band.min_score,
        "max_score": band.max_score,
        "is_active": band.is_active,
    }


def _sync_ensure_default_grading_config(session: Session, rule: RiskRuleVersion) -> None:
    existing = session.exec(select(RiskFactorDefinition)).first()
    now = utc_now()
    definitions_by_code: dict[str, RiskFactorDefinition] = {}
    if existing is None:
        for code, name, group, source_key, aggregation, display_order in DEFAULT_FACTOR_DEFINITIONS:
            definition = RiskFactorDefinition(
                factor_code=code,
                factor_name=name,
                factor_group=group,
                source_key=source_key,
                aggregation_mode=aggregation,
                display_order=display_order,
                created_at=now,
                updated_at=now,
            )
            session.add(definition)
            session.flush()
            definitions_by_code[code] = definition
    else:
        definitions_by_code = {
            item.factor_code: item for item in session.exec(select(RiskFactorDefinition)).all()
        }
    if not definitions_by_code:
        return
    if not session.exec(select(RiskFactorRule).where(RiskFactorRule.rule_version_id == rule.id)).first():
        for factor_code, rules in DEFAULT_FACTOR_RULES.items():
            definition = definitions_by_code.get(factor_code)
            if definition is None:
                continue
            for code, rule_type, match, minimum, maximum, boolean, score in rules:
                session.add(
                    RiskFactorRule(
                        rule_version_id=rule.id,
                        factor_definition_id=definition.id,
                        rule_code=code,
                        rule_type=rule_type,
                        match_value=match,
                        min_value=minimum,
                        max_value=maximum,
                        boolean_value=boolean,
                        risk_score=score,
                        created_at=now,
                        updated_at=now,
                    )
                )
    if not session.exec(select(RiskThresholdBand).where(RiskThresholdBand.rule_version_id == rule.id)).first():
        for band in DEFAULT_THRESHOLD_BANDS:
            session.add(RiskThresholdBand(rule_version_id=rule.id, **band, created_at=now, updated_at=now))
    if not session.exec(select(RiskTransactionRange).where(RiskTransactionRange.rule_version_id == rule.id)).first():
        for code, name, minimum, maximum, score in [
            ("BELOW_BDT_1M", "< BDT 1 Million", None, 999999, 1),
            ("BDT_1M_5M", "BDT 1M - 5M", 1000000, 5000000, 2),
            ("BDT_5M_50M", "BDT 5M - 50M", 5000000, 50000000, 3),
            ("ABOVE_BDT_50M", "> BDT 50M", 50000000, None, 5),
        ]:
            session.add(RiskTransactionRange(rule_version_id=rule.id, range_code=code, range_name=name, min_amount=minimum, max_amount=maximum, risk_score=score, created_at=now, updated_at=now))
    if not session.exec(select(RiskProductCategory).where(RiskProductCategory.rule_version_id == rule.id)).first():
        session.add(RiskProductCategory(rule_version_id=rule.id, product_code="INDIVIDUAL_BO_ACCOUNT", product_name="Individual BO Account", product_category="BO Account", risk_score=2, created_at=now, updated_at=now))
    session.flush()


async def _async_ensure_default_grading_config(db: AsyncSession, rule: RiskRuleVersion) -> None:
    result = await db.exec(select(RiskFactorDefinition))
    existing = result.first()
    now = utc_now()
    definitions_by_code: dict[str, RiskFactorDefinition] = {}
    if existing is None:
        for code, name, group, source_key, aggregation, display_order in DEFAULT_FACTOR_DEFINITIONS:
            definition = RiskFactorDefinition(factor_code=code, factor_name=name, factor_group=group, source_key=source_key, aggregation_mode=aggregation, display_order=display_order, created_at=now, updated_at=now)
            db.add(definition)
            await db.flush()
            definitions_by_code[code] = definition
    else:
        definitions_result = await db.exec(select(RiskFactorDefinition))
        definitions_by_code = {item.factor_code: item for item in definitions_result.all()}
    rules_result = await db.exec(select(RiskFactorRule).where(RiskFactorRule.rule_version_id == rule.id))
    if rules_result.first() is None:
        for factor_code, rules in DEFAULT_FACTOR_RULES.items():
            definition = definitions_by_code.get(factor_code)
            if definition is None:
                continue
            for code, rule_type, match, minimum, maximum, boolean, score in rules:
                db.add(RiskFactorRule(rule_version_id=rule.id, factor_definition_id=definition.id, rule_code=code, rule_type=rule_type, match_value=match, min_value=minimum, max_value=maximum, boolean_value=boolean, risk_score=score, created_at=now, updated_at=now))
    thresholds_result = await db.exec(select(RiskThresholdBand).where(RiskThresholdBand.rule_version_id == rule.id))
    if thresholds_result.first() is None:
        for band in DEFAULT_THRESHOLD_BANDS:
            db.add(RiskThresholdBand(rule_version_id=rule.id, **band, created_at=now, updated_at=now))
    transaction_result = await db.exec(select(RiskTransactionRange).where(RiskTransactionRange.rule_version_id == rule.id))
    if transaction_result.first() is None:
        for code, name, minimum, maximum, score in [
            ("BELOW_BDT_1M", "< BDT 1 Million", None, 999999, 1),
            ("BDT_1M_5M", "BDT 1M - 5M", 1000000, 5000000, 2),
            ("BDT_5M_50M", "BDT 5M - 50M", 5000000, 50000000, 3),
            ("ABOVE_BDT_50M", "> BDT 50M", 50000000, None, 5),
        ]:
            db.add(RiskTransactionRange(rule_version_id=rule.id, range_code=code, range_name=name, min_amount=minimum, max_amount=maximum, risk_score=score, created_at=now, updated_at=now))
    product_result = await db.exec(select(RiskProductCategory).where(RiskProductCategory.rule_version_id == rule.id))
    if product_result.first() is None:
        db.add(RiskProductCategory(rule_version_id=rule.id, product_code="INDIVIDUAL_BO_ACCOUNT", product_name="Individual BO Account", product_category="BO Account", risk_score=2, created_at=now, updated_at=now))
    await db.flush()


def _sync_grading_model(session: Session, rule: RiskRuleVersion) -> dict[str, Any]:
    definitions = list(session.exec(select(RiskFactorDefinition).order_by(RiskFactorDefinition.display_order.asc())).all())
    rules = list(session.exec(select(RiskFactorRule).where(RiskFactorRule.rule_version_id == rule.id)).all())
    bands = list(session.exec(select(RiskThresholdBand).where(RiskThresholdBand.rule_version_id == rule.id).where(RiskThresholdBand.is_active == True)).all())
    definitions_by_id = {item.id: item for item in definitions}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for rule_row in rules:
        definition = definitions_by_id.get(rule_row.factor_definition_id)
        if definition is None:
            continue
        grouped.setdefault(definition.factor_code, []).append(_rule_snapshot(rule_row))
    transactions = list(session.exec(select(RiskTransactionRange).where(RiskTransactionRange.rule_version_id == rule.id).where(RiskTransactionRange.is_active == True)).all())
    if transactions:
        grouped["transactional_risk"] = [
            {
                "id": item.id,
                "rule_code": item.range_code,
                "rule_type": "range",
                "match_value": None,
                "min_value": item.min_amount,
                "max_value": item.max_amount,
                "boolean_value": None,
                "risk_score": item.risk_score,
                "description": item.range_name,
                "is_active": item.is_active,
            }
            for item in transactions
        ]
    products = list(session.exec(select(RiskProductCategory).where(RiskProductCategory.rule_version_id == rule.id).where(RiskProductCategory.is_active == True)).all())
    if products:
        grouped["product_risk"] = [
            {
                "id": item.id,
                "rule_code": item.product_code,
                "rule_type": "normalized_match",
                "match_value": item.product_code.lower(),
                "risk_score": item.risk_score,
                "description": item.product_name,
                "is_active": item.is_active,
            }
            for item in products
        ]
    return {
        "factor_definitions": [_definition_snapshot(item) for item in definitions],
        "factor_rules": grouped,
        "threshold_bands": [_threshold_snapshot(item) for item in bands],
    }


async def _async_grading_model(db: AsyncSession, rule: RiskRuleVersion) -> dict[str, Any]:
    definitions = list((await db.exec(select(RiskFactorDefinition).order_by(RiskFactorDefinition.display_order.asc()))).all())
    rules = list((await db.exec(select(RiskFactorRule).where(RiskFactorRule.rule_version_id == rule.id))).all())
    bands = list((await db.exec(select(RiskThresholdBand).where(RiskThresholdBand.rule_version_id == rule.id).where(RiskThresholdBand.is_active == True))).all())
    definitions_by_id = {item.id: item for item in definitions}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for rule_row in rules:
        definition = definitions_by_id.get(rule_row.factor_definition_id)
        if definition is None:
            continue
        grouped.setdefault(definition.factor_code, []).append(_rule_snapshot(rule_row))
    transactions = list((await db.exec(select(RiskTransactionRange).where(RiskTransactionRange.rule_version_id == rule.id).where(RiskTransactionRange.is_active == True))).all())
    if transactions:
        grouped["transactional_risk"] = [
            {
                "id": item.id,
                "rule_code": item.range_code,
                "rule_type": "range",
                "match_value": None,
                "min_value": item.min_amount,
                "max_value": item.max_amount,
                "boolean_value": None,
                "risk_score": item.risk_score,
                "description": item.range_name,
                "is_active": item.is_active,
            }
            for item in transactions
        ]
    products = list((await db.exec(select(RiskProductCategory).where(RiskProductCategory.rule_version_id == rule.id).where(RiskProductCategory.is_active == True))).all())
    if products:
        grouped["product_risk"] = [
            {
                "id": item.id,
                "rule_code": item.product_code,
                "rule_type": "normalized_match",
                "match_value": item.product_code.lower(),
                "risk_score": item.risk_score,
                "description": item.product_name,
                "is_active": item.is_active,
            }
            for item in products
        ]
    return {
        "factor_definitions": [_definition_snapshot(item) for item in definitions],
        "factor_rules": grouped,
        "threshold_bands": [_threshold_snapshot(item) for item in bands],
    }


def _business_scores(rows: list[RiskBusinessCategory]) -> dict[str, Any]:
    scores: dict[str, Any] = {}
    for row in rows:
        if not row.is_active:
            continue
        snapshot = {
            "category_id": row.id,
            "category_code": row.category_code,
            "category_name": row.category_name,
            "risk_score": row.risk_score,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        scores[_normalized(row.category_code)] = snapshot
        scores[_normalized(row.category_name)] = snapshot
    scores.setdefault("default", {"category_code": "DEFAULT", "category_name": "default", "risk_score": 3, "fallback_used": True})
    return scores


def _profession_scores(rows: list[RiskProfessionCategory]) -> dict[str, Any]:
    scores: dict[str, Any] = {}
    for row in rows:
        if not row.is_active:
            continue
        snapshot = {
            "profession_id": row.id,
            "profession_code": row.profession_code,
            "profession_name": row.profession_name,
            "risk_score": row.risk_score,
            "updated_at": row.updated_at.isoformat() if row.updated_at else None,
        }
        scores[_normalized(row.profession_code)] = snapshot
        scores[_normalized(row.profession_name)] = snapshot
    scores.setdefault("default", {"profession_code": "DEFAULT", "profession_name": "default", "risk_score": 3, "fallback_used": True})
    return scores


def _sync_collect(session: Session, session_id: int, screening_request_id: int | None):
    identity = session.exec(select(CustomerIdentityProfile).where(CustomerIdentityProfile.session_id == session_id)).first()
    addresses = []
    nominee = None
    if identity:
        addresses = list(session.exec(select(CustomerAddress).where(CustomerAddress.profile_id == identity.id)).all())
        nominee = session.exec(select(CustomerNominee).where(CustomerNominee.profile_id == identity.id)).first()
    ocr = session.exec(select(OnboardingOCRExtraction).where(OnboardingOCRExtraction.session_id == session_id)).first()
    results: list[ScreeningResult] = []
    if screening_request_id is not None:
        results = list(session.exec(select(ScreeningResult).where(ScreeningResult.screening_request_id == screening_request_id)).all())
    business = _business_scores(list(session.exec(select(RiskBusinessCategory)).all()))
    profession = _profession_scores(list(session.exec(select(RiskProfessionCategory)).all()))
    return identity, addresses, nominee, ocr, results, business, profession


async def _async_collect(db: AsyncSession, session_id: int, screening_request_id: int | None):
    result = await db.exec(select(CustomerIdentityProfile).where(CustomerIdentityProfile.session_id == session_id))
    identity = result.first()
    addresses = []
    nominee = None
    if identity:
        address_result = await db.exec(select(CustomerAddress).where(CustomerAddress.profile_id == identity.id))
        addresses = list(address_result.all())
        nominee_result = await db.exec(select(CustomerNominee).where(CustomerNominee.profile_id == identity.id))
        nominee = nominee_result.first()
    ocr_result = await db.exec(select(OnboardingOCRExtraction).where(OnboardingOCRExtraction.session_id == session_id))
    ocr = ocr_result.first()
    results: list[ScreeningResult] = []
    if screening_request_id is not None:
        screening_result = await db.exec(select(ScreeningResult).where(ScreeningResult.screening_request_id == screening_request_id))
        results = list(screening_result.all())
    business_result = await db.exec(select(RiskBusinessCategory))
    profession_result = await db.exec(select(RiskProfessionCategory))
    return (
        identity,
        addresses,
        nominee,
        ocr,
        results,
        _business_scores(list(business_result.all())),
        _profession_scores(list(profession_result.all())),
    )


def _sync_persist(
    session: Session,
    *,
    session_id: int,
    actor_user_id: int | None,
    payload: dict[str, Any],
) -> CustomerRiskAssessment:
    now = utc_now()
    existing = session.exec(
        select(CustomerRiskAssessment)
        .where(CustomerRiskAssessment.session_id == session_id)
        .where(CustomerRiskAssessment.assessment_type == payload["assessment_type"])
        .order_by(desc(CustomerRiskAssessment.created_at))
    ).first()
    previous_score = existing.total_score if existing else None
    if existing is None:
        existing = CustomerRiskAssessment(session_id=session_id, rule_version=payload["rule_version"], assessment_type=payload["assessment_type"])
    existing.screening_request_id = payload.get("screening_request_id")
    existing.status = payload["status"]
    existing.total_score = payload["total_score"]
    existing.risk_category = payload["risk_category"]
    existing.rule_version = payload["rule_version"]
    existing.edd_required = payload["edd_required"]
    existing.edd_status = payload["edd_status"]
    existing.edd_reasons = payload["edd_reasons"]
    existing.rules_snapshot = payload["rules_snapshot"]
    existing.calculated_at = now
    existing.updated_at = now
    session.add(existing)
    session.flush()
    session.exec(delete(CustomerRiskFactorScore).where(CustomerRiskFactorScore.assessment_id == existing.id))
    for factor in payload["factors"]:
        session.add(
            CustomerRiskFactorScore(
                assessment_id=existing.id,
                factor_name=factor.name,
                factor_score=factor.score,
                source=factor.source,
                source_value=factor.value,
                rule_version=payload["rule_version"],
            )
        )
    session.add(
        AuditLog(
            session_id=session_id,
            actor_user_id=actor_user_id,
            event_type="risk_calculated",
            event_status="success",
            message=f"{payload['assessment_type']} risk assessment calculated.",
            payload={
                "previous_score": previous_score,
                "new_score": payload["total_score"],
                "risk_category": payload["risk_category"],
                "rule_version": payload["rule_version"],
                "edd_required": payload["edd_required"],
            },
        )
    )
    session.flush()
    session.refresh(existing)
    return existing


async def _async_persist(
    db: AsyncSession,
    *,
    session_id: int,
    actor_user_id: int | None,
    payload: dict[str, Any],
) -> CustomerRiskAssessment:
    now = utc_now()
    result = await db.exec(
        select(CustomerRiskAssessment)
        .where(CustomerRiskAssessment.session_id == session_id)
        .where(CustomerRiskAssessment.assessment_type == payload["assessment_type"])
        .order_by(desc(CustomerRiskAssessment.created_at))
    )
    existing = result.first()
    previous_score = existing.total_score if existing else None
    if existing is None:
        existing = CustomerRiskAssessment(session_id=session_id, rule_version=payload["rule_version"], assessment_type=payload["assessment_type"])
    existing.screening_request_id = payload.get("screening_request_id")
    existing.status = payload["status"]
    existing.total_score = payload["total_score"]
    existing.risk_category = payload["risk_category"]
    existing.rule_version = payload["rule_version"]
    existing.edd_required = payload["edd_required"]
    existing.edd_status = payload["edd_status"]
    existing.edd_reasons = payload["edd_reasons"]
    existing.rules_snapshot = payload["rules_snapshot"]
    existing.calculated_at = now
    existing.updated_at = now
    db.add(existing)
    await db.flush()
    await db.exec(delete(CustomerRiskFactorScore).where(CustomerRiskFactorScore.assessment_id == existing.id))
    for factor in payload["factors"]:
        db.add(
            CustomerRiskFactorScore(
                assessment_id=existing.id,
                factor_name=factor.name,
                factor_score=factor.score,
                source=factor.source,
                source_value=factor.value,
                rule_version=payload["rule_version"],
            )
        )
    db.add(
        AuditLog(
            session_id=session_id,
            actor_user_id=actor_user_id,
            event_type="risk_calculated",
            event_status="success",
            message=f"{payload['assessment_type']} risk assessment calculated.",
            payload={
                "previous_score": previous_score,
                "new_score": payload["total_score"],
                "risk_category": payload["risk_category"],
                "rule_version": payload["rule_version"],
                "edd_required": payload["edd_required"],
            },
        )
    )
    await db.flush()
    await db.refresh(existing)
    return existing


def calculate_and_persist_sync(
    session: Session,
    *,
    session_id: int,
    assessment_type: str,
    screening_request_id: int | None = None,
    actor_user_id: int | None = None,
) -> tuple[CustomerRiskAssessment, dict[str, Any]]:
    rule = _sync_active_rule_version(session)
    grading_model = _sync_grading_model(session, rule)
    identity, addresses, nominee, ocr, results, business, profession = _sync_collect(session, session_id, screening_request_id)
    payload = calculate_assessment_payload(
        assessment_type=assessment_type,
        rule_version=rule,
        identity_profile=identity,
        addresses=addresses,
        nominee=nominee,
        ocr=ocr,
        screening_results=results,
        business_scores=business,
        profession_scores=profession,
        configured_model=grading_model,
        screening_request_id=screening_request_id,
    )
    return _sync_persist(session, session_id=session_id, actor_user_id=actor_user_id, payload=payload), payload


async def calculate_and_persist_async(
    db: AsyncSession,
    *,
    session_id: int,
    assessment_type: str,
    screening_request_id: int | None = None,
    actor_user_id: int | None = None,
) -> tuple[CustomerRiskAssessment, dict[str, Any]]:
    rule = await _async_active_rule_version(db)
    grading_model = await _async_grading_model(db, rule)
    identity, addresses, nominee, ocr, results, business, profession = await _async_collect(db, session_id, screening_request_id)
    payload = calculate_assessment_payload(
        assessment_type=assessment_type,
        rule_version=rule,
        identity_profile=identity,
        addresses=addresses,
        nominee=nominee,
        ocr=ocr,
        screening_results=results,
        business_scores=business,
        profession_scores=profession,
        configured_model=grading_model,
        screening_request_id=screening_request_id,
    )
    return await _async_persist(db, session_id=session_id, actor_user_id=actor_user_id, payload=payload), payload


def latest_assessment_sync(session: Session, session_id: int, assessment_type: str | None = None) -> CustomerRiskAssessment | None:
    statement = select(CustomerRiskAssessment).where(CustomerRiskAssessment.session_id == session_id)
    if assessment_type:
        statement = statement.where(CustomerRiskAssessment.assessment_type == assessment_type)
    return session.exec(statement.order_by(desc(CustomerRiskAssessment.calculated_at))).first()


async def latest_assessment_async(db: AsyncSession, session_id: int, assessment_type: str | None = None) -> CustomerRiskAssessment | None:
    statement = select(CustomerRiskAssessment).where(CustomerRiskAssessment.session_id == session_id)
    if assessment_type:
        statement = statement.where(CustomerRiskAssessment.assessment_type == assessment_type)
    result = await db.exec(statement.order_by(desc(CustomerRiskAssessment.calculated_at)))
    return result.first()


async def list_factor_scores_async(db: AsyncSession, assessment_id: int) -> list[CustomerRiskFactorScore]:
    result = await db.exec(
        select(CustomerRiskFactorScore)
        .where(CustomerRiskFactorScore.assessment_id == assessment_id)
        .order_by(CustomerRiskFactorScore.id.asc())
    )
    return list(result.all())


def list_factor_scores_sync(session: Session, assessment_id: int) -> list[CustomerRiskFactorScore]:
    return list(
        session.exec(
            select(CustomerRiskFactorScore)
            .where(CustomerRiskFactorScore.assessment_id == assessment_id)
            .order_by(CustomerRiskFactorScore.id.asc())
        ).all()
    )


def ensure_review_case_sync(session: Session, screening: ScreeningRequest, assessment: CustomerRiskAssessment) -> None:
    if not assessment.edd_required and assessment.risk_category != "HIGH":
        return
    case = session.exec(
        select(ComplianceCase).where(ComplianceCase.screening_request_id == screening.id)
    ).first()
    if case is None:
        case = ComplianceCase(screening_request_id=screening.id)
    case.status = "OPEN"
    case.queue_name = "COMPLIANCE_REVIEW_CASE"
    case.resolution_note = None
    case.resolved_at = None
    case.updated_at = utc_now()
    session.add(case)
