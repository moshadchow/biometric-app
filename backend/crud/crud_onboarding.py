from __future__ import annotations

from datetime import datetime
from typing import Any

import logging

from sqlalchemy import desc, text
from sqlalchemy.exc import IntegrityError
from sqlmodel import select
from sqlmodel.ext.asyncio.session import AsyncSession

from model.models import (
    AuditLog,
    CustomerAddress,
    CustomerIdentityProfile,
    CustomerNominee,
    OnboardingFaceVerification,
    OnboardingOCRExtraction,
    OnboardingSession,
    OnboardingSignatureCapture,
    User,
)
from core.onboarding_state import TERMINAL_SESSION_STATUSES


logger = logging.getLogger(__name__)


def utc_now() -> datetime:
    return datetime.utcnow()


async def get_or_create_active_session(
    *,
    user_id: int,
    session: AsyncSession,
) -> OnboardingSession:
    await session.exec(
        text("SELECT pg_advisory_xact_lock(:lock_key)").bindparams(lock_key=user_id)
    )

    statement = (
        select(OnboardingSession)
        .where(OnboardingSession.user_id == user_id)
        .where(OnboardingSession.status.notin_(TERMINAL_SESSION_STATUSES))
        .order_by(desc(OnboardingSession.updated_at))
        .limit(1)
    )
    result = await session.exec(statement)
    onboarding_session = result.first()
    if onboarding_session:
        logger.info(
            "Reusing active onboarding session %s for user %s",
            onboarding_session.id,
            user_id,
        )
        return onboarding_session

    latest = await get_latest_session_for_user(user_id=user_id, session=session)
    if latest and latest.workflow_state == "ONBOARDING_COMPLETED":
        user_result = await session.exec(select(User).where(User.id == user_id))
        user = user_result.one_or_none()
        if user is None or not user.re_onboarding_allowed:
            session.add(
                AuditLog(
                    session_id=latest.id,
                    actor_user_id=user_id,
                    event_type="re_onboarding_blocked",
                    event_status="warning",
                    message="Completed customer attempted to restart onboarding without admin approval.",
                    payload={"workflow_state": latest.workflow_state},
                )
            )
            await session.flush()
            raise PermissionError("ONBOARDING_ALREADY_COMPLETED")

    onboarding_session = OnboardingSession(user_id=user_id)
    session.add(onboarding_session)
    try:
        await session.flush()
    except IntegrityError:
        await session.rollback()
        result = await session.exec(statement)
        onboarding_session = result.first()
        if onboarding_session:
            logger.warning(
                "Resolved onboarding session creation race for user %s by reusing session %s",
                user_id,
                onboarding_session.id,
            )
            return onboarding_session
        raise
    user_result = await session.exec(select(User).where(User.id == user_id))
    user = user_result.one_or_none()
    if user and user.re_onboarding_allowed:
        previous_reason = user.re_onboarding_reason
        user.re_onboarding_allowed = False
        user.re_onboarding_allowed_at = None
        user.re_onboarding_allowed_by = None
        user.re_onboarding_reason = None
        session.add(user)
        session.add(
            AuditLog(
                session_id=onboarding_session.id,
                actor_user_id=user_id,
                event_type="re_onboarding_approval_consumed",
                event_status="success",
                message="Admin re-onboarding approval consumed by new onboarding session.",
                payload={"reason": previous_reason},
            )
        )
    session.add(
        AuditLog(
            session_id=onboarding_session.id,
            actor_user_id=user_id,
            event_type="onboarding_session_created",
            event_status="success",
            message="Onboarding session created.",
            payload={"workflow_state": onboarding_session.workflow_state},
        )
    )
    await session.flush()
    await session.refresh(onboarding_session)
    return onboarding_session


async def get_latest_session_for_user(
    *,
    user_id: int,
    session: AsyncSession,
) -> OnboardingSession | None:
    result = await session.exec(
        select(OnboardingSession)
        .where(OnboardingSession.user_id == user_id)
        .order_by(desc(OnboardingSession.updated_at), desc(OnboardingSession.id))
        .limit(1)
    )
    return result.first()


