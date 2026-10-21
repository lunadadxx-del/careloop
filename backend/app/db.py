"""SQLite storage for CareLoop.

Local-only by design: medication data is health-adjacent, so it never leaves
this machine. No cloud sync, no analytics, no tracking.
"""
from __future__ import annotations

import json
import sqlite3
import threading
from datetime import datetime, date, timedelta

from . import config

_lock = threading.Lock()

SCHEMA = """
CREATE TABLE IF NOT EXISTS patients (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  name TEXT NOT NULL,
  relationship TEXT DEFAULT '',
  timezone TEXT DEFAULT 'Asia/Kolkata',
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS caregivers (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER NOT NULL REFERENCES patients(id),
  name TEXT NOT NULL,
  phone TEXT DEFAULT '',
  relation TEXT DEFAULT ''
);
CREATE TABLE IF NOT EXISTS medications (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER NOT NULL REFERENCES patients(id),
  name TEXT NOT NULL,
  dosage TEXT DEFAULT '',
  notes TEXT DEFAULT '',
  times_json TEXT NOT NULL DEFAULT '[]',
  days_json TEXT NOT NULL DEFAULT '[0,1,2,3,4,5,6]',
  active INTEGER NOT NULL DEFAULT 1,
  created_at TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS dose_events (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  medication_id INTEGER NOT NULL REFERENCES medications(id),
  scheduled_for TEXT NOT NULL,
  status TEXT NOT NULL DEFAULT 'pending',
  decided_at TEXT,
  source TEXT DEFAULT '',
  UNIQUE(medication_id, scheduled_for)
);
CREATE TABLE IF NOT EXISTS alerts (
  id INTEGER PRIMARY KEY AUTOINCREMENT,
  patient_id INTEGER NOT NULL REFERENCES patients(id),
  medication_id INTEGER REFERENCES medications(id),
  type TEXT NOT NULL,
  message TEXT NOT NULL,
  created_at TEXT NOT NULL,
  acknowledged INTEGER NOT NULL DEFAULT 0
);
"""

ALL_DAYS = [0, 1, 2, 3, 4, 5, 6]


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _lock, _connect() as conn:
        conn.executescript(SCHEMA)


def _d(row) -> dict | None:
    return dict(row) if row is not None else None


def _now_iso() -> str:
    return datetime.now().replace(microsecond=0).isoformat()


def normalize_time(value: str) -> str:
    """Accept '8', '8am', '8:30pm', '08:00', '20:00' -> 'HH:MM' (24h)."""
    v = (value or "").strip().lower().replace(" ", "")
    if not v:
        raise ValueError("Empty time value.")
    meridiem = None
    for suffix in ("am", "pm"):
        if v.endswith(suffix):
            meridiem = suffix
            v = v[: -len(suffix)]
            break
    parts = v.split(":")
    try:
        hour = int(parts[0])
        minute = int(parts[1]) if len(parts) > 1 else 0
    except ValueError:
        raise ValueError(f"Could not understand time '{value}'. Use e.g. 8am or 20:30.")
    if meridiem == "am" and hour == 12:
        hour = 0
    elif meridiem == "pm" and hour < 12:
        hour += 12
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Time '{value}' is out of range.")
    return f"{hour:02d}:{minute:02d}"


# ---------------------------------------------------------------- patients ---
def create_patient(name: str, relationship: str = "", timezone: str = "Asia/Kolkata") -> dict:
    name = (name or "").strip()
    if not name:
        raise ValueError("Patient name is required.")
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO patients(name, relationship, timezone, created_at) VALUES (?,?,?,?)",
            (name, relationship or "", timezone or "Asia/Kolkata", _now_iso()),
        )
        return _d(conn.execute("SELECT * FROM patients WHERE id=?", (cur.lastrowid,)).fetchone())


def list_patients() -> list[dict]:
    with _lock, _connect() as conn:
        return [_d(r) for r in conn.execute("SELECT * FROM patients ORDER BY id").fetchall()]


def get_patient(patient_id: int) -> dict | None:
    with _lock, _connect() as conn:
        return _d(conn.execute("SELECT * FROM patients WHERE id=?", (patient_id,)).fetchone())


