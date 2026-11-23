import pytest
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.security import passwords, verify_operational_store
from app.models import Role, User
from conftest import PASSWORD, bearer_for


def admin_for(client):
    with Session(client.app.state.engine) as db:
        db.add(User(username="admin", name="Station admin", station="A", role=Role.SP,
            password_hash=passwords.hash(PASSWORD), is_admin=True))
        db.commit()
    return bearer_for(client, "admin")


def test_logout_revokes_only_the_current_session(client):
    first, second = bearer_for(client, "io"), bearer_for(client, "io")
    assert client.post("/api/auth/logout", headers=first).status_code == 204
    assert client.get("/api/cases", headers=first).status_code == 401
    assert client.get("/api/cases", headers=second).status_code == 200


def test_password_change_revokes_previous_sessions(client):
    old = bearer_for(client, "io")
    values = {"current_password": PASSWORD, "new_password": "a-new-passphrase-for-tests"}
    changed = client.post("/api/auth/password", headers=old, json=values)
    assert changed.status_code == 200, changed.text
    assert client.get("/api/auth/me", headers=old).status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer " + changed.json()["access_token"]}).status_code == 200
    assert client.post("/api/auth/login", json={"username": "io", "password": PASSWORD}).status_code == 401


def test_officer_lifecycle_is_scoped_and_forces_password_change(client):
    io = bearer_for(client, "io")
    admin = admin_for(client)
    assert client.get("/api/officers", headers=io).status_code == 403
    assert "other" not in {user["username"] for user in client.get("/api/officers", headers=admin).json()}
    assert client.patch("/api/officers/3", headers=admin, json={"is_active": False}).status_code == 404
    created = client.post("/api/officers", headers=admin, json={"username": "new.io", "name": "Officer",
        "role": "IO", "temporary_password": "temporary-passphrase-123"})
    assert created.status_code == 201, created.text
    assert "password_hash" not in created.json()
    assert "temporary_password" not in created.json()
    assert created.json()["must_change_password"]
    user_id = created.json()["id"]
    login = client.post("/api/auth/login", json={"username": "new.io", "password": "temporary-passphrase-123"})
    token = {"Authorization": "Bearer " + login.json()["access_token"]}
    assert client.get("/api/cases", headers=token).status_code == 403
    assert client.post("/api/auth/password", headers=token, json={"current_password": "temporary-passphrase-123",
        "new_password": "individual-passphrase-456"}).status_code == 200
    assert client.patch(f"/api/officers/{user_id}", headers=admin, json={"is_active": False}).status_code == 200
    assert client.get("/api/auth/me", headers=token).status_code == 401
    assert client.post("/api/auth/login", json={"username": "new.io", "password": "individual-passphrase-456"}).status_code == 401
    with Session(client.app.state.engine) as db:
        admin_id = db.scalar(select(User.id).where(User.username == "admin"))
    assert client.patch(f"/api/officers/{admin_id}", headers=admin, json={"is_active": False}).status_code == 403


def test_login_attempts_are_throttled_without_exposing_usernames(client):
    for _ in range(10):
        assert client.post("/api/auth/login", json={"username": "unknown", "password": "wrong"}).status_code == 401
    result = client.post("/api/auth/login", json={"username": "unknown", "password": "wrong"})
    assert result.status_code == 429
    assert result.headers["Retry-After"] == "900"


def test_operational_startup_refuses_a_seeded_training_store(client):
    verify_operational_store(client.app.state.engine)
    with Session(client.app.state.engine) as db:
        db.add(User(username="demo.blocked", name="Synthetic account", station="A", role=Role.IO,
            password_hash=passwords.hash(PASSWORD)))
        db.commit()
    with pytest.raises(RuntimeError, match="seeded training database"):
        verify_operational_store(client.app.state.engine)
