from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import desc, func, or_
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.auth import get_current_user, is_admin, is_compliance_admin
from core.db import get_session
from model.models import (
    AuditLog,
    CustomerRiskFactorScore,
    RiskFactorDefinition,
    RiskFactorRule,
    RiskBusinessCategory,
    RiskProductCategory,
    RiskProfessionCategory,
    User,
    RiskRuleVersion,
    RiskThresholdBand,
    RiskTransactionRange,
    utc_now,
)
from core.risk_assessment import (
    calculate_and_persist_async,
    _async_ensure_default_grading_config,
    latest_assessment_async,
    list_factor_scores_async,
)
from crud import crud_compliance, crud_onboarding
from schemas import (
    AuditLogPublic,
    CustomerRiskAssessmentPublic,
    CustomerRiskFactorScorePublic,
    RiskAssessmentCalculateRequest,
    RiskBusinessCategoryCreate,
    RiskBusinessCategoryListResponse,
    RiskBusinessCategoryPublic,
    RiskBusinessCategoryUpdate,
    RiskCategoryChangePayload,
    RiskFactorDefinitionPublic,
    RiskFactorRulePayload,
    RiskFactorRulePublic,
    RiskFactorRulesResponse,
    RiskProductCategoryPayload,
    RiskProductCategoryPublic,
    RiskProfessionCategoryCreate,
    RiskProfessionCategoryListResponse,
    RiskProfessionCategoryPublic,
    RiskProfessionCategoryUpdate,
    RiskRuleVersionClonePayload,
    RiskRuleVersionListResponse,
    RiskRuleVersionPublic,
    RiskThresholdBandPayload,
    RiskThresholdBandPublic,
    RiskTransactionRangePayload,
    RiskTransactionRangePublic,
)


router = APIRouter()


def _category_code(value: str) -> str:
    return "_".join(value.strip().upper().replace("/", " ").replace("-", " ").split())


