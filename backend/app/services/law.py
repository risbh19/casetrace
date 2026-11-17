import json
from pathlib import Path

from sqlalchemy import select, type_coerce
from sqlalchemy.orm import Session

from app.models import LawSection
from app.schemas import Citation, LawAnswer
from app.services.llm import LLMProvider
from app.services.retrieval import requested_sections, score


def ingest(db: Session, source: Path, llm: LLMProvider) -> int:
    entries = json.loads(source.read_text(encoding="utf-8"))
    vectors = llm.embed(["search_document: " + row["title"] + ". " + row["summary"] for row in entries])
    existing = {(row.act, row.section): row for row in db.scalars(select(LawSection))}
    keys = {(row["act"], row["section"]) for row in entries}
    if len(keys) != len(entries):
        raise ValueError("Duplicate legal references in corpus")
    for key in existing.keys() - keys:
        db.delete(existing[key])
    for index, values in enumerate(entries):
        key = (values["act"], values["section"])
        row = existing.get(key)
        if row is None:
            row = LawSection(act=key[0], section=key[1])
            db.add(row)
        for field, value in values.items():
            setattr(row, field, value)
        row.embedding = vectors[index] if vectors else None
    db.commit()
    return len(entries)


def citation(row: LawSection) -> Citation:
    return Citation.model_validate(row, from_attributes=True)


def ask(db: Session, question: str, llm: LLMProvider) -> LawAnswer:
    rows = list(db.scalars(select(LawSection).order_by(LawSection.id)))
    explicit = requested_sections(question)
    ranked = sorted(
        ((score(question, row.keywords), row) for row in rows),
        key=lambda item: -item[0],
    )
    if explicit:
        selected = []
        for act, section in sorted(explicit):
            matches = [
                (rank, row) for rank, row in ranked if row.act == act
                and (row.section.casefold() == section or row.section.casefold().startswith(section + "("))
            ]
            if matches:
                selected.extend(row for rank, row in matches if rank == matches[0][0])
        selected = list(dict.fromkeys(selected))[:3]
    else:
        selected = [ranked[0][1]] if ranked and ranked[0][0] >= 8 else []
        if not selected and db.bind.dialect.name == "postgresql":
            vectors = llm.embed(["search_query: " + question])
            if vectors:
                from pgvector.sqlalchemy import Vector

                distance = type_coerce(LawSection.embedding, Vector(768)).cosine_distance(vectors[0])
                nearest = db.execute(
                    select(LawSection, distance).where(LawSection.embedding.is_not(None))
                    .order_by(distance).limit(1)
                ).first()
                if nearest is not None and nearest[1] <= 0.25:
                    selected = [nearest[0]]
    if not selected:
        return LawAnswer(status="unsure", answer="No reliable match in the demo legal corpus.", citations=[])
    citations = [citation(row) for row in selected]
    return LawAnswer(status="grounded", answer="\n\n".join(c.summary for c in citations), citations=citations)
