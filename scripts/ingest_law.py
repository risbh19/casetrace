from sqlalchemy.orm import Session

from app.core.config import Settings
from app.core.db import make_engine
from app.services.law import ingest
from app.services.llm import OllamaProvider


def main() -> None:
    options = Settings()
    engine = make_engine(options.database_url)
    with Session(engine) as db:
        total = ingest(db, options.corpus_path, OllamaProvider(options))
    engine.dispose()
    print(f"Indexed {total} verified section summaries.")


if __name__ == "__main__":
    main()
