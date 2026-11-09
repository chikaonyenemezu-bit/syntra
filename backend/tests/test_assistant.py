import json

import httpx
import pytest
from sqlalchemy import func, select

from app.config import settings
from app.models.audit_event import AuditEvent
from app.models.user import User
from app.services import assistant
from app.services.assistant_tools import TOOLS, ToolBox
from app.services.health_monitor import Heartbeat, record_heartbeat
from app.models.system import System


class FakeLLM:
    """Scripted model API: returns the given responses in order and records every request."""

    def __init__(self, responses):
        self.responses, self.requests = list(responses), []

    def __call__(self, request: httpx.Request) -> httpx.Response:
        self.requests.append({"url": str(request.url), "headers": dict(request.headers),
                              "body": json.loads(request.content)})
        status, body = self.responses.pop(0)
        return httpx.Response(status, json=body)


@pytest.fixture()
def use_llm(monkeypatch):
    def _use(provider, responses, **overrides):
        fake = FakeLLM(responses)
        monkeypatch.setattr(settings, "llm_provider", "auto")
        monkeypatch.setattr(settings, f"{provider}_api_key", "test-key-not-real")
        for k, v in overrides.items():
            monkeypatch.setattr(settings, k, v)
        monkeypatch.setattr(assistant, "transport", httpx.MockTransport(fake))
        return fake
    return _use


def user(db, name="it.ops") -> User:
    return db.scalars(select(User).where(User.username == name)).one()


def claude_text(text, i=50, o=80):
    return 200, {"content": [{"type": "text", "text": text}], "stop_reason": "end_turn",
                 "usage": {"input_tokens": i, "output_tokens": o}}


def claude_tools(*calls, i=100, o=20):
    return 200, {"content": [{"type": "text", "text": "Let me check."}] +
                 [{"type": "tool_use", "id": f"toolu_{n}", "name": name, "input": args}
                  for n, (name, args) in enumerate(calls)],
                 "stop_reason": "tool_use", "usage": {"input_tokens": i, "output_tokens": o}}


# --- without a model ---------------------------------------------------------------------------

def test_retrieval_only_without_api_key(db, monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "groq_api_key", "")
    assert assistant.status()["mode"] == "retrieval"
    q = assistant.ask(db, user(db), "Who closes an incident on a GxP system?")
    db.commit()
    assert (q.mode, q.answer, q.grounded, q.number) == ("retrieval", None, False, "AQ-000001")
    passages = json.loads(q.passages)
    assert passages[0]["ref"].startswith("SOP-ITO-001")
    event = db.scalars(select(AuditEvent).where(AuditEvent.action == "assistant.asked")).one()
    assert event.entity_id == "AQ-000001" and "Who closes" in event.details


# --- Claude --------------------------------------------------------------------------------------

def test_claude_tool_loop_with_verified_citations(db, use_llm):
    record_heartbeat(db, db.scalars(select(System).where(System.code == "MES-01")).one(),
                     Heartbeat("down", 0, 1.0, "EBR service unreachable"))
    fake = use_llm("anthropic", [
        claude_tools(("search_knowledge", {"query": "MES down paper batch record"}),
                     ("get_system_status", {"system_code": "MES-01"})),
        claude_text("Syntra shows MES-01 as down. Inform QA immediately [RB-MES-001 §2]; QA closes the "
                    "incident [SOP-ITO-001 §7]. See also [SOP-ITO-009 §2]."),
    ])
    q = assistant.ask(db, user(db), "MES-01 is down, what now?")
    db.commit()

    first, second = fake.requests
    assert first["url"] == "https://api.anthropic.com/v1/messages"
    assert first["headers"]["x-api-key"] == "test-key-not-real"
    assert first["headers"]["anthropic-version"] == settings.anthropic_version
    assert first["body"]["model"] == "claude-sonnet-5-5"
    assert {t["name"] for t in first["body"]["tools"]} == {t.name for t in TOOLS}
    assert "input_schema" in first["body"]["tools"][0]
    assert "<documents>" in first["body"]["messages"][-1]["content"]           # retrieved sections included
    assert "Never say that you acknowledged" in first["body"]["system"]
    results = second["body"]["messages"][-1]["content"]
    assert [r["tool_use_id"] for r in results] == ["toolu_0", "toolu_1"]
    assert json.loads(results[1]["content"])["systems"][0]["status"] == "down"

    assert (q.mode, q.provider, q.model) == ("llm", "anthropic", "claude-sonnet-5-5")
    cites = {c["ref"]: c["valid"] for c in json.loads(q.citations)}
    assert cites == {"RB-MES-001 §2": True, "SOP-ITO-001 §7": True, "SOP-ITO-009 §2": False}
    assert q.grounded and (q.input_tokens, q.output_tokens) == (150, 100)
    tools = json.loads(q.tool_calls)
    assert [t["name"] for t in tools] == ["search_knowledge", "get_system_status"]
    assert tools[1]["summary"] == "MES-01: down"
    event = db.scalars(select(AuditEvent).where(AuditEvent.action == "assistant.asked")).one()
    assert json.loads(event.details)["unverified_citations"] == ["SOP-ITO-009 §2"]


