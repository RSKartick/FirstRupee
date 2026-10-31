from __future__ import annotations

from datetime import timedelta
from typing import Any

from fastapi import APIRouter, Depends, Response
from sqlalchemy.orm import Session

from app.api.deps import SESSION_COOKIE, csrf_protected, current_session, database, optional_session, reference_date
from app.core.clock import utcnow
from app.core.config import get_settings
from app.core.errors import AuthError, ConflictError, NotFoundError
from app.core.security import hash_password, new_token, token_digest, verify_password
from app.data_sources.demo_catalog import DEMO_PROFILES
from app.models.tables import AuthSession, User
from app.repositories import owned as repo
from app.schemas.auth import LoginIn, RegisterIn
from app.services import workflow

router = APIRouter(prefix="/auth", tags=["auth"])


def _user_out(user: User) -> dict[str, Any]:
    return {"id": user.id, "email": user.email, "display_name": user.display_name, "is_guest": user.is_guest}


def _start_session(db: Session, response: Response, user: User) -> str:
    settings = get_settings()
    raw = new_token()
    csrf = new_token()
    ttl = timedelta(hours=settings.session_ttl_hours)
    db.add(AuthSession(user_id=user.id, token_digest=token_digest(raw), csrf_token=csrf, expires_at=utcnow() + ttl))
    db.commit()
    response.set_cookie(
        SESSION_COOKIE,
        raw,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
        max_age=int(ttl.total_seconds()),
        path="/",
    )
    return csrf


@router.post("/register", status_code=201)
def register(body: RegisterIn, response: Response, db: Session = Depends(database)) -> dict[str, Any]:
    if repo.get_user_by_email(db, body.email) is not None:
        raise ConflictError("An account with this email already exists.")
    user = User(email=body.email, display_name=body.display_name, password_hash=hash_password(body.password))
    db.add(user)
    db.commit()
    return {"user": _user_out(user), "csrf_token": _start_session(db, response, user)}


@router.post("/login")
def login(body: LoginIn, response: Response, db: Session = Depends(database)) -> dict[str, Any]:
    user = repo.get_user_by_email(db, body.email)
    if user is None or not verify_password(user.password_hash, body.password):
        raise AuthError("Invalid email or password.")
    return {"user": _user_out(user), "csrf_token": _start_session(db, response, user)}


@router.post("/logout", dependencies=[Depends(csrf_protected)])
def logout(response: Response, session: AuthSession = Depends(current_session), db: Session = Depends(database)) -> dict[str, bool]:
    db.delete(session)
    db.commit()
    response.delete_cookie(SESSION_COOKIE, path="/")
    return {"logged_out": True}


@router.get("/me")
def me(session: AuthSession | None = Depends(optional_session), db: Session = Depends(database)) -> dict[str, Any]:
    if session is None:
        return {"user": None, "csrf_token": None}
    user = db.get(User, session.user_id)
    if user is None:
        return {"user": None, "csrf_token": None}
    return {"user": _user_out(user), "csrf_token": session.csrf_token}


@router.post("/demo/{key}", status_code=201)
def demo(key: str, response: Response, db: Session = Depends(database), as_of=Depends(reference_date)) -> dict[str, Any]:
    """Creates a PRIVATE guest workspace containing a copy of a fictional demo investor. Visitors never share edits."""
    if key not in DEMO_PROFILES:
        raise NotFoundError("Demo investor not found.")
    guest = User(email=None, display_name=f"Guest · {DEMO_PROFILES[key]['display_name']}", is_guest=True, password_hash=None)
    db.add(guest)
    db.commit()
    profile = workflow.clone_demo_profile(db, guest, key, as_of)
    workflow.readiness_for(db, profile, as_of)
    return {"user": _user_out(guest), "csrf_token": _start_session(db, response, guest), "profile_id": profile.id}
