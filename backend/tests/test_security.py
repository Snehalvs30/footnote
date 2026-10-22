"""Tests for app/security.py: password hashing and session tokens.

Pure functions: no database or server needed.
"""

import uuid
from datetime import UTC, datetime, timedelta

import jwt

from app.config import settings
from app.security import (
    create_session_token,
    hash_password,
    read_session_token,
    verify_password,
)


def test_hash_is_not_the_password_and_verifies():
    password_hash = hash_password("correct horse battery")

    assert password_hash != "correct horse battery"
    assert verify_password("correct horse battery", password_hash)


def test_wrong_password_is_rejected():
    password_hash = hash_password("correct horse battery")

    assert not verify_password("wrong password", password_hash)


def test_same_password_gives_different_hashes():
    # Each hash includes a random salt, so identical passwords don't look identical
    # in the database, and precomputed "rainbow tables" are useless.
    assert hash_password("same password") != hash_password("same password")


def test_token_round_trip_returns_the_user_id():
    user_id = uuid.uuid4()

    assert read_session_token(create_session_token(user_id)) == user_id


def test_tampered_token_is_rejected():
    token = create_session_token(uuid.uuid4())
    tampered = token[:-5] + ("xxxxx" if not token.endswith("xxxxx") else "yyyyy")

    assert read_session_token(tampered) is None


def test_token_signed_with_another_key_is_rejected():
    # A forged token: right shape and claims, wrong signing key.
    now = datetime.now(UTC)
    forged = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": now, "exp": now + timedelta(hours=1)},
        "an-attackers-secret-key-that-is-long-enough",
        algorithm="HS256",
    )

    assert read_session_token(forged) is None


def test_expired_token_is_rejected():
    issued = datetime.now(UTC) - timedelta(hours=2)
    expired = jwt.encode(
        {"sub": str(uuid.uuid4()), "iat": issued, "exp": issued + timedelta(hours=1)},
        settings.jwt_secret.get_secret_value(),
        algorithm="HS256",
    )

    assert read_session_token(expired) is None