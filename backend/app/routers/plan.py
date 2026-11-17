from datetime import timedelta

from fastapi import APIRouter, HTTPException, Request
from sqlalchemy import select

from app.core.db import DB
from app.core.security import CaseAccess, Officer, lock_case, require_roles
from app.middleware.audit import record
from app.models import LawSection, PlanStep, Role
from app.schemas import PlanStepView, PlanUpdate
from app.services.law import citation
from app.services.plugins import load_plugin

router = APIRouter(prefix="/cases/{case_id}/plan")


def present(step: PlanStep) -> PlanStepView:
    return PlanStepView(
        id=step.id, title=step.title, instructions=step.instructions,
        legal_basis=step.legal_basis or "unsure", due_date=step.due_date, status=step.status,
    )


def get_steps(db: DB, case_id: int) -> list[PlanStep]:
    return list(db.scalars(select(PlanStep).where(PlanStep.case_id == case_id).order_by(PlanStep.id)))


@router.get("", response_model=list[PlanStepView])
def list_plan(case: CaseAccess, db: DB):
    return [present(step) for step in get_steps(db, case.id)]


@router.post("", response_model=list[PlanStepView])
def generate_plan(case: CaseAccess, db: DB, user: Officer, request: Request):
    require_roles(user, Role.IO, Role.SHO)
    lock_case(db, case)
    existing = get_steps(db, case.id)
    previous = {step.step_key for step in existing}
    _, checklist = load_plugin(case.case_type)
    laws = {(law.act, law.section): law for law in db.scalars(select(LawSection))}
    added = []
    for item in checklist:
        if item["key"] in previous:
            continue
        law = laws.get(tuple(item.get("legal_basis", [])))
        added.append(
            PlanStep(
                case_id=case.id, step_key=item["key"], title=item["title"], instructions=item["instructions"],
                legal_basis=citation(law).model_dump() if law else None,
                due_date=case.opened_on + timedelta(days=item["days"]),
            )
        )
    db.add_all(added)
    record(request, db, "plan.generated", "case", case.id, steps_added=len(added))
    return [present(step) for step in existing + added]


@router.patch("/{step_id}", response_model=PlanStepView)
def update_step(step_id: int, values: PlanUpdate, case: CaseAccess, db: DB, user: Officer, request: Request):
    require_roles(user, Role.IO, Role.SHO)
    step = db.scalar(select(PlanStep).where(PlanStep.id == step_id, PlanStep.case_id == case.id))
    if not step:
        raise HTTPException(404, "Plan step not found")
    step.status = values.status
    record(request, db, "plan.step_updated", "plan_step", step.id, status=step.status)
    return present(step)
