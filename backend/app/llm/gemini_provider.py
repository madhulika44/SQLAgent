"""Google Gemini provider (fallback). Uses the official `google-genai` SDK.

Differences from Groq worth knowing:
  - the system prompt is passed separately (`system_instruction`), not as a message
  - the assistant role is called "model" instead of "assistant"
"""

import time

from google import genai
from google.genai import errors, types

from app.llm.base import ChatMessage, LLMError, LLMProvider, LLMResponse, parse_retry_after


class GeminiProvider(LLMProvider):
    name = "gemini"

    def __init__(self, api_key: str, model: str, temperature: float, timeout_seconds: int):
        super().__init__(api_key, model, temperature, timeout_seconds)
        # HttpOptions.timeout is in MILLISECONDS.
        self.client = genai.Client(api_key=api_key,
                                   http_options=types.HttpOptions(timeout=timeout_seconds * 1000))

    def generate(self, system_prompt: str, messages: list[ChatMessage]) -> LLMResponse:
        started = time.perf_counter()
        contents = [
            types.Content(role="model" if m.role == "assistant" else "user",
                          parts=[types.Part(text=m.content)])
            for m in messages
        ]
        config = types.GenerateContentConfig(
            system_instruction=system_prompt,
            temperature=self.temperature,
            response_mime_type="application/json",   # JSON mode
        )
        try:
            response = self.client.models.generate_content(model=self.model, contents=contents, config=config)
        except errors.APIError as exc:
            rate_limited = exc.code == 429
            label = "rate limit reached (429)" if rate_limited else f"HTTP {exc.code}"
            raise LLMError(self.name, f"{label}: {exc.message}", rate_limited=rate_limited,
                           retry_after_seconds=parse_retry_after(str(exc)) if rate_limited else None) from exc
        except Exception as exc:          # network errors, timeouts
            raise LLMError(self.name, f"{type(exc).__name__}: {exc}") from exc

        text = response.text or ""
        return LLMResponse(text, self.name, self.model, int((time.perf_counter() - started) * 1000))
