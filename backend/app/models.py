"""
Pydantic models = the API's contract with the outside world (the React UI).

FastAPI uses them to:
  - validate incoming JSON (e.g. reject an empty question with a 422)
  - shape outgoing JSON (only declared fields are returned)
  - generate the interactive docs at http://localhost:8000/docs
"""

from typing import Any, Literal

from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------------------
# POST /ask
# ---------------------------------------------------------------------
class AskRequest(BaseModel):
    question: str = Field(..., min_length=1, max_length=1000,
                          examples=["Which city had the most delivered orders last month?"])

    @field_validator("question")
    @classmethod
    def not_blank(cls, value: str) -> str:
        if not value.strip():
            raise ValueError("question must not be blank")
        return value.strip()


class ChartSuggestion(BaseModel):
    type: Literal["bar", "line", "pie", "none"]
    x: str | None = None          # column for the x-axis / pie labels
    y: list[str] = []             # numeric column(s) to plot


class TraceStepModel(BaseModel):
    step: str
    status: Literal["ok", "error", "info"]
    detail: str
    duration_ms: int
    attempt: int | None = None
    sql: str | None = None
    data: dict[str, Any] = {}


class AskResponse(BaseModel):
    question: str
    sql: str | None
    explanation: str | None
    columns: list[str]
    rows: list[list[Any]]
    row_count: int
    truncated: bool
    attempts: int
    provider: str | None
    total_time_ms: int
    trace: list[TraceStepModel]
    error: str | None
    chart: ChartSuggestion


# ---------------------------------------------------------------------
# GET /health
# ---------------------------------------------------------------------
class DatabaseHealth(BaseModel):
    ok: bool
    message: str


class LLMHealth(BaseModel):
    configured: bool
    active_provider: str | None       # the provider tried first
    active_model: str | None
    fallback_providers: list[str]


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    database: DatabaseHealth
    llm: LLMHealth
    schema_cached: bool


# ---------------------------------------------------------------------
# GET /schema and POST /schema/refresh
# ---------------------------------------------------------------------
class SchemaColumn(BaseModel):
    name: str
    data_type: str
    nullable: bool
    description: str
    is_primary_key: bool
    references: str | None
    sample_values: list[str]


class SchemaTable(BaseModel):
    name: str
    description: str
    columns: list[SchemaColumn]


class SchemaRelationship(BaseModel):
    from_table: str
    from_column: str
    to_table: str
    to_column: str


class SchemaResponse(BaseModel):
    database: str
    tables: list[SchemaTable]
    relationships: list[SchemaRelationship]
    loaded_at: str
    load_time_ms: int


# ---------------------------------------------------------------------
# GET /examples
# ---------------------------------------------------------------------
class ExampleQuestion(BaseModel):
    question: str
    persona: str
    concepts: list[str]
    insight: str                      # what the answer should reveal (for the presenter)


class ExampleGroup(BaseModel):
    group: str
    questions: list[ExampleQuestion]


class ExamplesResponse(BaseModel):
    by_persona: list[ExampleGroup]
    by_concept: list[ExampleGroup]
