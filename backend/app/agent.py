"""
The SQL Agent: the loop that turns a question into an answer.

    question
       |
       v
    load schema (cached) -> build system prompt
       |
       v
    +-> call LLM -> parse JSON -> validate SQL -> execute on SQL Server --> result
    |                  |              |                  |
    |               bad JSON      rejected          SQL error
    |                  |              |                  |
    +------------------+--------------+------------------+
           feed the problem back to the LLM and try again
                    (up to AGENT_MAX_RETRIES retries)

Every step is recorded in a TRACE (name, what happened, duration, SQL)
so the UI can show how the agent "thinks" - and so you can learn from it.

No agent framework is used: this file IS the agent.
"""

import json
import logging
import re
import time
from dataclasses import asdict, dataclass, field

from app import prompts
from app.config import Settings, get_settings
from app.db import DatabaseError, run_query
from app.llm import AllProvidersFailedError, ChatMessage, LLMRouter
from app.schema_loader import get_schema, is_schema_cached
from app.validator import validate_sql

logger = logging.getLogger(__name__)

MAX_QUESTION_LENGTH = 1000


@dataclass
class TraceStep:
    step: str                 # e.g. "call_llm", "validate_sql", "execute_sql"
    status: str               # "ok", "error" or "info"
    detail: str               # human-readable description of what happened
    duration_ms: int = 0
    attempt: int | None = None
    sql: str | None = None
    data: dict = field(default_factory=dict)   # extra details (provider, row count, ...)


@dataclass
class AgentResult:
    question: str
    sql: str | None = None
    explanation: str | None = None
    columns: list[str] = field(default_factory=list)
    rows: list[list] = field(default_factory=list)
    row_count: int = 0
    truncated: bool = False
    attempts: int = 0
    provider: str | None = None
    total_time_ms: int = 0
    trace: list[TraceStep] = field(default_factory=list)
    error: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


class ResponseFormatError(Exception):
    """The LLM's reply wasn't the JSON object we asked for."""


def parse_llm_response(text: str) -> tuple[str | None, str]:
    """Extract (sql, explanation) from the model's reply.

    We asked for pure JSON, but models sometimes wrap it in ```json fences or
    add a sentence before it, so we look for the outermost {...} block."""
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
    start, end = cleaned.find("{"), cleaned.rfind("}")
    if start == -1 or end <= start:
        raise ResponseFormatError("no JSON object found in the reply")
    try:
        data = json.loads(cleaned[start:end + 1])
    except json.JSONDecodeError as exc:
        raise ResponseFormatError(f"invalid JSON ({exc.msg})") from exc
    if not isinstance(data, dict) or "sql" not in data:
        raise ResponseFormatError('the JSON object has no "sql" key')

    sql = data.get("sql")
    if sql is not None and not isinstance(sql, str):
        raise ResponseFormatError('"sql" must be a string or null')
    sql = sql.strip() if sql else None
    explanation = str(data.get("explanation") or "").strip()
    return sql or None, explanation


