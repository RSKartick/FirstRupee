"""Request dependencies: database session, reference date, session authentication and CSRF protection."""

from __future__ import annotations

from collections.abc import Iterator
from datetime import date

from fastapi import Depends, HTTPException, Request
from sqlalchemy.orm import Session

from app.core.clock import utc_today, utcnow
from app.core.security import token_digest, tokens_equal
from app.db.session import get_db
from app.models.tables import AuthSession, User
from app.repositories import owned as repo

SESSION_COOKIE = "fr_session"
CSRF_HEADER = "x-csrf-token"


def database() -> Iterator[Session]:
    yield from get_db()


def reference_date() -> date:
    """The single source of "today". Tests override this dependency to pin the reference date."""
    return utc_today()


def optional_session(request: Request, db: Session = Depends(database)) -> AuthSession | None:
    raw = request.cookies.get(SESSION_COOKIE)
    if not raw:
        return None
    row = repo.get_session_by_digest(db, token_digest(raw))
    if row is None or row.expires_at <= utcnow():
        return None
    return row


def current_session(session: AuthSession | None = Depends(optional_session)) -> AuthSession:
    if session is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return session


def current_user(session: AuthSession = Depends(current_session), db: Session = Depends(database)) -> User:
    user = db.get(User, session.user_id)
    if user is None:
        raise HTTPException(status_code=401, detail="Authentication required.")
    return user


def csrf_protected(request: Request, session: AuthSession = Depends(current_session)) -> None:
    """Synchronizer token: the value issued with the session must be echoed in a header on every state-changing request."""
    token = request.headers.get(CSRF_HEADER, "")
    if not token or not tokens_equal(token, session.csrf_token):
        raise HTTPException(status_code=403, detail="Invalid or missing CSRF token.")
