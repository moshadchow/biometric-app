from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from core.auth import get_current_user, is_admin
from core.config import settings
from core.db import get_session
from core.storage import IMAGE_MIME_TYPES, save_upload_file
from core.onboarding_state import (
    TERMINAL_SESSION_STATUSES,
    apply_workflow_state,
    current_step_for_state,
    next_required_step_for_state,
    resolve_session_state_async,
    transition_session_async,
)
from core.task_queue import enqueue_task
from crud import crud_compliance
from crud import crud_onboarding
from model.models import AuditLog, OnboardingSession, User
from schemas import (
    AdminCustomerOnboardingListResponse,
    AdminCustomerOnboardingPublic,
    ComplianceSummaryPublic,
    CustomerAddressPublic,
    CustomerIdentityFormPayload,
    CustomerIdentityFormResponse,
    CustomerIdentityProfilePublic,
    CustomerIdentitySubmitResponse,
    CustomerNomineePublic,
    OnboardingFaceVerificationPayload,
    OnboardingEligibilityResponse,
    OnboardingFaceVerificationPublic,
    OnboardingOCRExtractionPublic,
    OnboardingOCRPayload,
    OnboardingSessionListResponse,
    OnboardingSessionSummary,
    OnboardingSessionPublic,
    OnboardingSignatureCapturePublic,
    OnboardingSignaturePayload,
    OnboardingStepResponse,
    ReOnboardingApprovalPayload,
)
from tasks import start_screening_workflow


router = APIRouter()
logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.utcnow()


def to_naive_utc(value: datetime | None) -> datetime | None:
    if value is None:
        return None
    return value.replace(tzinfo=None)


async def save_upload_with_retry(
    upload: UploadFile,
    *,
    namespace: str,
    prefix: str,
    max_bytes: int | None = None,
    attempts: int = 2,
) -> dict[str, str | int]:
    last_error: Exception | None = None
    try:
        for attempt in range(attempts):
            try:
                if attempt > 0:
                    await upload.seek(0)
                return await save_upload_file(
                    upload,
                    namespace=namespace,
                    prefix=prefix,
                    max_bytes=max_bytes,
                )
            except OSError as exc:
                last_error = exc
                logger.warning("Upload write failed on attempt %s/%s: %s", attempt + 1, attempts, exc)
                if attempt + 1 < attempts:
                    await asyncio.sleep(0.1)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to persist the uploaded file.",
        ) from last_error
    finally:
        await upload.close()


def _load_payload(model_cls, raw_payload: str):
    try:
        return model_cls.model_validate_json(raw_payload)
    except Exception as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid onboarding payload.",
        ) from exc


