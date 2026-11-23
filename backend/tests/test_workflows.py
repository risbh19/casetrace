from hashlib import sha256

from conftest import bearer_for

ROOT = "/api/cases/1"


def test_roles_case_isolation_and_audit(client):
    assert client.get(ROOT).status_code == 401
    io = bearer_for(client, "io")
    other = bearer_for(client, "other")
    co = bearer_for(client, "co")
    request = {"reference": "TRAINING-002", "title": "Another case", "summary": "Fictional", "opened_on": "2024-02-03"}
    assert client.get(ROOT, headers=io).status_code == 200
    assert client.get(ROOT, headers=other).status_code == 404
    assert client.get("/api/cases", headers=other).json() == []
    assert client.post("/api/cases", headers=co, json=request).status_code == 403
    created = client.post("/api/cases", headers=io, json=request)
    assert created.status_code == 201, created.text
    assert client.post("/api/cases", headers=io, json=request).status_code == 409
    events = client.get(f"/api/cases/{created.json()['id']}/audit", headers=co).json()
    assert len(events) == 1
    assert events[0]["action"] == "case.created"
    assert events[0]["user_id"] == 1
    assert "Fictional" not in str(events)
    assert client.get(ROOT + "/audit", headers=io).status_code == 403


def test_evidence_preserves_original_and_rejects_duplicates(client):
    io = bearer_for(client, "io")
    case_evidence = ROOT + "/documents"
    body = "+91 90000 12345 · INR 19,500.22 · sample@demo · IFSC DEMO0000001".encode()
    headers = {**io, "X-Filename": "case.txt", "Content-Type": "application/octet-stream"}
    first = client.post(case_evidence, headers=headers, content=body)
    assert first.status_code == 201, first.text
    evidence = first.json()
    assert evidence["sha256"] == sha256(body).hexdigest()
    assert {item["kind"] for item in evidence["entities"]} == {"phone", "amount", "upi", "ifsc"}
    archived = client.get(f"{case_evidence}/{evidence['id']}/original", headers=io)
    assert archived.content == body
    assert "attachment" in archived.headers["Content-Disposition"]
    assert client.post(case_evidence, headers=headers, content=body).status_code == 409
    mismatch = client.post(case_evidence, headers={**headers, "X-Filename": "photo.jpg"}, content=body)
    assert mismatch.status_code == 422


def test_plan_checks_citations_and_preserves_officer_progress(client):
    io = bearer_for(client, "io")
    path = ROOT + "/plan"
    generated = client.post(path, headers=io)
    assert generated.status_code == 200, generated.text
    steps = generated.json()
    assert len(steps) == 5
    assert steps[0]["legal_basis"]["section"] == "173"
    assert "egazette.gov.in" in steps[0]["legal_basis"]["source_url"]
    assert steps[3]["legal_basis"] == "unsure"
    done = client.patch(f"{path}/{steps[0]['id']}", headers=io, json={"status": "DONE"})
    assert done.status_code == 200
    second = client.post(path, headers=io).json()
    assert second[0]["status"] == "DONE"
    assert [step["id"] for step in second] == [step["id"] for step in steps]


def test_approval_gate_and_simulated_send(client):
    io = bearer_for(client, "io")
    sho = bearer_for(client, "sho")
    values = {"kind": "bank_statement", "recipient": "Synthetic Bank", "facts": "Fictional transfer REF-0001."}
    created = client.post(ROOT + "/notices", headers=io, json=values)
    assert created.status_code == 201, created.text
    root = f"{ROOT}/notices/{created.json()['id']}"
    assert created.json()["status"] == "DRAFT"
    assert "TRAINING DRAFT" in created.json()["body"]
    assert client.post(root + "/approve", headers=io).status_code == 403
    assert client.post(root + "/send", headers=sho).status_code == 409
    approval = client.post(root + "/approve", headers=sho).json()
    assert approval["status"] == "APPROVED"
    assert approval["approved_by"] == 2
    assert client.post(root + "/send", headers=sho).json()["status"] == "SENT"
    assert client.post(root + "/send", headers=sho).status_code == 409
    own_id = client.post(ROOT + "/notices", headers=sho, json=values).json()["id"]
    assert client.post(f"{ROOT}/notices/{own_id}/approve", headers=sho).status_code == 403
    actions = {e["action"] for e in client.get(ROOT + "/audit", headers=sho).json()}
    assert {"notice.drafted", "notice.approved", "notice.send_simulated", "request.post"} <= actions


