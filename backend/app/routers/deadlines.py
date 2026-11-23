from datetime import date
from zoneinfo import ZoneInfo

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.core.db import DB
from app.core.security import CaseAccess, Officer, lock_case, require_roles
from app.middleware.audit import record
from app.models import Deadline, Role, now
from app.schemas import DeadlineInputs, DeadlineUpdate, DeadlineView
from app.services.deadlines import reminders
from app.services.plugins import load_plugin

router = APIRouter(prefix="/cases/{case_id}/deadlines")


def list_rows(db: DB, case_id: int):
    return db.scalars(
        select(Deadline).where(Deadline.case_id == case_id).order_by(Deadline.due_date, Deadline.id)
    ).all()


@router.get("", response_model=list[DeadlineView])
def list_deadlines(case: CaseAccess, db: DB):
    return list_rows(db, case.id)


@router.post("", response_model=list[DeadlineView])
def set_deadlines(values: DeadlineInputs, case: CaseAccess, db: DB, user: Officer, request: Request):
    require_roles(user, Role.IO, Role.SHO)
    if request.app.state.settings.environment == "production" and values.progress_on is None:
        raise HTTPException(422, "Enter the officer-confirmed progress-update anchor date")
    if values.progress_on and not case.opened_on <= values.progress_on <= now().astimezone(ZoneInfo("Asia/Kolkata")).date():
        raise HTTPException(422, "Review the progress anchor against the case date and today")
    if values.custody_on and not case.opened_on <= values.custody_on <= now().astimezone(ZoneInfo("Asia/Kolkata")).date():
        raise HTTPException(422, "Review the custody date against the case opening date and today")
    if values.supervisor_report_due and values.supervisor_report_due < case.opened_on:
        raise HTTPException(422, "Report target cannot precede case opening")
    upper = date(9999, 1, 1)
    if (values.custody_on and values.custody_on >= upper) or (values.progress_on and values.progress_on >= upper) or case.opened_on >= upper:
        raise HTTPException(422, "Date exceeds the supported calculation range")
    lock_case(db, case)
    existing = {row.kind: row for row in list_rows(db, case.id)}
    rules, _ = load_plugin(case.case_type)
    calculated = reminders(
        case.opened_on, rules, values.custody_on, values.custody_band, values.supervisor_report_due, values.progress_on,
    )
    retained = {item["kind"] for item in calculated}
    for kind, row in existing.items():
        if kind not in retained:
            db.delete(row)
    for values in calculated:
        previous = existing.get(values["kind"])
        if previous:
            if (previous.anchor_date, previous.due_date) != (values["anchor_date"], values["due_date"]):
                previous.completed = False
            for attribute, value in values.items():
                setattr(previous, attribute, value)
        else:
            db.add(Deadline(case_id=case.id, **values))
    record(request, db, "deadlines.calculated", "case", case.id)
    return list_rows(db, case.id)


@router.patch("/{deadline_id}", response_model=DeadlineView)
def set_completed(deadline_id: int, values: DeadlineUpdate, case: CaseAccess, db: DB, user: Officer, request: Request):
    require_roles(user, Role.IO, Role.SHO)
    row = db.scalar(select(Deadline).where(Deadline.id == deadline_id, Deadline.case_id == case.id))
    if not row:
        raise HTTPException(404, "Reminder not found")
    row.completed = values.completed
    record(request, db, "deadline.updated", "deadline", row.id, completed=row.completed)
    return row
