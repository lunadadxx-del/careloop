"""Tests for the agent loop, demo provider, and Bedrock message conversion."""
from app import db
from app.agent import AgentLoop, LLMProvider, ProviderResponse, ToolCall
from app.careloop_tools import SYSTEM_PROMPT, build_tools
from app.llm import BedrockProvider, DemoProvider


def _agent_for(patient_id: int) -> AgentLoop:
    schemas, impls = build_tools(patient_id)
    return AgentLoop(provider=DemoProvider(), tools=impls, tool_schemas=schemas,
                     system_prompt=SYSTEM_PROMPT.format(now="today"))


def test_demo_add_medication_flow():
    p = db.create_patient("Ramesh")
    agent = _agent_for(p["id"])
    res = agent.chat([], "add Metformin 500mg at 8am and 8pm")
    assert "Metformin" in res["reply"]
    assert res["cards"] and res["cards"][0]["type"] == "medication"
    assert len(db.list_medications(p["id"])) == 1


def test_demo_add_medication_asks_for_times():
    p = db.create_patient("Ramesh")
    agent = _agent_for(p["id"])
    res = agent.chat([], "add medication Dolo twice daily")
    assert "what time" in res["reply"].lower()
    assert db.list_medications(p["id"]) == []


def test_demo_schedule_and_record_taken():
    p = db.create_patient("Ramesh")
    agent = _agent_for(p["id"])
    agent.chat([], "add Metformin 500mg at 8am and 8pm")
    res = agent.chat([], "what's today's schedule?")
    assert res["cards"] and res["cards"][0]["type"] == "schedule"
    res2 = agent.chat([], "yes, taken")
    assert "taken" in res2["reply"].lower()
    assert res2["cards"] and res2["cards"][0]["type"] == "confirm"


def test_demo_adherence_and_help():
    p = db.create_patient("Ramesh")
    agent = _agent_for(p["id"])
    res = agent.chat([], "help")
    assert "medication" in res["reply"].lower()
    res2 = agent.chat([], "give me the weekly summary")
    assert res2["cards"] and res2["cards"][0]["type"] == "adherence"


def test_demo_unknown_question_falls_back_gracefully():
    p = db.create_patient("Ramesh")
    agent = _agent_for(p["id"])
    res = agent.chat([], "what is the capital of France?")
    assert res["reply"]  # never empty, never crashes


def test_loop_survives_unknown_tool():
    class Rogue(LLMProvider):
        def complete(self, messages, tools, system):
            return ProviderResponse(content=None,
                                    tool_calls=[ToolCall(id="x", name="nope", arguments={})])
    p = db.create_patient("Ramesh")
    schemas, impls = build_tools(p["id"])
    agent = AgentLoop(provider=Rogue(), tools=impls, tool_schemas=schemas,
                      system_prompt="sys", max_iterations=2)
    res = agent.chat([], "hi")
    assert res["reply"]  # graceful, no exception


def test_bedrock_converse_conversion():
    provider = BedrockProvider("amazon.nova-lite-v1:0", "us-east-1")
    history = [
        {"role": "user", "content": "add meds"},
        {"role": "assistant", "content": None,
         "tool_calls": [{"id": "t1", "name": "list_medications", "arguments": {}}]},
        {"role": "tool", "tool_call_id": "t1", "name": "list_medications",
         "content": "2 medications"},
    ]
    conv = provider._to_converse_messages(history)
    assert conv[0]["role"] == "user"
    assistant = conv[1]
    assert assistant["role"] == "assistant"
    assert assistant["content"][0]["toolUse"]["toolUseId"] == "t1"
    follow = conv[2]
    assert follow["role"] == "user"
    assert follow["content"][0]["toolResult"]["toolUseId"] == "t1"
    assert "2 medications" in follow["content"][0]["toolResult"]["content"]["text"]


def test_bedrock_tool_schema_conversion():
    provider = BedrockProvider("m", "us-east-1")
    tools = [{"name": "add_medication", "description": "Add meds",
              "parameters": {"type": "object", "properties": {"name": {"type": "string"}}}}]
    spec = provider._to_bedrock_tools(tools)[0]["toolSpec"]
    assert spec["name"] == "add_medication"
    assert spec["inputSchema"]["json"]["properties"]["name"]["type"] == "string"
