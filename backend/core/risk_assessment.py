from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import logging
from types import SimpleNamespace
from typing import Any

from sqlalchemy import delete, desc, or_
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
    RiskBusinessCategory,
    RiskFactorDefinition,
    RiskFactorRule,
    RiskProductCategory,
    RiskProfessionCategory,
    RiskRuleVersion,
    RiskThresholdBand,
    ScreeningRequest,
    ScreeningResult,
)


logger = logging.getLogger(__name__)

DEFAULT_THRESHOLDS = {"low_max": 9, "medium_max": 14}
PREVIEW_PROFILE_FIELDS = {
    "profession",
    "business_category",
    "product_type",
    "nationality",
    "residency_status",
    "source_of_funds",
    "expected_transaction_range",
    "beneficial_owner_different",
    "beneficial_owner_name",
    "beneficial_owner_identification_number",
    "beneficial_owner_nationality",
    "beneficial_owner_relationship",
    "onboarding_channel",
    "payload_metadata",
}


@dataclass
class RiskFactor:
    name: str
    code: str
    score: int
    source: str
    source_table: str | None
    selected_value: str | None
    rule_id: int | None
    match_status: str
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


def _present(value: Any) -> bool:
    return value is not None and str(value).strip() != ""


def _screening_matches(results: list[ScreeningResult], screening_type: str) -> list[ScreeningResult]:
    return [
        result
        for result in results
        if result.screening_type == screening_type and result.outcome != "NO_MATCH"
    ]


def _screening_match(results: list[ScreeningResult], screening_type: str) -> bool:
    return bool(_screening_matches(results, screening_type))


def _result_has_marker(result: ScreeningResult, marker: str) -> bool:
    marker_text = _normalized(marker)
    haystack = [
        result.outcome,
        result.list_name,
        result.evidence_summary,
        " ".join(result.risk_factors or []),
        str(result.matched_fields or {}),
        str(result.raw_payload or {}),
    ]
    return any(marker_text in _normalized(item) for item in haystack)


def _screening_marker(results: list[ScreeningResult], screening_type: str, marker: str) -> bool:
    return any(_result_has_marker(result, marker) for result in _screening_matches(results, screening_type))


def _rule_matches(rule: dict[str, Any], value: Any) -> bool:
    rule_type = rule.get("rule_type")
    if rule_type == "boolean":
        return bool(value) is bool(rule.get("boolean_value"))
    if rule_type == "normalized_match":
        return _normalized(value) == _normalized(rule.get("match_value") or rule.get("rule_code"))
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


def _rule_value(rule: dict[str, Any]) -> str:
    return _normalized(rule.get("match_value") or rule.get("rule_code"))


def _definition_snapshot(row: RiskFactorDefinition) -> dict[str, Any]:
    return {
        "id": row.id,
        "factor_code": row.factor_code,
        "factor_name": row.factor_name,
        "factor_group": row.factor_group,
        "source_key": row.source_key,
        "aggregation_mode": row.aggregation_mode,
        "is_active": row.is_active,
        "display_order": row.display_order,
    }


def _rule_snapshot(row: RiskFactorRule) -> dict[str, Any]:
    return {
        "id": row.id,
        "rule_code": row.rule_code,
        "rule_type": row.rule_type,
        "match_value": row.match_value,
        "min_value": row.min_value,
        "max_value": row.max_value,
        "boolean_value": row.boolean_value,
        "risk_score": row.risk_score,
        "description": row.description,
        "is_active": row.is_active,
    }


def _threshold_snapshot(row: RiskThresholdBand) -> dict[str, Any]:
    return {
        "id": row.id,
        "category_code": row.category_code,
        "category_name": row.category_name,
        "min_score": row.min_score,
        "max_score": row.max_score,
        "is_active": row.is_active,
    }


def _category_map(rows: list[Any], code_attr: str, name_attr: str, source_table: str) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not row.is_active:
            continue
        code = getattr(row, code_attr)
        name = getattr(row, name_attr)
        snapshot = {
            "id": row.id,
            "code": code,
            "name": name,
            "risk_score": row.risk_score,
            "source_table": source_table,
        }
        result[_normalized(code)] = snapshot
        result[_normalized(name)] = snapshot
    return result


def _product_map(rows: list[RiskProductCategory]) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for row in rows:
        if not row.is_active:
            continue
        snapshot = {
            "id": row.id,
            "code": row.product_code,
            "name": row.product_name,
            "category": row.product_category,
            "risk_score": row.risk_score,
            "source_table": "risk_product_categories",
        }
        result[_normalized(row.product_code)] = snapshot
        result[_normalized(row.product_name)] = snapshot
    return result


