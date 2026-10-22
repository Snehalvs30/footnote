"""Sign up, sign in, sign out, and "who am I?"."""

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.db import get_session
from app.models import User
from app.schemas import Credentials, UserOut
from app.security import (
    clear_session_cookie,
    get_current_user,
    hash_password,
    set_session_cookie,
    verify_password,
)

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", status_code=status.HTTP_201_CREATED)
def register(credentials: Credentials, response: Response, session: Session = Depends(get_session)) -> UserOut:
    """Creates an account and signs it in."""
    email = credentials.email.lower()
    if session.scalar(select(User).where(User.email == email)) is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "An account with this email already exists")

    user = User(email=email, password_hash=hash_password(credentials.password))
    session.add(user)
    session.commit()

    set_session_cookie(response, user.id)
    return UserOut(id=user.id, email=user.email)


@router.post("/login")
def login(credentials: Credentials, response: Response, session: Session = Depends(get_session)) -> UserOut:
    user = session.scalar(select(User).where(User.email == credentials.email.lower()))
    # One message for "no such email" and "wrong password", so attackers can't
    # use this endpoint to discover who has an account.
    if not verify_password(credentials.password, user.password_hash if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")

    set_session_cookie(response, user.id)
    return UserOut(id=user.id, email=user.email)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
def logout(response: Response) -> None:
    clear_session_cookie(response)


@router.get("/me")
def me(user: User = Depends(get_current_user)) -> UserOut:
    """The signed-in user, or 401. The frontend calls this on load to know if you're signed in."""
    return UserOut(id=user.id, email=user.email)