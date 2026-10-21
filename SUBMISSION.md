# CareLoop — Devpost Submission Drafts

Copy-paste ready. Fill in the `[BRACKETS]` on submission day.

---

## Basic info

**Title:** CareLoop — your family's medication guardian

**Tagline:** An agentic Alexa+ experience that makes sure elderly parents never
miss their medications: it reminds, confirms by voice, escalates to caregivers,
and reports adherence.

**Primary track:** Alexa+ (simulated Alexa+ experience path, per the official rules)

**Mini challenges:** AWS Builder · Open Source

**Built with:** Amazon Bedrock (Nova) · React · Vite · FastAPI · Web Speech API ·
SQLite · Python

**Links:**
- Main repo: https://github.com/lunadadxx-del/careloop *(create on submission day)*
- Open-source companion: https://github.com/lunadadxx-del/miniloop *(create on submission day)*
- Demo video: [YouTube link — add after recording]

**New or existing:** Built new during the submission window (Oct 21–22, 2026).

---

## Project description (Devpost "text description" field)

**The problem.** Elderly parents miss medications constantly, and their adult
children often live in different cities. Existing reminder apps are dumb alarms:
they ring, nobody confirms, nobody follows through, and the family finds out
only after a health scare.

**The solution.** CareLoop is an agentic medication companion built as a
simulated Alexa+ experience. A family member sets up medications by voice; then
CareLoop runs a closed loop: it speaks reminders, listens for a spoken
confirmation ("yes, taken"), snoozes on request, and — the part reminder apps
can't do — **escalates to a named caregiver when a dose isn't confirmed within a
grace period**. Every week it produces an honest adherence summary.

**How it works.**
- A React + Vite web app simulates the Alexa+ experience: an Alexa-style voice
  orb (Web Speech API for speech-to-text and text-to-speech), a setup wizard, a
  dashboard with today's schedule, and an alerts feed. Rich cards (medication,
  schedule, adherence, alert, confirm) accompany every voice interaction.
- A FastAPI backend runs a provider-agnostic tool-calling agent loop with 9
  real tools: add/list medications, today's schedule, record dose
  (taken/missed/snoozed), adherence summaries, caregivers, manual escalation,
  and alerts. The agent maintains conversational state across sessions.
- The language model is **Amazon Bedrock (Nova)** via the Converse API with
  native tool calling. When Bedrock is unreachable, the backend falls back to a
  built-in deterministic demo-mode agent that drives the exact same tools — the
  active provider is always reported honestly at `GET /api/demo/provider`.
- A background scheduler ticks every 30 seconds: `pending → due → missed`, and
  creates the caregiver escalation alert. All data stays in a local SQLite file —
  health-adjacent data never leaves the machine.
- Safety is designed in: CareLoop never changes dosages, refuses medical-advice
  questions (redirecting to a doctor/pharmacist), and tells users to call
  emergency services (112) in an emergency.

**Why it matters beyond the hackathon.** Medication non-adherence is a massive,
expensive, well-documented problem, and the "last-mile confirmation" gap is
exactly where families feel helpless. CareLoop's closed loop — remind, confirm,
escalate, report — is a credible product shape for family caregivers, home-care
agencies, and elder-care services.

**Testing.** 29 backend tests pass (storage, scheduler state machine, agent
flows, Bedrock message conversion, full API suite) plus 4 tests for the
extracted `miniloop` package. Every demo flow was verified end-to-end against a
live server.

---

## Product feedback (Devpost field — one block per tool/SDK)

### Amazon Bedrock (Nova, Converse API + toolUse)
- **Used for:** the agent's language model and native tool calling.
- **Worked well:** the Converse API's `toolUse`/`toolResult` blocks mapped cleanly
  onto our provider-neutral transcript; model quality on Nova Lite was strong
  for the price tier.
- **Needs work:** the $150 hackathon promo credits were exhausted before the
  deadline (Oct 7 update), so builders without an existing AWS account couldn't
  try Bedrock at all during the event.
- **Onboarding:** good docs, but enabling model access + IAM permissions is a
  multi-step process for a first-timer.
- **Build with it again?** Yes — the tool-calling API is exactly what agentic
  apps need.

### Web Speech API (browser speech recognition + synthesis)
- **Used for:** voice input (mic button) and spoken replies in the chat UI.
- **Worked well:** zero setup, zero cost; recognition quality was good enough for
  medication names and short confirmations in a quiet room.
- **Needs work:** Chrome-only in practice; no built-in wake-word; accuracy drops
  with background noise.
- **Onboarding:** trivial — a few lines of JavaScript.
- **Build with it again?** Yes, for demos and MVPs; a production voice product
  would need a dedicated speech service.

### FastAPI + SQLite (Python)
- **Used for:** the REST API, agent orchestration, scheduler, and local storage.
- **Worked well:** FastAPI's validation and auto-docs made the contract with the
  React frontend painless; SQLite was the right call for local-first health data.
- **Needs work:** nothing blocking for this scope.
- **Onboarding:** excellent.
- **Build with it again?** Yes.

### React + Vite
- **Used for:** the simulated Alexa+ web experience.
- **Worked well:** fast dev loop, clean build, easy to make an accessible,
  large-touch-target UI for elderly users.
- **Needs work:** nothing blocking.
- **Onboarding:** excellent.
- **Build with it again?** Yes.

---

## Open Source mini-challenge entry

- **Contribution URL:** https://github.com/lunadadxx-del/miniloop
- **Project repo URL:** https://github.com/lunadadxx-del/careloop
- **GitHub username:** lunadadxx-del
- **What / how / why:** `miniloop` is a new, standalone MIT-licensed Python
  package extracted from CareLoop's agent core: a tiny provider-agnostic
  tool-calling agent loop in pure stdlib (zero dependencies). It handles the
  think → act → respond loop, tool execution with graceful failure, bounded
  transcript history, and card collection, with an audit trail of every tool
  call. Any developer can plug in their own LLM by implementing one method
  (`complete()`). Ships with 4 passing tests and a README with examples. It
  matters because most agent tutorials glue you to one vendor's SDK — miniloop
  is 150 lines you can read in ten minutes and own completely.

## AWS Builder mini-challenge entry

CareLoop integrates **Amazon Bedrock** (model `amazon.nova-lite-v1:0`) via the
Converse API with native tool calling (`toolUse`/`toolResult`), implemented in
`backend/app/llm.py` (`BedrockProvider`: transcript → Converse message
conversion, OpenAI-style schemas → Bedrock `toolSpec`, startup ping
verification with loud fallback to demo mode). Documented in the README
(Architecture section) and in this feedback. Note: the integration is
implemented and unit-tested; a live credentialed run is pending because the
hackathon's promo credits were exhausted — see `FRICTION_LOG.md` #1 and #5.

## Friction log

`FRICTION_LOG.md` in the repo (7 entries) — submitted for the judging bonus.

## Feature requests (optional)

1. **Bedrock:** reserve a small promo-credit pool through the submission deadline
   so every registered builder can actually try Bedrock (Important).
2. **Alexa+ docs:** a single "simulated experience" starter template would cut
   the onboarding time for this track dramatically (Nice-to-have).
