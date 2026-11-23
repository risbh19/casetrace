from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.core.db import DB
from app.core.security import (
    CaseAccess,
    Officer,
    authenticate,
    case_filter,
    lock_case,
    require_roles,
    throttle_login,
    token_for,
)
from app.middleware.audit import record
from app.models import AuditLog, Case, Role, User
from app.schemas import AuditView, CaseAssignment, CaseCreate, CaseView, Login, LoginView, OfficerView

router = APIRouter()


@router.post("/auth/login", response_model=LoginView)
def login(values: Login, db: DB, request: Request):
    throttle_login(request, db, values.username)
    user = authenticate(db, values.username, values.password)
    request.state.actor_id = user.id
    token = token_for(request, user, db)
    record(request, db, "session.login", "user", user.id)
    return LoginView(access_token=token, officer=OfficerView.model_validate(user))


@router.get("/auth/me", response_model=OfficerView)
def me(user: Officer):
    return user


@router.get("/cases", response_model=list[CaseView])
def list_cases(db: DB, user: Officer):
    return db.scalars(select(Case).where(case_filter(user)).order_by(Case.opened_on.desc(), Case.id.desc())).all()


@router.post("/cases", response_model=CaseView, status_code=201)
def create_case(values: CaseCreate, db: DB, user: Officer, request: Request):
    require_roles(user, Role.IO, Role.SHO)
    case = Case(**values.model_dump(), station=user.station, assigned_to=user.id)
    db.add(case)
    db.flush()
    request.state.case_id = case.id
    record(request, db, "case.created", "case", case.id)
    return case


@router.get("/cases/{case_id}", response_model=CaseView)
def case_detail(case: CaseAccess):
    return case


@router.get("/case-officers", response_model=list[OfficerView])
def case_officers(user: Officer, db: DB):
    require_roles(user, Role.SHO, Role.CO, Role.SP)
    return db.scalars(select(User).where(User.station == user.station, User.role == Role.IO, User.is_active.is_(True))).all()


@router.patch("/cases/{case_id}/assignment", response_model=CaseView)
def assign_case(values: CaseAssignment, case: CaseAccess, db: DB, user: Officer, request: Request):
    require_roles(user, Role.SHO, Role.CO, Role.SP)
    officer = db.scalar(select(User).where(User.id == values.officer_id, User.station == case.station,
        User.role == Role.IO, User.is_active.is_(True)).with_for_update())
    if not officer:
        raise HTTPException(422, "Choose an active investigating officer from this station")
    lock_case(db, case)
    db.refresh(case)
    previous = case.assigned_to
    case.assigned_to = officer.id
    record(request, db, "case.reassigned", "case", case.id, previous_officer_id=previous, officer_id=officer.id)
    return case


@router.get("/cases/{case_id}/audit", response_model=list[AuditView])
def case_audit(case: CaseAccess, db: DB, user: Officer):
    require_roles(user, Role.SHO, Role.CO, Role.SP)
    return db.scalars(
        select(AuditLog).where(AuditLog.case_id == case.id).order_by(AuditLog.id.desc()).limit(250)
    ).all()


@router.get("/audit", response_model=list[AuditView])
def station_audit(db: DB, user: Officer):
    require_roles(user, Role.SHO, Role.CO, Role.SP)
    return db.scalars(
        select(AuditLog)
        .join(Case, AuditLog.case_id == Case.id)
        .where(Case.station == user.station)
        .order_by(AuditLog.id.desc())
        .limit(250)
    ).all()
