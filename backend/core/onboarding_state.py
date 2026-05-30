from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlmodel import Session, select
from sqlmodel.ext.asyncio.session import AsyncSession

from model.models import (
    AuditLog,
    ComplianceCase,
    CustomerIdentityProfile,
    CustomerRiskAssessment,
    OnboardingFaceVerification,
    OnboardingOCRExtraction,
    OnboardingSession,
    OnboardingSignatureCapture,
    ScreeningRequest,
)


TERMINAL_WORKFLOW_STATES = {"ONBOARDING_COMPLETED", "ONBOARDING_REJECTED"}
TERMINAL_SESSION_STATUSES = {"completed", "rejected"}


def utc_now() -> datetime:
    return datetime.utcnow()


def completed_steps_for_state(workflow_state: str) -> list[str]:
    steps: list[str] = []
    if workflow_state in {
        "FACE_VERIFICATION_COMPLETED",
        "OCR_PENDING",
        "OCR_COMPLETED",
        "IDENTITY_FORM_PENDING",
        "IDENTITY_FORM_IN_PROGRESS",
        "IDENTITY_FORM_COMPLETED",
        "SIGNATURE_PENDING",
        "SIGNATURE_COMPLETED",
        "SCREENING_PENDING",
        "SCREENING_IN_PROGRESS",
        "SCREENING_COMPLETED",
        "EDD_REQUIRED",
        "EDD_IN_REVIEW",
        "ONBOARDING_COMPLETED",
        "ONBOARDING_REJECTED",
    }:
        steps.append("face_verification")
    if workflow_state in {
        "OCR_COMPLETED",
        "IDENTITY_FORM_PENDING",
        "IDENTITY_FORM_IN_PROGRESS",
        "IDENTITY_FORM_COMPLETED",
        "SIGNATURE_PENDING",
        "SIGNATURE_COMPLETED",
        "SCREENING_PENDING",
        "SCREENING_IN_PROGRESS",
        "SCREENING_COMPLETED",
        "EDD_REQUIRED",
        "EDD_IN_REVIEW",
        "ONBOARDING_COMPLETED",
        "ONBOARDING_REJECTED",
    }:
        steps.append("ocr_extraction")
    if workflow_state in {
        "IDENTITY_FORM_COMPLETED",
        "SIGNATURE_PENDING",
        "SIGNATURE_COMPLETED",
        "SCREENING_PENDING",
        "SCREENING_IN_PROGRESS",
        "SCREENING_COMPLETED",
        "EDD_REQUIRED",
        "EDD_IN_REVIEW",
        "ONBOARDING_COMPLETED",
        "ONBOARDING_REJECTED",
    }:
        steps.append("identity_form")
    if workflow_state in {
        "SIGNATURE_COMPLETED",
        "ONBOARDING_COMPLETED",
        "ONBOARDING_REJECTED",
    }:
        steps.append("signature_capture")
    if workflow_state in {"SCREENING_COMPLETED", "ONBOARDING_COMPLETED", "ONBOARDING_REJECTED"}:
        steps.append("screening")
    return steps


def current_step_for_state(workflow_state: str) -> str:
    if workflow_state in {"ONBOARDING_STARTED", "FACE_VERIFICATION_PENDING"}:
        return "face_verification"
    if workflow_state in {"FACE_VERIFICATION_COMPLETED", "OCR_PENDING"}:
        return "ocr_extraction"
    if workflow_state in {"OCR_COMPLETED", "IDENTITY_FORM_PENDING", "IDENTITY_FORM_IN_PROGRESS"}:
        return "identity_form"
    if workflow_state in {"IDENTITY_FORM_COMPLETED", "SIGNATURE_PENDING"}:
        return "signature_capture"
    if workflow_state in {
        "SIGNATURE_COMPLETED",
        "SCREENING_PENDING",
        "SCREENING_IN_PROGRESS",
        "SCREENING_COMPLETED",
    }:
        return "screening_status"
    if workflow_state in {"EDD_REQUIRED", "EDD_IN_REVIEW"}:
        return "review_status"
    if workflow_state == "ONBOARDING_COMPLETED":
        return "complete"
    if workflow_state == "ONBOARDING_REJECTED":
        return "rejected"
    return "face_verification"


def next_required_step_for_state(workflow_state: str) -> str:
    return current_step_for_state(workflow_state)


def session_status_for_state(workflow_state: str) -> str:
    if workflow_state == "ONBOARDING_COMPLETED":
        return "completed"
    if workflow_state == "ONBOARDING_REJECTED":
        return "rejected"
    return "in_progress"


