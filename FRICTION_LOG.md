# CareLoop — Friction Log

Kept during the build, Oct 21–22, 2026. Submitted with the hackathon entry per
the official rules (friction-log bonus). Each entry: task attempted, steps taken,
expected vs actual, severity, workaround, actionable suggestion.

---

## 1. AWS $150 promotional credits unavailable
- **Task:** Request the $150 AWS Promotional Credits advertised for hackathon builders.
- **Steps:** Read the official rules page (section 4, "How To Enter").
- **Expected:** A working request form (deadline Oct 21, 12pm PT).
- **Actual:** Oct 7 update on the same page: *"We are out of credit codes and will no
  longer be accepting credit requests."* The form was also past its deadline.
- **Severity:** Medium — no free AWS runway for Bedrock experimentation.
- **Workaround:** Architected the LLM layer with two providers: `BedrockProvider`
  (real Converse-API tool calling, verified with a startup ping when credentials
  exist) and `DemoProvider` (deterministic, drives the exact same tools, zero cloud
  cost). The API honestly reports the active provider at `GET /api/demo/provider`.
- **Suggestion:** Either fund enough codes for the announced window or remove the
  offer from the rules once exhausted, so builders don't plan around it.

## 2. System Python is externally managed (PEP 668)
- **Task:** `pip install fastapi uvicorn pytest boto3` for the backend.
- **Steps:** Ran pip directly.
- **Expected:** Packages install.
- **Actual:** `error: externally-managed-environment` — refused to install.
- **Severity:** Low.
- **Workaround:** Project-local venv at `backend/.venv`; documented in README.
- **Suggestion:** N/A (environment-specific, not an Amazon tool).

## 3. Starlette TestClient skipped FastAPI lifespan in tests
- **Task:** Run API tests with `TestClient(app)` expecting lifespan (DB init,
  provider selection, scheduler thread) to execute.
- **Steps:** Wrote tests; `/api/chat` failed with `provider is None`.
- **Expected:** Lifespan runs on `TestClient.__enter__` (documented behavior).
- **Actual:** With the installed starlette/fastapi combination (and its
  `httpx`→`httpx2` deprecation shim), lifespan did not run; routes worked but
  lifespan-initialized state was missing.
- **Severity:** Medium — would have been a production outage pattern if the chat
  route depended on lifespan ordering.
- **Workaround:** Lazy provider selection (`_get_provider()` initializes on first
  use); lifespan kept for the scheduler thread, which uvicorn runs correctly.
- **Suggestion:** N/A (third-party library behavior, pinned in requirements).

## 4. Demo-mode agent re-triggered intents after tool calls (infinite loop)
- **Task:** Rule-based demo provider driving the same tools as Bedrock.
- **Steps:** First version matched intents on the last *user* message only.
- **Expected:** One tool call, then a summary reply.
- **Actual:** After tools executed, the next loop iteration re-matched the same
  intent → repeated tool calls until `max_iterations`.
- **Severity:** High (would have spammed dose records).
- **Workaround:** The provider now detects trailing `tool` messages after the last
  user message and returns their outcome as the reply instead of re-triggering.
- **Suggestion:** N/A (own code).

## 5. Bedrock model access unverified without AWS credentials
- **Task:** Verify the Bedrock (Nova) tool-calling integration end-to-end.
- **Steps:** Implemented `BedrockProvider` with Converse API + `toolUse`; added a
  startup `ping()`.
- **Expected:** Live verification.
- **Actual:** No AWS credentials available in the build environment, and the
  hackathon promo credits are exhausted (see #1), so the live call is
  implemented and code-reviewed but not yet executed against AWS. The message
  conversion (neutral transcript → Converse `toolUse`/`toolResult`, OpenAI-style
  schemas → Bedrock `toolSpec`) is unit-tested.
- **Severity:** Medium — affects the strength of the AWS Builder mini-challenge claim.
- **Workaround:** Honest fallback: startup ping failure → loud log + demo mode;
  `/api/demo/provider` reports exactly what is active; submission documents the
  integration as implemented, unit-tested, and pending a credentialed run.
- **Suggestion:** If Amazon wants Bedrock usage in this hackathon, keep a small
  credit pool reserved through the submission deadline.

---

*(Entries continue as the build progresses.)*

## 6. FastAPI lifespan defined but never registered
- **Task:** Run DB init + provider selection + scheduler thread at server startup.
- **Steps:** Started uvicorn; `POST /api/patients` → 500 `no such table: patients`.
- **Expected:** `lifespan` runs `db.init_db()` on startup.
- **Actual:** The `lifespan` function was defined but never passed to
  `FastAPI(..., lifespan=lifespan)`. Uvicorn reported "startup complete" with no
  error, and the missing init only surfaced on the first DB write.
- **Severity:** High — the app booted "successfully" but couldn't serve anything.
- **Workaround:** Registered the lifespan; also made provider selection lazy
  (`_get_provider()`) so `/api/chat` can't depend on lifespan ordering.
- **Suggestion:** For hackathon demos, always smoke-test a write path, not just
  `/health`.

## 7. Frontend/backend card contract mismatches
- **Task:** Wire the React frontend to the FastAPI backend.
- **Steps:** Compared `cards.jsx` against actual `/api/chat` responses.
- **Expected:** Card payloads match what the UI renders.
- **Actual:** Backend nested data (`card.medication`, `card.summary`) while the UI
  read flat fields (`card.name`, `card.percentage`); two card types
  (`medication_list`, `alert_list`) had no renderer and would have shown raw JSON.
- **Severity:** Medium — caught before the demo, not by a judge.
- **Workaround:** Flattened backend card payloads to top-level fields; added the
  two missing list renderers; re-verified every card type end-to-end.
- **Suggestion:** When two builders work in parallel, verify the contract with a
  live response sample, not just the spec doc.

## 8. Day-of-week convention mismatch between frontend and backend
- **Task:** Wire the React Setup tab's day-picker chips to the medication API.
- **Steps:** Compared the frontend's `DAY_LABELS` (0 = Sunday, JS convention)
  against the backend's `day.weekday()` filter (0 = Monday).
- **Expected:** Picking "Mon" schedules Monday doses.
- **Actual:** With specific days selected, doses would land one day off — a
  silent correctness bug in a medication app.
- **Severity:** High (wrong-day doses), but caught before any real use.
- **Workaround:** Standardized on the backend's Monday=0 convention; reordered
  the frontend chips to Monday-first and documented the convention in code.
- **Suggestion:** When two builders share a contract, nail down enum semantics
  (not just shapes) in the spec — `days: [0..6]` is ambiguous without it.

## 9. TTS speaking rate too fast for elderly listeners
- **Task:** Review the voice chat's speech synthesis settings.
- **Steps:** Read `ChatTab.jsx`; recalled a prior project where `rate = 0.95`
  drew a "speaks too fast" complaint on guided speech.
- **Expected:** Calm, unhurried spoken confirmations.
- **Actual:** 0.95 is brisk for medication reminders.
- **Severity:** Low.
- **Workaround:** Lowered to 0.85.
- **Suggestion:** N/A (own tuning).