def _business_public(row: RiskBusinessCategory, usage_count: int) -> RiskBusinessCategoryPublic:
    return RiskBusinessCategoryPublic(
        id=row.id,
        category_code=row.category_code,
        category_name=row.category_name,
        risk_score=row.risk_score,
        description=row.description,
        is_active=row.is_active,
        created_by=row.created_by,
        usage_count=usage_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


def _profession_public(row: RiskProfessionCategory, usage_count: int) -> RiskProfessionCategoryPublic:
    return RiskProfessionCategoryPublic(
        id=row.id,
        profession_code=row.profession_code,
        profession_name=row.profession_name,
        risk_score=row.risk_score,
        description=row.description,
        is_active=row.is_active,
        created_by=row.created_by,
        usage_count=usage_count,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


async def _usage_counts(db: AsyncSession, source: str, id_key: str, code_key: str, name_key: str) -> dict[str, int]:
    result = await db.exec(select(CustomerRiskFactorScore).where(CustomerRiskFactorScore.source == source))
    counts: dict[str, int] = {}
    for factor in result.all():
        source_value = factor.source_value or {}
        for key in (id_key, code_key, name_key):
            value = source_value.get(key)
            if value is not None:
                counts[str(value)] = counts.get(str(value), 0) + 1
                break
    return counts


def _business_usage(row: RiskBusinessCategory, counts: dict[str, int]) -> int:
    return (
        counts.get(str(row.id), 0)
        + counts.get(row.category_code, 0)
        + counts.get(row.category_name, 0)
    )


def _profession_usage(row: RiskProfessionCategory, counts: dict[str, int]) -> int:
    return (
        counts.get(str(row.id), 0)
        + counts.get(row.profession_code, 0)
        + counts.get(row.profession_name, 0)
    )


def _audit_category_change(
    *,
    actor_user_id: int | None,
    event_type: str,
    message: str,
    reason: str,
    previous: dict,
    new: dict,
) -> AuditLog:
    return AuditLog(
        actor_user_id=actor_user_id,
        event_type=event_type,
        event_status="success",
        message=message,
        payload={
            "reason": reason,
            "previous": previous,
            "new": new,
            "previous_score": previous.get("risk_score"),
            "new_score": new.get("risk_score"),
        },
    )


def _audit_config_change(
    *,
    actor_user_id: int | None,
    event_type: str,
    message: str,
    reason: str,
    previous: dict,
    new: dict,
) -> AuditLog:
    return AuditLog(
        actor_user_id=actor_user_id,
        event_type=event_type,
        event_status="success",
        message=message,
        payload={"reason": reason, "previous": previous, "new": new},
    )


async def _active_rule_version(db: AsyncSession) -> RiskRuleVersion:
    result = await db.exec(
        select(RiskRuleVersion)
        .where(RiskRuleVersion.status == "ACTIVE")
        .order_by(desc(RiskRuleVersion.effective_date))
    )
    row = result.first()
    if row is None:
        row = RiskRuleVersion(version="v1", status="ACTIVE", change_notes="Initial seeded risk grading model.")
        db.add(row)
        await db.flush()
        await db.refresh(row)
    await _async_ensure_default_grading_config(db, row)
    return row


async def _get_rule_version(version_id: int, db: AsyncSession) -> RiskRuleVersion:
    row = await db.get(RiskRuleVersion, version_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk rule version not found.")
    await _async_ensure_default_grading_config(db, row)
    return row


async def _editable_rule_version(db: AsyncSession, version_id: int | None = None) -> RiskRuleVersion:
    if version_id is not None:
        row = await _get_rule_version(version_id, db)
    else:
        row = await _active_rule_version(db)
    return row


def _validate_thresholds(bands: list[RiskThresholdBand]) -> None:
    active = sorted([band for band in bands if band.is_active], key=lambda item: item.min_score)
    previous_max: int | None = None
    for band in active:
        if band.max_score is not None and band.max_score < band.min_score:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Threshold max score must be greater than or equal to min score.")
        if previous_max is not None and band.min_score <= previous_max:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Risk threshold bands cannot overlap.")
        previous_max = band.max_score if band.max_score is not None else 10**9


async def _clone_rules_to_version(db: AsyncSession, source: RiskRuleVersion, target: RiskRuleVersion, actor_id: int | None) -> None:
    definitions = list((await db.exec(select(RiskFactorDefinition))).all())
    rules = list((await db.exec(select(RiskFactorRule).where(RiskFactorRule.rule_version_id == source.id))).all())
    thresholds = list((await db.exec(select(RiskThresholdBand).where(RiskThresholdBand.rule_version_id == source.id))).all())
    transactions = list((await db.exec(select(RiskTransactionRange).where(RiskTransactionRange.rule_version_id == source.id))).all())
    products = list((await db.exec(select(RiskProductCategory).where(RiskProductCategory.rule_version_id == source.id))).all())
    for rule in rules:
        db.add(RiskFactorRule(rule_version_id=target.id, factor_definition_id=rule.factor_definition_id, rule_code=rule.rule_code, rule_type=rule.rule_type, match_value=rule.match_value, min_value=rule.min_value, max_value=rule.max_value, boolean_value=rule.boolean_value, risk_score=rule.risk_score, description=rule.description, is_active=rule.is_active, created_by=actor_id))
    for band in thresholds:
        db.add(RiskThresholdBand(rule_version_id=target.id, category_code=band.category_code, category_name=band.category_name, min_score=band.min_score, max_score=band.max_score, is_active=band.is_active, created_by=actor_id))
    for item in transactions:
        db.add(RiskTransactionRange(rule_version_id=target.id, range_code=item.range_code, range_name=item.range_name, min_amount=item.min_amount, max_amount=item.max_amount, risk_score=item.risk_score, is_active=item.is_active, created_by=actor_id))
    for item in products:
        db.add(RiskProductCategory(rule_version_id=target.id, product_code=item.product_code, product_name=item.product_name, product_category=item.product_category, risk_score=item.risk_score, is_active=item.is_active, created_by=actor_id))
    for definition in definitions:
        definition.updated_at = utc_now()


def _business_snapshot(row: RiskBusinessCategory) -> dict:
    return {
        "id": row.id,
        "category_code": row.category_code,
        "category_name": row.category_name,
        "risk_score": row.risk_score,
        "description": row.description,
        "is_active": row.is_active,
    }


def _profession_snapshot(row: RiskProfessionCategory) -> dict:
    return {
        "id": row.id,
        "profession_code": row.profession_code,
        "profession_name": row.profession_name,
        "risk_score": row.risk_score,
        "description": row.description,
        "is_active": row.is_active,
    }


async def _get_business_category(category_id: int, db: AsyncSession) -> RiskBusinessCategory:
    row = await db.get(RiskBusinessCategory, category_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk business category not found.")
    return row


async def _get_profession_category(category_id: int, db: AsyncSession) -> RiskProfessionCategory:
    row = await db.get(RiskProfessionCategory, category_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk profession category not found.")
    return row


@router.get(
    "/admin/business-categories",
    response_model=RiskBusinessCategoryListResponse,
    dependencies=[Depends(is_compliance_admin())],
)
async def list_business_categories(
    q: str | None = None,
    is_active: bool | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
):
    statement = select(RiskBusinessCategory)
    count_statement = select(func.count()).select_from(RiskBusinessCategory)
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(or_(RiskBusinessCategory.category_code.ilike(pattern), RiskBusinessCategory.category_name.ilike(pattern)))
    if is_active is not None:
        filters.append(RiskBusinessCategory.is_active == is_active)
    for filter_item in filters:
        statement = statement.where(filter_item)
        count_statement = count_statement.where(filter_item)
    statement = statement.order_by(RiskBusinessCategory.category_name.asc()).offset(skip).limit(limit)
    rows = list((await db.exec(statement)).all())
    total = (await db.exec(count_statement)).one()
    counts = await _usage_counts(db, "risk_business_categories", "category_id", "category_code", "category_name")
    return RiskBusinessCategoryListResponse(items=[_business_public(row, _business_usage(row, counts)) for row in rows], total=total)


@router.post(
    "/admin/business-categories",
    response_model=RiskBusinessCategoryPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(is_compliance_admin())],
)
async def create_business_category(
    payload: RiskBusinessCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    now = utc_now()
    row = RiskBusinessCategory(
        category_code=_category_code(payload.category_code),
        category_name=payload.category_name.strip(),
        risk_score=payload.risk_score,
        description=payload.description,
        is_active=payload.is_active,
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Business category code or name already exists.") from exc
    db.add(
        _audit_category_change(
            actor_user_id=current_user.id,
            event_type="risk_business_category_created",
            message=f"Risk business category {row.category_name} created.",
            reason=payload.reason,
            previous={},
            new=_business_snapshot(row),
        )
    )
    await db.commit()
    await db.refresh(row)
    return _business_public(row, 0)


@router.put(
    "/admin/business-categories/{category_id}",
    response_model=RiskBusinessCategoryPublic,
    dependencies=[Depends(is_compliance_admin())],
)
async def update_business_category(
    category_id: int,
    payload: RiskBusinessCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await _get_business_category(category_id, db)
    previous = _business_snapshot(row)
    if payload.category_code is not None:
        row.category_code = _category_code(payload.category_code)
    if payload.category_name is not None:
        row.category_name = payload.category_name.strip()
    if payload.risk_score is not None:
        row.risk_score = payload.risk_score
    if payload.description is not None:
        row.description = payload.description
    if payload.is_active is not None:
        row.is_active = payload.is_active
    row.updated_at = utc_now()
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Business category code or name already exists.") from exc
    new = _business_snapshot(row)
    db.add(
        _audit_category_change(
            actor_user_id=current_user.id,
            event_type="risk_business_category_updated",
            message=f"Risk business category {row.category_name} updated.",
            reason=payload.reason,
            previous=previous,
            new=new,
        )
    )
    await db.commit()
    await db.refresh(row)
    counts = await _usage_counts(db, "risk_business_categories", "category_id", "category_code", "category_name")
    return _business_public(row, _business_usage(row, counts))


@router.post(
    "/admin/business-categories/{category_id}/activate",
    response_model=RiskBusinessCategoryPublic,
    dependencies=[Depends(is_compliance_admin())],
)
async def activate_business_category(
    category_id: int,
    payload: RiskCategoryChangePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await _get_business_category(category_id, db)
    previous = _business_snapshot(row)
    row.is_active = True
    row.updated_at = utc_now()
    db.add(row)
    await db.flush()
    db.add(_audit_category_change(actor_user_id=current_user.id, event_type="risk_business_category_status_changed", message=f"Risk business category {row.category_name} activated.", reason=payload.reason, previous=previous, new=_business_snapshot(row)))
    await db.commit()
    await db.refresh(row)
    counts = await _usage_counts(db, "risk_business_categories", "category_id", "category_code", "category_name")
    return _business_public(row, _business_usage(row, counts))


@router.post(
    "/admin/business-categories/{category_id}/deactivate",
    response_model=RiskBusinessCategoryPublic,
    dependencies=[Depends(is_compliance_admin())],
)
async def deactivate_business_category(
    category_id: int,
    payload: RiskCategoryChangePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await _get_business_category(category_id, db)
    previous = _business_snapshot(row)
    row.is_active = False
    row.updated_at = utc_now()
    db.add(row)
    await db.flush()
    db.add(_audit_category_change(actor_user_id=current_user.id, event_type="risk_business_category_status_changed", message=f"Risk business category {row.category_name} deactivated.", reason=payload.reason, previous=previous, new=_business_snapshot(row)))
    await db.commit()
    await db.refresh(row)
    counts = await _usage_counts(db, "risk_business_categories", "category_id", "category_code", "category_name")
    return _business_public(row, _business_usage(row, counts))


@router.get(
    "/admin/business-categories/{category_id}/audit",
    response_model=list[AuditLogPublic],
    dependencies=[Depends(is_compliance_admin())],
)
async def get_business_category_audit(category_id: int, db: AsyncSession = Depends(get_session)):
    await _get_business_category(category_id, db)
    result = await db.exec(
        select(AuditLog)
        .where(AuditLog.event_type.in_(["risk_business_category_created", "risk_business_category_updated", "risk_business_category_status_changed"]))
        .order_by(AuditLog.created_at.desc())
    )
    return [AuditLogPublic.model_validate(item) for item in result.all() if (item.payload or {}).get("new", {}).get("id") == category_id or (item.payload or {}).get("previous", {}).get("id") == category_id]


@router.get(
    "/admin/profession-categories",
    response_model=RiskProfessionCategoryListResponse,
    dependencies=[Depends(is_compliance_admin())],
)
async def list_profession_categories(
    q: str | None = None,
    is_active: bool | None = None,
    skip: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=500),
    db: AsyncSession = Depends(get_session),
):
    statement = select(RiskProfessionCategory)
    count_statement = select(func.count()).select_from(RiskProfessionCategory)
    filters = []
    if q:
        pattern = f"%{q}%"
        filters.append(or_(RiskProfessionCategory.profession_code.ilike(pattern), RiskProfessionCategory.profession_name.ilike(pattern)))
    if is_active is not None:
        filters.append(RiskProfessionCategory.is_active == is_active)
    for filter_item in filters:
        statement = statement.where(filter_item)
        count_statement = count_statement.where(filter_item)
    statement = statement.order_by(RiskProfessionCategory.profession_name.asc()).offset(skip).limit(limit)
    rows = list((await db.exec(statement)).all())
    total = (await db.exec(count_statement)).one()
    counts = await _usage_counts(db, "risk_profession_categories", "profession_id", "profession_code", "profession_name")
    return RiskProfessionCategoryListResponse(items=[_profession_public(row, _profession_usage(row, counts)) for row in rows], total=total)


@router.post(
    "/admin/profession-categories",
    response_model=RiskProfessionCategoryPublic,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(is_compliance_admin())],
)
async def create_profession_category(
    payload: RiskProfessionCategoryCreate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    now = utc_now()
    row = RiskProfessionCategory(
        profession_code=_category_code(payload.profession_code),
        profession_name=payload.profession_name.strip(),
        risk_score=payload.risk_score,
        description=payload.description,
        is_active=payload.is_active,
        created_by=current_user.id,
        created_at=now,
        updated_at=now,
    )
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profession category code or name already exists.") from exc
    db.add(
        _audit_category_change(
            actor_user_id=current_user.id,
            event_type="risk_profession_category_created",
            message=f"Risk profession category {row.profession_name} created.",
            reason=payload.reason,
            previous={},
            new=_profession_snapshot(row),
        )
    )
    await db.commit()
    await db.refresh(row)
    return _profession_public(row, 0)


@router.put(
    "/admin/profession-categories/{category_id}",
    response_model=RiskProfessionCategoryPublic,
    dependencies=[Depends(is_compliance_admin())],
)
async def update_profession_category(
    category_id: int,
    payload: RiskProfessionCategoryUpdate,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await _get_profession_category(category_id, db)
    previous = _profession_snapshot(row)
    if payload.profession_code is not None:
        row.profession_code = _category_code(payload.profession_code)
    if payload.profession_name is not None:
        row.profession_name = payload.profession_name.strip()
    if payload.risk_score is not None:
        row.risk_score = payload.risk_score
    if payload.description is not None:
        row.description = payload.description
    if payload.is_active is not None:
        row.is_active = payload.is_active
    row.updated_at = utc_now()
    db.add(row)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Profession category code or name already exists.") from exc
    db.add(
        _audit_category_change(
            actor_user_id=current_user.id,
            event_type="risk_profession_category_updated",
            message=f"Risk profession category {row.profession_name} updated.",
            reason=payload.reason,
            previous=previous,
            new=_profession_snapshot(row),
        )
    )
    await db.commit()
    await db.refresh(row)
    counts = await _usage_counts(db, "risk_profession_categories", "profession_id", "profession_code", "profession_name")
    return _profession_public(row, _profession_usage(row, counts))


@router.post(
    "/admin/profession-categories/{category_id}/activate",
    response_model=RiskProfessionCategoryPublic,
    dependencies=[Depends(is_compliance_admin())],
)
async def activate_profession_category(
    category_id: int,
    payload: RiskCategoryChangePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await _get_profession_category(category_id, db)
    previous = _profession_snapshot(row)
    row.is_active = True
    row.updated_at = utc_now()
    db.add(row)
    await db.flush()
    db.add(_audit_category_change(actor_user_id=current_user.id, event_type="risk_profession_category_status_changed", message=f"Risk profession category {row.profession_name} activated.", reason=payload.reason, previous=previous, new=_profession_snapshot(row)))
    await db.commit()
    await db.refresh(row)
    counts = await _usage_counts(db, "risk_profession_categories", "profession_id", "profession_code", "profession_name")
    return _profession_public(row, _profession_usage(row, counts))


@router.post(
    "/admin/profession-categories/{category_id}/deactivate",
    response_model=RiskProfessionCategoryPublic,
    dependencies=[Depends(is_compliance_admin())],
)
async def deactivate_profession_category(
    category_id: int,
    payload: RiskCategoryChangePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await _get_profession_category(category_id, db)
    previous = _profession_snapshot(row)
    row.is_active = False
    row.updated_at = utc_now()
    db.add(row)
    await db.flush()
    db.add(_audit_category_change(actor_user_id=current_user.id, event_type="risk_profession_category_status_changed", message=f"Risk profession category {row.profession_name} deactivated.", reason=payload.reason, previous=previous, new=_profession_snapshot(row)))
    await db.commit()
    await db.refresh(row)
    counts = await _usage_counts(db, "risk_profession_categories", "profession_id", "profession_code", "profession_name")
    return _profession_public(row, _profession_usage(row, counts))


@router.get(
    "/admin/profession-categories/{category_id}/audit",
    response_model=list[AuditLogPublic],
    dependencies=[Depends(is_compliance_admin())],
)
async def get_profession_category_audit(category_id: int, db: AsyncSession = Depends(get_session)):
    await _get_profession_category(category_id, db)
    result = await db.exec(
        select(AuditLog)
        .where(AuditLog.event_type.in_(["risk_profession_category_created", "risk_profession_category_updated", "risk_profession_category_status_changed"]))
        .order_by(AuditLog.created_at.desc())
    )
    return [AuditLogPublic.model_validate(item) for item in result.all() if (item.payload or {}).get("new", {}).get("id") == category_id or (item.payload or {}).get("previous", {}).get("id") == category_id]


@router.get("/admin/rule-versions", response_model=RiskRuleVersionListResponse, dependencies=[Depends(is_compliance_admin())])
async def list_rule_versions(db: AsyncSession = Depends(get_session)):
    await _active_rule_version(db)
    result = await db.exec(select(RiskRuleVersion).order_by(desc(RiskRuleVersion.effective_date), desc(RiskRuleVersion.id)))
    return RiskRuleVersionListResponse(items=[RiskRuleVersionPublic.model_validate(item) for item in result.all()])


@router.post("/admin/rule-versions/clone", response_model=RiskRuleVersionPublic, dependencies=[Depends(is_compliance_admin())])
async def clone_rule_version(
    payload: RiskRuleVersionClonePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    source = await _active_rule_version(db)
    now = utc_now()
    target = RiskRuleVersion(version=payload.version, status="DRAFT", thresholds=source.thresholds, rules_snapshot=source.rules_snapshot, created_by=current_user.id, change_notes=payload.change_notes, effective_date=now, created_at=now, updated_at=now)
    db.add(target)
    try:
        await db.flush()
    except IntegrityError as exc:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Risk rule version already exists.") from exc
    await _clone_rules_to_version(db, source, target, current_user.id)
    db.add(_audit_config_change(actor_user_id=current_user.id, event_type="risk_rule_version_cloned", message=f"Risk rule version {target.version} cloned from {source.version}.", reason=payload.change_notes, previous={"version": source.version}, new={"version": target.version, "status": target.status}))
    await db.commit()
    await db.refresh(target)
    return RiskRuleVersionPublic.model_validate(target)


@router.post("/admin/rule-versions/{version_id}/activate", response_model=RiskRuleVersionPublic, dependencies=[Depends(is_compliance_admin())])
async def activate_rule_version(
    version_id: int,
    payload: RiskCategoryChangePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    target = await _get_rule_version(version_id, db)
    bands = list((await db.exec(select(RiskThresholdBand).where(RiskThresholdBand.rule_version_id == target.id))).all())
    _validate_thresholds(bands)
    active_result = await db.exec(select(RiskRuleVersion).where(RiskRuleVersion.status == "ACTIVE"))
    now = utc_now()
    for active in active_result.all():
        if active.id != target.id:
            active.status = "RETIRED"
            active.retired_at = now
            active.updated_at = now
            db.add(active)
    previous = {"version": target.version, "status": target.status}
    target.status = "ACTIVE"
    target.activated_at = now
    target.effective_date = now
    target.updated_at = now
    db.add(target)
    db.add(_audit_config_change(actor_user_id=current_user.id, event_type="risk_rule_version_activated", message=f"Risk rule version {target.version} activated.", reason=payload.reason, previous=previous, new={"version": target.version, "status": target.status}))
    await db.commit()
    await db.refresh(target)
    return RiskRuleVersionPublic.model_validate(target)


@router.get("/admin/factor-rules", response_model=RiskFactorRulesResponse, dependencies=[Depends(is_compliance_admin())])
async def list_factor_rules(version_id: int | None = None, db: AsyncSession = Depends(get_session)):
    version = await _editable_rule_version(db, version_id)
    definitions = list((await db.exec(select(RiskFactorDefinition).order_by(RiskFactorDefinition.display_order.asc()))).all())
    rules = list((await db.exec(select(RiskFactorRule).where(RiskFactorRule.rule_version_id == version.id).order_by(RiskFactorRule.id.asc()))).all())
    return RiskFactorRulesResponse(definitions=[RiskFactorDefinitionPublic.model_validate(item) for item in definitions], rules=[RiskFactorRulePublic.model_validate(item) for item in rules])


@router.post("/admin/factor-rules", response_model=RiskFactorRulePublic, dependencies=[Depends(is_compliance_admin())])
async def create_factor_rule(
    payload: RiskFactorRulePayload,
    version_id: int | None = None,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    version = await _editable_rule_version(db, version_id)
    row = RiskFactorRule(rule_version_id=version.id, created_by=current_user.id, **payload.model_dump(exclude={"reason"}))
    db.add(row)
    await db.flush()
    db.add(_audit_config_change(actor_user_id=current_user.id, event_type="risk_factor_rule_created", message=f"Risk factor rule {row.rule_code} created.", reason=payload.reason, previous={}, new=RiskFactorRulePublic.model_validate(row).model_dump(mode="json")))
    await db.commit()
    await db.refresh(row)
    return RiskFactorRulePublic.model_validate(row)


@router.put("/admin/factor-rules/{rule_id}", response_model=RiskFactorRulePublic, dependencies=[Depends(is_compliance_admin())])
async def update_factor_rule(
    rule_id: int,
    payload: RiskFactorRulePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await db.get(RiskFactorRule, rule_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk factor rule not found.")
    previous = RiskFactorRulePublic.model_validate(row).model_dump(mode="json")
    for key, value in payload.model_dump(exclude={"reason"}).items():
        setattr(row, key, value)
    row.updated_at = utc_now()
    db.add(row)
    await db.flush()
    db.add(_audit_config_change(actor_user_id=current_user.id, event_type="risk_factor_rule_updated", message=f"Risk factor rule {row.rule_code} updated.", reason=payload.reason, previous=previous, new=RiskFactorRulePublic.model_validate(row).model_dump(mode="json")))
    await db.commit()
    await db.refresh(row)
    return RiskFactorRulePublic.model_validate(row)


@router.get("/admin/thresholds", response_model=list[RiskThresholdBandPublic], dependencies=[Depends(is_compliance_admin())])
async def list_thresholds(version_id: int | None = None, db: AsyncSession = Depends(get_session)):
    version = await _editable_rule_version(db, version_id)
    result = await db.exec(select(RiskThresholdBand).where(RiskThresholdBand.rule_version_id == version.id).order_by(RiskThresholdBand.min_score.asc()))
    return [RiskThresholdBandPublic.model_validate(item) for item in result.all()]


@router.put("/admin/thresholds/{band_id}", response_model=RiskThresholdBandPublic, dependencies=[Depends(is_compliance_admin())])
async def update_threshold(
    band_id: int,
    payload: RiskThresholdBandPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await db.get(RiskThresholdBand, band_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk threshold band not found.")
    previous = RiskThresholdBandPublic.model_validate(row).model_dump(mode="json")
    for key, value in payload.model_dump(exclude={"reason"}).items():
        setattr(row, key, value)
    row.updated_at = utc_now()
    db.add(row)
    await db.flush()
    bands = list((await db.exec(select(RiskThresholdBand).where(RiskThresholdBand.rule_version_id == row.rule_version_id))).all())
    _validate_thresholds(bands)
    db.add(_audit_config_change(actor_user_id=current_user.id, event_type="risk_threshold_updated", message=f"Risk threshold {row.category_code} updated.", reason=payload.reason, previous=previous, new=RiskThresholdBandPublic.model_validate(row).model_dump(mode="json")))
    await db.commit()
    await db.refresh(row)
    return RiskThresholdBandPublic.model_validate(row)


@router.get("/admin/transaction-ranges", response_model=list[RiskTransactionRangePublic], dependencies=[Depends(is_compliance_admin())])
async def list_transaction_ranges(version_id: int | None = None, db: AsyncSession = Depends(get_session)):
    version = await _editable_rule_version(db, version_id)
    result = await db.exec(select(RiskTransactionRange).where(RiskTransactionRange.rule_version_id == version.id).order_by(RiskTransactionRange.min_amount.asc()))
    return [RiskTransactionRangePublic.model_validate(item) for item in result.all()]


@router.put("/admin/transaction-ranges/{range_id}", response_model=RiskTransactionRangePublic, dependencies=[Depends(is_compliance_admin())])
async def update_transaction_range(
    range_id: int,
    payload: RiskTransactionRangePayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await db.get(RiskTransactionRange, range_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk transaction range not found.")
    previous = RiskTransactionRangePublic.model_validate(row).model_dump(mode="json")
    for key, value in payload.model_dump(exclude={"reason"}).items():
        setattr(row, key, value)
    row.updated_at = utc_now()
    db.add(row)
    await db.flush()
    db.add(_audit_config_change(actor_user_id=current_user.id, event_type="risk_transaction_range_updated", message=f"Risk transaction range {row.range_code} updated.", reason=payload.reason, previous=previous, new=RiskTransactionRangePublic.model_validate(row).model_dump(mode="json")))
    await db.commit()
    await db.refresh(row)
    return RiskTransactionRangePublic.model_validate(row)


@router.get("/admin/product-risks", response_model=list[RiskProductCategoryPublic], dependencies=[Depends(is_compliance_admin())])
async def list_product_risks(version_id: int | None = None, db: AsyncSession = Depends(get_session)):
    version = await _editable_rule_version(db, version_id)
    result = await db.exec(select(RiskProductCategory).where(RiskProductCategory.rule_version_id == version.id).order_by(RiskProductCategory.product_name.asc()))
    return [RiskProductCategoryPublic.model_validate(item) for item in result.all()]


@router.put("/admin/product-risks/{product_id}", response_model=RiskProductCategoryPublic, dependencies=[Depends(is_compliance_admin())])
async def update_product_risk(
    product_id: int,
    payload: RiskProductCategoryPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    row = await db.get(RiskProductCategory, product_id)
    if row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk product category not found.")
    previous = RiskProductCategoryPublic.model_validate(row).model_dump(mode="json")
    for key, value in payload.model_dump(exclude={"reason"}).items():
        setattr(row, key, value)
    row.updated_at = utc_now()
    db.add(row)
    await db.flush()
    db.add(_audit_config_change(actor_user_id=current_user.id, event_type="risk_product_risk_updated", message=f"Risk product {row.product_code} updated.", reason=payload.reason, previous=previous, new=RiskProductCategoryPublic.model_validate(row).model_dump(mode="json")))
    await db.commit()
    await db.refresh(row)
    return RiskProductCategoryPublic.model_validate(row)


async def _build_public_assessment(assessment, db: AsyncSession) -> CustomerRiskAssessmentPublic:
    factors = await list_factor_scores_async(db, assessment.id)
    return CustomerRiskAssessmentPublic(
        id=assessment.id,
        session_id=assessment.session_id,
        screening_request_id=assessment.screening_request_id,
        assessment_type=assessment.assessment_type,
        status=assessment.status,
        total_score=assessment.total_score,
        risk_category=assessment.risk_category,
        rule_version=assessment.rule_version,
        edd_required=assessment.edd_required,
        edd_status=assessment.edd_status,
        edd_reasons=assessment.edd_reasons,
        rules_snapshot=assessment.rules_snapshot,
        calculated_at=assessment.calculated_at,
        created_at=assessment.created_at,
        updated_at=assessment.updated_at,
        factors=[CustomerRiskFactorScorePublic.model_validate(factor) for factor in factors],
    )


async def _ensure_session_access(session_id: int, user: User, db: AsyncSession):
    if user.role == "admin":
        from sqlmodel import select
        from model.models import OnboardingSession

        result = await db.exec(select(OnboardingSession).where(OnboardingSession.id == session_id))
        session_row = result.one_or_none()
    else:
        session_row = await crud_onboarding.get_session_for_user(
            session_id=session_id,
            user_id=user.id,
            session=db,
        )
    if session_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding session not found.")
    return session_row


@router.post("/calculate", response_model=CustomerRiskAssessmentPublic)
async def calculate_risk_assessment(
    payload: RiskAssessmentCalculateRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    session_row = await _ensure_session_access(payload.session_id, current_user, db)
    screening = await crud_compliance.get_latest_screening_for_session(session_id=session_row.id, db=db)
    assessment, _ = await calculate_and_persist_async(
        db,
        session_id=session_row.id,
        assessment_type=payload.assessment_type,
        screening_request_id=screening.id if screening else None,
        actor_user_id=current_user.id,
    )
    await db.commit()
    return await _build_public_assessment(assessment, db)


@router.get("/{session_id}", response_model=CustomerRiskAssessmentPublic)
async def get_risk_assessment(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    await _ensure_session_access(session_id, current_user, db)
    assessment = await latest_assessment_async(db, session_id)
    if assessment is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Risk assessment not found.")
    return await _build_public_assessment(assessment, db)


@router.post("/{session_id}/recalculate", response_model=CustomerRiskAssessmentPublic, dependencies=[Depends(is_admin())])
async def recalculate_risk_assessment(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    session_row = await _ensure_session_access(session_id, current_user, db)
    screening = await crud_compliance.get_latest_screening_for_session(session_id=session_row.id, db=db)
    assessment, _ = await calculate_and_persist_async(
        db,
        session_id=session_row.id,
        assessment_type="final",
        screening_request_id=screening.id if screening else None,
        actor_user_id=current_user.id,
    )
    await db.commit()
    return await _build_public_assessment(assessment, db)
