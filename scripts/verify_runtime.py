"""Exercise real OCR and local models using synthetic verification data."""

import argparse

from sqlalchemy import select, type_coerce
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import make_engine
from app.models import LawSection
from app.services.extraction import extract
from app.services.law import ingest
from app.services.llm import OllamaProvider
from app.services.ocr import recognize


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--ocr", action="store_true")
    parser.add_argument("--models", action="store_true")
    args = parser.parse_args()
    settings = Settings()
    if settings.environment != "training":
        raise SystemExit("Run runtime probes in the isolated synthetic verification installation")
    if args.ocr:
        for extension, media in (("png", "image/png"), ("pdf", "application/pdf")):
            fixture = settings.corpus_path.parents[1] / "synthetic" / f"scanned-hi.{extension}"
            text, method = recognize(fixture.read_bytes(), media, settings)
            values = {(kind, value) for kind, value, _ in extract(text)}
            if method != "ocr" or not {("account", "9000012345"), ("amount", "19500.22"), ("date", "2024-02-29")} <= values:
                raise RuntimeError(f"Synthetic {extension} OCR probe did not meet its ground truth")
            print(f"Live Hindi {extension} OCR: account, amount and date passed", flush=True)
    if args.models:
        from pgvector.sqlalchemy import Vector

        provider = OllamaProvider(settings)
        answer = provider.generate("Return only READY.", "Synthetic local inference verification.")
        if not answer:
            raise RuntimeError("Live model inference returned no usable result")
        print(f"Live {settings.ollama_model} inference: returned a suggestion", flush=True)
        vectors = provider.embed(["search_query: electronic evidence certificate"])
        if not vectors:
            raise RuntimeError("Live embedding model did not return a finite 768-dimensional vector")
        engine = make_engine(settings.database_url)
        if engine.dialect.name != "postgresql":
            raise RuntimeError("Verify vector storage against PostgreSQL")
        with Session(engine) as db:
            count = ingest(db, settings.corpus_path, provider)
            rows = db.scalars(select(LawSection)).all()
            if not rows or any(row.embedding is None for row in rows):
                raise RuntimeError("The indexed legal sections do not all have embeddings")
            distance = type_coerce(LawSection.embedding, Vector(768)).cosine_distance(rows[0].embedding)
            result = db.execute(select(LawSection.id, distance).where(LawSection.embedding.is_not(None)).order_by(distance).limit(1)).first()
            if result[0] != rows[0].id or abs(result[1]) > 0.0001:
                raise RuntimeError("PostgreSQL cosine-distance verification failed")
        engine.dispose()
        print(f"Live embeddings: {count} sections stored; PostgreSQL nearest-vector check passed", flush=True)


if __name__ == "__main__":
    main()