def _business_scores(rows: list[RiskBusinessCategory]) -> dict[str, Any]:
    return _category_map(rows, "category_code", "category_name", "risk_business_categories")


def _profession_scores(rows: list[RiskProfessionCategory]) -> dict[str, Any]:
    return _category_map(rows, "profession_code", "profession_name", "risk_profession_categories")


def _factor_inputs(
    *,
    assessment_type: str,
    identity_profile: CustomerIdentityProfile | None,
    screening_results: list[ScreeningResult],
) -> dict[str, Any]:
    metadata = identity_profile.payload_metadata if identity_profile else {}
    return {
        "profession": identity_profile.profession if identity_profile else None,
        "business_category": identity_profile.business_category if identity_profile else None,
        "product_type": identity_profile.product_type if identity_profile else None,
        "nationality": identity_profile.nationality if identity_profile else None,
        "residency_status": identity_profile.residency_status if identity_profile else None,
        "source_of_funds": identity_profile.source_of_funds if identity_profile else None,
        "expected_transaction_range": identity_profile.expected_transaction_range if identity_profile else None,
        "beneficial_owner_different": bool(identity_profile and identity_profile.beneficial_owner_different),
        "onboarding_channel": identity_profile.onboarding_channel if identity_profile else None,
        "pep_match": _screening_match(screening_results, "pep"),
        "pep_associate_match": _screening_marker(screening_results, "pep", "associate") or bool(metadata.get("pep_associate")),
        "adverse_media_match": _screening_match(screening_results, "adverse_media"),
        "ip_risk_match": _screening_match(screening_results, "ip_risk"),
        "high_risk_ip_result": _screening_marker(screening_results, "ip_risk", "high"),
        "sanctions_match": _screening_match(screening_results, "sanctions"),
        "exit_list_match": _screening_match(screening_results, "exit_list"),
        "internal_watchlist_match": _screening_match(screening_results, "internal_watchlist"),
        "assessment_type": assessment_type,
    }


def _missing_factor(
    definition: dict[str, Any],
    *,
    value: Any,
    source: str,
    source_table: str | None,
    match_status: str,
) -> RiskFactor:
    return RiskFactor(
        name=str(definition.get("factor_name") or definition["factor_code"]),
        code=str(definition["factor_code"]),
        score=0,
        source=source,
        source_table=source_table,
        selected_value=str(value) if value is not None else None,
        rule_id=None,
        match_status=match_status,
        value={
            "submitted_value": value,
            "match_status": match_status,
            "risk_score": 0,
        },
    )


def _evaluate_rule_factor(
    definition: dict[str, Any],
    rules: list[dict[str, Any]],
    value: Any,
) -> RiskFactor:
    source_key = str(definition.get("source_key") or definition["factor_code"])
    if not _present(value) and not isinstance(value, bool):
        logger.warning("Risk factor input missing: factor=%s source_key=%s", definition["factor_code"], source_key)
        return _missing_factor(definition, value=value, source=source_key, source_table="risk_factor_rules", match_status="missing_value")

    active_rules = [rule for rule in rules if rule.get("is_active", True)]
    matches = [rule for rule in active_rules if _rule_matches(rule, value)]
    selected = None
    if matches:
        selected = max(matches, key=lambda item: int(item.get("risk_score", 0))) if definition.get("aggregation_mode") == "max" else matches[0]

    if selected is None:
        logger.warning(
            "Risk rule lookup failed: factor=%s source_key=%s submitted_value=%r",
            definition["factor_code"],
            source_key,
            value,
        )
        return _missing_factor(definition, value=value, source=source_key, source_table="risk_factor_rules", match_status="missing_config")

    score = int(selected.get("risk_score", 0))
    selected_value = str(value) if value is not None else None
    return RiskFactor(
        name=str(definition.get("factor_name") or definition["factor_code"]),
        code=str(definition["factor_code"]),
        score=score,
        source=source_key,
        source_table="risk_factor_rules",
        selected_value=selected_value,
        rule_id=selected.get("id"),
        match_status="matched",
        value={
            "submitted_value": value,
            "matched_rule_id": selected.get("id"),
            "matched_rule_code": selected.get("rule_code"),
            "rule_type": selected.get("rule_type"),
            "risk_score": score,
            "match_status": "matched",
        },
    )


