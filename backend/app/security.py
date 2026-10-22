"""Passwords, session tokens, and "who is calling?".

How a session works:
  1. Sign up / sign in: the API checks the password and sets a cookie holding a
     signed token (a JWT) that says "this is user X, valid for 12 hours".
  2. The browser sends that cookie with every request automatically.
  3. get_current_user() checks the token's signature and expiry, and loads the user.

The cookie is HttpOnly: JavaScript can't read it, so a malicious script injected
into the page (XSS) can't steal the session. SameSite=Lax stops other websites
from making requests that carry the cookie (CSRF).
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt
from fastapi import Cookie, Depends, HTTPException, Response, status
from pwdlib import PasswordHash
from sqlalchemy.orm import Session

from app.config import settings
from app.db import get_session
from app.models import User

SESSION_COOKIE = "footnote_session"
_ALGORITHM = "HS256"

# Argon2: a deliberately slow, memory-hungry hash, so stolen hashes can't be
# cracked by trying billions of guesses per second.
_password_hash = PasswordHash.recommended()

# Used to spend the same time checking a password when the email doesn't exist,
# so response times don't reveal which emails have accounts.
_DUMMY_HASH = _password_hash.hash("not-a-real-password")


def hash_password(password: str) -> str:
    return _password_hash.hash(password)


def verify_password(password: str, password_hash: str | None) -> bool:
    if password_hash is None:
        _password_hash.verify(password, _DUMMY_HASH)
        return False
    return _password_hash.verify(password, password_hash)


def create_session_token(user_id: uuid.UUID) -> str:
    now = datetime.now(UTC)
    claims = {"sub": str(user_id), "iat": now, "exp": now + timedelta(hours=settings.session_hours)}
    return jwt.encode(claims, settings.jwt_secret.get_secret_value(), algorithm=_ALGORITHM)


def read_session_token(token: str) -> uuid.UUID | None:
    """The user id inside a valid token, or None if it's forged, expired or malformed."""
    try:
        claims = jwt.decode(
            token,
            settings.jwt_secret.get_secret_value(),
            algorithms=[_ALGORITHM],  # never let the token choose its own algorithm
            options={"require": ["sub", "exp"]},
        )
        return uuid.UUID(claims["sub"])
    except (jwt.InvalidTokenError, ValueError):
        return None


def set_session_cookie(response: Response, user_id: uuid.UUID) -> None:
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user_id),
        max_age=settings.session_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.cookie_secure,
    )


def clear_session_cookie(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE, httponly=True, samesite="lax", secure=settings.cookie_secure)


def get_current_user(
    session: Session = Depends(get_session),
    token: str | None = Cookie(default=None, alias=SESSION_COOKIE),
) -> User:
    """FastAPI dependency: the signed-in user, or 401. Add it to any endpoint to protect it."""
    user_id = read_session_token(token) if token else None
    user = session.get(User, user_id) if user_id else None
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Sign in to continue")
    return user