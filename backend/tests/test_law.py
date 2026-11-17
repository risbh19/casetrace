import pytest
from conftest import bearer_for

GOLDEN = [
    ("What section permits zero FIR?", "BNSS", "173"),
    ("How long is allowed to sign an electronic FIR?", "BNSS", "173"),
    ("What section covers bank records?", "BNSS", "94"),
    ("Which provision addresses call detail records?", "BNSS", "94"),
    ("Who receives the video of a seizure?", "BNSS", "105"),
    ("What law addresses videography of seizure?", "BNSS", "105"),
    ("Can suspected stolen property be seized?", "BNSS", "106"),
    ("Which section is relevant to a bank freeze?", "BNSS", "106"),
    ("When does a forensic expert visit a crime scene?", "BNSS", "176(3)"),
    ("What are the default bail windows?", "BNSS", "187(3)"),
    ("Where is the custody limit?", "BNSS", "187(3)"),
    ("Is there a universal chargesheet deadline?", "BNSS", "193(1)"),
    ("How is electronic-device chain of custody included in the police report?", "BNSS", "193(3)(i)"),
    ("When is a victim progress update due?", "BNSS", "193(3)(ii)"),
    ("BNSS 193(3)(ii)", "BNSS", "193(3)(ii)"),
    ("What covers dishonest inducement and delivery of property?", "BNS", "318"),
    ("What law covers cheating by personation?", "BNS", "319"),
    ("Where is identity theft defined?", "IT Act", "66C"),
    ("What covers online impersonation using a digital device?", "IT Act", "66D"),
    ("Do I need an electronic record certificate?", "BSA", "63"),
]


def test_golden_law_citations(client):
    io = bearer_for(client, "io")
    reported = []
    for question, act, section in GOLDEN:
        result = client.post("/api/law/ask", headers=io, json={"question": question}).json()
        primary = result["citations"][0] if result["citations"] else {}
        if (primary.get("act"), primary.get("section")) != (act, section):
            reported.append((question, primary, section))
    assert not reported, reported


@pytest.mark.parametrize("question", ["What is the capital of France?", "BNSS 999"])
def test_unsupported_questions_abstain(client, question):
    io = bearer_for(client, "io")
    result = client.post("/api/law/ask", headers=io, json={"question": question}).json()
    assert result["status"] == "unsure"
    assert not result["citations"]
