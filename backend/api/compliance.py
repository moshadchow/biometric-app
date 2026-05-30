from __future__ import annotations

from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.auth import get_current_user, is_admin
from core.db import get_session
from core.onboarding_state import resolve_session_state_async, transition_session_async
from core.risk_assessment import latest_assessment_async, list_factor_scores_async
from core.task_queue import enqueue_task
from crud import crud_compliance, crud_onboarding
from model.models import ComplianceCase, OnboardingSession, User
from schemas import (
    AuditLogPublic,
    CaseDecisionPayload,
    ComplianceCaseDetailResponse,
    ComplianceCaseListResponse,
    ComplianceCasePublic,
    ComplianceSummaryPublic,
    CustomerRiskAssessmentPublic,
    CustomerRiskFactorScorePublic,
    RiskAssessmentPublic,
    ScreeningDetailsResponse,
    ScreeningResultPublic,
    ScreeningStartRequest,
    ScreeningStatusPublic,
)
from tasks import start_screening_workflow


router = APIRouter()


def utc_now() -> datetime:
    return datetime.utcnow()


async def _build_screening_status(screening, db: AsyncSession) -> ScreeningStatusPublic:
    decision = await crud_compliance.get_screening_decision(screening_request_id=screening.id, db=db)
    risk = await crud_compliance.get_risk_assessment(screening_request_id=screening.id, db=db)
    customer_risk = await latest_assessment_async(db, screening.session_id)
    return ScreeningStatusPublic(
        id=screening.id,
        session_id=screening.session_id,
        user_id=screening.user_id,
        status=screening.status,
        trigger_source=screening.trigger_source,
        workflow_id=screening.workflow_id,
        retry_count=screening.retry_count,
        started_at=screening.started_at,
        completed_at=screening.completed_at,
        last_error=screening.last_error,
        created_at=screening.created_at,
        updated_at=screening.updated_at,
        decision=decision.decision if decision else None,
        risk_category=customer_risk.risk_category if customer_risk else (risk.risk_category if risk else None),
        risk_score=customer_risk.total_score if customer_risk else (risk.risk_score if risk else None),
        review_required=screening.status == "REVIEW_REQUIRED" or bool(customer_risk and customer_risk.edd_required),
        activation_eligible=screening.status == "APPROVED",
    )


async def _build_customer_risk_public(session_id: int, db: AsyncSession) -> CustomerRiskAssessmentPublic | None:
    assessment = await latest_assessment_async(db, session_id)
    if assessment is None:
        return None
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
        factors=[CustomerRiskFactorScorePublic.model_validate(item) for item in factors],
    )


async def _ensure_customer_owns_screening(screening_id: int, user: User, db: AsyncSession):
    screening = await crud_compliance.get_screening_request(screening_id=screening_id, db=db)
    if screening is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Screening request not found.")
    if user.role != "admin" and screening.user_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User not authorized for this screening.")
    return screening


