"""
End-to-end tests: real SQL Server + real LLM.

Skipped automatically when the database is unreachable or no API key is set,
so `pytest` always works. They use your free-tier quota, so to skip them:
    pytest -m "not e2e"
"""

import pytest
from fastapi.testclient import TestClient

from app.config import get_settings
from app.db import check_connection

settings = get_settings()
db_ok, db_message = check_connection(settings)
has_llm_key = bool(settings.groq_api_key.get_secret_value() or settings.gemini_api_key.get_secret_value())

pytestmark = [
    pytest.mark.e2e,
    pytest.mark.skipif(not db_ok, reason=f"SQL Server not reachable: {db_message}"),
    pytest.mark.skipif(not has_llm_key, reason="No GROQ_API_KEY or GEMINI_API_KEY in .env"),
]


@pytest.fixture(scope="module")
def client():
    from app.main import app
    with TestClient(app) as test_client:      # `with` runs the startup (schema warm-up)
        yield test_client


def test_health(client):
    body = client.get("/health").json()
    assert body["status"] == "ok"
    assert body["database"]["ok"] is True
    assert body["schema_cached"] is True


def test_schema_lists_all_tables(client):
    body = client.get("/schema").json()
    assert len(body["tables"]) == 13
    assert any(t["name"] == "Orders" for t in body["tables"])


def test_examples_are_grouped(client):
    body = client.get("/examples").json()
    assert {g["group"] for g in body["by_persona"]} == {
        "City Manager", "Operations", "Marketing", "Restaurant Partnerships"}


def test_ask_count_of_cities(client):
    body = client.post("/ask", json={"question": "How many cities do we operate in?"}).json()
    assert body["error"] is None, body["error"]
    assert body["rows"] and body["rows"][0][0] == 8


def test_ask_orders_by_city_suggests_a_bar_chart(client):
    body = client.post("/ask", json={"question": "Total number of orders per city"}).json()
    assert body["error"] is None, body["error"]
    assert body["row_count"] == 8
    assert body["chart"]["type"] in ("bar", "pie")


def test_ask_to_delete_data_is_refused(client):
    body = client.post("/ask", json={"question": "Delete all cancelled orders"}).json()
    assert body["sql"] is None
    assert body["rows"] == []


def test_blank_question_is_a_422(client):
    assert client.post("/ask", json={"question": "  "}).status_code == 422
