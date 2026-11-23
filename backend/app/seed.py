import os
from datetime import date
from hashlib import sha256

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import make_engine
from app.core.security import passwords
from app.models import Case, Document, Entity, Role, Transaction, User
from app.routers.graph import parse_csv
from app.services.extraction import extract
from app.services.law import ingest
from app.services.llm import OllamaProvider

DEMO_USERS = (
    ("demo.io", "Aditi Sharma", Role.IO, "Training Station"),
    ("demo.sho", "Vikram Singh", Role.SHO, "Training Station"),
    ("demo.co", "Meera Verma", Role.CO, "Training Station"),
    ("demo.sp", "Neel Kapoor", Role.SP, "Training Station"),
    ("demo.other", "Training Officer", Role.IO, "Second Training Station"),
)


def main() -> None:
    password = os.environ.get("DEMO_PASSWORD", "")
    if len(password) < 12:
        raise SystemExit("Set DEMO_PASSWORD to a demo-only value of at least 12 characters.")
    options = Settings()
    if options.environment != "training":
        raise SystemExit("Synthetic seed accounts are disabled in production. Use app.manage to provision officers.")
    engine = make_engine(options.database_url)
    synthetic_dir = options.corpus_path.parent.parent / "synthetic"
    if not (synthetic_dir / "fir-01.txt").exists():
        raise SystemExit("Generate or restore the tracked synthetic fixtures first.")
    with Session(engine) as db:
        ingest(db, options.corpus_path, OllamaProvider(options))
        seeded = {row.username: row for row in db.scalars(select(User))}
        for username, name, role, station in DEMO_USERS:
            if username not in seeded:
                user = User(username=username, name=name, role=role, station=station, password_hash=passwords.hash(password),
                    is_admin=username == "demo.sp")
                seeded[username] = user
                db.add(user)
        db.flush()
        existing = set(db.scalars(select(Case.reference)))
        for index, source in enumerate(sorted(synthetic_dir.glob("fir-*.txt")), 1):
            reference = f"DEMO-FIR-{index:03}"
            if reference in existing:
                continue
            text = source.read_text(encoding="utf-8")
            title = next(line.split(": ", 1)[1] for line in text.splitlines() if line.startswith(("Subject:", "विषय:")))
            opened_on = date.fromisoformat(next(
                line.split(": ", 1)[1] for line in text.splitlines() if line.startswith(("Date:", "दिनांक:"))
            ))
            content = source.read_bytes()
            case = Case(
                reference=reference, title=title, opened_on=opened_on,
                summary="Training case for reviewing a reported digital payment and tracing synthetic transfers.",
                station=seeded["demo.io"].station, assigned_to=seeded["demo.io"].id,
            )
            db.add(case)
            db.flush()
            evidence = Document(
                case_id=case.id, filename=source.name, media_type="text/plain", sha256=sha256(content).hexdigest(),
                size=len(content), content=content, text=text, extraction_method="text",
                uploaded_by=seeded["demo.io"].id,
            )
            db.add(evidence)
            db.flush()
            for kind, value, method in extract(text):
                db.add(Entity(document_id=evidence.id, kind=kind, value=value, method=method))
            csv_file = synthetic_dir / f"bank-{index:02}.csv"
            if csv_file.exists():
                for tx in parse_csv(csv_file.read_text(encoding="utf-8")):
                    db.add(Transaction(case_id=case.id, **tx.model_dump()))
        db.commit()
    engine.dispose()
    print("Seeded five training users, synthetic cases and legal references.")


if __name__ == "__main__":
    main()
