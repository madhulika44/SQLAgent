"""Tests for guardrail #2 - the sqlglot validator. No database or LLM needed."""

import pytest

from app.validator import validate_sql

MAX_ROWS = 200


# ---------------------------------------------------------------------
# Queries that must be ALLOWED
# ---------------------------------------------------------------------
@pytest.mark.parametrize("sql", [
    "SELECT c.CityName FROM dbo.Cities AS c",
    "SELECT TOP (5) c.CityName FROM dbo.Cities AS c ORDER BY c.CityName",
    "WITH m AS (SELECT o.Status, COUNT(*) AS n FROM dbo.Orders AS o GROUP BY o.Status) SELECT m.Status, m.n FROM m",
    "SELECT o.OrderID, ROW_NUMBER() OVER (PARTITION BY o.CustomerID ORDER BY o.OrderDateTime) AS rn FROM dbo.Orders AS o",
    "SELECT c.CityName FROM dbo.Cities AS c WHERE NOT EXISTS (SELECT 1 FROM dbo.Areas AS a WHERE a.CityID = c.CityID)",
    "SELECT a.CityName FROM dbo.Cities a UNION ALL SELECT b.CityName FROM dbo.Cities b",
    "SELECT c.CityName FROM dbo.Cities AS c;",                    # trailing semicolon is fine
])
def test_allowed_queries(sql):
    result = validate_sql(sql, MAX_ROWS)
    assert result.is_valid, result.reason


def test_words_inside_string_literals_are_not_blocked():
    # 'Delete' and 'drop' appear only inside a string -> not a keyword.
    sql = "SELECT o.OrderID FROM dbo.Orders AS o WHERE o.CancellationReason = N'Please delete or drop my order'"
    assert validate_sql(sql, MAX_ROWS).is_valid


def test_column_names_containing_keywords_are_allowed():
    assert validate_sql("SELECT t.UpdatedAt, t.CreatedBy FROM dbo.Things AS t", MAX_ROWS).is_valid


# ---------------------------------------------------------------------
# Queries that must be BLOCKED
# ---------------------------------------------------------------------
@pytest.mark.parametrize("sql, expected_reason", [
    ("DELETE FROM dbo.Orders", "DELETE"),
    ("UPDATE dbo.Orders SET TotalAmount = 0", "UPDATE"),
    ("INSERT INTO dbo.Cities (CityName) VALUES ('X')", "INSERT"),
    ("MERGE dbo.Cities AS t USING dbo.Areas AS s ON 1 = 1 WHEN MATCHED THEN DELETE;", "MERGE"),
    ("DROP TABLE dbo.Orders", "DROP"),
    ("ALTER TABLE dbo.Orders ADD x INT", "ALTER"),
    ("CREATE TABLE dbo.Hack (x INT)", "CREATE"),
    ("TRUNCATE TABLE dbo.Ratings", "TRUNCATE"),
    ("EXEC xp_cmdshell 'dir'", "EXEC"),
    ("EXECUTE sp_executesql N'SELECT 1'", "EXECUTE"),
    ("GRANT SELECT ON dbo.Orders TO public", "GRANT"),
    ("SELECT * INTO dbo.Copy FROM dbo.Orders", "INTO"),
    ("SELECT * FROM OPENROWSET('SQLNCLI', 'Server=x;', 'SELECT 1')", "OPENROWSET"),
    ("SELECT 1; DROP TABLE dbo.Orders", "DROP"),
    ("WAITFOR DELAY '00:01:00'", "WAITFOR"),
    ("SELECT name FROM sys.objects WHERE 1 = 1; SELECT 2", "Exactly one statement"),
    ("SELECT sp_helptext FROM t", "SP_HELPTEXT"),
])
def test_blocked_queries(sql, expected_reason):
    result = validate_sql(sql, MAX_ROWS)
    assert not result.is_valid
    assert expected_reason in result.reason


@pytest.mark.parametrize("sql", ["", "   ", None])
def test_empty_query_is_rejected(sql):
    result = validate_sql(sql, MAX_ROWS)
    assert not result.is_valid and "empty" in result.reason


def test_invalid_syntax_is_rejected():
    result = validate_sql("SELEC city FROM (", MAX_ROWS)
    assert not result.is_valid and "not valid T-SQL" in result.reason


# ---------------------------------------------------------------------
# TOP enforcement
# ---------------------------------------------------------------------
def test_top_is_added_when_missing():
    result = validate_sql("SELECT c.CityName FROM dbo.Cities AS c", MAX_ROWS)
    assert "TOP 200" in result.sql.replace("\n", " ")
    assert result.changes


def test_top_is_added_to_the_outer_query_of_a_cte():
    sql = "WITH x AS (SELECT o.OrderID FROM dbo.Orders AS o) SELECT x.OrderID FROM x"
    result = validate_sql(sql, MAX_ROWS)
    outer = result.sql.split(")")[-1]           # text after the CTE
    assert "TOP 200" in outer.replace("\n", " ")


def test_existing_top_is_kept_unchanged():
    sql = "SELECT TOP (5) c.CityName FROM dbo.Cities AS c"
    result = validate_sql(sql, MAX_ROWS)
    assert result.sql == sql and not result.changes


def test_offset_fetch_paging_is_left_alone():
    sql = "SELECT o.OrderID FROM dbo.Orders AS o ORDER BY o.OrderID OFFSET 0 ROWS FETCH NEXT 10 ROWS ONLY"
    result = validate_sql(sql, MAX_ROWS)
    assert result.is_valid and "TOP" not in result.sql
