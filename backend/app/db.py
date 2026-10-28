"""
Database access - ALWAYS through the read-only login `sql_agent_reader`.

This is guardrail #3: even if a harmful query slipped past the prompt rules
and the validator, SQL Server itself would refuse to change anything.
"""

import logging
import re
from dataclasses import dataclass
from datetime import date, datetime, time
from decimal import Decimal

import pyodbc

from app.config import Settings, get_settings

logger = logging.getLogger(__name__)


class DatabaseError(Exception):
    """A query failed. The message is cleaned up so it can be shown to a
    user or sent back to the LLM as a hint for fixing its SQL."""


@dataclass
class QueryResult:
    columns: list[str]
    rows: list[list]          # JSON-safe values only
    truncated: bool           # True if more rows existed than we returned


def build_connection_string(settings: Settings) -> str:
    return ";".join([
        f"DRIVER={{{settings.db_driver}}}",
        f"SERVER={settings.db_server}",
        f"DATABASE={settings.db_name}",
        f"UID={settings.db_readonly_user}",
        f"PWD={settings.db_readonly_password.get_secret_value()}",
        # Driver 18 encrypts by default; local SQL Server has a self-signed certificate.
        f"TrustServerCertificate={settings.db_trust_server_certificate}",
        "Encrypt=yes",
        "ApplicationIntent=ReadOnly",
    ])


def get_connection(settings: Settings | None = None) -> pyodbc.Connection:
    """Open a new connection. A fresh connection per request keeps things
    simple and safe (no shared state between questions)."""
    settings = settings or get_settings()
    try:
        # timeout= here is the LOGIN timeout (seconds to wait for the server).
        conn = pyodbc.connect(build_connection_string(settings), timeout=10, autocommit=True)
    except pyodbc.Error as exc:
        raise DatabaseError(clean_error_message(exc)) from exc
    # conn.timeout is the QUERY timeout: SQL Server cancels slower queries.
    conn.timeout = settings.query_timeout_seconds
    return conn


def clean_error_message(exc: pyodbc.Error) -> str:
    """pyodbc errors look like:
        ('42S22', "[42S22] [Microsoft][ODBC Driver 18 for SQL Server][SQL Server]
          Invalid column name 'Revenue'. (207) (SQLExecDirectW)")
    Keep just the human-readable part: "Invalid column name 'Revenue'." """
    raw = str(exc.args[1]) if len(exc.args) > 1 else str(exc)
    message = re.sub(r"\[[^\]]*\]", "", raw)                     # drop [..] prefixes
    message = re.sub(r"\(\d+\)\s*\(SQL\w+\)", "", message)        # drop "(207) (SQLExecDirectW)"
    message = re.sub(r"\s*\(SQL\w+\)", "", message)
    message = re.sub(r"\s+", " ", message).strip(" ;")
    if "Query timeout expired" in raw or "HYT00" in str(exc.args[0]):
        return "The query took too long and was cancelled (query timeout)."
    return message or raw


def to_json_safe(value):
    """Convert database values into types that JSON (and the React UI) understand."""
    if isinstance(value, Decimal):
        # Whole numbers stay ints (counts, IDs); money/averages become floats.
        return int(value) if value == value.to_integral_value() else float(value)
    if isinstance(value, (datetime, date, time)):
        return value.isoformat()
    if isinstance(value, (bytes, bytearray)):
        return value.hex()
    return value     # str, int, float, bool and None are already JSON-safe


def run_query(sql: str, max_rows: int, settings: Settings | None = None) -> QueryResult:
    """Execute a SELECT and return at most `max_rows` rows.

    The validator already adds TOP to the query; fetchmany() is a second,
    independent limit in case a query (e.g. a UNION) still returns more."""
    conn = get_connection(settings)
    try:
        cursor = conn.cursor()
        cursor.execute(sql)
        if cursor.description is None:
            raise DatabaseError("The statement did not return a result set.")
        columns = [col[0] or f"column_{i + 1}" for i, col in enumerate(cursor.description)]
        raw_rows = cursor.fetchmany(max_rows + 1)   # one extra row tells us if there were more
        rows = [[to_json_safe(v) for v in row] for row in raw_rows[:max_rows]]
        return QueryResult(columns=columns, rows=rows, truncated=len(raw_rows) > max_rows)
    except pyodbc.Error as exc:
        raise DatabaseError(clean_error_message(exc)) from exc
    finally:
        conn.close()


def check_connection(settings: Settings | None = None) -> tuple[bool, str]:
    """Used by the /health endpoint: can we log in and run a trivial query?"""
    try:
        result = run_query("SELECT DB_NAME() AS DatabaseName, SUSER_NAME() AS LoginName", 1, settings)
        db_name, login = result.rows[0]
        return True, f"Connected to {db_name} as {login}"
    except DatabaseError as exc:
        return False, str(exc)
