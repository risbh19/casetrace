import os
from datetime import date
from pathlib import Path
from uuid import uuid4

import pytest
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from sqlalchemy import text
from sqlalchemy.engine import make_url
from sqlalchemy.orm import Session

os.environ.setdefault("JWT_SECRET", "testing-only-signing-key-with-more-than-32-characters")

from app.core.config import Settings  # noqa: E402
from app.core.db import make_engine  # noqa: E402
from app.core.security import passwords  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Case, Role, User  # noqa: E402
from app.services.law import ingest  # noqa: E402

SECRET = "testing-only-signing-key-with-more-than-32-characters"
PASSWORD = "test-password-123"


@pytest.fixture
def client(tmp_path):
    url = f"sqlite:///{tmp_path / 'test.db'}"
    owner = None
    schema = None
    if os.environ.get("TEST_DATABASE_URL"):
        base = make_url(os.environ["TEST_DATABASE_URL"])
        if not (base.database or "").startswith("casetrace_test"):
            raise RuntimeError("TEST_DATABASE_URL must name a disposable casetrace_test database")
        owner = make_engine(base.render_as_string(hide_password=False))
        schema = "test_" + uuid4().hex
        with owner.begin() as connection:
            connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        url = base.update_query_dict({"options": f"-csearch_path={schema},public"}).render_as_string(hide_password=False)
    config = Config(str(Path(__file__).parents[1] / "alembic.ini"))
    config.set_main_option("script_location", str(Path(__file__).parents[1] / "alembic"))
    config.attributes["database_url"] = url
    config.attributes["version_table_schema"] = schema
    command.upgrade(config, "head")
    app = create_app(Settings(database_url=url, jwt_secret=SECRET, environment="training", ollama_model="", embedding_model=""))
    engine = app.state.engine
    with Session(engine) as db:
        encoded = passwords.hash(PASSWORD)
        for user in [
            User(username="io", name="Training IO", role=Role.IO, station="A", password_hash=encoded),
            User(username="sho", name="Training SHO", role=Role.SHO, station="A", password_hash=encoded),
            User(username="other", name="Other IO", role=Role.IO, station="B", password_hash=encoded),
            User(username="co", name="Training CO", role=Role.CO, station="A", password_hash=encoded),
        ]:
            db.add(user)
        db.flush()
        db.add(Case(
            reference="TRAINING-001", title="Synthetic payment fraud",
            summary="Evidence for the training scenario.", station="A", assigned_to=1, opened_on=date(2024, 1, 20),
        ))
        db.commit()
        ingest(db, app.state.settings.corpus_path, app.state.llm)
    try:
        with TestClient(app) as http:
            yield http
    finally:
        engine.dispose()
        if owner is not None:
            with owner.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            owner.dispose()


def bearer_for(client, username):
    response = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}