def test_tool_rounds_are_limited(db, use_llm):
    fake = use_llm("anthropic", [claude_tools(("search_knowledge", {"query": "x"})),
                                 claude_text("Final answer [SOP-ITO-002 §5].")], llm_max_tool_rounds=1)
    q = assistant.ask(db, user(db), "Who approves changes?")
    assert fake.requests[0]["body"]["tool_choice"] == {"type": "auto"}
    assert fake.requests[1]["body"]["tool_choice"] == {"type": "none"}
    assert q.answer == "Final answer [SOP-ITO-002 §5]."


def test_model_error_falls_back_to_retrieval(db, use_llm):
    use_llm("anthropic", [(401, {"type": "error", "error": {"type": "authentication_error",
                                                            "message": "invalid x-api-key"}})])
    q = assistant.ask(db, user(db), "How do I sign a change request?")
    assert q.mode == "retrieval" and q.answer is None
    assert "HTTP 401 (the API key is invalid)" in q.error
    assert "SOP-ITO-004 §3" in [p["ref"] for p in json.loads(q.passages)][:3]


def test_history_is_sent(db, use_llm):
    fake = use_llm("anthropic", [claude_text("Yes [SOP-ITO-002 §5].")])
    assistant.ask(db, user(db), "And for a minor change?",
                  [{"question": "Who approves GxP changes?", "answer": "System Owner and QA."}])
    roles = [m["role"] for m in fake.requests[0]["body"]["messages"]]
    assert roles == ["user", "assistant", "user"]


# --- OpenAI ---------------------------------------------------------------------------------------

def test_openai_responses_tool_loop(db, use_llm):
    fake = use_llm("openai", [
        (200, {"id": "resp_1", "output": [{"type": "function_call", "call_id": "call_9", "name": "search_recalls",
                                           "arguments": json.dumps({"query": "metformin"})}],
               "usage": {"input_tokens": 90, "output_tokens": 10}}),
        (200, {"id": "resp_2", "output": [{"type": "message", "content": [
            {"type": "output_text", "text": "No metformin recalls are stored in Syntra."}]}],
               "usage": {"input_tokens": 120, "output_tokens": 15}}),
    ])
    q = assistant.ask(db, user(db), "Any metformin recalls?")
    first, second = fake.requests
    assert first["url"] == "https://api.openai.com/v1/responses"
    assert first["headers"]["authorization"] == "Bearer test-key-not-real"
    assert first["body"]["tools"][0]["type"] == "function" and "parameters" in first["body"]["tools"][0]
    assert second["body"]["previous_response_id"] == "resp_1"
    assert second["body"]["input"][0]["type"] == "function_call_output"
    assert second["body"]["input"][0]["call_id"] == "call_9"
    assert second["body"]["instructions"] == first["body"]["instructions"]
    assert (q.mode, q.provider, q.model) == ("llm", "openai", "gpt-6-luna")
    assert q.answer.startswith("No metformin") and (q.input_tokens, q.output_tokens) == (210, 25)
    assert q.grounded  # answered from live data


# --- tools -----------------------------------------------------------------------------------------

def test_tools_never_write(db):
    def counts():
        return [db.scalar(select(func.count()).select_from(t)) for t in (AuditEvent,)]
    before = counts()
    box = ToolBox(db)
    for name, args in [("search_knowledge", {"query": "change approval"}), ("get_system_status", {}),
                       ("list_incidents", {"status": "all"}), ("get_incident", {"number": "INC-999999"}),
                       ("list_change_requests", {"status": "all"}), ("search_recalls", {"query": "tablets"})]:
        json.loads(box.execute(name, args))
    db.flush()
    assert counts() == before
    assert not db.new and not db.dirty and not db.deleted


def test_bad_tool_calls_are_contained(db):
    box = ToolBox(db)
    assert "Unknown tool" in box.execute("delete_everything", {})
    assert "Invalid arguments" in box.execute("get_incident", {"number": "INC-1", "force": True})
    assert [r.ok for r in box.runs] == [False, False]


# --- API -------------------------------------------------------------------------------------------

def test_ask_api_and_feedback(client, login, monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "groq_api_key", "")
    v, ops = login("viewer"), login("it.ops")
    assert client.get("/api/assistant/status", headers=v).json()["documents"] == 11
    assert client.post("/api/assistant/ask", json={"question": "?"}, headers=v).status_code == 422
    a = client.post("/api/assistant/ask", json={"question": "What is a Class I recall?"}, headers=v).json()
    assert a["mode"] == "retrieval" and a["passages"][0]["doc_id"] == "RB-INT-001"
    n = a["number"]
    assert client.post(f"/api/assistant/queries/{n}/feedback", json={"rating": "helpful"},
                       headers=ops).status_code == 403
    r = client.post(f"/api/assistant/queries/{n}/feedback", json={"rating": "incorrect", "comment": "Too vague"},
                    headers=v).json()
    assert r["feedback"] == "incorrect"
    assert [q["number"] for q in client.get("/api/assistant/queries", headers=v).json()] == [n]
    assert client.get("/api/assistant/queries", headers=ops).json() == []


