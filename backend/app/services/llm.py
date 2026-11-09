"""Language model providers for the Knowledge Assistant: Claude (Messages API), OpenAI (Responses API)
and Groq (OpenAI-compatible Chat Completions).

Both run the same loop: the model may call tools, Syntra runs them and sends the results back, until
the model answers in text or the round limit is reached (then tools are switched off for the final
turn). The API key comes from the environment and is never logged or returned by the API.
"""
import json
from collections.abc import Callable
from dataclasses import dataclass, field

import httpx

from app.config import settings

DEFAULT_MODELS = {"anthropic": "claude-sonnet-5-5", "openai": "gpt-6-luna", "groq": "openai/gpt-oss-120b"}


class LLMError(Exception):
    """The model could not be used (bad key, rate limit, timeout, unexpected response)."""


@dataclass
class ToolSpec:
    name: str
    description: str
    parameters: dict  # JSON schema


@dataclass
class RunResult:
    text: str
    input_tokens: int = 0
    output_tokens: int = 0
    rounds: int = 0


# execute(name, arguments) -> result text that is sent back to the model
Executor = Callable[[str, dict], str]


@dataclass
class LLMConfig:
    provider: str | None   # anthropic | openai | None
    model: str | None
    api_key: str = field(default="", repr=False)


def resolve_config() -> LLMConfig:
    choice = settings.llm_provider.strip().lower()
    keys = {"anthropic": settings.anthropic_api_key.strip(), "openai": settings.openai_api_key.strip(),
            "groq": settings.groq_api_key.strip()}
    if choice == "none":
        return LLMConfig(None, None)
    if choice in keys:
        provider = choice if keys[choice] else None
    else:  # auto: whichever key is configured (if several: Claude, then OpenAI, then Groq)
        provider = next((p for p in ("anthropic", "openai", "groq") if keys[p]), None)
    if provider is None:
        return LLMConfig(None, None)
    return LLMConfig(provider, settings.llm_model.strip() or DEFAULT_MODELS[provider], keys[provider])


def _error_message(provider: str, resp: httpx.Response) -> str:
    try:
        body = resp.json()
        detail = body.get("error", {}).get("message") or str(body)[:200]
    except ValueError:
        detail = resp.text[:200]
    hint = {401: "the API key is invalid", 403: "the API key has no access to this model",
            404: "the model name is not available for this key", 429: "rate limit or quota reached"}.get(resp.status_code)
    return f"{provider} returned HTTP {resp.status_code}{f' ({hint})' if hint else ''}: {detail}"


class AnthropicProvider:
    name = "anthropic"

    def __init__(self, config: LLMConfig, transport: httpx.BaseTransport | None = None):
        self.config, self.transport = config, transport

    def run(self, system: str, messages: list[dict], tools: list[ToolSpec], execute: Executor) -> RunResult:
        tool_defs = [{"name": t.name, "description": t.description, "input_schema": t.parameters} for t in tools]
        msgs = [{"role": m["role"], "content": m["content"]} for m in messages]
        result = RunResult(text="")
        headers = {"x-api-key": self.config.api_key, "anthropic-version": settings.anthropic_version,
                   "content-type": "application/json"}
        with httpx.Client(timeout=settings.llm_timeout_seconds, transport=self.transport) as client:
            for round_no in range(1, settings.llm_max_tool_rounds + 2):
                last = round_no > settings.llm_max_tool_rounds
                body = {"model": self.config.model, "max_tokens": settings.llm_max_tokens, "system": system,
                        "messages": msgs, "tools": tool_defs,
                        "tool_choice": {"type": "none"} if last else {"type": "auto"}}
                try:
                    resp = client.post(f"{settings.anthropic_base_url.rstrip('/')}/v1/messages", headers=headers, json=body)
                except httpx.HTTPError as e:
                    raise LLMError(f"Could not reach the Claude API: {e.__class__.__name__}") from e
                if resp.status_code != 200:
                    raise LLMError(_error_message("Claude API", resp))
                data = resp.json()
                usage = data.get("usage", {})
                result.input_tokens += usage.get("input_tokens", 0)
                result.output_tokens += usage.get("output_tokens", 0)
                result.rounds = round_no
                blocks = data.get("content", [])
                calls = [b for b in blocks if b.get("type") == "tool_use"]
                if not calls or last:
                    result.text = "\n".join(b["text"] for b in blocks if b.get("type") == "text").strip()
                    return result
                msgs.append({"role": "assistant", "content": blocks})
                msgs.append({"role": "user", "content": [
                    {"type": "tool_result", "tool_use_id": c["id"], "content": execute(c["name"], c.get("input") or {})}
                    for c in calls]})
        return result