# -------------------------------------------------------------- caregivers ---
def add_caregiver(patient_id: int, name: str, phone: str = "", relation: str = "") -> dict:
    if not get_patient(patient_id):
        raise ValueError(f"No patient with id {patient_id}.")
    name = (name or "").strip()
    if not name:
        raise ValueError("Caregiver name is required.")
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO caregivers(patient_id, name, phone, relation) VALUES (?,?,?,?)",
            (patient_id, name, phone or "", relation or ""),
        )
        return _d(conn.execute("SELECT * FROM caregivers WHERE id=?", (cur.lastrowid,)).fetchone())


def list_caregivers(patient_id: int) -> list[dict]:
    with _lock, _connect() as conn:
        return [_d(r) for r in conn.execute(
            "SELECT * FROM caregivers WHERE patient_id=? ORDER BY id", (patient_id,)).fetchall()]


# ------------------------------------------------------------- medications ---
def add_medication(patient_id: int, name: str, dosage: str = "",
                   times: list[str] | None = None, days: list[int] | None = None,
                   notes: str = "") -> dict:
    if not get_patient(patient_id):
        raise ValueError(f"No patient with id {patient_id}.")
    name = (name or "").strip()
    if not name:
        raise ValueError("Medication name is required.")
    norm_times = [normalize_time(t) for t in (times or [])]
    if not norm_times:
        raise ValueError("At least one daily time is required (e.g. 8am, 8pm).")
    norm_days = sorted(set(int(d) for d in (days if days is not None else ALL_DAYS)))
    if not norm_days or any(d < 0 or d > 6 for d in norm_days):
        raise ValueError("Days must be numbers 0 (Monday) to 6 (Sunday).")
    with _lock, _connect() as conn:
        cur = conn.execute(
            """INSERT INTO medications(patient_id, name, dosage, notes, times_json, days_json, created_at)
               VALUES (?,?,?,?,?,?,?)""",
            (patient_id, name, dosage or "", notes or "",
             json.dumps(sorted(set(norm_times))), json.dumps(norm_days), _now_iso()),
        )
        row = _d(conn.execute("SELECT * FROM medications WHERE id=?", (cur.lastrowid,)).fetchone())
    return _med_dict(row)


def _med_dict(row: dict) -> dict:
    row = dict(row)
    row["times"] = json.loads(row.pop("times_json"))
    row["days"] = json.loads(row.pop("days_json"))
    return row


def list_medications(patient_id: int, active_only: bool = True) -> list[dict]:
    q = "SELECT * FROM medications WHERE patient_id=?"
    if active_only:
        q += " AND active=1"
    q += " ORDER BY name"
    with _lock, _connect() as conn:
        return [_med_dict(r) for r in conn.execute(q, (patient_id,)).fetchall()]


def get_medication(medication_id: int) -> dict | None:
    with _lock, _connect() as conn:
        row = conn.execute("SELECT * FROM medications WHERE id=?", (medication_id,)).fetchone()
        return _med_dict(row) if row else None


def find_medication_by_name(patient_id: int, name: str) -> dict | None:
    needle = (name or "").strip().lower()
    for med in list_medications(patient_id):
        if needle and (needle in med["name"].lower() or med["name"].lower() in needle):
            return med
    return None


# ------------------------------------------------------------ dose events ---
def ensure_dose_events(patient_id: int, day: date) -> None:
    """Create 'pending' dose events for every active medication/time on `day`."""
    for med in list_medications(patient_id):
        if day.weekday() not in med["days"]:
            continue
        for t in med["times"]:
            hh, mm = int(t[:2]), int(t[3:5])
            sched = datetime(day.year, day.month, day.day, hh, mm).isoformat(timespec="minutes")
            with _lock, _connect() as conn:
                conn.execute(
                    "INSERT OR IGNORE INTO dose_events(medication_id, scheduled_for, status) VALUES (?,?, 'pending')",
                    (med["id"], sched),
                )


