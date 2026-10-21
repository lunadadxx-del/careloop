"""LLM providers for CareLoop.

Two providers, one interface (see agent.LLMProvider):

- ``BedrockProvider`` — calls Amazon Bedrock (Nova) with real tool calling.
  This is the documented AWS integration for the AWS Builder mini challenge.
- ``DemoProvider`` — a deterministic, rule-based demo-mode agent that drives
  the *exact same tools* as the Bedrock path. It is honest demo mode, not a
  fake: every action it takes really mutates the database. The API reports
  which provider is active at GET /api/demo/provider so the UI can badge it.
"""
from __future__ import annotations

import json
import re

from .agent import LLMProvider, ProviderResponse, ToolCall


# ------------------------------------------------------------------ Bedrock --
class BedrockProvider(LLMProvider):
    """Amazon Bedrock via the Converse API (supports tool calling / toolUse)."""

    def __init__(self, model_id: str, region: str):
        self.model_id = model_id
        self.region = region
        self._client = None

    def _client_or_raise(self):
        if self._client is None:
            try:
                import boto3
            except ImportError as e:
                raise RuntimeError(
                    "boto3 is not installed. Run: pip install boto3") from e
            try:
                import boto3 as _b
                self._client = _b.client("bedrock-runtime", region_name=self.region)
            except Exception as e:
                raise RuntimeError(
                    "Could not create the Bedrock client. Check AWS_REGION and your "
                    f"AWS credentials (AWS_ACCESS_KEY_ID / AWS_SECRET_ACCESS_KEY). ({e})"
                ) from e
        return self._client

    @staticmethod
    def _to_bedrock_tools(tools: list[dict]) -> list[dict]:
        return [{
            "toolSpec": {
                "name": t["name"],
                "description": t.get("description", ""),
                "inputSchema": {"json": t.get("parameters", {"type": "object", "properties": {}})},
            }
        } for t in tools]

    def _to_converse_messages(self, messages: list[dict]) -> list[dict]:
        converse: list[dict] = []
        pending_results: list[dict] = []

        def flush_user(text: str | None):
            content = []
            for r in pending_results:
                content.append({"toolResult": r})
            pending_results.clear()
            if text:
                content.append({"text": text})
            converse.append({"role": "user", "content": content})

        for m in messages:
            role = m.get("role")
            if role == "user":
                flush_user(m.get("content") or "")
            elif role == "assistant":
                blocks = []
                if m.get("content"):
                    blocks.append({"text": m["content"]})
                for tc in m.get("tool_calls") or []:
                    blocks.append({"toolUse": {
                        "toolUseId": tc["id"], "name": tc["name"],
                        "input": tc.get("arguments") or {}}})
                converse.append({"role": "assistant", "content": blocks})
            elif role == "tool":
                pending_results.append({
                    "toolUseId": m.get("tool_call_id", "unknown"),
                    "content": {"text": m.get("content", "")},
                })
        if pending_results:
            flush_user(None)
        return converse

    def complete(self, messages: list[dict], tools: list[dict], system: str) -> ProviderResponse:
        client = self._client_or_raise()
        try:
            resp = client.converse(
                modelId=self.model_id,
                system=[{"text": system}],
                messages=self._to_converse_messages(messages),
                toolConfig={"tools": self._to_bedrock_tools(tools)},
            )
        except Exception as e:
            raise RuntimeError(
                "Bedrock request failed. Check that model "
                f"'{self.model_id}' is enabled in region '{self.region}' and your "
                f"credentials have bedrock:InvokeModel permission. ({e})"
            ) from e
        content, tool_calls = None, []
        for block in resp["output"]["message"]["content"]:
            if "text" in block:
                content = (content or "") + block["text"]
            if "toolUse" in block:
                tu = block["toolUse"]
                tool_calls.append(ToolCall(id=tu["toolUseId"], name=tu["name"],
                                           arguments=tu.get("input") or {}))
        return ProviderResponse(content=content, tool_calls=tool_calls)

    def ping(self) -> None:
        """One tiny call to prove the integration works end-to-end."""
        self.complete([{"role": "user", "content": "Reply with exactly: ok"}],
                      [], "You are a test probe.")


