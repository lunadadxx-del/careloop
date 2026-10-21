"""Tests for storage: patients, medications, dose events, alerts, adherence."""
from datetime import datetime, date, timedelta

import pytest

from app import db


def test_normalize_time_variants():
    assert db.normalize_time("8am") == "08:00"
    assert db.normalize_time("8:30pm") == "20:30"
    assert db.normalize_time("20:00") == "20:00"
    assert db.normalize_time("12am") == "00:00"
    assert db.normalize_time("12pm") == "12:00"
    with pytest.raises(ValueError):
        db.normalize_time("25:00")
    with pytest.raises(ValueError):
        db.normalize_time("breakfast")


def test_patient_and_caregiver_crud():
    p = db.create_patient("Ramesh", "father")
    assert p["name"] == "Ramesh"
    assert db.get_patient(p["id"])["id"] == p["id"]
    assert db.get_patient(9999) is None
    c = db.add_caregiver(p["id"], "Priya", "+919876543210", "daughter")
    assert c["phone"] == "+919876543210"
    assert len(db.list_caregivers(p["id"])) == 1
    with pytest.raises(ValueError):
        db.create_patient("   ")
    with pytest.raises(ValueError):
        db.add_caregiver(9999, "Nobody")


def test_add_medication_validation():
    p = db.create_patient("Ramesh")
    m = db.add_medication(p["id"], "Metformin", "500mg", ["8am", "8pm"])
    assert m["times"] == ["08:00", "20:00"]
    assert m["days"] == [0, 1, 2, 3, 4, 5, 6]
    with pytest.raises(ValueError):
        db.add_medication(p["id"], "Dolo", "650mg", [])
    with pytest.raises(ValueError):
        db.add_medication(p["id"], "Dolo", "650mg", ["25:00"])
    with pytest.raises(ValueError):
        db.add_medication(p["id"], "   ", "650mg", ["9am"])


def test_today_schedule_generation():
    p = db.create_patient("Ramesh")
    db.add_medication(p["id"], "Metformin", "500mg", ["08:00", "20:00"])
    now = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
    sched = db.get_today_schedule(p["id"], now)
    assert len(sched) == 2
    assert all(d["status"] == "pending" for d in sched)
    # idempotent: calling again must not duplicate
    assert len(db.get_today_schedule(p["id"], now)) == 2


def test_record_dose_event():
    p = db.create_patient("Ramesh")
    db.add_medication(p["id"], "Metformin", "500mg", ["08:00"])
    now = datetime.now().replace(hour=7, minute=0, second=0, microsecond=0)
    dose = db.get_today_schedule(p["id"], now)[0]
    row = db.record_dose_event(dose["dose_id"], "taken", source="voice")
    assert row["status"] == "taken" and row["source"] == "voice"
    with pytest.raises(ValueError):
        db.record_dose_event(dose["dose_id"], "vaporized")


def test_alerts_and_acknowledge():
    p = db.create_patient("Ramesh")
    a = db.create_alert(p["id"], None, "missed_dose", "Missed Metformin at 8 AM")
    assert len(db.list_alerts(p["id"])) == 1
    db.acknowledge_alert(a["id"])
    assert db.list_alerts(p["id"], include_acknowledged=False) == []


def test_adherence_summary():
    p = db.create_patient("Ramesh")
    db.add_medication(p["id"], "Metformin", "500mg", ["08:00", "20:00"])
    now = datetime.now().replace(hour=21, minute=0, second=0, microsecond=0)
    doses = db.get_today_schedule(p["id"], now)
    db.record_dose_event(doses[0]["dose_id"], "taken")
    # second dose still pending but in the past -> counts as scheduled, not taken
    s = db.adherence_summary(p["id"], 1, now)
    assert s["scheduled"] == 2 and s["taken"] == 1
    assert s["percentage"] == 50.0
    assert len(s["by_day"]) == 1


def test_adherence_ignores_future_doses():
    p = db.create_patient("Ramesh")
    db.add_medication(p["id"], "Metformin", "500mg", ["23:00"])
    now = datetime.now().replace(hour=9, minute=0, second=0, microsecond=0)
    s = db.adherence_summary(p["id"], 1, now)
    assert s["scheduled"] == 0 and s["percentage"] is None


def test_weekday_filtering():
    p = db.create_patient("Ramesh")
    # Monday-only medication (0 = Monday)
    db.add_medication(p["id"], "Weekly", "1 tab", ["09:00"], days=[0])
    monday = date(2026, 10, 19)  # a Monday
    tuesday = date(2026, 10, 20)
    assert monday.weekday() == 0 and tuesday.weekday() == 1
    now_mon = datetime(2026, 10, 19, 7, 0)
    now_tue = datetime(2026, 10, 20, 7, 0)
    assert len(db.get_today_schedule(p["id"], now_mon)) == 1
    assert len(db.get_today_schedule(p["id"], now_tue)) == 0
