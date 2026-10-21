"""CareLoop's tool implementations: the real actions the agent can take.

Each tool returns {"ok", "message", "card"}. The "message" is what gets
spoken/shown; the optional "card" is rendered as a rich UI card by the
frontend (medication, schedule, adherence, alert, confirm, lists).
"""
from __future__ import annotations

from datetime import datetime

from . import db

SYSTEM_PROMPT = """You are CareLoop, a warm and careful medication companion for a
family caring for an elder (for example, a son managing his father's medicines).

You can: add medications with daily schedules, list medications, check today's
dose schedule, record doses as taken/missed/snoozed, add caregivers, escalate
alerts to caregivers, and summarize medication adherence.

Rules you must always follow:
- You are not a medical professional. Never advise changing a dosage, stopping
  a medicine, or whether a medicine is needed. If asked about side effects,
  interactions, or whether to take/skip a dose for health reasons, say clearly
  that they should consult their doctor or pharmacist.
- In a medical emergency, tell them to call emergency services immediately
  (112 in India).
- Be warm, concise, and use simple language. Keep spoken replies to 1-3
  sentences; put detail in cards.
- Today's date and time is {now}. When the user says "morning dose" or similar,
  map it to the closest scheduled time today.
- After using tools, summarize what you did in plain words.
"""


def _fmt_time(iso: str) -> str:
    return datetime.fromisoformat(iso).strftime("%I:%M %p").lstrip("0")


