from __future__ import annotations

import time
from datetime import datetime, timezone
from typing import Any

from celery import chain, chord, group
from sqlmodel import Session, create_engine, select

from core.compliance import SCREENING_JOB_NAMES, run_provider
from core.onboarding_state import resolve_session_state_sync, transition_session_sync
from core.config import settings
from core.risk_assessment import calculate_and_persist_sync, ensure_review_case_sync, latest_assessment_sync
from model.models import (
    AuditLog,
    ComplianceCase,
    CustomerAddress,
    CustomerIdentityProfile,
    CustomerNominee,
    OnboardingOCRExtraction,
    OnboardingSession,
    OnboardingSignatureCapture,
    ProductOrder as Order,
    RiskAssessment,
    ScreeningDecision,
    ScreeningJob,
    ScreeningRequest,
    ScreeningResult,
)
from worker import celery_app


engine = create_engine(settings.DATABASE_SYNC_URL, echo=True)
STAGES = ["Packaging", "Shipping", "Delivered"]


def utc_now() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)


def _log_event(
    session: Session,
    *,
    screening_request_id: int | None = None,
    session_id: int | None = None,
    actor_user_id: int | None = None,
    event_type: str,
    message: str,
    event_status: str = "info",
    payload: dict[str, Any] | None = None,
) -> None:
    session.add(
        AuditLog(
            screening_request_id=screening_request_id,
            session_id=session_id,
            actor_user_id=actor_user_id,
            event_type=event_type,
            event_status=event_status,
            message=message,
            payload=payload or {},
        )
    )


def _get_or_create_job(
    session: Session,
    *,
    screening_request_id: int,
    job_name: str,
) -> ScreeningJob:
    job = session.exec(
        select(ScreeningJob).where(
            ScreeningJob.screening_request_id == screening_request_id,
            ScreeningJob.job_name == job_name,
        )
    ).first()
    if job is None:
        job = ScreeningJob(screening_request_id=screening_request_id, job_name=job_name)
        session.add(job)
        session.flush()
    return job


def _load_subject(session: Session, screening_request: ScreeningRequest) -> dict[str, Any]:
    onboarding_session = session.exec(
        select(OnboardingSession).where(OnboardingSession.id == screening_request.session_id)
    ).first()
    ocr = session.exec(
        select(OnboardingOCRExtraction).where(OnboardingOCRExtraction.session_id == screening_request.session_id)
    ).first()
    signature = session.exec(
        select(OnboardingSignatureCapture).where(OnboardingSignatureCapture.session_id == screening_request.session_id)
    ).first()
    identity_profile = session.exec(
        select(CustomerIdentityProfile).where(CustomerIdentityProfile.session_id == screening_request.session_id)
    ).first()
    identity_addresses = []
    identity_nominee = None
    if identity_profile:
        identity_addresses = list(
            session.exec(select(CustomerAddress).where(CustomerAddress.profile_id == identity_profile.id)).all()
        )
        identity_nominee = session.exec(
            select(CustomerNominee).where(CustomerNominee.profile_id == identity_profile.id)
        ).first()

    identity_fields = {}
    if identity_profile:
        identity_fields = {
            "name": identity_profile.applicant_name,
            "full_name": identity_profile.applicant_name,
            "nid_number": identity_profile.nid_number,
            "date_of_birth": identity_profile.date_of_birth,
            "father_name": identity_profile.father_name,
            "mother_name": identity_profile.mother_name,
            "profession": identity_profile.profession,
            "mobile_number": identity_profile.mobile_number,
            "monthly_income": identity_profile.monthly_income,
            "nationality": identity_profile.nationality,
            "source_of_funds": identity_profile.source_of_funds,
            "country": identity_profile.nationality,
        }

    return {
        "screening_request_id": screening_request.id,
        "session_id": screening_request.session_id,
        "user_id": screening_request.user_id,
        "fields": {**(ocr.fields if ocr else {}), **{k: v for k, v in identity_fields.items() if v}},
        "metadata": {
            "merged_text": ocr.merged_text if ocr else "",
            "signature_method": signature.signature_method if signature else None,
            "identity_form_type": identity_profile.form_type if identity_profile else None,
            "identity_risk_category": identity_profile.risk_category if identity_profile else None,
            "addresses": [
                {
                    "type": address.address_type,
                    "address_line": address.address_line,
                    "city": address.city,
                    "district": address.district,
                    "postal_code": address.postal_code,
                }
                for address in identity_addresses
            ],
            "nominee": {
                "name": identity_nominee.nominee_name,
                "relationship": identity_nominee.relationship,
            }
            if identity_nominee
            else None,
            "network": {},
        },
        "session_status": onboarding_session.status if onboarding_session else None,
    }


