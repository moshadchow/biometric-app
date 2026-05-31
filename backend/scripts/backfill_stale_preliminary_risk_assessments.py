from __future__ import annotations

import argparse
from pathlib import Path
import sys

from sqlalchemy import create_engine
from sqlmodel import Session, select

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from core.config import settings
from core.risk_assessment import utc_now
from core.risk_assessment import refresh_preliminary_assessment_sync, stale_preliminary_assessment_session_ids_sync
from core.onboarding_state import resolve_session_state_sync, transition_session_sync
from crud.crud_onboarding import form_type_for_risk
from model.models import CustomerIdentityProfile, CustomerRiskAssessment, OnboardingSession, ScreeningJob, ScreeningRequest, ScreeningResult


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Backfill stale preliminary risk assessments.")
    parser.add_argument(
        "--session-id",
        type=int,
        default=None,
        help="Restrict the backfill to a single onboarding session.",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="List stale sessions without recalculating or writing anything.",
    )
    return parser.parse_args()


def _candidate_session_ids(session: Session, session_id: int | None) -> list[int]:
    stale_ids = set(stale_preliminary_assessment_session_ids_sync(session))
    profile_ids = set(_profile_mismatch_session_ids(session, session_id))
    merged = sorted(stale_ids | profile_ids)
    if session_id is None:
        return merged
    return [session_id] if session_id in merged else []


def _profile_mismatch_session_ids(session: Session, session_id: int | None) -> list[int]:
    query = select(CustomerIdentityProfile).where(CustomerIdentityProfile.submitted_at.is_not(None))
    if session_id is not None:
        query = query.where(CustomerIdentityProfile.session_id == session_id)
    mismatches: list[int] = []
    for profile in session.exec(query).all():
        assessment = session.exec(
            select(CustomerRiskAssessment)
            .where(CustomerRiskAssessment.session_id == profile.session_id)
            .order_by(CustomerRiskAssessment.calculated_at.desc(), CustomerRiskAssessment.id.desc())
        ).first()
        if assessment is None:
            continue
        expected_form_type = form_type_for_risk(assessment.risk_category)
        if profile.risk_category != assessment.risk_category or profile.form_type != expected_form_type:
            mismatches.append(int(profile.session_id))
    return mismatches


def _sync_profile_risk_state(session: Session, *, session_id: int, risk_category: str) -> bool:
    profile = session.exec(
        select(CustomerIdentityProfile).where(CustomerIdentityProfile.session_id == session_id)
    ).first()
    if profile is None:
        return False
    expected_form_type = form_type_for_risk(risk_category)
    changed = profile.risk_category != risk_category or profile.form_type != expected_form_type
    if changed:
        profile.risk_category = risk_category
        profile.form_type = expected_form_type
        profile.updated_at = utc_now()
        session.add(profile)
    return changed


def _repair_stuck_screening_requests(session: Session, *, session_id: int | None, apply_changes: bool) -> int:
    query = select(ScreeningRequest).where(ScreeningRequest.status == "SCREENING_PENDING").where(ScreeningRequest.workflow_id.is_(None))
    if session_id is not None:
        query = query.where(ScreeningRequest.session_id == session_id)
    repaired = 0
    for screening in session.exec(query).all():
        has_jobs = session.exec(
            select(ScreeningJob).where(ScreeningJob.screening_request_id == screening.id)
        ).first() is not None
        has_results = session.exec(
            select(ScreeningResult).where(ScreeningResult.screening_request_id == screening.id)
        ).first() is not None
        if has_jobs or has_results:
            continue
        if apply_changes:
            screening.status = "SCREENING_FAILED"
            screening.last_error = "Screening workflow was never started."
            screening.updated_at = utc_now()
            session.add(screening)
            session_row = session.exec(select(OnboardingSession).where(OnboardingSession.id == screening.session_id)).first()
            if session_row is not None:
                state = resolve_session_state_sync(session, session_row)
                transition_session_sync(
                    session,
                    session_row,
                    state["workflow_state"],
                    actor_user_id=None,
                    event_type="screening_enqueue_failed_backfill",
                    message="Stuck screening request was marked as failed.",
                    payload={"screening_request_id": screening.id},
                )
        repaired += 1
    return repaired


def main() -> None:
    args = _parse_args()
    engine = create_engine(settings.DATABASE_SYNC_URL)

    with Session(engine) as session:
        candidate_ids = _candidate_session_ids(session, args.session_id)
        screening_repairs = _repair_stuck_screening_requests(
            session,
            session_id=args.session_id,
            apply_changes=not args.dry_run,
        )
        if args.dry_run:
            print(f"stale_preliminary_sessions={candidate_ids}")
            print(f"stuck_screening_repairs={screening_repairs}")
            return

        refreshed = 0
        profile_repairs = 0
        for session_id in candidate_ids:
            assessment, _ = refresh_preliminary_assessment_sync(
                session,
                session_id=session_id,
                actor_user_id=None,
            )
            if _sync_profile_risk_state(session, session_id=session_id, risk_category=assessment.risk_category):
                profile_repairs += 1
            session.commit()
            refreshed += 1
            print(
                f"refreshed session_id={session_id} assessment_id={assessment.id} "
                f"score={assessment.total_score} category={assessment.risk_category}"
            )

        if screening_repairs:
            session.commit()

        print(
            "Backfill complete: "
            f"candidates={len(candidate_ids)} refreshed={refreshed} "
            f"profile_repairs={profile_repairs} screening_repairs={screening_repairs} dry_run={args.dry_run}"
        )


if __name__ == "__main__":
    main()
