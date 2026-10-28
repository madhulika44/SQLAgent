"""Groq provider (default). Uses the official `groq` SDK, which follows the
OpenAI chat-completions format: a list of {role, content} messages."""

import time

import groq

from app.llm.base import ChatMessage, LLMError, LLMProvider, LLMResponse, parse_retry_after


class GroqProvider(LLMProvider):
    name = "groq"

    def __init__(self, api_key: str, model: str, temperature: float, timeout_seconds: int):
        super().__init__(api_key, model, temperature, timeout_seconds)
        # max_retries=0: if Groq says "rate limited", we'd rather fall back to
        # Gemini immediately than have the SDK silently wait and retry.
        self.client = groq.Groq(api_key=api_key, timeout=timeout_seconds, max_retries=0)

    def generate(self, system_prompt: str, messages: list[ChatMessage]) -> LLMResponse:
        started = time.perf_counter()
        chat = [{"role": "system", "content": system_prompt}]
        chat += [{"role": m.role, "content": m.content} for m in messages]
        try:
            completion = self.client.chat.completions.create(
                model=self.model,
                messages=chat,
                temperature=self.temperature,
                # JSON mode: the model must reply with a valid JSON object.
                response_format={"type": "json_object"},
            )
        except groq.RateLimitError as exc:
            raise LLMError(self.name, "rate limit reached (429): tokens/requests per minute exceeded",
                           rate_limited=True, retry_after_seconds=parse_retry_after(str(exc.message))) from exc
        except groq.APIStatusError as exc:
            raise LLMError(self.name, f"HTTP {exc.status_code}: {exc.message}") from exc
        except groq.APIError as exc:      # timeouts, connection problems, ...
            raise LLMError(self.name, str(exc)) from exc

        text = completion.choices[0].message.content or ""
        return LLMResponse(text, self.name, self.model, int((time.perf_counter() - started) * 1000))