@celery_app.task
def process_order(order_id: int):
    with Session(engine) as session:
        order = session.exec(select(Order).where(Order.id == order_id)).first()
        if not order:
            return {"error": "Order not found"}

        for stage in STAGES:
            time.sleep(10)
            order.status = stage
            session.add(order)
            session.commit()
            session.refresh(order)

    return {"order_id": order.id, "final_status": order.status}


@celery_app.task(bind=True)
def start_screening_workflow(self, screening_request_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        screening = session.exec(
            select(ScreeningRequest).where(ScreeningRequest.id == screening_request_id)
        ).first()
        if screening is None:
            return {"error": "screening_request_not_found"}
        if screening.status in {"APPROVED", "REJECTED", "REVIEW_REQUIRED"}:
            return {"screening_request_id": screening.id, "status": screening.status}

        screening.status = "SCREENING_IN_PROGRESS"
        screening.workflow_id = self.request.id
        screening.started_at = screening.started_at or utc_now()
        screening.updated_at = utc_now()
        session.add(screening)
        onboarding_session = session.exec(
            select(OnboardingSession).where(OnboardingSession.id == screening.session_id)
        ).first()
        if onboarding_session is not None:
            transition_session_sync(
                session,
                onboarding_session,
                "SCREENING_IN_PROGRESS",
                actor_user_id=screening.user_id,
                event_type="onboarding_screening_in_progress",
                message="Compliance screening workflow started.",
                payload={"screening_request_id": screening.id},
            )

        for job_name in SCREENING_JOB_NAMES:
            job = _get_or_create_job(session, screening_request_id=screening.id, job_name=job_name)
            job.status = "QUEUED"
            job.celery_task_id = None
            job.updated_at = utc_now()
            session.add(job)

        _log_event(
            session,
            screening_request_id=screening.id,
            session_id=screening.session_id,
            actor_user_id=screening.user_id,
            event_type="screening_workflow_started",
            message="Compliance screening workflow queued.",
            payload={"workflow_id": self.request.id},
        )
        session.commit()

    header = group(
        run_sanctions_screening.s(screening_request_id),
        run_pep_screening.s(screening_request_id),
        run_adverse_media_screening.s(screening_request_id),
        run_internal_watchlist_screening.s(screening_request_id),
        run_exit_list_screening.s(screening_request_id),
        run_ip_risk_assessment.s(screening_request_id),
    )
    callback = chain(
        calculate_risk_score.s(screening_request_id),
        finalize_screening_decision.s(screening_request_id),
    )
    chord(header)(callback)
    return {"screening_request_id": screening_request_id, "status": "SCREENING_IN_PROGRESS"}


def _run_screening_task(screening_request_id: int, job_name: str) -> dict[str, Any]:
    with Session(engine) as session:
        screening = session.exec(
            select(ScreeningRequest).where(ScreeningRequest.id == screening_request_id)
        ).first()
        if screening is None:
            return {"error": "screening_request_not_found"}
        job = _get_or_create_job(session, screening_request_id=screening_request_id, job_name=job_name)
        job.status = "STARTED"
        job.started_at = job.started_at or utc_now()
        job.updated_at = utc_now()
        session.add(job)
        _log_event(
            session,
            screening_request_id=screening.id,
            session_id=screening.session_id,
            actor_user_id=screening.user_id,
            event_type=f"{job_name}_started",
            message=f"{job_name} screening started.",
        )
        session.commit()

        try:
            subject = _load_subject(session, screening)
            payload = run_provider(job_name, subject)
            result = session.exec(
                select(ScreeningResult).where(
                    ScreeningResult.screening_request_id == screening_request_id,
                    ScreeningResult.screening_type == job_name,
                )
            ).first()
            if result is None:
                result = ScreeningResult(screening_request_id=screening_request_id, **payload)
                session.add(result)
            else:
                for key, value in payload.items():
                    setattr(result, key, value)
                result.updated_at = utc_now()
                session.add(result)

            job.status = "SUCCEEDED"
            job.completed_at = utc_now()
            job.updated_at = utc_now()
            session.add(job)
            _log_event(
                session,
                screening_request_id=screening.id,
                session_id=screening.session_id,
                actor_user_id=screening.user_id,
                event_type=f"{job_name}_completed",
                message=f"{job_name} screening completed.",
                event_status="success",
                payload={"outcome": payload["outcome"]},
            )
            session.commit()
            return payload
        except Exception as exc:
            job.status = "FAILED"
            job.retry_count += 1
            job.last_error = str(exc)
            job.updated_at = utc_now()
            session.add(job)
            screening.last_error = str(exc)
            screening.updated_at = utc_now()
            session.add(screening)
            _log_event(
                session,
                screening_request_id=screening.id,
                session_id=screening.session_id,
                actor_user_id=screening.user_id,
                event_type=f"{job_name}_failed",
                message=f"{job_name} screening failed.",
                event_status="error",
                payload={"error": str(exc)},
            )
            session.commit()
            raise


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def run_sanctions_screening(self, screening_request_id: int) -> dict[str, Any]:
    return _run_screening_task(screening_request_id, "sanctions")


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def run_pep_screening(self, screening_request_id: int) -> dict[str, Any]:
    return _run_screening_task(screening_request_id, "pep")


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def run_adverse_media_screening(self, screening_request_id: int) -> dict[str, Any]:
    return _run_screening_task(screening_request_id, "adverse_media")


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def run_internal_watchlist_screening(self, screening_request_id: int) -> dict[str, Any]:
    return _run_screening_task(screening_request_id, "internal_watchlist")


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def run_exit_list_screening(self, screening_request_id: int) -> dict[str, Any]:
    return _run_screening_task(screening_request_id, "exit_list")


@celery_app.task(bind=True, autoretry_for=(Exception,), retry_backoff=True, retry_kwargs={"max_retries": 2})
def run_ip_risk_assessment(self, screening_request_id: int) -> dict[str, Any]:
    return _run_screening_task(screening_request_id, "ip_risk")


@celery_app.task
def calculate_risk_score(results: list[dict[str, Any]], screening_request_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        screening = session.exec(
            select(ScreeningRequest).where(ScreeningRequest.id == screening_request_id)
        ).first()
        if screening is None:
            return {"error": "screening_request_not_found"}
        customer_assessment, customer_payload = calculate_and_persist_sync(
            session,
            session_id=screening.session_id,
            assessment_type="final",
            screening_request_id=screening_request_id,
            actor_user_id=screening.user_id,
        )
        risk_payload = {
            "risk_score": customer_assessment.total_score,
            "risk_category": customer_assessment.risk_category,
            "decision": customer_payload["decision"],
            "review_required": customer_payload["decision"] == "REVIEW_REQUIRED",
            "factors": [
                {
                    "rule": factor.name,
                    "severity": "high" if factor.score >= 5 else "medium" if factor.score >= 3 else "low",
                    "score": factor.score,
                    "source": factor.source,
                }
                for factor in customer_payload["factors"]
            ],
            "rules_snapshot": customer_assessment.rules_snapshot,
            "edd_required": customer_assessment.edd_required,
            "edd_reasons": customer_assessment.edd_reasons,
        }
        assessment = session.exec(
            select(RiskAssessment).where(RiskAssessment.screening_request_id == screening_request_id)
        ).first()
        if assessment is None:
            assessment = RiskAssessment(screening_request_id=screening_request_id, **risk_payload)
            session.add(assessment)
        else:
            assessment.risk_score = risk_payload["risk_score"]
            assessment.risk_category = risk_payload["risk_category"]
            assessment.factors = risk_payload["factors"]
            assessment.rules_snapshot = risk_payload["rules_snapshot"]
            assessment.updated_at = utc_now()
            session.add(assessment)

        screening.updated_at = utc_now()
        session.add(screening)
        _log_event(
            session,
            screening_request_id=screening_request_id,
            session_id=screening.session_id,
            actor_user_id=screening.user_id,
            event_type="risk_score_calculated",
            message="Risk score calculated.",
            event_status="success",
            payload=risk_payload,
        )
        session.commit()

    return risk_payload


@celery_app.task
def finalize_screening_decision(risk_payload: dict[str, Any], screening_request_id: int) -> dict[str, Any]:
    with Session(engine) as session:
        screening = session.exec(
            select(ScreeningRequest).where(ScreeningRequest.id == screening_request_id)
        ).first()
        if screening is None:
            return {"error": "screening_request_not_found"}

        decision = session.exec(
            select(ScreeningDecision).where(ScreeningDecision.screening_request_id == screening_request_id)
        ).first()
        previous_decision = decision.decision if decision else None
        if decision is None:
            decision = ScreeningDecision(
                screening_request_id=screening_request_id,
                decision=risk_payload["decision"],
                previous_decision=previous_decision,
                reason="Automated compliance decision.",
                notes="Generated by compliance risk scoring.",
            )
            session.add(decision)
        else:
            decision.previous_decision = previous_decision
            decision.decision = risk_payload["decision"]
            decision.reason = "Automated compliance decision."
            decision.notes = "Generated by compliance risk scoring."
            decision.decision_source = "system"
            decision.decided_at = utc_now()
            decision.updated_at = utc_now()
            session.add(decision)

        screening.status = risk_payload["decision"]
        screening.completed_at = utc_now()
        screening.updated_at = utc_now()
        session.add(screening)

        case = session.exec(
            select(ComplianceCase).where(ComplianceCase.screening_request_id == screening_request_id)
        ).first()
        customer_assessment = latest_assessment_sync(session, screening.session_id, "final")
        if customer_assessment is not None:
            ensure_review_case_sync(session, screening, customer_assessment)
            case = session.exec(
                select(ComplianceCase).where(ComplianceCase.screening_request_id == screening_request_id)
            ).first()

        if risk_payload["decision"] == "REVIEW_REQUIRED":
            if case is None:
                case = ComplianceCase(screening_request_id=screening_request_id)
            case.status = "OPEN"
            case.queue_name = "COMPLIANCE_REVIEW_CASE" if risk_payload.get("edd_required") else case.queue_name
            case.resolution_note = None
            case.resolved_at = None
            case.updated_at = utc_now()
            session.add(case)
        elif case is not None:
            case.status = "RESOLVED"
            case.resolution_note = f"Closed automatically with decision {risk_payload['decision']}."
            case.resolved_at = utc_now()
            case.updated_at = utc_now()
            session.add(case)

        onboarding_session = session.exec(
            select(OnboardingSession).where(OnboardingSession.id == screening.session_id)
        ).first()
        if onboarding_session is not None:
            state = resolve_session_state_sync(session, onboarding_session)
            transition_session_sync(
                session,
                onboarding_session,
                state["workflow_state"],
                actor_user_id=screening.user_id,
                event_type="screening_finalized_session_state",
                message=f"Onboarding session updated after screening decision {risk_payload['decision']}.",
                payload={"screening_request_id": screening_request_id, "decision": risk_payload["decision"]},
            )

        _log_event(
            session,
            screening_request_id=screening_request_id,
            session_id=screening.session_id,
            actor_user_id=screening.user_id,
            event_type="screening_finalized",
            message=f"Compliance decision finalized as {risk_payload['decision']}.",
            event_status="success",
            payload=risk_payload,
        )
        session.commit()

    return {
        "screening_request_id": screening_request_id,
        "decision": risk_payload["decision"],
        "risk_category": risk_payload["risk_category"],
        "risk_score": risk_payload["risk_score"],
    }
