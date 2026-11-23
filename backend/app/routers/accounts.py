from argon2.exceptions import VerificationError
from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.core.db import DB
from app.core.security import Officer, passwords, token_for
from app.middleware.audit import record
from app.models import AuthSession, User
from app.schemas import LoginView, OfficerCreate, OfficerUpdate, OfficerView, PasswordChange

router = APIRouter()


@router.post("/auth/logout", status_code=204)
def logout(user: Officer, db: DB, request: Request):
    db.get(AuthSession, request.state.session_id).revoked = True
    record(request, db, "session.logout", "user", user.id)


@router.post("/auth/password", response_model=LoginView)
def change_password(values: PasswordChange, user: Officer, db: DB, request: Request):
    try:
        passwords.verify(user.password_hash, values.current_password)
    except VerificationError:
        raise HTTPException(403, "Current password is incorrect") from None
    if values.current_password == values.new_password:
        raise HTTPException(422, "Choose a different password")
    user.password_hash = passwords.hash(values.new_password)
    user.session_version += 1
    user.must_change_password = False
    token = token_for(request, user, db)
    record(request, db, "account.password_changed", "user", user.id)
    return LoginView(access_token=token, officer=OfficerView.model_validate(user))


def administrator(user: User) -> None:
    if not user.is_admin:
        raise HTTPException(403, "Account administration permission is required")


@router.get("/officers", response_model=list[OfficerView])
def list_officers(user: Officer, db: DB):
    administrator(user)
    return db.scalars(select(User).where(User.station == user.station).order_by(User.id)).all()


@router.post("/officers", response_model=OfficerView, status_code=201)
def create_officer(values: OfficerCreate, user: Officer, db: DB, request: Request):
    administrator(user)
    if request.app.state.settings.environment == "production" and values.username.lower().startswith("demo."):
        raise HTTPException(422, "Demo account names are reserved for the training installation")
    officer = User(username=values.username.lower(), name=values.name, role=values.role,
        station=user.station, password_hash=passwords.hash(values.temporary_password), must_change_password=True)
    db.add(officer)
    db.flush()
    record(request, db, "account.created", "user", officer.id, role=officer.role.value)
    return officer


@router.patch("/officers/{officer_id}", response_model=OfficerView)
def update_officer(officer_id: int, values: OfficerUpdate, user: Officer, db: DB, request: Request):
    administrator(user)
    officer = db.scalar(select(User).where(User.id == officer_id, User.station == user.station).with_for_update())
    if not officer:
        raise HTTPException(404, "Officer not found")
    if officer.is_admin:
        raise HTTPException(403, "Administrator changes require the installation operator")
    for name in ("is_active", "role"):
        value = getattr(values, name)
        if value is not None:
            setattr(officer, name, value)
    if values.temporary_password:
        officer.password_hash = passwords.hash(values.temporary_password)
        officer.must_change_password = True
    officer.session_version += 1
    record(request, db, "account.updated", "user", officer.id, active=officer.is_active, role=officer.role.value)
    return officer
