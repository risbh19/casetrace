import os
from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

os.environ.setdefault("JWT_SECRET", "testing-only-signing-key-with-more-than-32-characters")

from app.core.config import Settings  # noqa: E402
from app.core.security import passwords  # noqa: E402
from app.main import create_app  # noqa: E402
from app.models import Base, Case, Role, User  # noqa: E402
from app.services.law import ingest  # noqa: E402

SECRET = "testing-only-signing-key-with-more-than-32-characters"
PASSWORD = "test-password-123"


@pytest.fixture
def client(tmp_path):
    app = create_app(Settings(database_url=f"sqlite:///{tmp_path / 'test.db'}", jwt_secret=SECRET))
    engine = app.state.engine
    Base.metadata.create_all(engine)
    with Session(engine) as db:
        encoded = passwords.hash(PASSWORD)
        for user in [
            User(id=1, username="io", name="Training IO", role=Role.IO, station="A", password_hash=encoded),
            User(id=2, username="sho", name="Training SHO", role=Role.SHO, station="A", password_hash=encoded),
            User(id=3, username="other", name="Other IO", role=Role.IO, station="B", password_hash=encoded),
            User(id=4, username="co", name="Training CO", role=Role.CO, station="A", password_hash=encoded),
        ]:
            db.add(user)
        db.flush()
        db.add(Case(
            id=1, reference="TRAINING-001", title="Synthetic payment fraud",
            summary="Evidence for the training scenario.", station="A", assigned_to=1, opened_on=date(2024, 1, 20),
        ))
        db.commit()
        ingest(db, app.state.settings.corpus_path, app.state.llm)
    with TestClient(app) as http:
        yield http


def bearer_for(client, username):
    response = client.post("/api/auth/login", json={"username": username, "password": PASSWORD})
    assert response.status_code == 200, response.text
    return {"Authorization": "Bearer " + response.json()["access_token"]}