async def build_session_response(
    session_row,
    db: AsyncSession,
) -> OnboardingSessionPublic:
    face = await crud_onboarding.get_face_verification(session_id=session_row.id, db=db)
    ocr = await crud_onboarding.get_ocr_extraction(session_id=session_row.id, db=db)
    signature = await crud_onboarding.get_signature_capture(session_id=session_row.id, db=db)
    compliance_summary = await crud_compliance.get_screening_summary(session_id=session_row.id, db=db)
    state = await resolve_session_state_async(db, session_row)
    if (
        session_row.workflow_state != state["workflow_state"]
        or session_row.current_step != state["current_step"]
        or session_row.completed_steps != state["completed_steps"]
        or session_row.status != ("completed" if state["workflow_state"] == "ONBOARDING_COMPLETED" else "rejected" if state["workflow_state"] == "ONBOARDING_REJECTED" else "in_progress")
    ):
        apply_workflow_state(session_row, state["workflow_state"])
        db.add(session_row)

    return OnboardingSessionPublic(
        id=session_row.id,
        user_id=session_row.user_id,
        status=session_row.status,
        current_step=session_row.current_step,
        workflow_state=session_row.workflow_state,
        completed_steps=session_row.completed_steps or [],
        next_required_step=state["next_required_step"],
        draft_availability=state["draft_availability"],
        document_references={
            "customer_photo": (
                {"path": face.reference_file_path, "file_name": face.reference_file_name}
                if face and face.reference_file_path
                else None
            ),
            "secondary_photo": (
                {"path": face.captured_file_path, "file_name": face.captured_file_name}
                if face
                else None
            ),
            "nid_front": (
                {"path": ocr.front_file_path, "file_name": ocr.front_file_name}
                if ocr
                else None
            ),
            "nid_back": (
                {"path": ocr.back_file_path, "file_name": ocr.back_file_name}
                if ocr and ocr.back_file_path
                else None
            ),
            "signature": (
                {"path": signature.signature_file_path, "file_name": signature.signature_file_name}
                if signature and signature.signature_file_path
                else None
            ),
        },
        risk_category=state["risk_category"],
        activation_status=session_row.activation_status,
        started_at=session_row.started_at,
        updated_at=session_row.updated_at,
        last_resumed_at=to_naive_utc(session_row.last_resumed_at),
        resume_count=session_row.resume_count,
        completed_at=to_naive_utc(session_row.completed_at),
        face_verification=(
            OnboardingFaceVerificationPublic(
                id=face.id,
                session_id=face.session_id,
                result=face.result,
                distance=face.distance,
                threshold=face.threshold,
                error_message=face.error_message,
                captured_file_path=face.captured_file_path,
                reference_file_path=face.reference_file_path,
                captured_file_name=face.captured_file_name,
                reference_file_name=face.reference_file_name,
                metadata=face.payload_metadata,
                created_at=to_naive_utc(face.created_at),
                updated_at=to_naive_utc(face.updated_at),
            )
            if face
            else None
        ),
        ocr_extraction=OnboardingOCRExtractionPublic.model_validate(ocr) if ocr else None,
        signature_capture=(
            OnboardingSignatureCapturePublic(
                id=signature.id,
                session_id=signature.session_id,
                signature_method=signature.signature_method,
                verification_method=signature.verification_method,
                account_risk=signature.account_risk,
                signer_name=signature.signer_name,
                signature_file_path=signature.signature_file_path,
                signature_file_name=signature.signature_file_name,
                signature_record=signature.signature_record,
                audit_log=signature.audit_log,
                metadata=signature.payload_metadata,
                integrity_hash=signature.integrity_hash,
                submitted_at=to_naive_utc(signature.submitted_at),
                created_at=to_naive_utc(signature.created_at),
                updated_at=to_naive_utc(signature.updated_at),
            )
            if signature
            else None
        ),
        compliance_summary=ComplianceSummaryPublic(**compliance_summary) if compliance_summary else None,
    )


def _public_identity_profile(profile) -> CustomerIdentityProfilePublic:
    return CustomerIdentityProfilePublic(
        id=profile.id,
        session_id=profile.session_id,
        form_type=profile.form_type,
        risk_category=profile.risk_category,
        status=profile.status,
        applicant_name=profile.applicant_name,
        account_number=profile.account_number,
        unique_account_number=profile.unique_account_number,
        nid_number=profile.nid_number,
        father_name=profile.father_name,
        mother_name=profile.mother_name,
        spouse_name=profile.spouse_name,
        date_of_birth=profile.date_of_birth,
        gender=profile.gender,
        profession=profile.profession,
        mobile_number=profile.mobile_number,
        monthly_income=profile.monthly_income,
        nationality=profile.nationality,
        source_of_funds=profile.source_of_funds,
        tin=profile.tin,
        expected_transaction_range=profile.expected_transaction_range,
        expected_transaction_pattern=profile.expected_transaction_pattern,
        existing_customer_review=profile.existing_customer_review,
        additional_documents_obtained=profile.additional_documents_obtained,
        additional_remarks=profile.additional_remarks,
        beneficial_owner_different=profile.beneficial_owner_different,
        beneficial_owner_name=profile.beneficial_owner_name,
        beneficial_owner_nationality=profile.beneficial_owner_nationality,
        beneficial_owner_identification_number=profile.beneficial_owner_identification_number,
        beneficial_owner_relationship=profile.beneficial_owner_relationship,
        ocr_snapshot=profile.ocr_snapshot,
        ocr_corrections=profile.ocr_corrections,
        metadata=profile.payload_metadata,
        created_at=to_naive_utc(profile.created_at),
        updated_at=to_naive_utc(profile.updated_at),
        submitted_at=to_naive_utc(profile.submitted_at),
    )


