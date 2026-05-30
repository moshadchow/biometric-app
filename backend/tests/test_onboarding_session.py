from __future__ import annotations

import asyncio
import json
import unittest
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from fastapi import FastAPI
from sqlalchemy.exc import IntegrityError

from api.onboarding import router as onboarding_router
from core.auth import get_current_user
from core.db import get_session
from crud import crud_onboarding
from model.models import OnboardingSession, User


@dataclass
class SharedOnboardingStore:
    sessions: list[OnboardingSession] = field(default_factory=list)
    next_id: int = 1
    locks: dict[int, asyncio.Lock] = field(default_factory=dict)

    def lock_for(self, user_id: int) -> asyncio.Lock:
        lock = self.locks.get(user_id)
        if lock is None:
            lock = asyncio.Lock()
            self.locks[user_id] = lock
        return lock


class FakeResult:
    def __init__(self, rows: list[Any]):
        self._rows = rows

    def first(self) -> OnboardingSession | None:
        return self._rows[0] if self._rows else None

    def one_or_none(self) -> OnboardingSession | None:
        return self.first()

    def all(self) -> list[OnboardingSession]:
        return list(self._rows)


class FakeAsyncSession:
    def __init__(self, store: SharedOnboardingStore, user_id: int):
        self.store = store
        self.user_id = user_id
        self._pending: OnboardingSession | None = None
        self.user = User(id=user_id, username="customer", password="hashed", role="customer")

    async def exec(self, statement: Any) -> FakeResult:
        sql = str(statement)
        if sql.startswith("SELECT pg_advisory_xact_lock"):
            await asyncio.sleep(0)
            return FakeResult([])

        if "FROM onboarding_session" in sql:
            rows = [
                session
                for session in self.store.sessions
                if session.user_id == self.user_id
            ]
            if "NOT IN" in sql:
                rows = [session for session in rows if session.status not in {"completed", "rejected"}]
            rows.sort(key=lambda session: (session.updated_at, session.id or 0), reverse=True)
            return FakeResult(rows[:1])

        if 'FROM "user"' in sql:
            return FakeResult([self.user])

        return FakeResult([])

    def add(self, record: OnboardingSession) -> None:
        if isinstance(record, OnboardingSession):
            self._pending = record

    async def flush(self) -> None:
        if self._pending is None:
            return

        existing = next(
            (
                session
                for session in self.store.sessions
                if session.user_id == self.user_id and session.status not in {"completed", "rejected"}
            ),
            None,
        )
        if existing is not None:
            raise IntegrityError(
                "duplicate active onboarding session",
                params={"user_id": self.user_id},
                orig=Exception("duplicate active onboarding session"),
            )

        record = self._pending
        self._pending = None
        record.id = self.store.next_id
        self.store.next_id += 1
        self.store.sessions.append(record)

    async def refresh(self, record: OnboardingSession) -> None:
        return None

    async def rollback(self) -> None:
        self._pending = None


class HttpFakeAsyncSession(FakeAsyncSession):
    def __init__(self, store: SharedOnboardingStore, user_id: int):
        super().__init__(store, user_id)
        self._lock_acquired = False

    async def exec(self, statement: Any) -> FakeResult:
        sql = str(statement)
        if sql.startswith("SELECT pg_advisory_xact_lock"):
            await self.store.lock_for(self.user_id).acquire()
            self._lock_acquired = True
            return FakeResult([])
        return await super().exec(statement)

    def release(self) -> None:
        if self._lock_acquired:
            lock = self.store.lock_for(self.user_id)
            if lock.locked():
                lock.release()
            self._lock_acquired = False


async def call_asgi_json(app: Any, method: str, path: str) -> tuple[int, dict[str, Any]]:
    response_start: dict[str, Any] = {}
    body_chunks: list[bytes] = []
    request_sent = False

    async def receive() -> dict[str, Any]:
        nonlocal request_sent
        if not request_sent:
            request_sent = True
            return {"type": "http.request", "body": b"", "more_body": False}
        return {"type": "http.disconnect"}

    async def send(message: dict[str, Any]) -> None:
        if message["type"] == "http.response.start":
            response_start.update(message)
        elif message["type"] == "http.response.body":
            body_chunks.append(message.get("body", b""))

    scope = {
        "type": "http",
        "asgi": {"version": "3.0", "spec_version": "2.3"},
        "http_version": "1.1",
        "method": method,
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("utf-8"),
        "query_string": b"",
        "headers": [],
        "client": ("testclient", 50000),
        "server": ("testserver", 80),
    }

    await app(scope, receive, send)
    payload = json.loads(b"".join(body_chunks).decode("utf-8"))
    return response_start["status"], payload