async def get_session_for_user(
    *,
    session_id: int,
    user_id: int,
    session: AsyncSession,
) -> OnboardingSession | None:
    statement = select(OnboardingSession).where(
        OnboardingSession.id == session_id,
        OnboardingSession.user_id == user_id,
    )
    result = await session.exec(statement)
    return result.one_or_none()


async def get_face_verification(
    *,
    session_id: int,
    db: AsyncSession,
) -> OnboardingFaceVerification | None:
    statement = select(OnboardingFaceVerification).where(
        OnboardingFaceVerification.session_id == session_id
    )
    result = await db.exec(statement)
    return result.one_or_none()


async def upsert_face_verification(
    *,
    session_id: int,
    payload: dict[str, Any],
    db: AsyncSession,
) -> OnboardingFaceVerification:
    record = await get_face_verification(session_id=session_id, db=db)
    if record is None:
        record = OnboardingFaceVerification(session_id=session_id, **payload)
        db.add(record)
    else:
        for key, value in payload.items():
            setattr(record, key, value)
        record.updated_at = utc_now()

    await db.flush()
    await db.refresh(record)
    return record


async def get_ocr_extraction(
    *,
    session_id: int,
    db: AsyncSession,
) -> OnboardingOCRExtraction | None:
    statement = select(OnboardingOCRExtraction).where(
        OnboardingOCRExtraction.session_id == session_id
    )
    result = await db.exec(statement)
    return result.one_or_none()


async def upsert_ocr_extraction(
    *,
    session_id: int,
    payload: dict[str, Any],
    db: AsyncSession,
) -> OnboardingOCRExtraction:
    record = await get_ocr_extraction(session_id=session_id, db=db)
    if record is None:
        record = OnboardingOCRExtraction(session_id=session_id, **payload)
        db.add(record)
    else:
        for key, value in payload.items():
            setattr(record, key, value)
        record.updated_at = utc_now()

    await db.flush()
    await db.refresh(record)
    return record


PROFILE_FIELDS = {
    "applicant_name",
    "account_number",
    "unique_account_number",
    "nid_number",
    "father_name",
    "mother_name",
    "spouse_name",
    "date_of_birth",
    "gender",
    "profession",
    "mobile_number",
    "monthly_income",
    "nationality",
    "source_of_funds",
    "tin",
    "expected_transaction_range",
    "expected_transaction_pattern",
    "existing_customer_review",
    "additional_documents_obtained",
    "additional_remarks",
    "beneficial_owner_different",
    "beneficial_owner_name",
    "beneficial_owner_nationality",
    "beneficial_owner_identification_number",
    "beneficial_owner_relationship",
}


def build_identity_prefill(ocr: OnboardingOCRExtraction | None) -> dict[str, Any]:
    fields = ocr.fields if ocr else {}
    address = fields.get("addressRaw") or fields.get("address") or ""
    district = fields.get("district")
    return {
        "profile": {
            "applicant_name": fields.get("nameEnglish") or fields.get("nameBengali"),
            "nid_number": fields.get("idNumber"),
            "father_name": fields.get("fatherName"),
            "mother_name": fields.get("motherName"),
            "date_of_birth": fields.get("dateOfBirth"),
        },
        "present_address": {
            "address_line": address,
            "district": district,
        },
        "permanent_address": {
            "address_line": address,
            "district": district,
        },
    }


def calculate_pre_form_risk(ocr: OnboardingOCRExtraction | None) -> dict[str, Any]:
    from core.compliance import SCREENING_JOB_NAMES, calculate_risk, run_provider

    subject = {
        "fields": ocr.fields if ocr else {},
        "metadata": {"merged_text": ocr.merged_text if ocr else "", "network": {}},
    }
    results = [run_provider(job_name, subject) for job_name in SCREENING_JOB_NAMES]
    risk = calculate_risk(results)
    return {
        "risk_category": risk["risk_category"],
        "risk_score": risk["risk_score"],
        "factors": risk["factors"],
        "rules_snapshot": risk["rules_snapshot"],
    }


def form_type_for_risk(risk_category: str) -> str:
    return "simplified" if risk_category == "LOW" else "regular"


