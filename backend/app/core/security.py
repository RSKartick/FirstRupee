"""Password hashing (Argon2id via argon2-cffi), opaque session tokens and CSRF comparison helpers.

Session tokens are random, opaque and stored only as SHA-256 digests, so a database leak does not expose live sessions.
"""

from __future__ import annotations

import hashlib
import hmac
import logging
import secrets

from argon2 import PasswordHasher
from argon2.exceptions import Argon2Error, InvalidHashError

logger = logging.getLogger("firstrupee.security")
# argon2-cffi's default parameters use the Argon2id variant.
_hasher = PasswordHasher()


def hash_password(password: str) -> str:
    return _hasher.hash(password)


def verify_password(password_hash: str | None, password: str) -> bool:
    if not password_hash:
        return False
    try:
        return _hasher.verify(password_hash, password)
    except InvalidHashError:
        logger.warning("Stored password hash is malformed or uses an unsupported format.")
        return False
    except (Argon2Error, ValueError):
        return False


def new_token() -> str:
    return secrets.token_urlsafe(32)


def token_digest(token: str) -> str:
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def tokens_equal(a: str, b: str) -> bool:
    return hmac.compare_digest(a.encode("utf-8"), b.encode("utf-8"))