class OnboardingSessionConcurrencyTest(unittest.IsolatedAsyncioTestCase):
    async def test_concurrent_ensure_returns_same_session_for_same_user(self) -> None:
        store = SharedOnboardingStore()
        session_a = FakeAsyncSession(store, user_id=1)
        session_b = FakeAsyncSession(store, user_id=1)

        result_a, result_b = await asyncio.gather(
            crud_onboarding.get_or_create_active_session(user_id=1, session=session_a),
            crud_onboarding.get_or_create_active_session(user_id=1, session=session_b),
        )

        self.assertIsNotNone(result_a.id)
        self.assertEqual(result_a.id, result_b.id)
        self.assertEqual(len(store.sessions), 1)
        self.assertEqual(store.sessions[0].user_id, 1)
        self.assertEqual(store.sessions[0].status, "in_progress")
        self.assertIsInstance(store.sessions[0].started_at, datetime)
        self.assertIsNone(store.sessions[0].started_at.tzinfo)

    async def test_completed_customer_without_admin_approval_is_blocked(self) -> None:
        store = SharedOnboardingStore(
            sessions=[
                OnboardingSession(
                    id=1,
                    user_id=1,
                    status="completed",
                    current_step="complete",
                    workflow_state="ONBOARDING_COMPLETED",
                    completed_steps=["face_verification", "ocr_extraction", "identity_form", "signature_capture", "screening"],
                )
            ],
            next_id=2,
        )
        session = FakeAsyncSession(store, user_id=1)

        with self.assertRaises(PermissionError):
            await crud_onboarding.get_or_create_active_session(user_id=1, session=session)

        self.assertEqual(len(store.sessions), 1)

    async def test_completed_customer_with_admin_approval_gets_new_session_once(self) -> None:
        store = SharedOnboardingStore(
            sessions=[
                OnboardingSession(
                    id=1,
                    user_id=1,
                    status="completed",
                    current_step="complete",
                    workflow_state="ONBOARDING_COMPLETED",
                    completed_steps=["face_verification", "ocr_extraction", "identity_form", "signature_capture", "screening"],
                )
            ],
            next_id=2,
        )
        session = FakeAsyncSession(store, user_id=1)
        session.user.re_onboarding_allowed = True
        session.user.re_onboarding_reason = "Admin approved retest."

        result = await crud_onboarding.get_or_create_active_session(user_id=1, session=session)

        self.assertEqual(result.id, 2)
        self.assertEqual(len(store.sessions), 2)
        self.assertFalse(session.user.re_onboarding_allowed)


class OnboardingSessionEndpointTest(unittest.IsolatedAsyncioTestCase):
    def setUp(self) -> None:
        self.store = SharedOnboardingStore()
        self.app = FastAPI()
        self.app.include_router(onboarding_router, prefix="/api/v1/onboarding")

        async def override_get_current_user() -> User:
            return User(id=1, username="customer", password="hashed", role="customer")

        async def override_get_session():
            session = HttpFakeAsyncSession(self.store, user_id=1)
            try:
                yield session
            finally:
                session.release()

        self.app.dependency_overrides[get_current_user] = override_get_current_user
        self.app.dependency_overrides[get_session] = override_get_session

    def tearDown(self) -> None:
        self.app.dependency_overrides.clear()

    async def test_concurrent_ensure_endpoint_returns_same_session(self) -> None:
        response_a, response_b = await asyncio.gather(
            call_asgi_json(self.app, "POST", "/api/v1/onboarding/sessions/ensure"),
            call_asgi_json(self.app, "POST", "/api/v1/onboarding/sessions/ensure"),
        )

        status_a, payload_a = response_a
        status_b, payload_b = response_b
        self.assertEqual(status_a, 200)
        self.assertEqual(status_b, 200)

        session_a = payload_a["session"]
        session_b = payload_b["session"]
        self.assertEqual(session_a["id"], session_b["id"])
        self.assertEqual(len(self.store.sessions), 1)
        self.assertEqual(self.store.sessions[0].user_id, 1)
        self.assertEqual(self.store.sessions[0].status, "in_progress")


if __name__ == "__main__":
    unittest.main()
