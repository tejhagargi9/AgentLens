"""Provider-agnostic access to the chat model.

Agents call `structured()` and `chat()` rather than building models themselves, so the
provider is chosen in one place (AGENTOS_LLM_MODEL) and tests can replace these two functions.
"""

import re
from functools import lru_cache
from typing import Any

from langchain.chat_models import init_chat_model
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import AIMessage, BaseMessage
from pydantic import BaseModel

from agentos.core.config import get_settings


class LLMNotConfiguredError(Exception):
    pass


def require_llm_configured() -> None:
    if not get_settings().llm_api_key:
        raise LLMNotConfiguredError(
            "No LLM API key is configured. Set AGENTOS_LLM_API_KEY in apps/api/.env and restart."
        )


@lru_cache
def get_chat_model() -> BaseChatModel:
    require_llm_configured()
    settings = get_settings()
    return init_chat_model(settings.llm_model, api_key=settings.llm_api_key)


async def structured[T: BaseModel](schema: type[T], messages: list[Any]) -> T:
    """Ask the model for an answer that conforms to `schema`."""
    return await get_chat_model().with_structured_output(schema).ainvoke(messages)


async def chat(messages: list[Any], tools: list[dict] | None = None) -> AIMessage:
    """Plain chat completion; with `tools`, the reply may contain tool calls."""
    model = get_chat_model()
    return await (model.bind_tools(tools) if tools else model).ainvoke(messages)


def describe_error(exc: BaseException) -> str:
    """A short, user-facing reason for a failed model or tool call."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[0]  # async libraries wrap the real error in groups
    text = str(exc) or type(exc).__name__
    if "RESOURCE_EXHAUSTED" in text or "rate limit" in text.lower():
        limit = re.search(r"limit: (\d+), model: ([\w.\-]+)", text)
        retry = re.search(r"retry in ((?:\d+h)?(?:\d+m)?[\d.]+s)", text)
        message = "The LLM provider's quota or rate limit was exceeded"
        if limit:
            message += f" ({limit[1]} requests allowed for {limit[2]})"
        if retry:
            message += f"; retry in {re.sub(r'\.\d+s$', 's', retry[1])}"
        return message + "."
    return text[:300]


def text_of(message: BaseMessage) -> str:
    """Message content as plain text (providers may return a list of content blocks)."""
    return str(message.text)