class SQLAgent:
    def __init__(self, settings: Settings | None = None, router: LLMRouter | None = None):
        self.settings = settings or get_settings()
        self.router = router or LLMRouter(self.settings)

    # -----------------------------------------------------------------
    # Public entry point
    # -----------------------------------------------------------------
    def ask(self, question: str) -> AgentResult:
        started = time.perf_counter()
        result = AgentResult(question=(question or "").strip())
        try:
            self._run(result)
        except Exception as exc:     # last-resort safety net: never crash the caller
            logger.exception("Unexpected agent error")
            result.error = f"Unexpected error: {type(exc).__name__}"
            self._add(result, "agent", "error", f"Unexpected error: {exc}")
        result.total_time_ms = int((time.perf_counter() - started) * 1000)
        return result

    # -----------------------------------------------------------------
    # The loop
    # -----------------------------------------------------------------
    def _run(self, result: AgentResult) -> None:
        # Step 0: sanity-check the question itself.
        if not result.question:
            result.error = "Please enter a question."
            return
        if len(result.question) > MAX_QUESTION_LENGTH:
            result.error = f"The question is too long (max {MAX_QUESTION_LENGTH} characters)."
            return

        # Step 1: schema (cached after the first call).
        t = time.perf_counter()
        was_cached = is_schema_cached()
        try:
            schema = get_schema()
        except DatabaseError as exc:
            result.error = f"Could not read the database schema: {exc}"
            self._add(result, "load_schema", "error", result.error, t)
            return
        self._add(result, "load_schema", "ok",
                  f"{len(schema.tables)} tables, {len(schema.relationships)} relationships "
                  f"({'from cache' if was_cached else 'read from database'})", t)

        # Step 2: system prompt = rules + schema. Conversation starts with the question.
        t = time.perf_counter()
        system_prompt = prompts.build_system_prompt(schema.to_prompt_text(), schema.database,
                                                    self.settings.agent_max_rows)
        messages = [ChatMessage("user", prompts.build_question_message(result.question))]
        self._add(result, "build_prompt", "ok",
                  f"System prompt with schema: {len(system_prompt):,} characters "
                  f"(~{len(system_prompt) // 4:,} tokens)", t)

        # Step 3: the attempt loop.
        max_attempts = 1 + self.settings.agent_max_retries
        last_problem = ""
        for attempt in range(1, max_attempts + 1):
            result.attempts = attempt

            # 3a. Ask the LLM.
            t = time.perf_counter()
            try:
                routed = self.router.generate(system_prompt, messages)
            except AllProvidersFailedError as exc:
                result.error = str(exc)
                self._add(result, "call_llm", "error", str(exc), t, attempt)
                return
            for failure in routed.failures:
                self._add(result, "llm_fallback", "info",
                          f"{failure.provider} failed ({failure.message}); fell back to the next provider",
                          attempt=attempt, data={"failed_provider": failure.provider,
                                                 "rate_limited": failure.rate_limited})
            if routed.waited_seconds:
                self._add(result, "rate_limit_wait", "info",
                          f"Waited {routed.waited_seconds:.1f}s for a rate limit to reset, then retried",
                          attempt=attempt)
            response = routed.response
            result.provider = response.provider
            messages.append(ChatMessage("assistant", response.text))
            self._add(result, "call_llm", "ok", f"{response.provider} ({response.model}) answered", t, attempt,
                      data={"provider": response.provider, "model": response.model})

            # 3b. Parse the JSON reply.
            t = time.perf_counter()
            try:
                sql, explanation = parse_llm_response(response.text)
            except ResponseFormatError as exc:
                last_problem = f"Unusable LLM reply: {exc}"
                self._add(result, "parse_response", "error", last_problem, t, attempt,
                          data={"raw_reply": response.text[:500]})
                messages.append(ChatMessage("user", prompts.build_format_error_message(str(exc))))
                continue
            result.explanation = explanation
            if sql is None:
                # The model declined: unanswerable, or a request to modify data.
                result.sql = None
                self._add(result, "parse_response", "info", f"No SQL generated: {explanation}", t, attempt)
                return
            self._add(result, "parse_response", "ok", "Got SQL and explanation", t, attempt, sql=sql)

            # 3c. Validate (guardrail #2).
            t = time.perf_counter()
            check = validate_sql(sql, self.settings.agent_max_rows)
            if not check.is_valid:
                last_problem = f"Validator rejected the query: {check.reason}"
                self._add(result, "validate_sql", "error", last_problem, t, attempt, sql=sql)
                messages.append(ChatMessage("user", prompts.build_validation_error_message(check.reason)))
                continue
            result.sql = check.sql
            self._add(result, "validate_sql", "ok",
                      "Passed: single read-only SELECT" + (f"; {'; '.join(check.changes)}" if check.changes else ""),
                      t, attempt, sql=check.sql)

            # 3d. Execute with the read-only login (guardrail #3).
            t = time.perf_counter()
            try:
                query = run_query(check.sql, self.settings.agent_max_rows, self.settings)
            except DatabaseError as exc:
                last_problem = f"SQL Server error: {exc}"
                self._add(result, "execute_sql", "error", last_problem, t, attempt, sql=check.sql)
                messages.append(ChatMessage("user", prompts.build_database_error_message(str(exc))))
                continue

            result.columns, result.rows = query.columns, query.rows
            result.row_count, result.truncated = len(query.rows), query.truncated
            self._add(result, "execute_sql", "ok",
                      f"Returned {result.row_count} row(s)" + (" (truncated)" if query.truncated else ""),
                      t, attempt, sql=check.sql, data={"row_count": result.row_count})
            return   # success

        result.error = f"Could not produce a working query after {max_attempts} attempts. Last problem: {last_problem}"
        self._add(result, "agent", "error", result.error)

    # -----------------------------------------------------------------
    # Trace helper
    # -----------------------------------------------------------------
    @staticmethod
    def _add(result: AgentResult, step: str, status: str, detail: str, started: float | None = None,
             attempt: int | None = None, sql: str | None = None, data: dict | None = None) -> None:
        duration = int((time.perf_counter() - started) * 1000) if started is not None else 0
        result.trace.append(TraceStep(step, status, detail, duration, attempt, sql, data or {}))
        logger.debug("[%s] %s: %s", status, step, detail)
