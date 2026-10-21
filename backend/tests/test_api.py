"""End-to-end API tests through FastAPI's TestClient."""
from fastapi.testclient import TestClient

from app.main import app


def _client():
    return TestClient(app)


def test_health_and_provider():
    with _client() as c:
        assert c.get("/api/health").json()["status"] == "ok"
        assert "demo" in c.get("/api/demo/provider").json()["provider"]


def test_patient_medication_flow():
    with _client() as c:
        p = c.post("/api/patients", json={"name": "Ramesh", "relationship": "father"}).json()
        assert p["id"] > 0
        assert c.get("/api/patients").json()[0]["name"] == "Ramesh"

        bad = c.post(f"/api/patients/{p['id']}/medications",
                     json={"name": "Dolo", "dosage": "650mg", "times": []})
        assert bad.status_code == 400  # times required

        m = c.post(f"/api/patients/{p['id']}/medications",
                   json={"name": "Metformin", "dosage": "500mg",
                         "times": ["08:00", "20:00"]}).json()
        assert m["times"] == ["08:00", "20:00"]

        sched = c.get(f"/api/patients/{p['id']}/schedule/today").json()
        assert len(sched) == 2

        ev = c.post(f"/api/doses/{sched[0]['dose_id']}/event",
                    json={"event": "taken"}).json()
        assert ev["status"] == "taken"

        bad_ev = c.post(f"/api/doses/{sched[1]['dose_id']}/event",
                        json={"event": "vaporized"})
        assert bad_ev.status_code == 400

        adh = c.get(f"/api/patients/{p['id']}/adherence?days=7").json()
        assert adh["taken"] >= 1


def test_chat_add_and_confirm_flow():
    with _client() as c:
        p = c.post("/api/patients", json={"name": "Ramesh"}).json()
        r1 = c.post("/api/chat", json={"patient_id": p["id"],
                                       "message": "add Metformin 500mg at 8am and 8pm"}).json()
        assert "Metformin" in r1["reply"]
        assert r1["cards"][0]["type"] == "medication"

        r2 = c.post("/api/chat", json={"session_id": "default",
                                       "message": "what's due today?"}).json()
        assert r2["cards"][0]["type"] == "schedule"

        r3 = c.post("/api/chat", json={"message": "yes"}).json()
        assert "taken" in r3["reply"].lower()


def test_chat_without_patient_prompts_setup():
    with _client() as c:
        r = c.post("/api/chat", json={"session_id": "fresh", "message": "hello"}).json()
        assert "set up" in r["reply"].lower()


def test_demo_trigger_due_and_alerts():
    with _client() as c:
        p = c.post("/api/patients", json={"name": "Ramesh"}).json()
        c.post(f"/api/patients/{p['id']}/medications",
               json={"name": "Metformin", "dosage": "500mg", "times": ["08:00"]})
        dose = c.post("/api/demo/trigger-due", json={"patient_id": p["id"]}).json()
        assert dose["status"] == "due"
        assert c.get(f"/api/patients/{p['id']}/alerts").json() == []


def test_caregiver_crud():
    with _client() as c:
        p = c.post("/api/patients", json={"name": "Ramesh"}).json()
        cg = c.post(f"/api/patients/{p['id']}/caregivers",
                    json={"name": "Priya", "phone": "+911234567890",
                          "relation": "daughter"}).json()
        assert cg["name"] == "Priya"
        assert len(c.get(f"/api/patients/{p['id']}/caregivers").json()) == 1


def test_404s():
    with _client() as c:
        assert c.get("/api/patients/9999/schedule/today").status_code == 404
        assert c.get("/api/patients/9999/adherence").status_code == 404
