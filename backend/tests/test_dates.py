from datetime import UTC, date, datetime, timedelta

import pytest
from pydantic import ValidationError

from app import schemas


@pytest.mark.parametrize("hour,day", [(18, 23), (19, 24)])
def test_case_opening_uses_indian_calendar_across_utc_midnight(monkeypatch, hour, day):
    class FrozenDateTime(datetime):
        @classmethod
        def now(cls, tz=None):
            return datetime(2026, 11, 23, hour, tzinfo=UTC).astimezone(tz)

    monkeypatch.setattr(schemas, "datetime", FrozenDateTime)
    values = {"reference": "DATE-CHECK", "title": "Calendar boundary", "summary": "Synthetic"}
    today = date(2026, 11, day)
    assert schemas.CaseCreate(**values, opened_on=today).opened_on == today
    with pytest.raises(ValidationError, match="Opening date cannot be in the future"):
        schemas.CaseCreate(**values, opened_on=today + timedelta(days=1))