def test_money_trail_import_is_repeatable_and_checks_latest_balance(client):
    io = bearer_for(client, "io")
    csv = (
        "reference,from_acc,to_acc,amount,ts,balance_remaining\n"
        "T1,A,B,99,2024-02-03T09:00:00+05:30,90\n"
        "T2,B,C,70,2024-02-03T09:01:00+05:30,30\n"
        "T3,B,C,10,2024-02-03T09:02:00+05:30,35\n"
        "T4,A,D,20,2024-02-03T09:03:00+05:30,0\n"
    )
    path = ROOT + "/transactions/import"
    assert client.post(path, headers=io, json={"csv": csv}).json() == {"added": 4, "repeated": 0}
    assert client.post(path, headers=io, json={"csv": csv}).json() == {"added": 0, "repeated": 4}
    assert client.post(path, headers=io, json={"csv": csv.replace("T1,A,B,99", "T1,A,B,98")}).status_code == 409
    graph = client.get(ROOT + "/graph", headers=io).json()
    assert [item["id"] for item in graph["priorities"]] == ["C"]
    assert graph["priorities"][0]["balance_remaining"] == "35.00"
    assert next(edge for edge in graph["edges"] if edge["source"] == "B")["amount"] == "80.00"


def test_deadlines_separate_progress_custody_and_supervisor_target(client):
    io = bearer_for(client, "io")
    path = ROOT + "/deadlines"
    values = {
        "custody_on": "2024-01-31", "custody_band": "other_offence", "supervisor_report_due": "2024-05-02",
    }
    reminders = {item["kind"]: item for item in client.post(path, headers=io, json=values).json()}
    assert reminders["victim_progress"]["due_date"] == "2024-04-19"
    assert reminders["custody_review"]["due_date"] == "2024-03-31"
    assert reminders["report_target"]["due_date"] == "2024-05-02"
    review = reminders["custody_review"]
    assert client.patch(f"{path}/{review['id']}", headers=io, json={"completed": True}).json()["completed"]
    values["custody_band"] = "death_life_or_ten_years_or_more"
    current = {item["kind"]: item for item in client.post(path, headers=io, json=values).json()}
    assert current["custody_review"]["due_date"] == "2024-04-30"
    assert not current["custody_review"]["completed"]
    assert client.post(path, headers=io, json={"custody_on": "2024-01-31"}).status_code == 422


def test_clearing_optional_dates_removes_stale_reminders(client):
    io = bearer_for(client, "io")
    path = ROOT + "/deadlines"
    first = client.post(path, headers=io, json={
        "custody_on": "2024-01-31", "custody_band": "other_offence",
        "supervisor_report_due": "2024-05-02",
    }).json()
    assert len(first) == 3
    cleared = client.post(path, headers=io, json={
        "custody_on": None, "custody_band": None, "supervisor_report_due": None,
    })
    assert cleared.status_code == 200
    assert [row["kind"] for row in cleared.json()] == ["victim_progress"]
    assert client.get(path, headers=io).json() == cleared.json()


def test_production_requires_confirmed_progress_anchor(client):
    io = bearer_for(client, "io")
    client.app.state.settings.environment = "production"
    path = ROOT + "/deadlines"
    assert client.post(path, headers=io, json={}).status_code == 422
    result = client.post(path, headers=io, json={"progress_on": "2024-02-01"})
    assert result.status_code == 200
    assert result.json()[0]["anchor_date"] == "2024-02-01"
    assert result.json()[0]["due_date"] == "2024-05-01"