def build_tools(patient_id: int):
    """Return (tool_schemas, tool_implementations) bound to one patient."""

    def add_medication(name: str, dosage: str = "", times: list | None = None,
                       notes: str = "") -> dict:
        med = db.add_medication(patient_id, name, dosage, times or [], None, notes)
        times_str = ", ".join(_fmt_time(f"2000-01-01T{t}") for t in med["times"])
        return {
            "ok": True,
            "message": (f"Added {med['name']}"
                        + (f" {med['dosage']}" if med['dosage'] else "")
                        + f", scheduled daily at {times_str}."),
            "card": {"type": "medication", **med},
        }

    def list_medications() -> dict:
        meds = db.list_medications(patient_id)
        if not meds:
            return {"ok": True,
                    "message": "No medications are set up yet. Say 'add' followed by the "
                               "medication name, dosage and times — for example, 'add "
                               "Metformin 500mg at 8am and 8pm'."}
        names = "; ".join(
            f"{m['name']} {m['dosage']} at "
            + ", ".join(_fmt_time(f"2000-01-01T{t}") for t in m["times"]) for m in meds)
        return {"ok": True,
                "message": f"{len(meds)} medication(s) on schedule: {names}.",
                "card": {"type": "medication_list", "medications": meds,
                         "title": "Medications"}}

    def get_today_schedule() -> dict:
        now = datetime.now()
        doses = db.get_today_schedule(patient_id, now)
        if not doses:
            return {"ok": True, "message": "Nothing is scheduled for today yet."}
        parts = [f"{d['medication_name']} at {_fmt_time(d['scheduled_for'])} — {d['status']}"
                 for d in doses]
        return {"ok": True,
                "message": f"Today's doses: {'; '.join(parts)}.",
                "card": {"type": "schedule", "doses": doses}}

    def _pick_dose(medication_name: str = ""):
        doses = [d for d in db.get_today_schedule(patient_id, datetime.now())
                 if d["status"] in ("due", "pending", "snoozed")]
        if medication_name:
            needle = medication_name.lower()
            doses = [d for d in doses if needle in d["medication_name"].lower()
                     or d["medication_name"].lower() in needle]
        doses.sort(key=lambda d: d["scheduled_for"])
        return doses[0] if doses else None

    def record_dose(medication_name: str = "", which: str = "next",
                    event: str = "taken") -> dict:
        event = (event or "taken").lower()
        dose = _pick_dose(medication_name)
        if not dose:
            return {"ok": False,
                    "message": "There's no pending dose to record right now. "
                               "Today's schedule may already be complete."}
        db.record_dose_event(dose["dose_id"], event, source="voice")
        label = f"{dose['medication_name']} ({dose['dosage']}) at {_fmt_time(dose['scheduled_for'])}"
        if event == "taken":
            msg = f"Recorded — {label} taken. Well done."
        elif event == "missed":
            msg = (f"Recorded — {label} marked as missed. I've logged it; "
                   "try to keep the next dose on time.")
        else:
            msg = f"{label} snoozed."
        return {"ok": True, "message": msg,
                "card": {"type": "confirm", "action": event, "message": msg,
                         "dose": dose}}

    def snooze_dose(medication_name: str = "") -> dict:
        dose = _pick_dose(medication_name)
        if not dose:
            return {"ok": False, "message": "There's no pending dose to snooze right now."}
        db.record_dose_event(dose["dose_id"], "snoozed", source="voice")
        msg = (f"Snoozed {dose['medication_name']} — I'll remind you again "
                 "in 15 minutes.")
        return {"ok": True, "message": msg,
                "card": {"type": "confirm", "action": "snoozed", "message": msg,
                         "dose": dose}}

    def get_adherence(days: int = 7) -> dict:
        s = db.adherence_summary(patient_id, int(days or 7), datetime.now())
        card = {"type": "adherence", "title": "Adherence", **s}
        if s["percentage"] is None:
            return {"ok": True,
                    "message": "No doses scheduled yet, so there's no adherence to report.",
                    "card": card}
        return {"ok": True,
                "message": (f"Adherence over the last {len(s['by_day'])} days: "
                            f"{s['percentage']}% — {s['taken']} of {s['scheduled']} doses taken."),
                "card": card}

    def add_caregiver(name: str, phone: str = "", relation: str = "") -> dict:
        c = db.add_caregiver(patient_id, name, phone, relation)
        msg = (f"Added {c['name']} as a caregiver"
                 + (f" ({c['relation']})" if c['relation'] else "")
                 + ". They'll be notified if a dose is missed.")
        return {"ok": True, "message": msg,
                "card": {"type": "confirm", "action": "caregiver_added",
                         "message": msg, "caregiver": c}}

    def escalate_now(medication_name: str = "", reason: str = "") -> dict:
        dose = _pick_dose(medication_name) if medication_name else None
        msg = reason or "Manual escalation from chat."
        alert = db.create_alert(patient_id, dose["medication_id"] if dose else None,
                                "manual", f"Caregiver alert: {msg}")
        caregivers = db.list_caregivers(patient_id)
        who = ", ".join(c["name"] for c in caregivers) or "the caregiver"
        return {"ok": True,
                "message": f"Alert sent to {who}: {msg}",
                "card": {"type": "alert", "message": alert["message"],
                         "created_at": alert["created_at"], "alert": alert}}

    def get_alerts() -> dict:
        alerts = db.list_alerts(patient_id, include_acknowledged=False)
        if not alerts:
            return {"ok": True, "message": "No active alerts. Everything looks on track."}
        return {"ok": True,
                "message": f"{len(alerts)} active alert(s). The latest: {alerts[0]['message']}",
                "card": {"type": "alert_list", "alerts": alerts,
                         "title": "Alerts"}}

    schemas = [
        {"name": "add_medication", "description": "Add a medication with daily dose times.",
         "parameters": {"type": "object", "properties": {
             "name": {"type": "string", "description": "Medication name"},
             "dosage": {"type": "string", "description": "e.g. 500mg"},
             "times": {"type": "array", "items": {"type": "string"},
                       "description": "Daily times as HH:MM 24h, e.g. [\"08:00\", \"20:00\"]"},
             "notes": {"type": "string"}}, "required": ["name", "times"]}},
        {"name": "list_medications", "description": "List all active medications.",
         "parameters": {"type": "object", "properties": {}}},
        {"name": "get_today_schedule", "description": "Today's doses with their statuses.",
         "parameters": {"type": "object", "properties": {}}},
        {"name": "record_dose",
         "description": "Record the next pending dose as taken or missed.",
         "parameters": {"type": "object", "properties": {
             "medication_name": {"type": "string"},
             "which": {"type": "string", "description": "Which dose; default 'next'"},
             "event": {"type": "string", "enum": ["taken", "missed"]}}, "required": []}},
        {"name": "snooze_dose", "description": "Snooze the next pending dose by 15 minutes.",
         "parameters": {"type": "object", "properties": {
             "medication_name": {"type": "string"}}}},
        {"name": "get_adherence", "description": "Adherence summary for the last N days.",
         "parameters": {"type": "object", "properties": {
             "days": {"type": "integer", "description": "Default 7"}}}},
        {"name": "add_caregiver", "description": "Add a caregiver to notify on missed doses.",
         "parameters": {"type": "object", "properties": {
             "name": {"type": "string"}, "phone": {"type": "string"},
             "relation": {"type": "string"}}, "required": ["name"]}},
        {"name": "escalate_now", "description": "Immediately alert caregivers.",
         "parameters": {"type": "object", "properties": {
             "medication_name": {"type": "string"}, "reason": {"type": "string"}}}},
        {"name": "get_alerts", "description": "List unacknowledged alerts.",
         "parameters": {"type": "object", "properties": {}}},
    ]
    impls = {
        "add_medication": add_medication,
        "list_medications": list_medications,
        "get_today_schedule": get_today_schedule,
        "record_dose": record_dose,
        "snooze_dose": snooze_dose,
        "get_adherence": get_adherence,
        "add_caregiver": add_caregiver,
        "escalate_now": escalate_now,
        "get_alerts": get_alerts,
    }
    return schemas, impls
