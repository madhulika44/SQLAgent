"""
The common interface every LLM provider implements.

The agent only ever talks to `LLMProvider.generate(...)`. It doesn't know or
care whether Groq or Gemini answers - that's what makes switching providers
(or adding a third one later) a one-file change.
"""

import re
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Literal


@dataclass
class ChatMessage:
    """One turn of the conversation. 'assistant' = what the LLM said earlier;
    we send it back on retries so the model can see (and fix) its own SQL."""
    role: Literal["user", "assistant"]
    content: str


@dataclass
class LLMResponse:
    text: str          # the raw text the model returned (should be JSON)
    provider: str      # "groq" or "gemini"
    model: str
    duration_ms: int


class LLMError(Exception):
    """A provider call failed. `rate_limited` is True for HTTP 429 (quota
    exceeded); `retry_after_seconds` is how long the provider asked us to
    wait, when it told us. The router uses both to decide what to do next."""

    def __init__(self, provider: str, message: str, rate_limited: bool = False,
                 retry_after_seconds: float | None = None):
        super().__init__(f"{provider}: {message}")
        self.provider = provider
        self.message = message
        self.rate_limited = rate_limited
        self.retry_after_seconds = retry_after_seconds


def parse_retry_after(text: str) -> float | None:
    """Find a wait time in an error message, e.g. Groq's 'Please try again in 4.98s'
    or Gemini's "retryDelay': '12s'". Returns seconds, or None if not found."""
    match = re.search(r"try again in (?:(\d+)m)?([\d.]+)s|retryDelay\W+(\d+(?:\.\d+)?)s", text)
    if not match:
        return None
    minutes, seconds, gemini_seconds = match.groups()
    if gemini_seconds:
        return float(gemini_seconds)
    return int(minutes or 0) * 60 + float(seconds)


class LLMProvider(ABC):
    name: str = "base"

    def __init__(self, api_key: str, model: str, temperature: float, timeout_seconds: int):
        self.api_key = api_key
        self.model = model
        self.temperature = temperature
        self.timeout_seconds = timeout_seconds

    @abstractmethod
    def generate(self, system_prompt: str, messages: list[ChatMessage]) -> LLMResponse:
        """Send the system prompt + conversation, return the model's reply.
        Must raise LLMError on any failure."""
