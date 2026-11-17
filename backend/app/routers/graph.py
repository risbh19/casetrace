import csv
from datetime import UTC
from io import StringIO

from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel, Field, ValidationError
from sqlalchemy import select

from app.core.db import DB
from app.core.security import CaseAccess, Officer, lock_case, require_roles
from app.middleware.audit import record
from app.models import Role, Transaction
from app.schemas import TransactionCreate
from app.services.trail import build_graph

router = APIRouter(prefix="/cases/{case_id}")


class CsvImport(BaseModel):
    csv: str = Field(min_length=1, max_length=150_000)


def transactions_for(db: DB, case_id: int):
    return db.scalars(
        select(Transaction).where(Transaction.case_id == case_id).order_by(Transaction.ts, Transaction.id)
    ).all()


def parse_csv(text: str) -> list[TransactionCreate]:
    reader = csv.DictReader(StringIO(text.lstrip("\ufeff")), strict=True)
    required = set(TransactionCreate.model_fields) - {"balance_remaining"}
    supplied = reader.fieldnames
    if not supplied or not required.issubset(supplied) or len(set(supplied)) != len(supplied):
        raise HTTPException(422, "CSV needs reference, from_acc, to_acc, amount and ts columns")
    rows = []
    try:
        for row in reader:
            if len(rows) >= 300 or None in row:
                raise HTTPException(422, "Use up to 300 rows with the same number of columns as the header")
            row["balance_remaining"] = row.get("balance_remaining") or None
            try:
                rows.append(TransactionCreate.model_validate(row))
            except ValidationError:
                raise HTTPException(422, f"Invalid transaction on CSV line {reader.line_num}") from None
    except csv.Error:
        raise HTTPException(422, f"Malformed CSV near line {reader.line_num}") from None
    if not rows:
        raise HTTPException(422, "The CSV contains no transactions")
    if len({row.reference for row in rows}) != len(rows):
        raise HTTPException(422, "Transaction references must be unique within a CSV")
    return rows


@router.get("/graph")
def get_graph(case: CaseAccess, db: DB):
    return build_graph(transactions_for(db, case.id))


@router.post("/transactions/import")
def import_csv(values: CsvImport, case: CaseAccess, db: DB, user: Officer, request: Request):
    require_roles(user, Role.IO, Role.SHO)
    rows = parse_csv(values.csv)
    lock_case(db, case)
    existing = {row.reference: row for row in transactions_for(db, case.id)}
    added = []
    for row in rows:
        previous = existing.get(row.reference)
        if previous is not None:
            previous_values = {key: getattr(previous, key) for key in TransactionCreate.model_fields}
            if previous.ts.tzinfo is None:
                previous_values["ts"] = previous.ts.replace(tzinfo=UTC)
            old = TransactionCreate.model_validate(previous_values)
            if old != row:
                raise HTTPException(409, "A transfer with that reference already exists with different values")
        else:
            added.append(Transaction(case_id=case.id, **row.model_dump()))
    if len(existing) + len(added) > 1000:
        raise HTTPException(422, "Demo cases support up to 1,000 transfers")
    db.add_all(added)
    record(request, db, "transactions.imported", "case", case.id, added=len(added), repeated=len(rows) - len(added))
    return {"added": len(added), "repeated": len(rows) - len(added)}
