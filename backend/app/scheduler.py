"""Reminder + escalation engine.

A background thread ticks this every CARELOOP_SCHEDULER_INTERVAL seconds:

- pending -> due        when the scheduled time arrives
- due -> missed         when GRACE_MINUTES pass with no confirmation;
                        creates a caregiver alert (the escalation)
- snoozed -> due        SNOOZE_MINUTES after the snooze

``tick()`` is a pure function of (db, now) so it is fully unit-testable.
"""
from __future__ import annotations

from datetime import datetime, timedelta

from . import config, db


def tick(now: datetime | None = None) -> list[dict]:
    now = now or datetime.now()
    transitions: list[dict] = []
    for patient in db.list_patients():
        for dose in db.get_today_schedule(patient["id"], now):
            sched = datetime.fromisoformat(dose["scheduled_for"])
            status = dose["status"]
            if status == "pending" and now >= sched:
                db.set_dose_status(dose["dose_id"], "due", "system")
                transitions.append({"dose_id": dose["dose_id"], "to": "due"})
            elif status == "due" and now >= sched + timedelta(minutes=config.GRACE_MINUTES):
                db.set_dose_status(dose["dose_id"], "missed", "system")
                caregivers = db.list_caregivers(patient["id"])
                who = ", ".join(c["name"] for c in caregivers) or "the caregiver"
                message = (
                    f"Missed dose: {dose['medication_name']}"
                    + (f" ({dose['dosage']})" if dose["dosage"] else "")
                    + f" scheduled at {sched.strftime('%I:%M %p').lstrip('0')} was not "
                    f"confirmed within {config.GRACE_MINUTES} minutes. "
                    f"Notifying {who}."
                )
                db.create_alert(patient["id"], dose["medication_id"], "missed_dose", message)
                transitions.append({"dose_id": dose["dose_id"], "to": "missed"})
            elif status == "snoozed" and dose.get("decided_at"):
                wake = datetime.fromisoformat(dose["decided_at"]) + timedelta(
                    minutes=config.SNOOZE_MINUTES)
                if now >= wake:
                    db.set_dose_status(dose["dose_id"], "due", "system")
                    transitions.append({"dose_id": dose["dose_id"], "to": "due"})
    return transitions