def _evaluate_category_factor(
    definition: dict[str, Any],
    value: Any,
    lookup: dict[str, dict[str, Any]],
    source_table: str,
) -> RiskFactor:
    source_key = str(definition.get("source_key") or definition["factor_code"])
    if not _present(value):
        logger.warning("Risk category input missing: factor=%s source_key=%s", definition["factor_code"], source_key)
        return _missing_factor(definition, value=value, source=source_key, source_table=source_table, match_status="missing_value")

    matched = lookup.get(_normalized(value))
    if matched is None:
        logger.warning(
            "Risk category lookup failed: factor=%s source_key=%s source_table=%s submitted_value=%r",
            definition["factor_code"],
            source_key,
            source_table,
            value,
        )
        return _missing_factor(definition, value=value, source=source_key, source_table=source_table, match_status="missing_config")

    score = int(matched["risk_score"])
    return RiskFactor(
        name=str(definition.get("factor_name") or definition["factor_code"]),
        code=str(definition["factor_code"]),
        score=score,
        source=source_key,
        source_table=source_table,
        selected_value=str(value),
        rule_id=matched.get("id"),
        match_status="matched",
        value={
            "submitted_value": value,
            "matched_id": matched.get("id"),
            "matched_code": matched.get("code"),
            "matched_name": matched.get("name"),
            "risk_score": score,
            "match_status": "matched",
        },
    )


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
    del addresses, nominee, ocr
    configured_model = configured_model or {}
    thresholds = rule_version.thresholds or DEFAULT_THRESHOLDS
    factor_inputs = _factor_inputs(
        assessment_type=assessment_type,
        identity_profile=identity_profile,
        screening_results=screening_results,
    )
    factor_rules = configured_model.get("factor_rules") or {}
    product_scores = configured_model.get("product_scores") or {}
    factors: list[RiskFactor] = []

    for definition in sorted(configured_model.get("factor_definitions") or [], key=lambda item: int(item.get("display_order", 0))):
        if not definition.get("is_active", True):
            continue
        source_key = str(definition.get("source_key") or definition["factor_code"])
        value = factor_inputs.get(source_key)
        if source_key == "profession":
            factors.append(_evaluate_category_factor(definition, value, profession_scores, "risk_profession_categories"))
        elif source_key == "business_category":
            factors.append(_evaluate_category_factor(definition, value, business_scores, "risk_business_categories"))
        elif source_key == "product_type":
            factors.append(_evaluate_category_factor(definition, value, product_scores, "risk_product_categories"))
        else:
            factors.append(_evaluate_rule_factor(definition, factor_rules.get(str(definition["factor_code"]), []), value))

    total_score = sum(factor.score for factor in factors)
    category = classify_score_with_bands(total_score, configured_model.get("threshold_bands") or [], thresholds)
    pep_match = bool(factor_inputs["pep_match"])
    ip_match = bool(factor_inputs["ip_risk_match"])
    adverse_media_match = bool(factor_inputs["adverse_media_match"])
    sanctions_match = bool(factor_inputs["sanctions_match"])
    internal_match = bool(factor_inputs["internal_watchlist_match"])
    exit_match = bool(factor_inputs["exit_list_match"])
    beneficial_owner_concern = bool(
        identity_profile
        and identity_profile.beneficial_owner_different
        and (
            not identity_profile.beneficial_owner_name
            or not identity_profile.beneficial_owner_identification_number
        )
    )

    edd_reasons: list[str] = []
    if category == "HIGH":
        edd_reasons.append("risk_category_high")
    if pep_match:
        edd_reasons.append("pep_match_found")
    if ip_match:
        edd_reasons.append("ip_match_found")
    if adverse_media_match:
        edd_reasons.append("adverse_media_match_found")
    if beneficial_owner_concern:
        edd_reasons.append("beneficial_ownership_concern")

    hard_reject = sanctions_match or internal_match or exit_match
    if hard_reject:
        category = "HIGH"
        edd_reasons.append("hard_reject_screening_match")

    edd_required = bool(edd_reasons)
    return {
        "assessment_type": assessment_type,
        "screening_request_id": screening_request_id,
        "status": "EDD_REQUIRED" if edd_required else "RISK_COMPLETED",
        "total_score": total_score,
        "risk_category": category,
        "rule_version": rule_version.version,
        "edd_required": edd_required,
        "edd_status": "EDD_REQUIRED" if edd_required else None,
        "edd_reasons": sorted(set(edd_reasons)),
        "decision": "REJECTED" if hard_reject else ("REVIEW_REQUIRED" if category != "LOW" or edd_required else "APPROVED"),
        "factors": factors,
        "rules_snapshot": {
            **(rule_version.rules_snapshot or {}),
            "thresholds": thresholds,
            "threshold_bands": configured_model.get("threshold_bands") or [],
            "factor_definitions": configured_model.get("factor_definitions") or [],
            "factor_rules": configured_model.get("factor_rules") or {},
        },
    }