async def build_identity_form_response(
    *,
    session_row,
    db: AsyncSession,
    include_session: bool = False,
) -> CustomerIdentityFormResponse:
    profile = await crud_onboarding.ensure_identity_profile(session_id=session_row.id, db=db)
    addresses = await crud_onboarding.get_identity_addresses(profile_id=profile.id, db=db)
    nominee = await crud_onboarding.get_identity_nominee(profile_id=profile.id, db=db)
    face = await crud_onboarding.get_face_verification(session_id=session_row.id, db=db)
    ocr = await crud_onboarding.get_ocr_extraction(session_id=session_row.id, db=db)
    session_summary = build_session_summary(session_row) if include_session else None
    return CustomerIdentityFormResponse(
        profile=_public_identity_profile(profile),
        addresses={
            "present": CustomerAddressPublic.model_validate(addresses["present"]) if addresses.get("present") else None,
            "permanent": CustomerAddressPublic.model_validate(addresses["permanent"]) if addresses.get("permanent") else None,
        },
        nominee=(
            CustomerNomineePublic(
                id=nominee.id,
                nominee_name=nominee.nominee_name,
                relationship=nominee.relationship,
                photograph_file_path=nominee.photograph_file_path,
                photograph_file_name=nominee.photograph_file_name,
                metadata=nominee.payload_metadata,
            )
            if nominee
            else None
        ),
        document_references={
            "customer_photo": (
                {"path": face.reference_file_path, "file_name": face.reference_file_name}
                if face and face.reference_file_path
                else None
            ),
            "secondary_photo": (
                {"path": face.captured_file_path, "file_name": face.captured_file_name}
                if face
                else None
            ),
            "nid_front": (
                {"path": ocr.front_file_path, "file_name": ocr.front_file_name}
                if ocr
                else None
            ),
            "nid_back": (
                {"path": ocr.back_file_path, "file_name": ocr.back_file_name}
                if ocr and ocr.back_file_path
                else None
            ),
        },
        session=session_summary,
    )


def build_session_summary(session_row) -> OnboardingSessionSummary:
    workflow_state = getattr(session_row, "workflow_state", None) or "ONBOARDING_STARTED"
    return OnboardingSessionSummary(
        id=session_row.id,
        user_id=session_row.user_id,
        status=session_row.status,
        current_step=session_row.current_step,
        workflow_state=workflow_state,
        completed_steps=getattr(session_row, "completed_steps", None) or [],
        next_required_step=next_required_step_for_state(workflow_state),
        draft_availability={},
        risk_category=None,
        activation_status=session_row.activation_status,
        started_at=session_row.started_at,
        updated_at=session_row.updated_at,
        last_resumed_at=to_naive_utc(getattr(session_row, "last_resumed_at", None)),
        resume_count=getattr(session_row, "resume_count", 0) or 0,
        completed_at=to_naive_utc(session_row.completed_at),
    )


def _destination_for_eligibility(latest_session, user: User) -> str:
    if latest_session is None:
        return "onboarding"
    if latest_session.workflow_state == "ONBOARDING_COMPLETED" and not user.re_onboarding_allowed:
        return "customer_dashboard"
    if latest_session.workflow_state == "ONBOARDING_REJECTED":
        return "rejected"
    return "onboarding"


def build_eligibility_response(
    *,
    user: User,
    latest_session,
) -> OnboardingEligibilityResponse:
    destination = _destination_for_eligibility(latest_session, user)
    latest_summary = build_session_summary(latest_session) if latest_session else None
    completed = bool(latest_session and latest_session.workflow_state == "ONBOARDING_COMPLETED")
    rejected = bool(latest_session and latest_session.workflow_state == "ONBOARDING_REJECTED")
    can_start = not completed or user.re_onboarding_allowed
    can_resume = bool(
        latest_session
        and latest_session.status not in TERMINAL_SESSION_STATUSES
        and latest_session.workflow_state != "ONBOARDING_COMPLETED"
    )
    if completed and not user.re_onboarding_allowed:
        message = "Onboarding is already completed. Admin approval is required before re-onboarding."
    elif user.re_onboarding_allowed:
        message = "Re-onboarding has been approved by an administrator."
    elif rejected:
        message = "Onboarding was rejected."
    elif can_resume:
        message = "Active onboarding session can be resumed."
    else:
        message = "Customer can start onboarding."
    return OnboardingEligibilityResponse(
        user_id=user.id,
        username=user.username,
        latest_session=latest_summary,
        can_start_onboarding=can_start,
        can_resume_onboarding=can_resume,
        re_onboarding_allowed=user.re_onboarding_allowed,
        destination=destination,
        message=message,
    )