@router.post("/screenings", response_model=ScreeningStatusPublic, status_code=status.HTTP_202_ACCEPTED)
async def start_screening(
    payload: ScreeningStartRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    session_row = await crud_onboarding.get_session_for_user(
        session_id=payload.session_id,
        user_id=current_user.id,
        session=db,
    )
    if session_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding session not found.")

    screening = await crud_compliance.ensure_screening_request(
        session_row=session_row,
        trigger_source=payload.trigger_source,
        db=db,
    )
    await db.commit()
    enqueue_task(start_screening_workflow, screening.id)
    refreshed = await crud_compliance.get_screening_request(screening_id=screening.id, db=db)
    return await _build_screening_status(refreshed, db)


@router.get("/screenings/{screening_id}", response_model=ScreeningStatusPublic)
async def get_screening_status(
    screening_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    screening = await _ensure_customer_owns_screening(screening_id, current_user, db)
    return await _build_screening_status(screening, db)


@router.get("/screenings/{screening_id}/results", response_model=ScreeningDetailsResponse)
async def get_screening_results(
    screening_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    screening = await _ensure_customer_owns_screening(screening_id, current_user, db)
    if current_user.role != "admin":
        return ScreeningDetailsResponse(
            screening=await _build_screening_status(screening, db),
            risk_assessment=None,
            results=[],
            audit_logs=[],
        )

    risk = await crud_compliance.get_risk_assessment(screening_request_id=screening_id, db=db)
    customer_risk = await _build_customer_risk_public(screening.session_id, db)
    results = await crud_compliance.list_screening_results(screening_request_id=screening_id, db=db)
    audit_logs = await crud_compliance.list_audit_logs(screening_request_id=screening_id, db=db)
    return ScreeningDetailsResponse(
        screening=await _build_screening_status(screening, db),
        risk_assessment=RiskAssessmentPublic.model_validate(risk) if risk else None,
        customer_risk_assessment=customer_risk,
        results=[ScreeningResultPublic.model_validate(item) for item in results],
        audit_logs=[AuditLogPublic.model_validate(item) for item in audit_logs],
    )


@router.post("/screenings/{screening_id}/retry", response_model=ScreeningStatusPublic, status_code=status.HTTP_202_ACCEPTED)
async def retry_screening(
    screening_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    screening = await _ensure_customer_owns_screening(screening_id, current_user, db)
    session_row = await crud_onboarding.get_session_for_user(
        session_id=screening.session_id,
        user_id=screening.user_id,
        session=db,
    )
    if session_row is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding session not found.")

    screening.retry_count += 1
    screening.status = "SCREENING_PENDING"
    screening.completed_at = None
    screening.last_error = None
    screening.updated_at = utc_now()
    db.add(screening)
    await db.commit()
    enqueue_task(start_screening_workflow, screening.id)
    refreshed = await crud_compliance.get_screening_request(screening_id=screening.id, db=db)
    return await _build_screening_status(refreshed, db)


async def _build_case_public(case: ComplianceCase, db: AsyncSession) -> ComplianceCasePublic:
    screening = await crud_compliance.get_screening_request(screening_id=case.screening_request_id, db=db)
    risk = await crud_compliance.get_risk_assessment(screening_request_id=case.screening_request_id, db=db)
    decision = await crud_compliance.get_screening_decision(screening_request_id=case.screening_request_id, db=db)
    username = None
    if screening is not None:
        session_row = await crud_onboarding.get_session_for_user(
            session_id=screening.session_id,
            user_id=screening.user_id,
            session=db,
        )
        if session_row:
            user_result = await db.exec(select(User).where(User.id == screening.user_id))
            user_row = user_result.one_or_none()
            username = user_row.username if user_row else None
    customer_risk = await _build_customer_risk_public(screening.session_id, db) if screening else None

    return ComplianceCasePublic(
        id=case.id,
        screening_request_id=case.screening_request_id,
        status=case.status,
        queue_name=case.queue_name,
        reviewer_id=case.reviewer_id,
        opened_at=case.opened_at,
        resolved_at=case.resolved_at,
        resolution_note=case.resolution_note,
        created_at=case.created_at,
        updated_at=case.updated_at,
        screening_status=screening.status if screening else "UNKNOWN",
        decision=decision.decision if decision else None,
        risk_category=customer_risk.risk_category if customer_risk else (risk.risk_category if risk else None),
        risk_score=customer_risk.total_score if customer_risk else (risk.risk_score if risk else None),
        username=username,
    )


@router.get("/cases", response_model=ComplianceCaseListResponse, dependencies=[Depends(is_admin())])
async def list_cases(
    db: AsyncSession = Depends(get_session),
):
    cases = await crud_compliance.list_cases(db=db)
    return ComplianceCaseListResponse(items=[await _build_case_public(item, db) for item in cases])


@router.get("/cases/{case_id}", response_model=ComplianceCaseDetailResponse, dependencies=[Depends(is_admin())])
async def get_case_details(
    case_id: int,
    db: AsyncSession = Depends(get_session),
):
    case = await crud_compliance.get_case(case_id=case_id, db=db)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compliance case not found.")
    screening = await crud_compliance.get_screening_request(screening_id=case.screening_request_id, db=db)
    risk = await crud_compliance.get_risk_assessment(screening_request_id=case.screening_request_id, db=db)
    customer_risk = await _build_customer_risk_public(screening.session_id, db) if screening else None
    results = await crud_compliance.list_screening_results(screening_request_id=case.screening_request_id, db=db)
    audit_logs = await crud_compliance.list_audit_logs(screening_request_id=case.screening_request_id, db=db)
    return ComplianceCaseDetailResponse(
        case=await _build_case_public(case, db),
        screening=await _build_screening_status(screening, db),
        risk_assessment=RiskAssessmentPublic.model_validate(risk) if risk else None,
        customer_risk_assessment=customer_risk,
        results=[ScreeningResultPublic.model_validate(item) for item in results],
        audit_logs=[AuditLogPublic.model_validate(item) for item in audit_logs],
    )


async def _resolve_case(
    *,
    case_id: int,
    payload: CaseDecisionPayload,
    target_decision: str,
    current_user: User,
    db: AsyncSession,
) -> ComplianceCaseDetailResponse:
    case = await crud_compliance.get_case(case_id=case_id, db=db)
    if case is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Compliance case not found.")
    screening = await crud_compliance.get_screening_request(screening_id=case.screening_request_id, db=db)
    decision = await crud_compliance.get_screening_decision(screening_request_id=case.screening_request_id, db=db)
    previous_decision = decision.decision if decision else screening.status

    case.status = "RESOLVED"
    case.reviewer_id = current_user.id
    case.resolved_at = utc_now()
    case.resolution_note = payload.notes or payload.reason
    case.updated_at = utc_now()
    db.add(case)

    if decision is None:
        from model.models import ScreeningDecision, AuditLog  # local import to avoid widening top-level imports

        decision = ScreeningDecision(
            screening_request_id=screening.id,
            decision=target_decision,
            decision_source="manual",
            reviewer_id=current_user.id,
            previous_decision=previous_decision,
            reason=payload.reason,
            notes=payload.notes,
        )
        db.add(decision)
    else:
        decision.previous_decision = previous_decision
        decision.decision = target_decision
        decision.decision_source = "manual"
        decision.reviewer_id = current_user.id
        decision.reason = payload.reason
        decision.notes = payload.notes
        decision.decided_at = utc_now()
        decision.updated_at = utc_now()
        db.add(decision)

    screening.status = target_decision
    screening.completed_at = screening.completed_at or utc_now()
    screening.updated_at = utc_now()
    db.add(screening)

    result = await db.exec(select(OnboardingSession).where(OnboardingSession.id == screening.session_id))
    session_row = result.one_or_none()
    if session_row is not None:
        customer_risk = await latest_assessment_async(db, session_row.id, "final")
        if customer_risk is not None and customer_risk.edd_required:
            customer_risk.edd_status = "EDD_APPROVED" if target_decision == "APPROVED" else "EDD_REJECTED"
            customer_risk.status = customer_risk.edd_status
            customer_risk.updated_at = utc_now()
            db.add(customer_risk)
            await db.flush()
        state = await resolve_session_state_async(db, session_row)
        await transition_session_async(
            db,
            session_row,
            state["workflow_state"],
            actor_user_id=current_user.id,
            event_type="onboarding_compliance_decision_applied",
            message=f"Onboarding session updated after compliance decision {target_decision}.",
            payload={"screening_request_id": screening.id, "decision": target_decision},
        )

    from model.models import AuditLog

    db.add(
        AuditLog(
            screening_request_id=screening.id,
            session_id=screening.session_id,
            actor_user_id=current_user.id,
            event_type="manual_case_decision",
            event_status="success",
            message=f"Compliance case resolved as {target_decision}.",
            payload={
                "previous_decision": previous_decision,
                "new_decision": target_decision,
                "reason": payload.reason,
                "notes": payload.notes,
                "edd_decision": target_decision,
            },
        )
    )
    await db.commit()
    await db.refresh(case)

    refreshed_screening = await crud_compliance.get_screening_request(screening_id=screening.id, db=db)
    risk = await crud_compliance.get_risk_assessment(screening_request_id=case.screening_request_id, db=db)
    customer_risk = await _build_customer_risk_public(refreshed_screening.session_id, db) if refreshed_screening else None
    results = await crud_compliance.list_screening_results(screening_request_id=case.screening_request_id, db=db)
    audit_logs = await crud_compliance.list_audit_logs(screening_request_id=case.screening_request_id, db=db)
    return ComplianceCaseDetailResponse(
        case=await _build_case_public(case, db),
        screening=await _build_screening_status(refreshed_screening, db),
        risk_assessment=RiskAssessmentPublic.model_validate(risk) if risk else None,
        customer_risk_assessment=customer_risk,
        results=[ScreeningResultPublic.model_validate(item) for item in results],
        audit_logs=[AuditLogPublic.model_validate(item) for item in audit_logs],
    )


@router.post("/cases/{case_id}/approve", response_model=ComplianceCaseDetailResponse, dependencies=[Depends(is_admin())])
async def approve_case(
    case_id: int,
    payload: CaseDecisionPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await _resolve_case(
        case_id=case_id,
        payload=payload,
        target_decision="APPROVED",
        current_user=current_user,
        db=db,
    )


@router.post("/cases/{case_id}/reject", response_model=ComplianceCaseDetailResponse, dependencies=[Depends(is_admin())])
async def reject_case(
    case_id: int,
    payload: CaseDecisionPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await _resolve_case(
        case_id=case_id,
        payload=payload,
        target_decision="REJECTED",
        current_user=current_user,
        db=db,
    )