def _project_identity_profile(
    identity_profile: CustomerIdentityProfile | None,
    overrides: dict[str, Any] | None,
) -> Any:
    overrides = overrides or {}
    payload_metadata = dict(getattr(identity_profile, "payload_metadata", {}) or {})
    if isinstance(overrides.get("metadata"), dict):
        payload_metadata.update(overrides["metadata"])

    projected = {
        field_name: getattr(identity_profile, field_name, None) if identity_profile is not None else None
        for field_name in PREVIEW_PROFILE_FIELDS
        if field_name != "payload_metadata"
    }
    projected["payload_metadata"] = payload_metadata

    for field_name, value in overrides.items():
        if field_name in PREVIEW_PROFILE_FIELDS and field_name != "payload_metadata":
            projected[field_name] = value

    return SimpleNamespace(**projected)


def _sync_active_rule_version(session: Session) -> RiskRuleVersion:
    rule = session.exec(
        select(RiskRuleVersion)
        .where(RiskRuleVersion.status == "ACTIVE")
        .order_by(desc(RiskRuleVersion.effective_date))
    ).first()
    if rule is None:
        rule = RiskRuleVersion(version="v1", thresholds=DEFAULT_THRESHOLDS, rules_snapshot={"source": "database"})
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
        rule = RiskRuleVersion(version="v1", thresholds=DEFAULT_THRESHOLDS, rules_snapshot={"source": "database"})
        db.add(rule)
        await db.flush()
        await db.refresh(rule)
    await _async_ensure_default_grading_config(db, rule)
    return rule


def _sync_ensure_default_grading_config(session: Session, rule: RiskRuleVersion) -> None:
    del rule
    session.flush()


async def _async_ensure_default_grading_config(db: AsyncSession, rule: RiskRuleVersion) -> None:
    del rule
    await db.flush()


def _sync_grading_model(session: Session, rule: RiskRuleVersion) -> dict[str, Any]:
    definitions = list(session.exec(select(RiskFactorDefinition).order_by(RiskFactorDefinition.display_order.asc())).all())
    rules = list(session.exec(select(RiskFactorRule).where(RiskFactorRule.rule_version_id == rule.id).where(RiskFactorRule.is_active == True)).all())
    bands = list(session.exec(select(RiskThresholdBand).where(RiskThresholdBand.rule_version_id == rule.id).where(RiskThresholdBand.is_active == True)).all())
    products = list(session.exec(select(RiskProductCategory).where(RiskProductCategory.rule_version_id == rule.id).where(RiskProductCategory.is_active == True)).all())
    definitions_by_id = {item.id: item for item in definitions}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for rule_row in rules:
        definition = definitions_by_id.get(rule_row.factor_definition_id)
        if definition is not None:
            grouped.setdefault(definition.factor_code, []).append(_rule_snapshot(rule_row))
    return {
        "factor_definitions": [_definition_snapshot(item) for item in definitions],
        "factor_rules": grouped,
        "threshold_bands": [_threshold_snapshot(item) for item in bands],
        "product_scores": _product_map(products),
    }


async def _async_grading_model(db: AsyncSession, rule: RiskRuleVersion) -> dict[str, Any]:
    definitions = list((await db.exec(select(RiskFactorDefinition).order_by(RiskFactorDefinition.display_order.asc()))).all())
    rules = list((await db.exec(select(RiskFactorRule).where(RiskFactorRule.rule_version_id == rule.id).where(RiskFactorRule.is_active == True))).all())
    bands = list((await db.exec(select(RiskThresholdBand).where(RiskThresholdBand.rule_version_id == rule.id).where(RiskThresholdBand.is_active == True))).all())
    products = list((await db.exec(select(RiskProductCategory).where(RiskProductCategory.rule_version_id == rule.id).where(RiskProductCategory.is_active == True))).all())
    definitions_by_id = {item.id: item for item in definitions}
    grouped: dict[str, list[dict[str, Any]]] = {}
    for rule_row in rules:
        definition = definitions_by_id.get(rule_row.factor_definition_id)
        if definition is not None:
            grouped.setdefault(definition.factor_code, []).append(_rule_snapshot(rule_row))
    return {
        "factor_definitions": [_definition_snapshot(item) for item in definitions],
        "factor_rules": grouped,
        "threshold_bands": [_threshold_snapshot(item) for item in bands],
        "product_scores": _product_map(products),
    }


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
    return identity, addresses, nominee, ocr, results, _business_scores(list(business_result.all())), _profession_scores(list(profession_result.all()))


