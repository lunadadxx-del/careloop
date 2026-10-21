"""Tests for the reminder/escalation scheduler tick()."""
from datetime import datetime, timedelta

from app import config, db, scheduler


def _setup_one_med(when: datetime, times=("08:00",)):
    p = db.create_patient("Ramesh")
    db.add_caregiver(p["id"], "Priya", "+911234567890", "daughter")
    db.add_medication(p["id"], "Metformin", "500mg", list(times))
    return p


def test_pending_becomes_due():
    p = _setup_one_med(datetime.now())
    now = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    # force the 08:00 dose to exist today
    trans = scheduler.tick(now)
    assert any(t["to"] == "due" for t in trans)
    sched = db.get_today_schedule(p["id"], now)
    assert sched[0]["status"] == "due"


def test_due_becomes_missed_with_escalation():
    p = _setup_one_med(datetime.now())
    sched_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    db.get_today_schedule(p["id"], sched_time)  # generate events
    due_time = sched_time + timedelta(minutes=1)
    scheduler.tick(due_time)
    late = sched_time + timedelta(minutes=config.GRACE_MINUTES + 1)
    trans = scheduler.tick(late)
    assert any(t["to"] == "missed" for t in trans)
    alerts = db.list_alerts(p["id"])
    assert len(alerts) == 1
    assert alerts[0]["type"] == "missed_dose"
    assert "Priya" in alerts[0]["message"]  # caregiver named in escalation


def test_taken_dose_never_escalates():
    p = _setup_one_med(datetime.now())
    sched_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    doses = db.get_today_schedule(p["id"], sched_time)
    db.record_dose_event(doses[0]["dose_id"], "taken", source="voice")
    late = sched_time + timedelta(minutes=config.GRACE_MINUTES + 60)
    trans = scheduler.tick(late)
    assert trans == []
    assert db.list_alerts(p["id"]) == []


def test_snooze_rearms():
    p = _setup_one_med(datetime.now())
    sched_time = datetime.now().replace(hour=8, minute=0, second=0, microsecond=0)
    doses = db.get_today_schedule(p["id"], sched_time)
    db.record_dose_event(doses[0]["dose_id"], "snoozed", source="voice")
    # Backdate the snooze decision so the re-arm window has passed
    # (record_dose_event stamps wall-clock time, which is after sched_time).
    import sqlite3
    from app import config as _config
    conn = sqlite3.connect(_config.DB_PATH)
    conn.execute("UPDATE dose_events SET decided_at=? WHERE id=?",
                 (sched_time.isoformat(), doses[0]["dose_id"]))
    conn.commit()
    conn.close()
    wake = sched_time + timedelta(minutes=config.SNOOZE_MINUTES + 1)
    trans = scheduler.tick(wake)
    assert any(t["to"] == "due" for t in trans)


def test_future_dose_untouched():
    p = _setup_one_med(datetime.now(), times=("23:00",))
    now = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    assert scheduler.tick(now) == []