async def get_identity_profile(
    *,
    session_id: int,
    db: AsyncSession,
) -> CustomerIdentityProfile | None:
    result = await db.exec(
        select(CustomerIdentityProfile).where(CustomerIdentityProfile.session_id == session_id)
    )
    return result.one_or_none()


async def get_identity_addresses(
    *,
    profile_id: int,
    db: AsyncSession,
) -> dict[str, CustomerAddress | None]:
    result = await db.exec(select(CustomerAddress).where(CustomerAddress.profile_id == profile_id))
    addresses = {row.address_type: row for row in result.all()}
    return {
        "present": addresses.get("present"),
        "permanent": addresses.get("permanent"),
    }


async def get_identity_nominee(
    *,
    profile_id: int,
    db: AsyncSession,
) -> CustomerNominee | None:
    result = await db.exec(select(CustomerNominee).where(CustomerNominee.profile_id == profile_id))
    return result.one_or_none()


async def ensure_identity_profile(
    *,
    session_id: int,
    db: AsyncSession,
) -> CustomerIdentityProfile:
    profile = await get_identity_profile(session_id=session_id, db=db)
    if profile is not None:
        return profile

    ocr = await get_ocr_extraction(session_id=session_id, db=db)
    prefill = build_identity_prefill(ocr)
    from core.risk_assessment import calculate_and_persist_async

    preliminary_assessment, preliminary_payload = await calculate_and_persist_async(
        db,
        session_id=session_id,
        assessment_type="preliminary",
    )
    risk = {
        "risk_category": preliminary_assessment.risk_category,
        "risk_score": preliminary_assessment.total_score,
        "factors": [
            {"rule": factor.name, "score": factor.score, "source": factor.source}
            for factor in preliminary_payload["factors"]
        ],
        "rules_snapshot": preliminary_assessment.rules_snapshot,
    }
    profile = CustomerIdentityProfile(
        session_id=session_id,
        form_type=form_type_for_risk(risk["risk_category"]),
        risk_category=risk["risk_category"],
        status="IDENTITY_FORM_PENDING",
        ocr_snapshot={
            **prefill["profile"],
            "present_address": prefill["present_address"],
            "permanent_address": prefill["permanent_address"],
        },
        payload_metadata={"pre_form_risk": risk},
        **{key: value for key, value in prefill["profile"].items() if value is not None},
    )
    db.add(profile)
    await db.flush()

    for address_type, address_payload in (
        ("present", prefill["present_address"]),
        ("permanent", prefill["permanent_address"]),
    ):
        db.add(CustomerAddress(profile_id=profile.id, address_type=address_type, **address_payload))

    db.add(CustomerNominee(profile_id=profile.id))
    await db.flush()
    await db.refresh(profile)
    return profile


def _profile_payload(payload: dict[str, Any]) -> dict[str, Any]:
    return {key: payload[key] for key in PROFILE_FIELDS if key in payload}


def _address_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    return {
        "address_line": payload.get("address_line"),
        "city": payload.get("city"),
        "district": payload.get("district"),
        "postal_code": payload.get("postal_code"),
    }


def _nominee_payload(payload: dict[str, Any] | None) -> dict[str, Any]:
    payload = payload or {}
    return {
        "nominee_name": payload.get("nominee_name"),
        "relationship": payload.get("relationship"),
    }


def compute_ocr_corrections(profile: CustomerIdentityProfile, addresses: dict[str, CustomerAddress | None]) -> dict[str, Any]:
    snapshot = profile.ocr_snapshot or {}
    current = {
        "applicant_name": profile.applicant_name,
        "nid_number": profile.nid_number,
        "father_name": profile.father_name,
        "mother_name": profile.mother_name,
        "date_of_birth": profile.date_of_birth,
        "present_address": {
            "address_line": addresses["present"].address_line if addresses.get("present") else None,
            "district": addresses["present"].district if addresses.get("present") else None,
        },
        "permanent_address": {
            "address_line": addresses["permanent"].address_line if addresses.get("permanent") else None,
            "district": addresses["permanent"].district if addresses.get("permanent") else None,
        },
    }
    corrections: dict[str, Any] = {}
    for key, original_value in snapshot.items():
        current_value = current.get(key)
        if current_value != original_value:
            corrections[key] = {"from": original_value, "to": current_value}
    return corrections


