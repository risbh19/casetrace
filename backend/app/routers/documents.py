from hashlib import sha256
from pathlib import PurePosixPath
from typing import Annotated
from urllib.parse import quote, unquote

from fastapi import APIRouter, Header, HTTPException, Request, Response
from sqlalchemy import select
from starlette.concurrency import run_in_threadpool

from app.core.db import DB
from app.core.security import CaseAccess, Officer, require_roles
from app.middleware.audit import record
from app.models import Document, Entity, Role
from app.schemas import DocumentDetail, DocumentView, EntityView
from app.services.extraction import confirm_ambiguous_accounts, extract
from app.services.ocr import MAX_BYTES, classify, recognize

router = APIRouter(prefix="/cases/{case_id}/documents")


def document_in_case(db: DB, case_id: int, document_id: int) -> Document:
    document = db.scalar(select(Document).where(Document.id == document_id, Document.case_id == case_id))
    if not document:
        raise HTTPException(404, "Evidence file not found")
    return document


@router.get("", response_model=list[DocumentView])
def list_documents(case: CaseAccess, db: DB):
    return db.scalars(select(Document).where(Document.case_id == case.id).order_by(Document.id.desc())).all()


@router.post("", response_model=DocumentDetail, status_code=201)
async def upload_document(
    case: CaseAccess, db: DB, user: Officer, request: Request, x_filename: Annotated[str, Header()],
):
    require_roles(user, Role.IO, Role.SHO)
    content = bytearray()
    async for chunk in request.stream():
        if len(content) + len(chunk) > MAX_BYTES:
            raise HTTPException(413, "Evidence files are limited to 8 MiB")
        content.extend(chunk)
    if not content:
        raise HTTPException(422, "The evidence file is empty")
    name = PurePosixPath(unquote(x_filename).replace("\\", "/")).name
    if not name or len(name) > 200 or any(ord(c) < 32 for c in name):
        raise HTTPException(422, "Invalid evidence filename")
    return await run_in_threadpool(save_document, case.id, db, user.id, request, name, bytes(content))


def save_document(case_id: int, db: DB, user_id: int, request: Request, name: str, content: bytes):
    try:
        media = classify(name, content)
    except ValueError as exc:
        raise HTTPException(422, str(exc)) from None
    digest = sha256(content).hexdigest()
    if db.scalar(select(Document.id).where(Document.case_id == case_id, Document.sha256 == digest)):
        raise HTTPException(409, "This exact evidence file is already on the case")
    try:
        media = classify(name, content)
        text, method = recognize(content, media, request.app.state.settings)
    except (ValueError, OSError) as exc:
        detail = "Text files must use UTF-8" if isinstance(exc, UnicodeDecodeError) else str(exc)
        raise HTTPException(422, detail) from None
    found = {(kind, value): source for kind, value, source in extract(text)}
    if request.app.state.settings.ollama_model:
        for kind, value, source in confirm_ambiguous_accounts(text, request.app.state.llm.generate):
            found.setdefault((kind, value), source)
    document = Document(
        case_id=case_id, filename=name, media_type=media, content=content, text=text,
        extraction_method=method, sha256=digest, size=len(content), uploaded_by=user_id,
    )
    db.add(document)
    db.flush()
    for (kind, value), source in found.items():
        db.add(Entity(document_id=document.id, kind=kind, value=value, method=source))
    record(request, db, "evidence.uploaded", "document", document.id, bytes=len(content), sha256=digest)
    return DocumentDetail(
        **DocumentView.model_validate(document).model_dump(),
        text=text,
        entities=[EntityView(kind=k, value=v, method=s) for (k, v), s in found.items()],
    )


@router.get("/{document_id}", response_model=DocumentDetail)
def inspect_document(document_id: int, case: CaseAccess, db: DB):
    document = document_in_case(db, case.id, document_id)
    entities = db.scalars(select(Entity).where(Entity.document_id == document.id).order_by(Entity.id)).all()
    return DocumentDetail(
        **DocumentView.model_validate(document).model_dump(), text=document.text,
        entities=[EntityView.model_validate(entity) for entity in entities],
    )


@router.get("/{document_id}/original")
def download(document_id: int, case: CaseAccess, db: DB):
    document = document_in_case(db, case.id, document_id)
    return Response(
        document.content, media_type="application/octet-stream",
        headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(document.filename, safe='')}"},
    )
