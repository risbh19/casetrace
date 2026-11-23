import re
from datetime import UTC, datetime
from hashlib import sha256
from io import BytesIO

from pypdf import PdfReader
from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models import LawPage
from app.schemas import LawPassage
from app.services.retrieval import STOP_WORDS, requested_sections


def index_pdf(db: Session, act: str, source_url: str, content: bytes) -> int:
    if not content.startswith(b"%PDF-") or len(content) > 30 * 1024 * 1024:
        raise ValueError("Use an official PDF of at most 30 MiB")
    reader = PdfReader(BytesIO(content))
    if reader.is_encrypted or not 1 <= len(reader.pages) <= 2000:
        raise ValueError("Use an unencrypted document of at most 2,000 pages")
    digest = sha256(content).hexdigest()
    today = datetime.now(UTC).date()
    pages = [(n + 1, page.extract_text() or "") for n, page in enumerate(reader.pages)]
    if sum(len(text.strip()) for _, text in pages) < 100:
        raise ValueError("The source has no usable text; review the original PDF")
    # Parse completely before replacing a previously indexed source.
    db.execute(delete(LawPage).where(LawPage.act == act))
    db.add_all([LawPage(act=act, page=n, text=text, source_url=source_url,
        source_sha256=digest, retrieved_on=today) for n, text in pages if text.strip()])
    db.commit()
    return len(pages)


def search_pages(db: Session, question: str) -> list[LawPassage]:
    terms = set(re.findall(r"[a-z]{3,}", question.lower())) - STOP_WORDS - {"section", "bnss", "bns", "act", "bsa"}
    explicit = requested_sections(question)
    statement = select(LawPage)
    if explicit:
        statement = statement.where(LawPage.act.in_({act for act, _ in explicit}))
    ranked = []
    for page in db.scalars(statement.order_by(LawPage.id)):
        text = page.text.lower()
        references = [section.split("(", 1)[0] for act, section in explicit if act == page.act]
        matches_reference = any(re.search(rf"(?m)^\s*{re.escape(section)}\.(?!\d)", text) for section in references)
        if explicit and not matches_reference:
            continue
        positions = [m.start() for term in terms for m in re.finditer(rf"\b{re.escape(term)}\b", text)]
        overlap = sum(bool(re.search(rf"\b{re.escape(term)}\b", text)) for term in terms)
        if not explicit and overlap < max(2, min(3, len(terms))):
            continue
        start = max(0, min(positions, default=0) - 180)
        contents_page = "arrangement of sections" in text or len(re.findall(r"(?m)^\s*\d+[a-z]?\.", text)) > 12
        rank = overlap * 10 + min(len(positions), 20) - (100 if contents_page else 0)
        ranked.append((rank, page, start))
    ranked.sort(key=lambda item: (-item[0], item[1].page))
    return [LawPassage(act=page.act, page=page.page, text=page.text[start:start + 2400],
        source_url=page.source_url, source_sha256=page.source_sha256, retrieved_on=page.retrieved_on)
        for _, page, start in ranked[:3]]
