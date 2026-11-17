from typing import Any

from fastapi import Request
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from app.models import AuditLog

WRITE_METHODS = {"POST", "PATCH", "PUT", "DELETE"}


def record(
    request: Request,
    db: Session,
    action: str,
    entity: str,
    entity_id: int | None = None,
    **payload: Any,
) -> None:
    db.add(
        AuditLog(
            user_id=getattr(request.state, "actor_id", None),
            case_id=getattr(request.state, "case_id", None),
            action=action,
            entity=entity,
            entity_id=str(entity_id) if entity_id is not None else None,
            payload=payload,
        )
    )
    db.commit()
    request.state.audit_recorded = True


async def audit_writes(request: Request, call_next):
    response = await call_next(request)
    if request.method not in WRITE_METHODS or not request.url.path.startswith("/api/"):
        return response
    if getattr(request.state, "audit_recorded", False):
        return response

    def record_request() -> None:
        # Store the route pattern and outcome, never submitted text, paths or credentials.
        route = request.scope.get("route")
        with Session(request.app.state.engine) as db:
            record(
                request,
                db,
                f"request.{request.method.lower()}",
                "request",
                route=getattr(route, "path", "unmatched"),
                status=response.status_code,
            )

    await run_in_threadpool(record_request)
    return response