def draft_availability_for_state(
    *,
    workflow_state: str,
    identity_profile: CustomerIdentityProfile | None,
    signature: OnboardingSignatureCapture | None,
    risk: CustomerRiskAssessment | None,
) -> dict[str, bool]:
    return {
        "identity_form": bool(
            identity_profile
            and identity_profile.status
            in {"IDENTITY_FORM_PENDING", "IDENTITY_FORM_DRAFT_SAVED", "IDENTITY_FORM_IN_PROGRESS", "IDENTITY_FORM_COMPLETED"}
        ),
        "signature_capture": bool(signature),
        "risk_assessment": bool(risk),
        "supporting_documents": workflow_state
        not in {"ONBOARDING_STARTED", "FACE_VERIFICATION_PENDING"},
    }


def apply_workflow_state(
    session_row: OnboardingSession,
    workflow_state: str,
    *,
    completed_at: datetime | None = None,
) -> None:
    session_row.workflow_state = workflow_state
    session_row.completed_steps = completed_steps_for_state(workflow_state)
    session_row.current_step = current_step_for_state(workflow_state)
    session_row.status = session_status_for_state(workflow_state)
    if workflow_state == "ONBOARDING_COMPLETED":
        session_row.activation_status = "eligible"
        session_row.completed_at = completed_at or session_row.completed_at or utc_now()
    elif workflow_state == "ONBOARDING_REJECTED":
        session_row.activation_status = "blocked"
        session_row.completed_at = completed_at or session_row.completed_at or utc_now()
    elif workflow_state in {"SCREENING_PENDING", "SCREENING_IN_PROGRESS", "EDD_REQUIRED", "EDD_IN_REVIEW"}:
        session_row.activation_status = "blocked"
    elif workflow_state in {"IDENTITY_FORM_COMPLETED", "SIGNATURE_PENDING", "SCREENING_COMPLETED"}:
        session_row.activation_status = "pending"
    session_row.updated_at = utc_now()


async def transition_session_async(
    db: AsyncSession,
    session_row: OnboardingSession,
    workflow_state: str,
    *,
    actor_user_id: int | None = None,
    event_type: str = "onboarding_state_transition",
    message: str | None = None,
    payload: dict[str, Any] | None = None,
) -> OnboardingSession:
    previous_state = getattr(session_row, "workflow_state", None)
    apply_workflow_state(session_row, workflow_state)
    db.add(session_row)
    if previous_state != workflow_state:
        db.add(
            AuditLog(
                session_id=session_row.id,
                actor_user_id=actor_user_id,
                event_type=event_type,
                event_status="success",
                message=message or f"Onboarding workflow moved to {workflow_state}.",
                payload={
                    "previous_state": previous_state,
                    "workflow_state": workflow_state,
                    **(payload or {}),
                },
            )
        )
    await db.flush()
    await db.refresh(session_row)
    return session_row


def transition_session_sync(
    db: Session,
    session_row: OnboardingSession,
    workflow_state: str,
    *,
    actor_user_id: int | None = None,
    event_type: str = "onboarding_state_transition",
    message: str | None = None,
    payload: dict[str, Any] | None = None,
) -> OnboardingSession:
    previous_state = getattr(session_row, "workflow_state", None)
    apply_workflow_state(session_row, workflow_state)
    db.add(session_row)
    if previous_state != workflow_state:
        db.add(
            AuditLog(
                session_id=session_row.id,
                actor_user_id=actor_user_id,
                event_type=event_type,
                event_status="success",
                message=message or f"Onboarding workflow moved to {workflow_state}.",
                payload={
                    "previous_state": previous_state,
                    "workflow_state": workflow_state,
                    **(payload or {}),
                },
            )
        )
    return session_row


async def latest_async(db: AsyncSession, model, session_id: int, order_field: str = "created_at"):
    result = await db.exec(
        select(model)
        .where(model.session_id == session_id)
        .order_by(getattr(model, order_field).desc(), model.id.desc())
    )
    return result.first()


def latest_sync(db: Session, model, session_id: int, order_field: str = "created_at"):
    return db.exec(
        select(model)
        .where(model.session_id == session_id)
        .order_by(getattr(model, order_field).desc(), model.id.desc())
    ).first()