def test_question_about_a_record_finds_its_runbook(db, monkeypatch):
    monkeypatch.setattr(settings, "anthropic_api_key", "")
    monkeypatch.setattr(settings, "openai_api_key", "")
    monkeypatch.setattr(settings, "groq_api_key", "")
    record_heartbeat(db, db.scalars(select(System).where(System.code == "LIMS-01")).one(),
                     Heartbeat("down", 0, 1.0, "Database connection pool exhausted"))
    db.commit()
    q = assistant.ask(db, user(db), "What should I do about INC-000001?")
    refs = [p["ref"] for p in json.loads(q.passages)]
    assert refs[:2] == ["RB-LIMS-001 §1", "RB-LIMS-001 §2"]      # the system's runbook comes first
    assert len(refs) <= assistant.MAX_CONTEXT


# --- Groq (OpenAI-compatible Chat Completions) ------------------------------------------------

def groq_tools(*calls):
    return 200, {"choices": [{"finish_reason": "tool_calls", "message": {"role": "assistant", "content": None,
                 "tool_calls": [{"id": f"call_{n}", "type": "function",
                                 "function": {"name": name, "arguments": json.dumps(args)}}
                                for n, (name, args) in enumerate(calls)]}}],
                 "usage": {"prompt_tokens": 700, "completion_tokens": 30}}


def groq_text(text):
    return 200, {"choices": [{"finish_reason": "stop", "message": {"role": "assistant", "content": text}}],
                 "usage": {"prompt_tokens": 900, "completion_tokens": 120}}


def test_groq_tool_loop(db, use_llm):
    fake = use_llm("groq", [
        groq_tools(("get_system_status", {"system_code": "LIMS-01"})),
        groq_text("Syntra shows LIMS-01 as unknown. QA closes GxP incidents [SOP-ITO-001 §7]."),
    ])
    q = assistant.ask(db, user(db), "Who closes incidents on LIMS-01?")
    first, second = fake.requests
    assert first["url"] == "https://api.groq.com/openai/v1/chat/completions"
    assert first["headers"]["authorization"] == "Bearer test-key-not-real"
    assert first["body"]["model"] == "openai/gpt-oss-120b"
    assert first["body"]["messages"][0]["role"] == "system"
    assert first["body"]["tools"][0]["type"] == "function" and "parameters" in first["body"]["tools"][0]["function"]
    assistant_msg, tool_msg = second["body"]["messages"][-2:]
    assert assistant_msg["tool_calls"][0]["id"] == "call_0"
    assert (tool_msg["role"], tool_msg["tool_call_id"]) == ("tool", "call_0")
    assert json.loads(tool_msg["content"])["systems"][0]["code"] == "LIMS-01"
    assert (q.mode, q.provider, q.model) == ("llm", "groq", "openai/gpt-oss-120b")
    assert json.loads(q.citations)[0] == {**json.loads(q.citations)[0], "ref": "SOP-ITO-001 §7", "valid": True}
    assert (q.input_tokens, q.output_tokens) == (1600, 150)


def test_groq_retries_malformed_tool_call_once(db, use_llm):
    failed = (400, {"error": {"message": "Failed to call a function.", "type": "invalid_request_error",
                              "code": "tool_use_failed"}})
    fake = use_llm("groq", [failed, groq_text("Answer [SOP-ITO-002 §5].")])
    q = assistant.ask(db, user(db), "Who approves GxP changes?")
    assert len(fake.requests) == 2 and q.mode == "llm"
    fake = use_llm("groq", [failed, failed])
    q = assistant.ask(db, user(db), "Who approves GxP changes?")
    assert q.mode == "retrieval" and "HTTP 400" in q.error


def test_provider_choice_follows_configured_key(monkeypatch):
    from app.services.llm import resolve_config
    for k in ("anthropic_api_key", "openai_api_key", "groq_api_key"):
        monkeypatch.setattr(settings, k, "")
    monkeypatch.setattr(settings, "llm_provider", "auto")
    assert resolve_config().provider is None
    monkeypatch.setattr(settings, "groq_api_key", "gsk_x")
    assert (resolve_config().provider, resolve_config().model) == ("groq", "openai/gpt-oss-120b")
    monkeypatch.setattr(settings, "llm_model", "llama-3.3-70b-versatile")
    assert resolve_config().model == "llama-3.3-70b-versatile"
    monkeypatch.setattr(settings, "anthropic_api_key", "sk-ant-x")
    assert resolve_config().provider == "anthropic"           # several keys: Claude first
    monkeypatch.setattr(settings, "llm_provider", "groq")
    assert resolve_config().provider == "groq"                # unless chosen explicitly
    assert "gsk_x" not in repr(resolve_config())              # the key never appears in logs/reprs
