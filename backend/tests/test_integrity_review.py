import pytest
from app.core.security import passwords
from app.models import Role, User
from conftest import bearer_for
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session


def upload(client, token, path="/api/cases/1/documents"):
    return client.post(path, headers={**token, "X-Filename": "receipt.txt", "Content-Type": "application/octet-stream"},
        content=b"Fictional dispatch proof; phone +91 90000 12345.")


def test_originals_and_audit_events_cannot_be_changed_in_database(client):
    io = bearer_for(client, "io")
    assert upload(client, io).status_code == 201
    for statement in ("UPDATE documents SET text = 'changed'", "DELETE FROM documents", "UPDATE audit_logs SET action = 'changed'", "DELETE FROM audit_logs"):
        with Session(client.app.state.engine) as db:
            with pytest.raises(DBAPIError):
                db.execute(text(statement))
            db.rollback()


def test_production_notice_requires_recorded_dispatch_proof(client):
    io, sho = bearer_for(client, "io"), bearer_for(client, "sho")
    client.app.state.settings.environment = "production"
    notice = client.post("/api/cases/1/notices", headers=io, json={"kind": "bank_statement", "recipient": "Bank", "facts": "Recorded facts for review"}).json()
    assert notice["body"].startswith("DRAFT FOR AUTHORIZED OFFICER REVIEW")
    root = f"/api/cases/1/notices/{notice['id']}"
    assert client.post(root + "/approve", headers=sho).status_code == 200
    assert client.post(root + "/send", headers=sho).status_code == 409
    values = {"channel": "official_portal", "reference": "dispatch-001", "evidence_document_id": 999999}
    assert client.post(root + "/dispatch", headers=sho, json=values).status_code == 422
    values["evidence_document_id"] = upload(client, io).json()["id"]
    assert client.post(root + "/dispatch", headers=io, json=values).status_code == 403
    sent = client.post(root + "/dispatch", headers=sho, json=values)
    assert sent.status_code == 200, sent.text
    assert sent.json()["delivery_reference"] == "dispatch-001"
    assert client.post(root + "/dispatch", headers=sho, json=values).status_code == 409


def test_case_links_and_dashboard_obey_access_boundaries(client):
    io, sho, other = bearer_for(client, "io"), bearer_for(client, "sho"), bearer_for(client, "other")
    values = {"reference": "LINKED-002", "title": "Related training case", "summary": "Fictional", "opened_on": "2024-02-03"}
    case_id = client.post("/api/cases", headers=io, json=values).json()["id"]
    assert upload(client, io).status_code == 201
    assert upload(client, io, f"/api/cases/{case_id}/documents").status_code == 201
    result = client.get("/api/cases/1/links", headers=io).json()
    assert result[0]["id"] == case_id
    assert result[0]["kind"] == "phone"
    assert client.get("/api/cases/1/links", headers=other).status_code == 404
    assert client.get("/api/dashboard", headers=io).status_code == 403
    assert client.get("/api/dashboard", headers=sho).json()["case_count"] == 2


def test_reassignment_requires_a_supervisor_and_updates_case_access(client):
    from conftest import PASSWORD

    with Session(client.app.state.engine) as db:
        target = User(username="replacement", name="Replacement officer", station="A", role=Role.IO,
            password_hash=passwords.hash(PASSWORD))
        db.add(target)
        db.commit()
        target_id = target.id
    io, sho = bearer_for(client, "io"), bearer_for(client, "sho")
    path = "/api/cases/1/assignment"
    assert client.patch(path, headers=io, json={"officer_id": target_id}).status_code == 403
    assert client.patch(path, headers=sho, json={"officer_id": 3}).status_code == 422
    assert client.patch(path, headers=sho, json={"officer_id": target_id}).status_code == 200
    assert client.get("/api/cases/1", headers=io).status_code == 404
    assert client.get("/api/cases/1", headers=bearer_for(client, "replacement")).status_code == 200
