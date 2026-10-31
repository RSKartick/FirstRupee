"""Domain exceptions. Messages are written for the end user and never contain stack traces, SQL, keys or provider payloads."""

from __future__ import annotations


class DomainError(Exception):
    status_code = 422

    def __init__(self, message: str, details: list[str] | None = None) -> None:
        super().__init__(message)
        self.message = message
        self.details = details or []


class ValidationProblem(DomainError):
    status_code = 422


class NotFoundError(DomainError):
    """Used for records that do not exist *or* belong to another user (non-disclosing)."""

    status_code = 404

    def __init__(self, message: str = "Record not found.") -> None:
        super().__init__(message)


class ConflictError(DomainError):
    status_code = 409


class AuthError(DomainError):
    """Deliberately generic messages (e.g. invalid email or password) to avoid account enumeration."""

    status_code = 401