# -------------------------------------------------------------- Demo mode --
class DemoProvider(LLMProvider):
    """Deterministic demo-mode provider.

    It drives the *exact same tools* as the Bedrock path, so everything it
    does really happens in the database. Intent matching is rule-based and
    intentionally simple — it exists so the demo works with zero cloud
    credentials. The active provider is always reported honestly via
    GET /api/demo/provider.
    """

    TIME_RE = re.compile(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)?", re.IGNORECASE)
    DOSAGE_RE = re.compile(
        r"(\d+(?:\.\d+)?\s*(?:mg|g|ml|mcg|tablets?|tabs?|capsules?|drops?|puffs?))",
        re.IGNORECASE)
    PHONE_RE = re.compile(r"(\+?\d[\d\s\-]{7,}\d)")
    FILLER = re.compile(
        r"\b(at|daily|every day|a day|per day|times|time|and|the|for|my|dad's|dad|"
        r"morning|afternoon|evening|night|noon|please|add|medication|medicine|med|"
        r"pill|tablet|dose)\b", re.IGNORECASE)

    def complete(self, messages: list[dict], tools: list[dict], system: str) -> ProviderResponse:
        # If tools just ran (tool messages after the last user message),
        # summarize the outcome instead of triggering the intent again.
        last_user_idx = -1
        for i, m in enumerate(messages):
            if m.get("role") == "user" and m.get("content"):
                last_user_idx = i
        trailing_tools = [m for m in messages[last_user_idx + 1:]
                          if m.get("role") == "tool" and m.get("content")]
        if trailing_tools:
            return ProviderResponse(content=trailing_tools[-1]["content"])

        text = messages[last_user_idx]["content"] if last_user_idx >= 0 else ""
        t = text.strip().lower()
        names = {tool["name"] for tool in tools}

        def call(tool_name: str, **args) -> ProviderResponse:
            if tool_name not in names:
                return ProviderResponse(content="I can't do that right now.")
            return ProviderResponse(content=None,
                                    tool_calls=[ToolCall(id="demo-1", name=tool_name,
                                                         arguments=args)])

        # greetings
        if re.match(r"^(hi|hii+|hello|hey|namaste|good (morning|afternoon|evening))\b", t):
            return ProviderResponse(
                content=("Hello! I'm CareLoop, your family's medication companion. "
                         "I can add medications, check today's schedule, record doses, "
                         "and summarize adherence. What would you like to do?"))
        # help
        if re.search(r"\bhelp\b|what can you do|how do (i|you)", t):
            return ProviderResponse(
                content=("Here's what I can do: add a medication ('add Metformin 500mg "
                         "at 8am and 8pm'), show today's schedule, record a dose as taken "
                         "or missed, snooze a reminder, add a caregiver, and give you a "
                         "weekly adherence summary. Just talk to me naturally."))
        # add caregiver
        if "caregiver" in t and re.search(r"\badd\b", t):
            rest = re.sub(r"(?i)\badd\b|\bcaregiver\b", "", text).strip(" ,")
            phone = ""
            m = self.PHONE_RE.search(rest)
            if m:
                phone = re.sub(r"[\s\-]", "", m.group(1))
                rest = self.PHONE_RE.sub("", rest)
            name = re.sub(r"(?i)\b(called|named)\b", "", rest).strip(" ,")
            if not name:
                return ProviderResponse(content="Who should I add as a caregiver? Tell me their name, e.g. 'add caregiver Priya'.")
            return call("add_caregiver", name=name, phone=phone)
        # add medication
        if re.search(r"\badd\b", t) and re.search(
                r"medication|medicine|\bmed\b|pill|tablet|\bdose\b|^add\s+\w", t) \
                and "caregiver" not in t:
            parsed = self._parse_add_medication(text)
            if parsed.get("need_clarification"):
                return ProviderResponse(content=parsed["need_clarification"])
            return call("add_medication", **parsed)
        # manual escalation
        if re.search(r"escalate|notify|send alert|alert.*caregiver", t):
            reason = re.sub(r"(?i)escalate|notify|send alert|alert|caregiver|please", "", text).strip(" ,")
            return call("escalate_now", reason=reason or "Manual escalation from chat.")
        # snooze
        if "snooz" in t:
            return call("snooze_dose", medication_name=self._med_mention(t))
        # record missed
        if re.search(r"\b(mark|record|log)\b", t) and re.search(r"\bmiss", t):
            return call("record_dose", medication_name=self._med_mention(t),
                        which="next", event="missed")
        # record taken
        if (re.match(r"^(yes|yeah|done|taken|confirm|confirmed|ok|okay)\b", t)
                or (re.search(r"\b(mark|record|log)\b", t)
                    and re.search(r"\btak(en|e)\b|\btook\b", t))
                or (re.search(r"\btaken\b|\btook\b", t) and "did" not in t)):
            return call("record_dose", medication_name=self._med_mention(t),
                        which="next", event="taken")
        # adherence summary
        if re.search(r"adher|summary|report|progress|how.*doing|week", t):
            return call("get_adherence", days=7)
        # list medications
        if re.search(r"\blist\b|\bshow\b", t) and re.search(r"medication|medicine|\bmeds?\b|pill", t):
            return call("list_medications")
        # alerts
        if re.search(r"\balerts?\b", t):
            return call("get_alerts")
        # schedule / status queries ("did dad take...", "what's due")
        if re.search(r"schedule|today|due|pending|remaining|\bleft\b|did\b.*\btake\b|status", t):
            return call("get_today_schedule")

        return ProviderResponse(
            content=("I didn't quite catch that. You can ask me about today's schedule, "
                     "tell me a dose was taken, add a medication, or ask for the weekly "
                     "summary. For example: 'add Dolo 650mg at 9am and 9pm'."))

    # -- helpers ---------------------------------------------------------
    def _med_mention(self, t: str) -> str:
        cleaned = re.sub(
            r"(?i)\b(mark|record|log|as|snooze|the|a|an|dose|medication|medicine|med|pill|"
            r"tablet|taken|took|missed|skip|skipped|yes|done|confirm|please|for|dad's|dad|my)\b",
            "", t).strip(" ,.")
        return cleaned

    def _parse_add_medication(self, text: str) -> dict:
        work = re.sub(r"(?i)^.*?\badd\b", "", text)  # drop everything up to 'add'
        dosage = ""
        m = self.DOSAGE_RE.search(work)
        if m:
            dosage = m.group(1).strip()
            work = self.DOSAGE_RE.sub(" ", work)
        times = []
        for tm in self.TIME_RE.finditer(work):
            hour, minute, mer = tm.group(1), tm.group(2) or "0", (tm.group(3) or "").lower()
            h = int(hour)
            # skip bare numbers that are clearly not times (e.g. "650" leftovers)
            if not mer and (h > 23 or (len(tm.group(1)) > 2)):
                continue
            if mer == "pm" and h < 12:
                h += 12
            if mer == "am" and h == 12:
                h = 0
            if 0 <= h <= 23 and 0 <= int(minute) <= 59:
                times.append(f"{h:02d}:{int(minute):02d}")
        # de-dupe, keep order
        times = list(dict.fromkeys(times))
        # remove time expressions textually (best effort)
        work = re.sub(r"\d{1,2}(?::\d{2})?\s*(?:am|pm)", " ", work, flags=re.IGNORECASE)
        work = re.sub(r"\b\d{1,2}:\d{2}\b", " ", work)
        name = self.FILLER.sub(" ", work)
        name = re.sub(r"\s+", " ", name).strip(" ,.")
        # strip a trailing dosage-less number fragment
        name = re.sub(r"\b\d+\s*$", "", name).strip()

        if re.search(r"(?i)twice|two times|thrice|three times|once daily", text) and not times:
            return {"need_clarification":
                    f"Got it — {name or 'that medication'}. What times should I schedule it? "
                    "For example: 'at 8am and 8pm'."}
        if not name:
            return {"need_clarification":
                    "Which medication should I add? For example: 'add Metformin 500mg at 8am and 8pm'."}
        if not times:
            return {"need_clarification":
                    f"Got it — {name}. What time(s) should I schedule it each day? "
                    "For example: 'at 8am and 8pm'."}
        return {"name": name, "dosage": dosage, "times": times}
