from datetime import UTC, datetime, timedelta
from hashlib import sha256
from secrets import token_urlsafe
from typing import Annotated

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError
from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.core.db import DB
from app.models import AuthSession, Case, LoginBucket, Role, User

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
    if not user or not user.is_active:
        raise unauthorized("Invalid username or password")
    return user


def token_for(request: Request, user: User, db: DB) -> str:
    options = request.app.state.settings
    issued = datetime.now(UTC)
    expires = issued + timedelta(minutes=options.token_minutes)
    identifier = token_urlsafe(32)
    db.execute(delete(AuthSession).where(AuthSession.expires_at < issued))
    db.add(AuthSession(id=identifier, user_id=user.id, expires_at=expires))
    return jwt.encode(
        {
            "sub": str(user.id),
            "iat": issued,
            "exp": expires,
            "jti": identifier,
            "ver": user.session_version,
            "iss": ISSUER,
            "aud": ISSUER,
        },
        options.jwt_secret,
        algorithm="HS256",
    )


def verify_operational_store(engine) -> None:
    with Session(engine) as db:
        if db.scalar(select(User.id).where(User.username.startswith("demo.")).limit(1)) or db.scalar(
            select(Case.id).where(Case.reference.startswith("DEMO-FIR-")).limit(1)
        ):
            raise RuntimeError("Production cannot use a seeded training database. Provision a separate operational installation.")


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
            options={"require": ["exp", "iat", "sub", "jti", "ver"]},
        )
        user = db.get(User, int(claims["sub"]))
        active = db.get(AuthSession, claims["jti"])
    except (jwt.InvalidTokenError, ValueError):
        raise unauthorized("Session expired or invalid") from None
    if not user or not user.is_active or not active or active.revoked or active.user_id != user.id or claims["ver"] != user.session_version:
        raise unauthorized("Session expired or invalid")
    request.state.actor_id = user.id
    request.state.session_id = active.id
    if user.must_change_password and request.url.path not in {"/api/auth/me", "/api/auth/password", "/api/auth/logout"}:
        raise HTTPException(403, "Change your temporary password before opening case records")
    return user


def throttle_login(request: Request, db: DB, username: str) -> None:
    from time import time

    from sqlalchemy.dialects.postgresql import insert as pg_insert
    from sqlalchemy.dialects.sqlite import insert as sqlite_insert

    window = int(time()) // 900
    db.execute(delete(LoginBucket).where(LoginBucket.window < window - 1))
    insert = pg_insert if db.bind.dialect.name == "postgresql" else sqlite_insert
    exceeded = False
    for value, maximum in (("user:" + username.lower(), 10), ("ip:" + (request.client.host if request.client else "unknown"), 200)):
        key = sha256(value.encode()).hexdigest()
        count = db.scalar(insert(LoginBucket).values(key=key, window=window, attempts=1)
            .on_conflict_do_update(index_elements=["key", "window"], set_={"attempts": LoginBucket.attempts + 1})
            .returning(LoginBucket.attempts))
        exceeded = exceeded or count > maximum
    db.commit()
    if exceeded:
        raise HTTPException(429, "Too many sign-in attempts. Try again after 15 minutes.", headers={"Retry-After": "900"})


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
