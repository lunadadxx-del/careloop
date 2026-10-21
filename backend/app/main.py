"""CareLoop backend — FastAPI app.

Serves the REST API consumed by the (simulated Alexa+) web frontend, runs the
tool-calling agent, and ticks the reminder/escalation scheduler in the
background.

Run:  uvicorn app.main:app --reload        (from the backend/ directory)
"""
from __future__ import annotations

import threading
from contextlib import asynccontextmanager
from datetime import datetime

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from . import config, db, scheduler
from .agent import AgentLoop
from .careloop_tools import SYSTEM_PROMPT, build_tools
from .llm import BedrockProvider, DemoProvider

# ------------------------------------------------------------------ state ---
SESSIONS: dict[str, dict] = {}  # session_id -> {"history": [...], "patient_id": ...}
_agent_provider = None
_provider_label = "demo"


def _select_provider():
    """Pick the LLM provider. Bedrock is verified with a tiny ping; if it is
    unreachable (no creds / no model access), fall back to demo mode rather
    than serving a broken chat. The active provider is always reported at
    GET /api/demo/provider."""
    global _provider_label
    if config.LLM_PROVIDER == "bedrock":
        provider = BedrockProvider(config.BEDROCK_MODEL_ID, config.AWS_REGION)
        try:
            provider.ping()
            _provider_label = f"bedrock:{config.BEDROCK_MODEL_ID}"
            print(f"[careloop] LLM provider: {_provider_label} (verified)")
            return provider
        except Exception as e:  # noqa: BLE001 - fall back loudly, stay usable
            print(f"[careloop] Bedrock unavailable ({e}); falling back to demo mode.")
            _provider_label = f"demo (bedrock unavailable: {e})"
    else:
        print("[careloop] LLM provider: demo mode (set CARELOOP_LLM_PROVIDER=bedrock for AWS)")
    return DemoProvider()


def _get_provider():
    """Lazy provider selection: works whether or not the app lifespan ran
    (some TestClient versions skip lifespan; uvicorn runs it normally)."""
    global _agent_provider
    if _agent_provider is None:
        _agent_provider = _select_provider()
    return _agent_provider


def _scheduler_loop(stop: threading.Event):
    while not stop.wait(config.SCHEDULER_INTERVAL_SECONDS):
        try:
            scheduler.tick()
        except Exception as e:  # noqa: BLE001 - scheduler must never die
            print(f"[careloop] scheduler tick failed: {e}")


_stop_event = threading.Event()


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    global _agent_provider
    _agent_provider = _select_provider()
    thread = threading.Thread(target=_scheduler_loop, args=(_stop_event,), daemon=True)
    thread.start()
    print("[careloop] scheduler started")
    yield
    _stop_event.set()


app = FastAPI(title="CareLoop", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # local demo; tighten for any public deployment
    allow_methods=["*"],
    allow_headers=["*"],
)


# ----------------------------------------------------------------- models ---
class PatientIn(BaseModel):
    name: str
    relationship: str = ""
    timezone: str = "Asia/Kolkata"


class CaregiverIn(BaseModel):
    name: str
    phone: str = ""
    relation: str = ""


class MedicationIn(BaseModel):
    name: str
    dosage: str = ""
    times: list[str] = Field(default_factory=list)
    days: list[int] | None = None
    notes: str = ""


class DoseEventIn(BaseModel):
    event: str  # taken | missed | snoozed


class ChatIn(BaseModel):
    session_id: str = "default"
    message: str
    patient_id: int | None = None


class TriggerDueIn(BaseModel):
    patient_id: int


# ----------------------------------------------------------------- helpers --
def _require_patient(patient_id: int) -> dict:
    patient = db.get_patient(patient_id)
    if not patient:
        raise HTTPException(status_code=404, detail=f"No patient with id {patient_id}.")
    return patient


def _agent_for(patient_id: int) -> AgentLoop:
    schemas, impls = build_tools(patient_id)
    system = SYSTEM_PROMPT.format(now=datetime.now().strftime("%A, %d %B %Y, %I:%M %p"))
    return AgentLoop(provider=_get_provider(), tools=impls, tool_schemas=schemas,
                     system_prompt=system)


