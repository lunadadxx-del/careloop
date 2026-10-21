# CareLoop — Demo Video Script (target 2:30, hard limit 3:00)

## Recording setup (do this first)

1. **Use a laptop/desktop with Chrome or Edge** (the voice UI needs the Web Speech API).
2. Start the backend: `cd backend && source .venv/bin/activate && CARELOOP_GRACE_MINUTES=30 uvicorn app.main:app --port 8000`
3. Start the frontend: `cd frontend && npm run dev` → open http://localhost:5173
4. Allow microphone access when the browser asks.
5. Record screen at 1080p (OBS, or your OS's built-in recorder). **No copyrighted music.**
6. Speak the voiceover lines slowly and clearly, in English. Pause 2 seconds between shots — it makes editing easy.

> For Shot 5 (escalation), restart the backend with `CARELOOP_GRACE_MINUTES=1`
> so you only wait ~70 seconds for the alert instead of 30 minutes.

---

## Shot 1 — Hook (0:00–0:20)

**On screen:** Title card: "CareLoop — your family's medication guardian."
**Say:** "Millions of elderly parents miss their medications every day, and their
children live in different cities. Reminder apps are just alarms — nobody follows
through. CareLoop is an agentic medication companion: it reminds, listens for
confirmation, escalates to caregivers when a dose is missed, and reports weekly
adherence. Let me show you."

## Shot 2 — Setup (0:20–0:50)

**On screen:** Setup tab. Add patient "Ramesh", relationship "father". Add caregiver
"Priya", relation "daughter".
**Say:** "Setup takes a minute. I add my father Ramesh, and my sister Priya as the
caregiver who gets notified if anything goes wrong."

## Shot 3 — Add medication by voice (0:50–1:20)

**On screen:** Chat tab. Click the mic, say: *"Add Metformin 500mg at 8am and 8pm."*
A medication card appears. Then say: *"What's due today?"* → schedule card appears.
**Say:** "Everything else happens by voice, like talking to Alexa. I add the
medication schedule conversationally, and CareLoop keeps today's plan."

## Shot 4 — Reminder + voice confirmation (1:20–1:50)

**On screen:** Dashboard tab → click **"Demo: mark next dose due"** (clearly labeled
demo control). A dose shows as *due*. Back to Chat, click mic, say: *"Yes, taken."*
Confirmation card appears.
**Say:** "When a dose is due, CareLoop reminds out loud. Dad — or anyone nearby —
just says 'taken', and it's recorded. No app to open, no buttons to find."

## Shot 5 — Missed-dose escalation (1:50–2:20)

**On screen:** (Backend restarted with 1-minute grace.) Dashboard → demo-trigger a
dose due. Wait ~70 seconds. Open the **Alerts** tab: a missed-dose alert naming
caregiver Priya.
**Say:** "Here's the part reminder apps can't do. If nobody confirms within the
grace period, CareLoop marks the dose missed and escalates — the caregiver gets an
alert with exactly what was missed and when."

## Shot 6 — Weekly adherence summary (2:20–2:45)

**On screen:** Chat tab. Say: *"Give me the weekly summary."* Adherence card with
chart appears.
**Say:** "And every week, the family gets an honest adherence summary — no guilt,
just the facts."

## Shot 7 — Tech + close (2:45–2:58)

**On screen:** Repo URL on screen: github.com/lunadadxx-del/careloop
**Say:** "CareLoop is built for the Alexa+ track as a simulated Alexa+ experience:
a React voice UI, a Python agent with real tool calling, Amazon Bedrock for the
language model, and local-first storage so sensitive health data never leaves the
machine. Thank you."

---

## Editing checklist

- [ ] Total runtime under 3:00 (aim 2:30)
- [ ] CareLoop is visible and working in every shot — no slides-only stretches
- [ ] No third-party logos, trademarks, or copyrighted music
- [ ] Voiceover in English, clearly audible
- [ ] Export 1080p, upload to YouTube as **Public** (or Unlisted → Public before submitting)