def _factor_record_kwargs(factor: RiskFactor, rule_version: str) -> dict[str, Any]:
    return {
        "factor_name": factor.name,
        "factor_code": factor.code,
        "factor_score": factor.score,
        "source": factor.source,
        "source_table": factor.source_table,
        "selected_value": factor.selected_value,
        "rule_id": factor.rule_id,
        "match_status": factor.match_status,
        "source_value": factor.value,
        "rule_version": rule_version,
    }


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
        session.add(CustomerRiskFactorScore(assessment_id=existing.id, **_factor_record_kwargs(factor, payload["rule_version"])))
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
        db.add(CustomerRiskFactorScore(assessment_id=existing.id, **_factor_record_kwargs(factor, payload["rule_version"])))
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


async def preview_preliminary_assessment_async(
    db: AsyncSession,
    *,
    session_id: int,
    identity_values: dict[str, Any],
    screening_request_id: int | None = None,
) -> dict[str, Any]:
    rule = await _async_active_rule_version(db)
    grading_model = await _async_grading_model(db, rule)
    identity, addresses, nominee, ocr, results, business, profession = await _async_collect(
        db,
        session_id,
        screening_request_id,
    )
    projected_identity = _project_identity_profile(identity, identity_values)
    payload = calculate_assessment_payload(
        assessment_type="preliminary",
        rule_version=rule,
        identity_profile=projected_identity,
        addresses=addresses,
        nominee=nominee,
        ocr=ocr,
        screening_results=results,
        business_scores=business,
        profession_scores=profession,
        configured_model=grading_model,
        screening_request_id=screening_request_id,
    )
    payload["form_type"] = form_type_for_category(payload["risk_category"])
    return payload


def _refresh_preliminary_assessment_log(
    *,
    session_id: int,
    assessment_id: int,
    total_score: int,
    actor_user_id: int | None,
) -> None:
    logger.info(
        "Preliminary risk assessment refreshed after identity completion: session_id=%s assessment_id=%s total_score=%s actor_user_id=%s",
        session_id,
        assessment_id,
        total_score,
        actor_user_id,
    )


def refresh_preliminary_assessment_sync(
    session: Session,
    *,
    session_id: int,
    actor_user_id: int | None = None,
) -> tuple[CustomerRiskAssessment, dict[str, Any]]:
    assessment, payload = calculate_and_persist_sync(
        session,
        session_id=session_id,
        assessment_type="preliminary",
        actor_user_id=actor_user_id,
    )
    _refresh_preliminary_assessment_log(
        session_id=session_id,
        assessment_id=assessment.id or 0,
        total_score=assessment.total_score,
        actor_user_id=actor_user_id,
    )
    return assessment, payload


async def refresh_preliminary_assessment_async(
    db: AsyncSession,
    *,
    session_id: int,
    actor_user_id: int | None = None,
) -> tuple[CustomerRiskAssessment, dict[str, Any]]:
    assessment, payload = await calculate_and_persist_async(
        db,
        session_id=session_id,
        assessment_type="preliminary",
        actor_user_id=actor_user_id,
    )
    _refresh_preliminary_assessment_log(
        session_id=session_id,
        assessment_id=assessment.id or 0,
        total_score=assessment.total_score,
        actor_user_id=actor_user_id,
    )
    return assessment, payload


def stale_preliminary_assessment_session_ids_sync(session: Session) -> list[int]:
    statement = (
        select(CustomerRiskAssessment.session_id)
        .join(CustomerIdentityProfile, CustomerIdentityProfile.session_id == CustomerRiskAssessment.session_id)
        .where(CustomerRiskAssessment.assessment_type == "preliminary")
        .where(CustomerIdentityProfile.status == "IDENTITY_FORM_COMPLETED")
        .where(CustomerIdentityProfile.submitted_at.is_not(None))
        .where(
            or_(
                CustomerRiskAssessment.total_score == 0,
                CustomerRiskAssessment.calculated_at < CustomerIdentityProfile.submitted_at,
            )
        )
        .group_by(CustomerRiskAssessment.session_id)
        .order_by(CustomerRiskAssessment.session_id.asc())
    )
    session_ids: list[int] = []
    for row in session.exec(statement).all():
        try:
            session_ids.append(int(row[0]))
        except (TypeError, KeyError, IndexError):
            session_ids.append(int(getattr(row, "session_id", row)))
    return session_ids


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
