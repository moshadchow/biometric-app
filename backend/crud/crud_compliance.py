from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from model.models import (
    AuditLog,
    ComplianceCase,
    CustomerRiskAssessment,
    OnboardingSession,
    RiskAssessment,
    ScreeningDecision,
    ScreeningJob,
    ScreeningRequest,
    ScreeningResult,
)


def utc_now() -> datetime:
    return datetime.utcnow()


async def get_latest_screening_for_session(
    *,
    session_id: int,
    db: AsyncSession,
) -> ScreeningRequest | None:
    statement = (
        select(ScreeningRequest)
        .where(ScreeningRequest.session_id == session_id)
        .order_by(ScreeningRequest.created_at.desc())
    )
    result = await db.exec(statement)
    return result.first()


async def get_screening_request(
    *,
    screening_id: int,
    db: AsyncSession,
) -> ScreeningRequest | None:
    result = await db.exec(select(ScreeningRequest).where(ScreeningRequest.id == screening_id))
    return result.one_or_none()


async def create_screening_request(
    *,
    session_row: OnboardingSession,
    trigger_source: str,
    db: AsyncSession,
) -> ScreeningRequest:
    screening = ScreeningRequest(
        session_id=session_row.id,
        user_id=session_row.user_id,
        trigger_source=trigger_source,
    )
    db.add(screening)
    await db.flush()
    await db.refresh(screening)
    return screening


async def ensure_screening_request(
    *,
    session_row: OnboardingSession,
    trigger_source: str,
    db: AsyncSession,
) -> ScreeningRequest:
    current = await get_latest_screening_for_session(session_id=session_row.id, db=db)
    if current and current.status not in {"APPROVED", "REJECTED", "FAILED"}:
        return current
    return await create_screening_request(session_row=session_row, trigger_source=trigger_source, db=db)


async def get_risk_assessment(
    *,
    screening_request_id: int,
    db: AsyncSession,
) -> RiskAssessment | None:
    result = await db.exec(
        select(RiskAssessment).where(RiskAssessment.screening_request_id == screening_request_id)
    )
    return result.one_or_none()


async def get_latest_customer_risk_assessment(
    *,
    session_id: int,
    db: AsyncSession,
) -> CustomerRiskAssessment | None:
    result = await db.exec(
        select(CustomerRiskAssessment)
        .where(CustomerRiskAssessment.session_id == session_id)
        .order_by(CustomerRiskAssessment.calculated_at.desc())
    )
    return result.first()


async def get_screening_decision(
    *,
    screening_request_id: int,
    db: AsyncSession,
) -> ScreeningDecision | None:
    result = await db.exec(
        select(ScreeningDecision).where(ScreeningDecision.screening_request_id == screening_request_id)
    )
    return result.one_or_none()


async def list_screening_results(
    *,
    screening_request_id: int,
    db: AsyncSession,
) -> list[ScreeningResult]:
    result = await db.exec(
        select(ScreeningResult)
        .where(ScreeningResult.screening_request_id == screening_request_id)
        .order_by(ScreeningResult.created_at.asc())
    )
    return list(result.all())


async def list_audit_logs(
    *,
    screening_request_id: int,
    db: AsyncSession,
) -> list[AuditLog]:
    result = await db.exec(
        select(AuditLog)
        .where(AuditLog.screening_request_id == screening_request_id)
        .order_by(AuditLog.created_at.desc())
    )
    return list(result.all())


async def list_cases(
    *,
    db: AsyncSession,
) -> list[ComplianceCase]:
    result = await db.exec(select(ComplianceCase).order_by(ComplianceCase.updated_at.desc()))
    return list(result.all())


async def get_case(
    *,
    case_id: int,
    db: AsyncSession,
) -> ComplianceCase | None:
    result = await db.exec(select(ComplianceCase).where(ComplianceCase.id == case_id))
    return result.one_or_none()


async def get_screening_summary(
    *,
    session_id: int,
    db: AsyncSession,
) -> dict[str, Any] | None:
    screening = await get_latest_screening_for_session(session_id=session_id, db=db)
    if screening is None:
        return None

    decision = await get_screening_decision(screening_request_id=screening.id, db=db)
    risk = await get_risk_assessment(screening_request_id=screening.id, db=db)
    customer_risk = await get_latest_customer_risk_assessment(session_id=session_id, db=db)
    return {
        "screening_request_id": screening.id,
        "screening_status": screening.status,
        "final_decision": decision.decision if decision else None,
        "risk_category": customer_risk.risk_category if customer_risk else (risk.risk_category if risk else None),
        "risk_score": customer_risk.total_score if customer_risk else (risk.risk_score if risk else None),
        "review_required": screening.status == "REVIEW_REQUIRED" or bool(customer_risk and customer_risk.edd_required),
        "activation_eligible": screening.status == "APPROVED",
        "last_updated_at": screening.updated_at,
    }
