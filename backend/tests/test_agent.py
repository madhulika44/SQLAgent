"""
Tests for the agent: JSON parsing of LLM replies, and the retry loop.

The loop tests use FakeRouter (scripted LLM replies) and patch run_query,
so they need neither a database nor an API key.
"""

import pytest

from app import agent as agent_module
from app.agent import ResponseFormatError, SQLAgent, parse_llm_response
from app.config import Settings
from app.db import DatabaseError, QueryResult
from app.schema_loader import Column, SchemaInfo, Table


# ---------------------------------------------------------------------
# parse_llm_response
# ---------------------------------------------------------------------
def test_parses_plain_json():
    sql, explanation = parse_llm_response('{"sql": "SELECT 1", "explanation": "One."}')
    assert sql == "SELECT 1" and explanation == "One."


def test_parses_json_inside_markdown_fences():
    reply = '```json\n{"sql": "SELECT 1", "explanation": "x"}\n```'
    assert parse_llm_response(reply)[0] == "SELECT 1"


def test_parses_json_with_text_around_it():
    reply = 'Here you go:\n{"sql": "SELECT 1", "explanation": "x"}\nHope that helps!'
    assert parse_llm_response(reply)[0] == "SELECT 1"


def test_null_sql_means_the_model_declined():
    sql, explanation = parse_llm_response('{"sql": null, "explanation": "Cannot modify data."}')
    assert sql is None and "modify" in explanation


def test_empty_string_sql_is_treated_as_declined():
    assert parse_llm_response('{"sql": "  ", "explanation": "x"}')[0] is None


@pytest.mark.parametrize("reply", [
    "SELECT 1",                                   # no JSON at all
    '{"sql": "SELECT 1", "explanation": ',       # truncated JSON
    '{"query": "SELECT 1"}',                      # wrong key
    '{"sql": 42, "explanation": "x"}',            # wrong type
])
def test_unusable_replies_raise(reply):
    with pytest.raises(ResponseFormatError):
        parse_llm_response(reply)


# ---------------------------------------------------------------------
# The retry loop
# ---------------------------------------------------------------------
TINY_SCHEMA = SchemaInfo(
    database="TestDB",
    tables=[Table("Cities", "Cities", [Column("CityName", "nvarchar(50)", False, "Name")])],
    relationships=[], loaded_at="now", load_time_ms=0,
)


@pytest.fixture
def agent_env(monkeypatch):
    """Replace the schema and the database with fakes."""
    monkeypatch.setattr(agent_module, "get_schema", lambda: TINY_SCHEMA)
    monkeypatch.setattr(agent_module, "is_schema_cached", lambda: True)
    executed = []

    def fake_run_query(sql, max_rows, settings=None):
        executed.append(sql)
        if "Population" in sql:
            raise DatabaseError("Invalid column name 'Population'.")
        return QueryResult(columns=["CityName"], rows=[["Bengaluru"], ["Mumbai"]], truncated=False)

    monkeypatch.setattr(agent_module, "run_query", fake_run_query)
    return executed


SETTINGS = Settings(_env_file=None, agent_max_retries=3)


def test_happy_path_first_attempt(agent_env, fake_router):
    router = fake_router(['{"sql": "SELECT c.CityName FROM dbo.Cities AS c", "explanation": "All cities"}'])
    result = SQLAgent(SETTINGS, router).ask("List cities")
    assert result.error is None
    assert result.attempts == 1
    assert result.rows == [["Bengaluru"], ["Mumbai"]]
    assert "TOP 200" in result.sql.replace("\n", " ")          # validator added a limit
    assert [s.step for s in result.trace][-1] == "execute_sql"


def test_sql_error_is_sent_back_and_fixed(agent_env, fake_router):
    router = fake_router([
        '{"sql": "SELECT c.Population FROM dbo.Cities AS c", "explanation": "x"}',
        '{"sql": "SELECT c.CityName FROM dbo.Cities AS c", "explanation": "fixed"}',
    ])
    result = SQLAgent(SETTINGS, router).ask("City populations")
    assert result.error is None and result.attempts == 2
    # The second LLM call must include the SQL Server error message.
    feedback = router.received[1][-1].content
    assert "Invalid column name 'Population'" in feedback


def test_validator_rejection_is_sent_back(agent_env, fake_router):
    router = fake_router([
        '{"sql": "DROP TABLE dbo.Cities", "explanation": "x"}',
        '{"sql": "SELECT c.CityName FROM dbo.Cities AS c", "explanation": "ok"}',
    ])
    result = SQLAgent(SETTINGS, router).ask("Remove cities")
    assert result.attempts == 2 and result.error is None
    assert "safety validator" in router.received[1][-1].content
    assert len(agent_env) == 1                     # the DROP never reached the database


def test_bad_json_is_retried(agent_env, fake_router):
    router = fake_router(["not json", '{"sql": "SELECT c.CityName FROM dbo.Cities AS c", "explanation": "ok"}'])
    result = SQLAgent(SETTINGS, router).ask("List cities")
    assert result.attempts == 2 and result.error is None


def test_gives_up_after_max_retries(agent_env, fake_router):
    bad = '{"sql": "SELECT c.Population FROM dbo.Cities AS c", "explanation": "x"}'
    router = fake_router([bad] * 4)                 # 1 attempt + 3 retries
    result = SQLAgent(SETTINGS, router).ask("City populations")
    assert result.attempts == 4
    assert "after 4 attempts" in result.error


def test_declined_question_returns_explanation_without_sql(agent_env, fake_router):
    router = fake_router(['{"sql": null, "explanation": "I can only read data."}'])
    result = SQLAgent(SETTINGS, router).ask("Delete all orders")
    assert result.sql is None and result.error is None
    assert result.explanation == "I can only read data."
    assert agent_env == []                          # nothing was executed


def test_blank_question_is_rejected_without_calling_the_llm(agent_env, fake_router):
    router = fake_router([])
    result = SQLAgent(SETTINGS, router).ask("   ")
    assert result.error and router.received == []
