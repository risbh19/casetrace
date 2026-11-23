from datetime import datetime
from zoneinfo import ZoneInfo

from fastapi import APIRouter
from sqlalchemy import and_, func, select

from app.core.db import DB
from app.core.security import CaseAccess, Officer, case_filter, require_roles
from app.models import Case, Deadline, Document, Entity, Notice, NoticeState, PlanStep, Role
from app.schemas import CaseView

router = APIRouter()


@router.get("/dashboard")
def supervisor_dashboard(user: Officer, db: DB):
    require_roles(user, Role.SHO, Role.CO, Role.SP)
    cases = select(Case.id).where(case_filter(user))
    today = datetime.now(ZoneInfo("Asia/Kolkata")).date()
    overdue = select(Deadline).where(Deadline.case_id.in_(cases), Deadline.completed.is_(False), Deadline.due_date < today)
    return {
        "case_count": db.scalar(select(func.count()).select_from(Case).where(Case.id.in_(cases))),
        "open_steps": db.scalar(select(func.count()).select_from(PlanStep).where(PlanStep.case_id.in_(cases), PlanStep.status == "OPEN")),
        "pending_notices": db.scalar(select(func.count()).select_from(Notice).where(Notice.case_id.in_(cases), Notice.status == NoticeState.DRAFT)),
        "overdue_reminders": db.scalar(select(func.count()).select_from(overdue.subquery())),
        "recent_cases": [CaseView.model_validate(case) for case in db.scalars(select(Case).where(Case.id.in_(cases)).order_by(Case.created_at.desc()).limit(20))],
    }


@router.get("/cases/{case_id}/links")
def related_cases(case: CaseAccess, user: Officer, db: DB):
    identifiers = select(Entity.kind, Entity.value).join(Document, Document.id == Entity.document_id).where(
        Document.case_id == case.id, Entity.kind.in_(["phone", "account", "upi"])).distinct().subquery()
    rows = db.execute(select(Case.id, Case.reference, Case.title, Entity.kind, Entity.value)
        .join(Document, Document.case_id == Case.id).join(Entity, Entity.document_id == Document.id)
        .join(identifiers, and_(identifiers.c.kind == Entity.kind, identifiers.c.value == Entity.value))
        .where(Case.id != case.id, case_filter(user)).distinct().order_by(Case.id, Entity.kind, Entity.value).limit(100))
    return [dict(row._mapping) for row in rows]