def get_today_schedule(patient_id: int, now: datetime) -> list[dict]:
    ensure_dose_events(patient_id, now.date())
    prefix = now.date().isoformat()
    with _lock, _connect() as conn:
        rows = conn.execute(
            """SELECT d.id AS dose_id, d.medication_id, m.name AS medication_name,
                      m.dosage AS dosage, d.scheduled_for, d.status, d.decided_at, d.source
               FROM dose_events d JOIN medications m ON m.id = d.medication_id
               WHERE m.patient_id=? AND d.scheduled_for LIKE ? AND m.active=1
               ORDER BY d.scheduled_for""",
            (patient_id, prefix + "%"),
        ).fetchall()
        return [_d(r) for r in rows]


def set_dose_status(dose_id: int, status: str, source: str = "") -> dict | None:
    with _lock, _connect() as conn:
        conn.execute(
            "UPDATE dose_events SET status=?, decided_at=?, source=? WHERE id=?",
            (status, _now_iso(), source, dose_id),
        )
        return _d(conn.execute("SELECT * FROM dose_events WHERE id=?", (dose_id,)).fetchone())


USER_EVENTS = {"taken", "missed", "snoozed"}


def record_dose_event(dose_id: int, event: str, source: str = "manual") -> dict:
    event = (event or "").lower()
    if event not in USER_EVENTS:
        raise ValueError(f"Event must be one of {sorted(USER_EVENTS)}.")
    row = set_dose_status(dose_id, event, source)
    if not row:
        raise ValueError(f"No dose with id {dose_id}.")
    return row


# ------------------------------------------------------------------ alerts ---
def create_alert(patient_id: int, medication_id: int | None, type: str, message: str) -> dict:
    with _lock, _connect() as conn:
        cur = conn.execute(
            "INSERT INTO alerts(patient_id, medication_id, type, message, created_at) VALUES (?,?,?,?,?)",
            (patient_id, medication_id, type, message, _now_iso()),
        )
        return _d(conn.execute("SELECT * FROM alerts WHERE id=?", (cur.lastrowid,)).fetchone())


def list_alerts(patient_id: int, include_acknowledged: bool = True) -> list[dict]:
    q = "SELECT * FROM alerts WHERE patient_id=?"
    if not include_acknowledged:
        q += " AND acknowledged=0"
    q += " ORDER BY created_at DESC"
    with _lock, _connect() as conn:
        return [_d(r) for r in conn.execute(q, (patient_id,)).fetchall()]


def acknowledge_alert(alert_id: int) -> None:
    with _lock, _connect() as conn:
        conn.execute("UPDATE alerts SET acknowledged=1 WHERE id=?", (alert_id,))


# --------------------------------------------------------------- adherence ---
def adherence_summary(patient_id: int, days: int, now: datetime) -> dict:
    days = max(1, min(days, 30))
    # Don't judge days before tracking started: a new user's first week
    # shouldn't show past days as missed.
    patient = get_patient(patient_id)
    start_day = now.date() - timedelta(days=days - 1)
    if patient and patient.get("created_at"):
        created_day = datetime.fromisoformat(patient["created_at"]).date()
        start_day = max(start_day, created_day)
    by_day, taken_total, scheduled_total = [], 0, 0
    day = start_day
    while day <= now.date():
        ensure_dose_events(patient_id, day)
        with _lock, _connect() as conn:
            rows = conn.execute(
                """SELECT d.status, d.scheduled_for FROM dose_events d
                   JOIN medications m ON m.id = d.medication_id
                   WHERE m.patient_id=? AND d.scheduled_for LIKE ? AND m.active=1""",
                (patient_id, day.isoformat() + "%"),
            ).fetchall()
        # Doses scheduled in the future don't count against adherence yet.
        rows = [r for r in rows if datetime.fromisoformat(r["scheduled_for"]) <= now]
        scheduled = len(rows)
        taken = sum(1 for r in rows if r["status"] == "taken")
        by_day.append({"date": day.isoformat(), "taken": taken, "scheduled": scheduled})
        taken_total += taken
        scheduled_total += scheduled
        day += timedelta(days=1)
    pct = round(100.0 * taken_total / scheduled_total, 1) if scheduled_total else None
    return {"percentage": pct, "by_day": by_day, "taken": taken_total, "scheduled": scheduled_total}