class OpenAIProvider:
    name = "openai"

    def __init__(self, config: LLMConfig, transport: httpx.BaseTransport | None = None):
        self.config, self.transport = config, transport

    @staticmethod
    def _text(data: dict) -> str:
        parts = []
        for item in data.get("output", []):
            if item.get("type") == "message":
                parts += [c.get("text", "") for c in item.get("content", []) if c.get("type") == "output_text"]
        return "\n".join(parts).strip()

    def run(self, system: str, messages: list[dict], tools: list[ToolSpec], execute: Executor) -> RunResult:
        tool_defs = [{"type": "function", "name": t.name, "description": t.description, "parameters": t.parameters}
                     for t in tools]
        next_input: list[dict] = [{"role": m["role"], "content": m["content"]} for m in messages]
        previous_id = None
        result = RunResult(text="")
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}
        with httpx.Client(timeout=settings.llm_timeout_seconds, transport=self.transport) as client:
            for round_no in range(1, settings.llm_max_tool_rounds + 2):
                last = round_no > settings.llm_max_tool_rounds
                body = {"model": self.config.model, "instructions": system, "input": next_input,
                        "tools": tool_defs, "tool_choice": "none" if last else "auto",
                        "max_output_tokens": settings.llm_max_tokens}
                if previous_id:
                    body["previous_response_id"] = previous_id  # instructions are not carried over: resent
                try:
                    resp = client.post(f"{settings.openai_base_url.rstrip('/')}/v1/responses", headers=headers, json=body)
                except httpx.HTTPError as e:
                    raise LLMError(f"Could not reach the OpenAI API: {e.__class__.__name__}") from e
                if resp.status_code != 200:
                    raise LLMError(_error_message("OpenAI API", resp))
                data = resp.json()
                usage = data.get("usage") or {}
                result.input_tokens += usage.get("input_tokens", 0)
                result.output_tokens += usage.get("output_tokens", 0)
                result.rounds = round_no
                calls = [i for i in data.get("output", []) if i.get("type") == "function_call"]
                if not calls or last:
                    result.text = self._text(data)
                    return result
                previous_id = data.get("id")
                next_input = []
                for c in calls:
                    try:
                        args = json.loads(c.get("arguments") or "{}")
                    except ValueError:
                        args = {}
                    next_input.append({"type": "function_call_output", "call_id": c["call_id"],
                                       "output": execute(c["name"], args)})
        return result


class ChatCompletionsProvider:
    """OpenAI-compatible Chat Completions with tools (used for Groq)."""

    name = "groq"
    label = "Groq API"

    def __init__(self, config: LLMConfig, transport: httpx.BaseTransport | None = None):
        self.config, self.transport = config, transport

    def _post(self, client: httpx.Client, body: dict) -> dict:
        url = f"{settings.groq_base_url.rstrip('/')}/chat/completions"
        headers = {"Authorization": f"Bearer {self.config.api_key}", "Content-Type": "application/json"}
        for attempt in (1, 2):
            try:
                resp = client.post(url, headers=headers, json=body)
            except httpx.HTTPError as e:
                raise LLMError(f"Could not reach the {self.label}: {e.__class__.__name__}") from e
            if resp.status_code == 200:
                return resp.json()
            # Groq answers 400 "tool_use_failed" when the model wrote a malformed tool call: retry once.
            if resp.status_code == 400 and "tool_use_failed" in resp.text and attempt == 1:
                continue
            raise LLMError(_error_message(self.label, resp))
        raise LLMError(f"{self.label}: the model could not produce a valid tool call")

    def run(self, system: str, messages: list[dict], tools: list[ToolSpec], execute: Executor) -> RunResult:
        tool_defs = [{"type": "function", "function": {"name": t.name, "description": t.description,
                                                       "parameters": t.parameters}} for t in tools]
        msgs = [{"role": "system", "content": system}] + [{"role": m["role"], "content": m["content"]} for m in messages]
        result = RunResult(text="")
        with httpx.Client(timeout=settings.llm_timeout_seconds, transport=self.transport) as client:
            for round_no in range(1, settings.llm_max_tool_rounds + 2):
                last = round_no > settings.llm_max_tool_rounds
                data = self._post(client, {"model": self.config.model, "messages": msgs, "tools": tool_defs,
                                           "tool_choice": "none" if last else "auto",
                                           "max_completion_tokens": settings.llm_max_tokens})
                usage = data.get("usage") or {}
                result.input_tokens += usage.get("prompt_tokens", 0)
                result.output_tokens += usage.get("completion_tokens", 0)
                result.rounds = round_no
                choices = data.get("choices") or []
                if not choices:
                    raise LLMError(f"{self.label} returned no answer")
                message = choices[0].get("message") or {}
                calls = message.get("tool_calls") or []
                if not calls or last:
                    result.text = (message.get("content") or "").strip()
                    return result
                msgs.append({"role": "assistant", "content": message.get("content") or "",
                             "tool_calls": [{"id": c["id"], "type": "function",
                                             "function": {"name": c["function"]["name"],
                                                          "arguments": c["function"].get("arguments") or "{}"}}
                                            for c in calls]})
                for c in calls:
                    try:
                        args = json.loads(c["function"].get("arguments") or "{}")
                    except ValueError:
                        args = {}
                    msgs.append({"role": "tool", "tool_call_id": c["id"], "name": c["function"]["name"],
                                 "content": execute(c["function"]["name"], args if isinstance(args, dict) else {})})
        return result


def get_provider(config: LLMConfig, transport: httpx.BaseTransport | None = None):
    if config.provider == "anthropic":
        return AnthropicProvider(config, transport)
    if config.provider == "openai":
        return OpenAIProvider(config, transport)
    if config.provider == "groq":
        return ChatCompletionsProvider(config, transport)
    return None
