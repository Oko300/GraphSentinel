"""
Thin LangChain-compatible chat model wrapper around LiteLLM.
Supports tool-calling (function calling) and works with LangGraph's
create_react_agent. Handles Gemini key rotation + model fallback transparently.
"""

from __future__ import annotations

import json
from typing import Any, Optional, Sequence

import litellm
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import (
    AIMessage,
    BaseMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)
from langchain_core.outputs import ChatGeneration, ChatResult
from langchain_core.tools import BaseTool
from pydantic import Field

from src.agent.key_rotation import current_key, rotate_key
from src.config import GEMINI_MODEL

# Silence litellm noise + set a real global timeout (avoids "None seconds")
litellm.suppress_debug_info = True
litellm.request_timeout = 90

# Only live models — gemini-2.0-flash / 1.5-flash are shut down (404)
MODEL_FALLBACKS = [
    GEMINI_MODEL,                 # e.g. gemini/gemini-3.8-flash  (primary)
    "gemini/gemini-3.8-flash",    # explicit same model as safety net
]

_TRANSIENT_ERRORS = (
    "quota", "rate", "429", "limit", "exceeded", "resource",
    "503", "unavailable", "high demand", "temporarily", "serviceunavailable",
    "timeout", "timed out", "connection", "connect",
)


def _to_litellm_messages(messages: list[BaseMessage]) -> list[dict]:
    """Convert LangChain messages → litellm / OpenAI message dicts."""
    out = []
    for m in messages:
        if isinstance(m, SystemMessage):
            out.append({"role": "system", "content": m.content})
        elif isinstance(m, HumanMessage):
            out.append({"role": "user", "content": m.content})
        elif isinstance(m, AIMessage):
            msg: dict = {"role": "assistant", "content": m.content or ""}
            if m.tool_calls:
                msg["tool_calls"] = []
                for tc in m.tool_calls:
                    # CRITICAL: arguments MUST be a proper JSON string (double quotes).
                    # str(dict) produces single quotes and breaks Gemini conversion.
                    args = tc.get("args") or {}
                    if isinstance(args, str):
                        arguments = args
                    else:
                        arguments = json.dumps(args)
                    msg["tool_calls"].append(
                        {
                            "id": tc.get("id") or tc.get("name", "call"),
                            "type": "function",
                            "function": {
                                "name": tc["name"],
                                "arguments": arguments,
                            },
                        }
                    )
            out.append(msg)
        elif isinstance(m, ToolMessage):
            out.append(
                {
                    "role": "tool",
                    "tool_call_id": m.tool_call_id,
                    "content": str(m.content),
                }
            )
        else:
            out.append({"role": "user", "content": str(m.content)})
    return out


def _to_lc_ai_message(response) -> AIMessage:
    """Convert a litellm response → LangChain AIMessage (with tool_calls)."""
    choice = response.choices[0]
    msg = choice.message
    content = msg.content or ""

    tool_calls = []
    if hasattr(msg, "tool_calls") and msg.tool_calls:
        for tc in msg.tool_calls:
            try:
                args = json.loads(tc.function.arguments)
            except Exception:
                args = {"raw": tc.function.arguments}
            tool_calls.append(
                {
                    "id": tc.id,
                    "name": tc.function.name,
                    "args": args,
                    "type": "tool_call",
                }
            )

    return AIMessage(content=content, tool_calls=tool_calls)


def _tool_schema(tool: BaseTool) -> dict:
    """Convert a LangChain tool → OpenAI function schema for litellm."""
    schema = (
        tool.args_schema.model_json_schema()
        if tool.args_schema
        else {"type": "object", "properties": {}}
    )
    return {
        "type": "function",
        "function": {
            "name": tool.name,
            "description": tool.description or "",
            "parameters": schema,
        },
    }


def _try_all_keys(call_kwargs: dict) -> AIMessage:
    """
    Try every Gemini key in round-robin order.
    On transient errors (503 / quota / timeout) rotate to the next key.
    Raises RuntimeError only if every key fails.
    """
    from src.agent.key_rotation import get_rotator
    rotator = get_rotator()
    last_error = None

    for _ in range(len(rotator)):
        call_kwargs["api_key"] = rotator.current
        try:
            response = litellm.completion(**call_kwargs)
            return _to_lc_ai_message(response)
        except Exception as e:
            err = str(e).lower()
            if any(kw in err for kw in _TRANSIENT_ERRORS):
                last_error = e
                rotate_key()
                continue
            raise  # non-transient error — surface immediately

    raise last_error  # all keys exhausted for this model


class LiteLLMChat(BaseChatModel):
    """
    LangChain BaseChatModel powered by LiteLLM with:
    - Automatic Gemini key rotation (7 keys, round-robin)
    - Model fallback (gemini-3.8-flash only — older Flash models are retired)
    """

    model: str = Field(default_factory=lambda: GEMINI_MODEL)
    temperature: float = 0.0
    max_tokens: int = 4096
    _bound_tools: list = []

    class Config:
        arbitrary_types_allowed = True

    @property
    def _llm_type(self) -> str:
        return "litellm-gemini-rotated"

    def bind_tools(
        self,
        tools: Sequence[BaseTool | dict],
        **kwargs: Any,
    ) -> "LiteLLMChat":
        clone = self.__class__(
            model=self.model,
            temperature=self.temperature,
            max_tokens=self.max_tokens,
        )
        clone._bound_tools = list(tools)
        return clone

    def _generate(
        self,
        messages: list[BaseMessage],
        stop: Optional[list[str]] = None,
        run_manager=None,
        **kwargs: Any,
    ) -> ChatResult:
        lm_messages = _to_litellm_messages(messages)
        base_kwargs: dict = {
            "messages": lm_messages,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
            "timeout": 90,
            "request_timeout": 90,
        }
        if self._bound_tools:
            base_kwargs["tools"] = [
                _tool_schema(t) if isinstance(t, BaseTool) else t
                for t in self._bound_tools
            ]
            base_kwargs["tool_choice"] = "auto"
        if stop:
            base_kwargs["stop"] = stop

        # ── Try primary model, then fallbacks ─────────────────────────────
        last_error = None
        for model_name in MODEL_FALLBACKS:
            call_kwargs = {**base_kwargs, "model": model_name}
            try:
                print(f"[LiteLLMChat] Trying model: {model_name}")
                ai_msg = _try_all_keys(call_kwargs)
                return ChatResult(generations=[ChatGeneration(message=ai_msg)])
            except Exception as e:
                err = str(e).lower()
                if any(kw in err for kw in _TRANSIENT_ERRORS):
                    print(f"[LiteLLMChat] {model_name} overloaded/timeout, trying next…")
                    last_error = e
                    continue
                raise  # hard error — don't swallow it

        raise RuntimeError(
            f"All Gemini models and keys exhausted. Last error: {last_error}"
        )
