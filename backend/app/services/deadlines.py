from datetime import date, timedelta
from typing import Any


def reminders(
    opened_on: date, rules: dict, custody_on: date | None, custody_band: str | None, supervisor_due: date | None,
) -> list[dict[str, Any]]:
    result = [
        {
            "kind": "victim_progress",
            "anchor_date": opened_on,
            "due_date": opened_on + timedelta(days=rules["victim_progress_days"]),
            "basis": "BNSS 193(3)(ii)",
            "note": "Demo uses case opening as the progress-update anchor. Confirm the correct date for review.",
        }
    ]
    if custody_on is not None and custody_band is not None:
        result.append(
            {
                "kind": "custody_review",
                "anchor_date": custody_on,
                "due_date": custody_on + timedelta(days=rules["custody_days"][custody_band]),
                "basis": "BNSS 187(3)",
                "note": "Review the confirmed remand date, counting convention, and offence band.",
            }
        )
    if supervisor_due is not None:
        result.append(
            {
                "kind": "report_target",
                "anchor_date": opened_on,
                "due_date": supervisor_due,
                "basis": "Officer-set target · BNSS 193(1)",
                "note": "Internal target for report review. The statute requires avoiding unnecessary delay.",
            }
        )
    return result
