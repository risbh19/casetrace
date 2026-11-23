import importlib.util
from io import BytesIO
from pathlib import Path

import pytest
from cryptography.exceptions import InvalidTag

spec = importlib.util.spec_from_file_location("backup", Path(__file__).parents[2] / "scripts/backup.py")
backup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(backup)


def test_backup_round_trip_and_tampering_detection():
    content = b"synthetic database bytes" * 100_000
    encrypted = BytesIO()
    key = bytes(range(32))
    backup.encrypt_stream(BytesIO(content), encrypted, key)
    assert content[:200] not in encrypted.getvalue()
    plain = BytesIO()
    backup.decrypt_stream(BytesIO(encrypted.getvalue()), plain, key)
    assert plain.getvalue() == content
    damaged = bytearray(encrypted.getvalue())
    damaged[-1] ^= 1
    with pytest.raises(InvalidTag):
        backup.decrypt_stream(BytesIO(damaged), None, key)
