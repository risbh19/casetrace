from app.services.extraction import confirm_ambiguous_accounts, extract


def test_regex_extracts_unique_values_and_ignores_invalid_dates():
    text = (
        "दिनांक 2024-02-30 और 29/02/2024। खाता संख्या 9000012345, "
        "IFSC demo0000001. INR 1,02,450.20 via demo.user@test. Phone +91 90000 76543. "
        "Phone +91 90000 76543. email person@example.com. Amount INR 12345678901234567890123456."
    )
    assert set(extract(text)) == {
        ("date", "2024-02-29", "regex"), ("phone", "9000076543", "regex"),
        ("account", "9000012345", "regex"), ("ifsc", "DEMO0000001", "regex"),
        ("amount", "102450.20", "regex"), ("upi", "demo.user@test", "regex"),
    }


def test_ambiguous_accounts_require_exact_source_digits():
    evidence = "account 1234 5678 90"
    assert not confirm_ambiguous_accounts(evidence, lambda *_: "1234567899")
    assert confirm_ambiguous_accounts(evidence, lambda *_: "1234567890") == [
        ("account", "1234567890", "local-model"),
    ]


def test_labeled_accounts_tolerate_ocr_spacing_without_inventing_digits():
    text = "खाता संखया 900001 2345\naccount 1234 5678 90\naccount 123456 123456 123456 123456"
    accounts = {value for kind, value, _ in extract(text) if kind == "account"}
    assert accounts == {"9000012345", "1234567890"}
