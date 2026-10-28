"""
Chooses which provider to call, and falls back to the other one on failure.

Free tiers have tight limits (Groq: ~8,000 tokens per minute, i.e. only
about two questions per minute with our ~4,000-token prompt). During a demo
a burst of questions can hit that limit. Instead of showing an error:

  1. try the primary provider, then the fallback provider;
  2. if BOTH failed and one of them was rate limited with a short
     "try again in N seconds" hint, wait that long once and retry it.

Every failure and wait is returned to the agent so it shows up in the trace.
"""

import logging
import time
from dataclasses import dataclass, field

from app.config import Settings
from app.llm.base import ChatMessage, LLMError, LLMProvider, LLMResponse
from app.llm.gemini_provider import GeminiProvider
from app.llm.groq_provider import GroqProvider

logger = logging.getLogger(__name__)

PROVIDER_CLASSES = {"groq": GroqProvider, "gemini": GeminiProvider}

# Waiting longer than this would feel broken in a live demo - give up instead.
MAX_RATE_LIMIT_WAIT_SECONDS = 20


class AllProvidersFailedError(Exception):
    """Every configured provider failed for this request."""


@dataclass
class RouterResult:
    response: LLMResponse
    failures: list[LLMError] = field(default_factory=list)   # providers that failed before success
    waited_seconds: float = 0.0                               # time spent waiting for a rate limit


class LLMRouter:
    def __init__(self, settings: Settings):
        self.settings = settings
        self.providers = self._build_providers()
        if not self.providers:
            raise ValueError("No LLM provider configured: set GROQ_API_KEY and/or GEMINI_API_KEY in .env")

    def _build_providers(self) -> list[LLMProvider]:
        """Primary provider first, then the other one (if fallback is on).
        A provider without an API key is skipped."""
        s = self.settings
        configs = {
            "groq": (s.groq_api_key.get_secret_value(), s.groq_model),
            "gemini": (s.gemini_api_key.get_secret_value(), s.gemini_model),
        }
        order = [s.llm_provider] + [p for p in configs if p != s.llm_provider]
        if not s.llm_fallback_enabled:
            order = order[:1]

        providers = []
        for name in order:
            api_key, model = configs[name]
            if not api_key:
                logger.warning("Skipping %s: no API key in .env", name)
                continue
            providers.append(PROVIDER_CLASSES[name](api_key, model, s.llm_temperature, s.llm_timeout_seconds))
        return providers

    @property
    def primary(self) -> LLMProvider:
        return self.providers[0]

    def _try(self, provider: LLMProvider, system_prompt: str, messages: list[ChatMessage]) -> LLMResponse:
        response = provider.generate(system_prompt, messages)
        logger.info("LLM answered: provider=%s model=%s in %d ms",
                    response.provider, response.model, response.duration_ms)
        return response

    def generate(self, system_prompt: str, messages: list[ChatMessage]) -> RouterResult:
        failures: list[LLMError] = []

        # 1. Each provider in order (primary first).
        for provider in self.providers:
            try:
                return RouterResult(self._try(provider, system_prompt, messages), failures)
            except LLMError as exc:
                logger.warning("LLM provider %s failed (%s) - trying next provider", provider.name, exc.message)
                failures.append(exc)

        # 2. All failed. If a provider was rate limited with a short wait, wait once and retry it.
        waitable = [(f, p) for f, p in zip(failures, self.providers)
                    if f.rate_limited and f.retry_after_seconds is not None
                    and f.retry_after_seconds <= MAX_RATE_LIMIT_WAIT_SECONDS]
        if waitable:
            failure, provider = min(waitable, key=lambda fp: fp[0].retry_after_seconds)
            wait = failure.retry_after_seconds + 0.5
            logger.warning("All providers failed; %s asked us to wait %.1fs - waiting, then retrying",
                           provider.name, failure.retry_after_seconds)
            time.sleep(wait)
            try:
                return RouterResult(self._try(provider, system_prompt, messages), failures, waited_seconds=wait)
            except LLMError as exc:
                failures.append(exc)

        details = "; ".join(str(f) for f in failures)
        raise AllProvidersFailedError(f"All LLM providers failed: {details}")