async def save_identity_form(
    *,
    session_id: int,
    payload: dict[str, Any],
    status_value: str,
    actor_user_id: int,
    db: AsyncSession,
    nominee_photo_info: dict[str, Any] | None = None,
) -> CustomerIdentityProfile:
    profile = await ensure_identity_profile(session_id=session_id, db=db)
    for key, value in _profile_payload(payload).items():
        setattr(profile, key, value)
    profile.status = status_value
    profile.updated_at = utc_now()
    if status_value == "IDENTITY_FORM_COMPLETED":
        profile.submitted_at = utc_now()
    if payload.get("metadata"):
        profile.payload_metadata = {**(profile.payload_metadata or {}), **payload["metadata"]}
    db.add(profile)
    await db.flush()

    current_addresses = await get_identity_addresses(profile_id=profile.id, db=db)
    for address_type, key in (("present", "present_address"), ("permanent", "permanent_address")):
        address = current_addresses.get(address_type)
        values = _address_payload(payload.get(key))
        if address is None:
            address = CustomerAddress(profile_id=profile.id, address_type=address_type, **values)
        else:
            for field, value in values.items():
                setattr(address, field, value)
            address.updated_at = utc_now()
        db.add(address)

    nominee = await get_identity_nominee(profile_id=profile.id, db=db)
    nominee_values = _nominee_payload(payload.get("nominee"))
    if nominee is None:
        nominee = CustomerNominee(profile_id=profile.id, **nominee_values)
    else:
        for field, value in nominee_values.items():
            setattr(nominee, field, value)
        nominee.updated_at = utc_now()
    if nominee_photo_info is not None:
        nominee.photograph_file_path = str(nominee_photo_info["stored_path"])
        nominee.photograph_file_name = str(nominee_photo_info["original_name"])
        nominee.payload_metadata = {
            **(nominee.payload_metadata or {}),
            "content_type": nominee_photo_info["content_type"],
            "size_bytes": nominee_photo_info["size_bytes"],
        }
    db.add(nominee)

    await db.flush()
    addresses = await get_identity_addresses(profile_id=profile.id, db=db)
    profile.ocr_corrections = compute_ocr_corrections(profile, addresses)
    profile.updated_at = utc_now()
    db.add(profile)

    db.add(
        AuditLog(
            session_id=session_id,
            actor_user_id=actor_user_id,
            event_type="identity_form_saved" if status_value != "IDENTITY_FORM_COMPLETED" else "identity_form_submitted",
            event_status="success",
            message="Customer identity form saved." if status_value != "IDENTITY_FORM_COMPLETED" else "Customer identity form submitted.",
            payload={
                "status": status_value,
                "form_type": profile.form_type,
                "risk_category": profile.risk_category,
                "ocr_corrections": profile.ocr_corrections,
            },
        )
    )
    if profile.ocr_corrections:
        db.add(
            AuditLog(
                session_id=session_id,
                actor_user_id=actor_user_id,
                event_type="identity_form_ocr_corrections",
                event_status="info",
                message="Customer corrected OCR-extracted identity fields.",
                payload=profile.ocr_corrections,
            )
        )
    await db.flush()
    await db.refresh(profile)
    return profile


async def get_signature_capture(
    *,
    session_id: int,
    db: AsyncSession,
) -> OnboardingSignatureCapture | None:
    statement = select(OnboardingSignatureCapture).where(
        OnboardingSignatureCapture.session_id == session_id
    )
    result = await db.exec(statement)
    return result.one_or_none()


async def upsert_signature_capture(
    *,
    session_id: int,
    payload: dict[str, Any],
    db: AsyncSession,
) -> OnboardingSignatureCapture:
    record = await get_signature_capture(session_id=session_id, db=db)
    if record is None:
        record = OnboardingSignatureCapture(session_id=session_id, **payload)
        db.add(record)
    else:
        for key, value in payload.items():
            setattr(record, key, value)
        record.updated_at = utc_now()

    await db.flush()
    await db.refresh(record)
    return record
