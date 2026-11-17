from fastapi import APIRouter, Request
from sqlalchemy import select

from app.core.db import DB
from app.core.security import CaseAccess, Officer, authenticate, case_filter, require_roles, token_for
from app.middleware.audit import record
from app.models import AuditLog, Case, Role
from app.schemas import AuditView, CaseCreate, CaseView, Login, LoginView, OfficerView

router = APIRouter()


@router.post("/auth/login", response_model=LoginView)
def login(values: Login, db: DB, request: Request):
    user = authenticate(db, values.username, values.password)
    request.state.actor_id = user.id
    record(request, db, "session.login", "user", user.id)
    return LoginView(access_token=token_for(request, user), officer=OfficerView.model_validate(user))


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
