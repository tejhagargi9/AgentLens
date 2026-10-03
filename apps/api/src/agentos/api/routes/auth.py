import uuid

from fastapi import APIRouter, HTTPException, Response, status
from pydantic import BaseModel, EmailStr, Field, field_validator
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError

from agentos.api.deps import CurrentUser, SessionDep
from agentos.core.config import get_settings
from agentos.core.security import (
    SESSION_COOKIE,
    create_session_token,
    hash_password,
    password_problems,
    verify_password,
)
from agentos.db.models import User

router = APIRouter()


class LoginRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=1, max_length=128)

    @field_validator("email")
    @classmethod
    def _normalise_email(cls, value: str) -> str:
        return value.strip().lower()


class SignupRequest(LoginRequest):
    @field_validator("password")
    @classmethod
    def _check_password_rules(cls, value: str) -> str:
        if problems := password_problems(value):
            raise ValueError("Password must contain " + ", ".join(problems))
        return value


class UserResponse(BaseModel):
    id: uuid.UUID
    email: str


def _start_session(response: Response, user: User) -> UserResponse:
    settings = get_settings()
    response.set_cookie(
        SESSION_COOKIE,
        create_session_token(user.id),
        max_age=settings.session_ttl_hours * 3600,
        httponly=True,
        samesite="lax",
        secure=settings.environment != "development",
    )
    return UserResponse(id=user.id, email=user.email)


@router.post("/signup", status_code=status.HTTP_201_CREATED)
async def signup(body: SignupRequest, response: Response, session: SessionDep) -> UserResponse:
    user = User(email=body.email, password_hash=hash_password(body.password))
    session.add(user)
    try:
        await session.commit()
    except IntegrityError:
        # The unique constraint is the source of truth, so concurrent signups can't both win.
        raise HTTPException(
            status.HTTP_409_CONFLICT, "An account with this email already exists"
        ) from None
    return _start_session(response, user)


@router.post("/login")
async def login(body: LoginRequest, response: Response, session: SessionDep) -> UserResponse:
    user = await session.scalar(select(User).where(User.email == body.email))
    if not verify_password(body.password, user.password_hash if user else None):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return _start_session(response, user)


@router.post("/logout", status_code=status.HTTP_204_NO_CONTENT)
async def logout(response: Response) -> None:
    response.delete_cookie(SESSION_COOKIE)


@router.get("/me")
async def me(user: CurrentUser) -> UserResponse:
    return UserResponse(id=user.id, email=user.email)