@router.post("/sessions/ensure", response_model=OnboardingStepResponse)
async def ensure_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    try:
        onboarding_session = await crud_onboarding.get_or_create_active_session(
            user_id=current_user.id,
            session=db,
        )
    except PermissionError as exc:
        if str(exc) == "ONBOARDING_ALREADY_COMPLETED":
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail={
                    "code": "ONBOARDING_ALREADY_COMPLETED",
                    "message": "Onboarding is already completed. Admin approval is required before re-onboarding.",
                },
            ) from exc
        raise
    response = await build_session_response(onboarding_session, db)
    return OnboardingStepResponse(message="Onboarding session ready.", session=response)


@router.get("/session/eligibility", response_model=OnboardingEligibilityResponse)
async def get_onboarding_eligibility(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    latest = await crud_onboarding.get_latest_session_for_user(user_id=current_user.id, session=db)
    if latest:
        await build_session_response(latest, db)
    return build_eligibility_response(user=current_user, latest_session=latest)


@router.get("/sessions/current", response_model=OnboardingStepResponse)
async def get_current_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    statement = (
        select(OnboardingSession)
        .where(OnboardingSession.user_id == current_user.id)
        .where(OnboardingSession.status.notin_(TERMINAL_SESSION_STATUSES))
        .order_by(OnboardingSession.updated_at.desc())
    )
    result = await db.exec(statement)
    onboarding_session = result.first()
    if onboarding_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No active onboarding session found.",
        )
    response = await build_session_response(onboarding_session, db)
    return OnboardingStepResponse(message="Current onboarding session loaded.", session=response)