def derive_workflow_state(
    *,
    session_row: OnboardingSession,
    face: OnboardingFaceVerification | None,
    ocr: OnboardingOCRExtraction | None,
    identity_profile: CustomerIdentityProfile | None,
    signature: OnboardingSignatureCapture | None,
    screening: ScreeningRequest | None,
    risk: CustomerRiskAssessment | None,
    case: ComplianceCase | None,
) -> str:
    if screening and screening.status == "REJECTED":
        return "ONBOARDING_REJECTED"
    if screening and screening.status == "APPROVED":
        if signature:
            return "ONBOARDING_COMPLETED"
        return "SIGNATURE_PENDING"
    if risk and risk.edd_required:
        return "EDD_IN_REVIEW" if case and case.status == "OPEN" else "EDD_REQUIRED"
    if screening and screening.status == "REVIEW_REQUIRED":
        return "EDD_IN_REVIEW" if case and case.status == "OPEN" else "EDD_REQUIRED"
    if screening and screening.status in {"SCREENING_PENDING", "SCREENING_IN_PROGRESS"}:
        return screening.status
    if session_row.status == "rejected" or session_row.workflow_state == "ONBOARDING_REJECTED":
        return "ONBOARDING_REJECTED"
    if signature:
        return "SIGNATURE_COMPLETED"
    if identity_profile and identity_profile.status == "IDENTITY_FORM_COMPLETED":
        return "SIGNATURE_PENDING"
    if identity_profile and identity_profile.status in {"IDENTITY_FORM_DRAFT_SAVED", "IDENTITY_FORM_IN_PROGRESS"}:
        return "IDENTITY_FORM_IN_PROGRESS"
    if identity_profile and identity_profile.status == "IDENTITY_FORM_PENDING":
        return "IDENTITY_FORM_PENDING"
    if ocr:
        return "OCR_COMPLETED"
    if session_row.workflow_state == "OCR_PENDING":
        return "OCR_PENDING"
    if face:
        return "FACE_VERIFICATION_COMPLETED"
    return "FACE_VERIFICATION_PENDING"


async def resolve_session_state_async(db: AsyncSession, session_row: OnboardingSession) -> dict[str, Any]:
    session_id = session_row.id
    face = await latest_async(db, OnboardingFaceVerification, session_id)
    ocr = await latest_async(db, OnboardingOCRExtraction, session_id)
    identity_profile = await latest_async(db, CustomerIdentityProfile, session_id)
    signature = await latest_async(db, OnboardingSignatureCapture, session_id)
    screening = await latest_async(db, ScreeningRequest, session_id)
    risk = await latest_async(db, CustomerRiskAssessment, session_id, "calculated_at")
    case = None
    if screening:
        result = await db.exec(select(ComplianceCase).where(ComplianceCase.screening_request_id == screening.id))
        case = result.one_or_none()
    workflow_state = derive_workflow_state(
        session_row=session_row,
        face=face,
        ocr=ocr,
        identity_profile=identity_profile,
        signature=signature,
        screening=screening,
        risk=risk,
        case=case,
    )
    return {
        "workflow_state": workflow_state,
        "completed_steps": completed_steps_for_state(workflow_state),
        "current_step": current_step_for_state(workflow_state),
        "next_required_step": next_required_step_for_state(workflow_state),
        "draft_availability": draft_availability_for_state(
            workflow_state=workflow_state,
            identity_profile=identity_profile,
            signature=signature,
            risk=risk,
        ),
        "risk_category": risk.risk_category if risk else (identity_profile.risk_category if identity_profile else None),
        "identity_profile": identity_profile,
        "signature": signature,
        "screening": screening,
        "risk": risk,
    }


def resolve_session_state_sync(db: Session, session_row: OnboardingSession) -> dict[str, Any]:
    session_id = session_row.id
    face = latest_sync(db, OnboardingFaceVerification, session_id)
    ocr = latest_sync(db, OnboardingOCRExtraction, session_id)
    identity_profile = latest_sync(db, CustomerIdentityProfile, session_id)
    signature = latest_sync(db, OnboardingSignatureCapture, session_id)
    screening = latest_sync(db, ScreeningRequest, session_id)
    risk = latest_sync(db, CustomerRiskAssessment, session_id, "calculated_at")
    case = None
    if screening:
        case = db.exec(select(ComplianceCase).where(ComplianceCase.screening_request_id == screening.id)).first()
    workflow_state = derive_workflow_state(
        session_row=session_row,
        face=face,
        ocr=ocr,
        identity_profile=identity_profile,
        signature=signature,
        screening=screening,
        risk=risk,
        case=case,
    )
    return {
        "workflow_state": workflow_state,
        "completed_steps": completed_steps_for_state(workflow_state),
        "current_step": current_step_for_state(workflow_state),
        "next_required_step": next_required_step_for_state(workflow_state),
    }
