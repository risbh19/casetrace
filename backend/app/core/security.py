from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select

from app.core.db import DB
from app.models import Case, Role, User

ISSUER = "investigation-copilot"
passwords = PasswordHasher(memory_cost=19_456, time_cost=2, parallelism=1)
dummy_hash = passwords.hash("invalid-login")
bearer = HTTPBearer(auto_error=False)


def authenticate(db: DB, username: str, password: str) -> User:
    user = db.scalar(select(User).where(User.username == username.lower()))
    try:
        passwords.verify(user.password_hash if user else dummy_hash, password)
    except VerificationError:
        raise unauthorized("Invalid username or password") from None
    if not user:
        raise unauthorized("Invalid username or password")
    return user


def token_for(request: Request, user: User) -> str:
    options = request.app.state.settings
    issued = datetime.now(UTC)
    return jwt.encode(
        {
            "sub": str(user.id),
            "iat": issued,
            "exp": issued + timedelta(minutes=options.token_minutes),
            "iss": ISSUER,
            "aud": ISSUER,
        },
        options.jwt_secret,
        algorithm="HS256",
    )


def unauthorized(detail: str) -> HTTPException:
    return HTTPException(status_code=401, detail=detail, headers={"WWW-Authenticate": "Bearer"})


def current_user(
    request: Request,
    db: DB,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> User:
    if credentials is None:
        raise unauthorized("Sign in first")
    try:
        claims = jwt.decode(
            credentials.credentials,
            request.app.state.settings.jwt_secret,
            algorithms=["HS256"],
            audience=ISSUER,
            issuer=ISSUER,
            options={"require": ["exp", "iat", "sub"]},
        )
        user = db.get(User, int(claims["sub"]))
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized("Session expired or invalid") from None
    if not user:
        raise unauthorized("Session expired or invalid")
    request.state.actor_id = user.id
    return user


Officer = Annotated[User, Depends(current_user)]


def require_roles(user: User, *roles: Role) -> None:
    if user.role not in roles:
        raise HTTPException(403, "This action requires a different officer role")


def case_filter(user: User):
    if user.role == Role.IO:
        return (Case.station == user.station) & (Case.assigned_to == user.id)
    return Case.station == user.station


def access_case(case_id: int, request: Request, db: DB, user: Officer) -> Case:
    case = db.scalar(select(Case).where(Case.id == case_id, case_filter(user)))
    if not case:
        raise HTTPException(404, "Case not found")
    request.state.case_id = case.id
    return case


CaseAccess = Annotated[Case, Depends(access_case)]


def lock_case(db: DB, case: Case) -> None:
    db.execute(select(Case.id).where(Case.id == case.id).with_for_update())