# ------------------------------------------------------------------ routes --
@app.get("/api/health")
def health():
    return {"status": "ok", "provider": _provider_label}


@app.get("/api/demo/provider")
def provider_info():
    return {"provider": _provider_label,
            "demo_mode": _provider_label.startswith("demo")}


@app.post("/api/patients")
def create_patient(body: PatientIn):
    try:
        return db.create_patient(body.name, body.relationship, body.timezone)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/patients")
def list_patients():
    return db.list_patients()


@app.post("/api/patients/{patient_id}/caregivers")
def add_caregiver(patient_id: int, body: CaregiverIn):
    _require_patient(patient_id)
    try:
        return db.add_caregiver(patient_id, body.name, body.phone, body.relation)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/patients/{patient_id}/caregivers")
def list_caregivers(patient_id: int):
    _require_patient(patient_id)
    return db.list_caregivers(patient_id)


@app.post("/api/patients/{patient_id}/medications")
def add_medication(patient_id: int, body: MedicationIn):
    _require_patient(patient_id)
    try:
        return db.add_medication(patient_id, body.name, body.dosage,
                                 body.times, body.days, body.notes)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/patients/{patient_id}/medications")
def list_medications(patient_id: int):
    _require_patient(patient_id)
    return db.list_medications(patient_id)


@app.get("/api/patients/{patient_id}/schedule/today")
def today_schedule(patient_id: int):
    _require_patient(patient_id)
    return db.get_today_schedule(patient_id, datetime.now())


@app.post("/api/doses/{dose_id}/event")
def dose_event(dose_id: int, body: DoseEventIn):
    try:
        return db.record_dose_event(dose_id, body.event, source="manual")
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/api/patients/{patient_id}/adherence")
def adherence(patient_id: int, days: int = 7):
    _require_patient(patient_id)
    return db.adherence_summary(patient_id, days, datetime.now())


@app.get("/api/patients/{patient_id}/alerts")
def list_alerts(patient_id: int):
    _require_patient(patient_id)
    return db.list_alerts(patient_id)


@app.post("/api/alerts/{alert_id}/acknowledge")
def acknowledge_alert(alert_id: int):
    db.acknowledge_alert(alert_id)
    return {"ok": True}


@app.post("/api/demo/trigger-due")
def trigger_due(body: TriggerDueIn):
    """Demo control: force the next pending dose into 'due' so the reminder
    flow can be shown on demand in the video."""
    _require_patient(body.patient_id)
    doses = [d for d in db.get_today_schedule(body.patient_id, datetime.now())
             if d["status"] in ("pending", "snoozed")]
    if not doses:
        raise HTTPException(status_code=400, detail="No pending doses to trigger.")
    doses.sort(key=lambda d: d["scheduled_for"])
    updated = db.set_dose_status(doses[0]["dose_id"], "due", "demo")
    return {**doses[0], "status": updated["status"]}


@app.post("/api/chat")
def chat(body: ChatIn):
    message = (body.message or "").strip()
    if not message:
        raise HTTPException(status_code=400, detail="Message is empty.")
    session = SESSIONS.setdefault(body.session_id, {"history": [], "patient_id": None})
    if body.patient_id is not None:
        _require_patient(body.patient_id)
        session["patient_id"] = body.patient_id
    patient_id = session.get("patient_id")
    if patient_id is None:
        patients = db.list_patients()
        if len(patients) == 1:
            patient_id = patients[0]["id"]
            session["patient_id"] = patient_id
    if patient_id is None:
        return {"reply": ("Welcome to CareLoop! Let's set up first — who's taking the "
                          "medications? Tell me their name in the Setup tab, then come "
                          "back and talk to me."),
                "cards": [], "speak": True}
    try:
        result = _agent_for(patient_id).chat(session["history"], message)
    except RuntimeError as e:
        raise HTTPException(status_code=502, detail=str(e))
    session["history"] = result["history"]
    return {"reply": result["reply"], "cards": result["cards"], "speak": True}