@router.get("/session/current", response_model=OnboardingStepResponse)
async def get_current_resume_session(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    return await get_current_session(current_user=current_user, db=db)


@router.get("/sessions", response_model=OnboardingSessionListResponse)
async def list_sessions(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    statement = (
        select(OnboardingSession)
        .where(OnboardingSession.user_id == current_user.id)
        .order_by(OnboardingSession.updated_at.desc())
    )
    result = await db.exec(statement)
    items = [build_session_summary(row) for row in result.all()]
    return OnboardingSessionListResponse(items=items)


async def _admin_customer_public(user: User, db: AsyncSession) -> AdminCustomerOnboardingPublic:
    latest = await crud_onboarding.get_latest_session_for_user(user_id=user.id, session=db)
    if latest:
        await build_session_response(latest, db)
    return AdminCustomerOnboardingPublic(
        user_id=user.id,
        username=user.username,
        role=user.role,
        re_onboarding_allowed=user.re_onboarding_allowed,
        re_onboarding_allowed_at=to_naive_utc(user.re_onboarding_allowed_at),
        re_onboarding_allowed_by=user.re_onboarding_allowed_by,
        re_onboarding_reason=user.re_onboarding_reason,
        latest_session=build_session_summary(latest) if latest else None,
    )


@router.get("/admin/customers", response_model=AdminCustomerOnboardingListResponse, dependencies=[Depends(is_admin())])
async def list_customer_onboarding_statuses(
    db: AsyncSession = Depends(get_session),
):
    result = await db.exec(
        select(User)
        .where(User.role != "admin")
        .order_by(User.username.asc())
    )
    return AdminCustomerOnboardingListResponse(
        items=[await _admin_customer_public(user, db) for user in result.all()]
    )


@router.post(
    "/admin/customers/{user_id}/re-onboarding/allow",
    response_model=AdminCustomerOnboardingPublic,
    dependencies=[Depends(is_admin())],
)
async def allow_re_onboarding(
    user_id: int,
    payload: ReOnboardingApprovalPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    result = await db.exec(select(User).where(User.id == user_id, User.role != "admin"))
    customer = result.one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    latest = await crud_onboarding.get_latest_session_for_user(user_id=user_id, session=db)
    if latest is None or latest.workflow_state != "ONBOARDING_COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Re-onboarding can only be approved for completed customers.",
        )
    customer.re_onboarding_allowed = True
    customer.re_onboarding_allowed_at = utc_now()
    customer.re_onboarding_allowed_by = current_user.id
    customer.re_onboarding_reason = payload.reason
    db.add(customer)
    db.add(
        AuditLog(
            session_id=latest.id,
            actor_user_id=current_user.id,
            event_type="re_onboarding_approved",
            event_status="success",
            message="Administrator approved customer re-onboarding.",
            payload={"customer_user_id": user_id, "reason": payload.reason, "notes": payload.notes},
        )
    )
    await db.commit()
    await db.refresh(customer)
    return await _admin_customer_public(customer, db)


@router.post(
    "/admin/customers/{user_id}/re-onboarding/revoke",
    response_model=AdminCustomerOnboardingPublic,
    dependencies=[Depends(is_admin())],
)
async def revoke_re_onboarding(
    user_id: int,
    payload: ReOnboardingApprovalPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    result = await db.exec(select(User).where(User.id == user_id, User.role != "admin"))
    customer = result.one_or_none()
    if customer is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Customer not found.")
    latest = await crud_onboarding.get_latest_session_for_user(user_id=user_id, session=db)
    customer.re_onboarding_allowed = False
    customer.re_onboarding_allowed_at = None
    customer.re_onboarding_allowed_by = None
    customer.re_onboarding_reason = None
    db.add(customer)
    db.add(
        AuditLog(
            session_id=latest.id if latest else None,
            actor_user_id=current_user.id,
            event_type="re_onboarding_revoked",
            event_status="success",
            message="Administrator revoked customer re-onboarding approval.",
            payload={"customer_user_id": user_id, "reason": payload.reason, "notes": payload.notes},
        )
    )
    await db.commit()
    await db.refresh(customer)
    return await _admin_customer_public(customer, db)


async def _get_owned_session_or_404(
    *,
    session_id: int,
    current_user: User,
    db: AsyncSession,
):
    onboarding_session = await crud_onboarding.get_session_for_user(
        session_id=session_id,
        user_id=current_user.id,
        session=db,
    )
    if onboarding_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding session not found.")
    return onboarding_session


@router.get("/session/{session_id}/status", response_model=OnboardingStepResponse)
async def get_session_status(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    onboarding_session = await _get_owned_session_or_404(session_id=session_id, current_user=current_user, db=db)
    response = await build_session_response(onboarding_session, db)
    return OnboardingStepResponse(message="Onboarding session status loaded.", session=response)


@router.post("/session/{session_id}/resume", response_model=OnboardingStepResponse)
async def resume_session(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    onboarding_session = await _get_owned_session_or_404(session_id=session_id, current_user=current_user, db=db)
    state = await resolve_session_state_async(db, onboarding_session)
    await transition_session_async(
        db,
        onboarding_session,
        state["workflow_state"],
        actor_user_id=current_user.id,
        event_type="onboarding_session_resumed",
        message="Customer resumed onboarding session.",
        payload={
            "current_step": state["current_step"],
            "next_required_step": state["next_required_step"],
        },
    )
    onboarding_session.last_resumed_at = utc_now()
    onboarding_session.resume_count = (onboarding_session.resume_count or 0) + 1
    db.add(onboarding_session)
    await db.flush()
    await db.refresh(onboarding_session)
    response = await build_session_response(onboarding_session, db)
    return OnboardingStepResponse(message="Onboarding session resumed.", session=response)


def _validate_identity_submission(payload: CustomerIdentityFormPayload, form_type: str) -> None:
    missing: list[str] = []
    common = {
        "applicant_name": payload.applicant_name,
        "date_of_birth": payload.date_of_birth,
        "mobile_number": payload.mobile_number,
        "present_address.address_line": payload.present_address.address_line,
        "permanent_address.address_line": payload.permanent_address.address_line,
    }
    for field, value in common.items():
        if not str(value or "").strip():
            missing.append(field)
    if form_type == "regular":
        regular = {
            "source_of_funds": payload.source_of_funds,
            "nationality": payload.nationality,
            "monthly_income": payload.monthly_income,
        }
        for field, value in regular.items():
            if not str(value or "").strip():
                missing.append(field)
    if missing:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail={"message": "Identity form validation failed.", "missing_fields": missing},
        )


@router.get("/identity-form/{session_id}", response_model=CustomerIdentityFormResponse)
async def get_identity_form(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    onboarding_session = await _get_owned_session_or_404(session_id=session_id, current_user=current_user, db=db)
    ocr = await crud_onboarding.get_ocr_extraction(session_id=session_id, db=db)
    if ocr is None:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="OCR extraction is required before identity form.")
    form = await build_identity_form_response(session_row=onboarding_session, db=db, include_session=True)
    await db.commit()
    return form


@router.post("/identity-form/{session_id}/draft", response_model=CustomerIdentityFormResponse)
async def save_identity_form_draft(
    session_id: int,
    payload: CustomerIdentityFormPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    onboarding_session = await _get_owned_session_or_404(session_id=session_id, current_user=current_user, db=db)
    await crud_onboarding.save_identity_form(
        session_id=session_id,
        payload=payload.model_dump(),
        status_value="IDENTITY_FORM_DRAFT_SAVED",
        actor_user_id=current_user.id,
        db=db,
    )
    await transition_session_async(
        db,
        onboarding_session,
        "IDENTITY_FORM_IN_PROGRESS",
        actor_user_id=current_user.id,
        event_type="identity_form_draft_saved",
        message="Customer identity form draft saved.",
    )
    await db.commit()
    return await build_identity_form_response(session_row=onboarding_session, db=db, include_session=True)


@router.patch("/identity-form/{session_id}/autosave", response_model=CustomerIdentityFormResponse)
async def autosave_identity_form(
    session_id: int,
    payload: CustomerIdentityFormPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    onboarding_session = await _get_owned_session_or_404(session_id=session_id, current_user=current_user, db=db)
    await crud_onboarding.save_identity_form(
        session_id=session_id,
        payload=payload.model_dump(),
        status_value="IDENTITY_FORM_DRAFT_SAVED",
        actor_user_id=current_user.id,
        db=db,
    )
    await transition_session_async(
        db,
        onboarding_session,
        "IDENTITY_FORM_IN_PROGRESS",
        actor_user_id=current_user.id,
        event_type="identity_form_autosaved",
        message="Customer identity form autosaved.",
    )
    await db.commit()
    return await build_identity_form_response(session_row=onboarding_session, db=db, include_session=True)


@router.put("/identity-form/{session_id}", response_model=CustomerIdentityFormResponse)
async def update_identity_form(
    session_id: int,
    payload: CustomerIdentityFormPayload,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    onboarding_session = await _get_owned_session_or_404(session_id=session_id, current_user=current_user, db=db)
    await crud_onboarding.save_identity_form(
        session_id=session_id,
        payload=payload.model_dump(),
        status_value="IDENTITY_FORM_IN_PROGRESS",
        actor_user_id=current_user.id,
        db=db,
    )
    await transition_session_async(
        db,
        onboarding_session,
        "IDENTITY_FORM_IN_PROGRESS",
        actor_user_id=current_user.id,
        event_type="identity_form_updated",
        message="Customer identity form updated.",
    )
    await db.commit()
    return await build_identity_form_response(session_row=onboarding_session, db=db, include_session=True)


@router.post("/identity-form/{session_id}/submit", response_model=CustomerIdentitySubmitResponse)
async def submit_identity_form(
    session_id: int,
    payload: str = Form(...),
    nominee_photo: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    onboarding_session = await _get_owned_session_or_404(session_id=session_id, current_user=current_user, db=db)
    parsed = _load_payload(CustomerIdentityFormPayload, payload)
    profile = await crud_onboarding.ensure_identity_profile(session_id=session_id, db=db)
    _validate_identity_submission(parsed, profile.form_type)

    nominee_photo_info = None
    if nominee_photo is not None:
        if nominee_photo.content_type not in IMAGE_MIME_TYPES:
            raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Nominee photograph must be PNG or JPG.")
        nominee_photo_info = await save_upload_with_retry(
            nominee_photo,
            namespace=f"session-{session_id}",
            prefix="nominee-photo",
            max_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
        )

    await crud_onboarding.save_identity_form(
        session_id=session_id,
        payload=parsed.model_dump(),
        status_value="IDENTITY_FORM_COMPLETED",
        actor_user_id=current_user.id,
        db=db,
        nominee_photo_info=nominee_photo_info,
    )
    screening_request = await crud_compliance.ensure_screening_request(
        session_row=onboarding_session,
        trigger_source="identity_form_submission",
        db=db,
    )
    await transition_session_async(
        db,
        onboarding_session,
        "SCREENING_PENDING",
        actor_user_id=current_user.id,
        event_type="screening_pending",
        message="Compliance screening request created.",
        payload={"screening_request_id": screening_request.id},
    )
    await db.commit()
    await db.refresh(onboarding_session)
    enqueue_task(start_screening_workflow, screening_request.id)
    form = await build_identity_form_response(session_row=onboarding_session, db=db, include_session=True)
    return CustomerIdentitySubmitResponse(
        message="Customer identity form submitted.",
        form=form,
        session=build_session_summary(onboarding_session),
    )


@router.get("/sessions/{session_id}", response_model=OnboardingStepResponse)
async def get_session_details(
    session_id: int,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    onboarding_session = await crud_onboarding.get_session_for_user(
        session_id=session_id,
        user_id=current_user.id,
        session=db,
    )
    if onboarding_session is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Onboarding session not found.",
        )

    response = await build_session_response(onboarding_session, db)
    return OnboardingStepResponse(message="Onboarding session loaded.", session=response)


@router.post("/sessions/{session_id}/face-verification", response_model=OnboardingStepResponse)
async def store_face_verification(
    session_id: int,
    payload: str = Form(...),
    captured_image: UploadFile = File(...),
    reference_image: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    onboarding_session = await crud_onboarding.get_session_for_user(
        session_id=session_id,
        user_id=current_user.id,
        session=db,
    )
    if onboarding_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding session not found.")

    parsed = _load_payload(OnboardingFaceVerificationPayload, payload)

    if captured_image.content_type not in IMAGE_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Captured image must be PNG or JPG.")
    if reference_image and reference_image.content_type not in IMAGE_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Reference image must be PNG or JPG.")

    captured_info = await save_upload_with_retry(
        captured_image,
        namespace=f"session-{session_id}",
        prefix="face-captured",
        max_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
    )

    reference_info = None
    if reference_image is not None:
        reference_info = await save_upload_with_retry(
            reference_image,
            namespace=f"session-{session_id}",
            prefix="face-reference",
            max_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
        )

    record = await crud_onboarding.upsert_face_verification(
        session_id=session_id,
        db=db,
        payload={
            "result": parsed.result,
            "distance": parsed.distance,
            "threshold": parsed.threshold,
            "error_message": parsed.error_message,
            "captured_file_path": str(captured_info["stored_path"]),
            "reference_file_path": str(reference_info["stored_path"]) if reference_info else None,
            "captured_file_name": str(captured_info["original_name"]),
            "reference_file_name": str(reference_info["original_name"]) if reference_info else None,
            "payload_metadata": {
                **parsed.metadata,
                "captured_content_type": captured_info["content_type"],
                "captured_size_bytes": captured_info["size_bytes"],
                "reference_content_type": reference_info["content_type"] if reference_info else None,
                "reference_size_bytes": reference_info["size_bytes"] if reference_info else None,
            },
        },
    )

    await transition_session_async(
        db,
        onboarding_session,
        "OCR_PENDING",
        actor_user_id=current_user.id,
        event_type="face_verification_completed",
        message="Face verification completed.",
    )

    response = await build_session_response(onboarding_session, db)
    return OnboardingStepResponse(message="Face verification stored.", session=response)


@router.post("/sessions/{session_id}/ocr-extraction", response_model=OnboardingStepResponse)
async def store_ocr_extraction(
    session_id: int,
    payload: str = Form(...),
    front_file: UploadFile = File(...),
    back_file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    onboarding_session = await crud_onboarding.get_session_for_user(
        session_id=session_id,
        user_id=current_user.id,
        session=db,
    )
    if onboarding_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding session not found.")

    parsed = _load_payload(OnboardingOCRPayload, payload)

    if front_file.content_type not in IMAGE_MIME_TYPES and front_file.content_type != "application/pdf":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Front document must be a JPG, PNG, or PDF file.")
    if back_file and back_file.content_type not in IMAGE_MIME_TYPES and back_file.content_type != "application/pdf":
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Back document must be a JPG, PNG, or PDF file.")

    front_info = await save_upload_with_retry(
        front_file,
        namespace=f"session-{session_id}",
        prefix="ocr-front",
        max_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
    )

    back_info = None
    if back_file is not None:
        back_info = await save_upload_with_retry(
            back_file,
            namespace=f"session-{session_id}",
            prefix="ocr-back",
            max_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
        )

    front_text = parsed.front.get("combinedText") or parsed.front.get("combined_text") or ""
    back_text = ""
    if parsed.back:
        back_text = parsed.back.get("combinedText") or parsed.back.get("combined_text") or ""

    record = await crud_onboarding.upsert_ocr_extraction(
        session_id=session_id,
        db=db,
        payload={
            "front_file_path": str(front_info["stored_path"]),
            "back_file_path": str(back_info["stored_path"]) if back_info else None,
            "front_file_name": str(front_info["original_name"]),
            "back_file_name": str(back_info["original_name"]) if back_info else None,
            "front_text": front_text,
            "back_text": back_text or None,
            "merged_text": parsed.mergedText,
            "fields": parsed.fields,
            "front_detection": parsed.frontDetection,
            "back_detection": parsed.backDetection,
            "completed_at": to_naive_utc(
                datetime.fromisoformat(parsed.completedAt.replace("Z", "+00:00"))
            ),
        },
    )

    await crud_onboarding.ensure_identity_profile(session_id=session_id, db=db)
    await transition_session_async(
        db,
        onboarding_session,
        "IDENTITY_FORM_PENDING",
        actor_user_id=current_user.id,
        event_type="ocr_completed",
        message="OCR extraction completed.",
    )
    await db.commit()
    await db.refresh(onboarding_session)

    response = await build_session_response(onboarding_session, db)
    return OnboardingStepResponse(message="OCR extraction stored.", session=response)


@router.post("/sessions/{session_id}/signature", response_model=OnboardingStepResponse)
async def store_signature_capture(
    session_id: int,
    payload: str = Form(...),
    signature_file: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_session),
):
    onboarding_session = await crud_onboarding.get_session_for_user(
        session_id=session_id,
        user_id=current_user.id,
        session=db,
    )
    if onboarding_session is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Onboarding session not found.")

    identity_profile = await crud_onboarding.get_identity_profile(session_id=session_id, db=db)
    if identity_profile is None or identity_profile.status != "IDENTITY_FORM_COMPLETED":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Customer identity form must be submitted before signature capture.",
        )

    parsed = _load_payload(OnboardingSignaturePayload, payload)

    if signature_file and signature_file.content_type not in IMAGE_MIME_TYPES:
        raise HTTPException(status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE, detail="Signature file must be PNG or JPG.")

    signature_info = None
    if signature_file is not None:
        signature_info = await save_upload_with_retry(
            signature_file,
            namespace=f"session-{session_id}",
            prefix="signature",
            max_bytes=settings.MAX_UPLOAD_SIZE_BYTES,
        )

    record = await crud_onboarding.upsert_signature_capture(
        session_id=session_id,
        db=db,
        payload={
            "signature_method": parsed.signatureMethod,
            "verification_method": parsed.verificationMethod,
            "account_risk": parsed.accountRisk,
            "signer_name": parsed.signerName,
            "signature_file_path": str(signature_info["stored_path"]) if signature_info else None,
            "signature_file_name": str(signature_info["original_name"]) if signature_info else None,
            "signature_record": parsed.model_dump(),
            "audit_log": parsed.auditLog,
            "payload_metadata": parsed.metadata,
            "integrity_hash": parsed.integrityHash,
            "submitted_at": to_naive_utc(
                datetime.fromisoformat(
                    (parsed.metadata.get("submittedAt") or parsed.metadata.get("submitted_at")).replace(
                        "Z",
                        "+00:00",
                    )
                )
            )
            if (parsed.metadata.get("submittedAt") or parsed.metadata.get("submitted_at"))
            else utc_now(),
        },
    )

    state = await resolve_session_state_async(db, onboarding_session)
    await transition_session_async(
        db,
        onboarding_session,
        state["workflow_state"],
        actor_user_id=current_user.id,
        event_type="signature_capture_submitted",
        message="Signature capture submitted.",
    )

    response = await build_session_response(onboarding_session, db)
    return OnboardingStepResponse(message="Signature stored.", session=response)
