"""
Reads the database schema LIVE and turns it into text for the LLM.

The LLM has never seen our database. Everything it knows about tables,
columns and relationships comes from the text built here, so this text
decides how good the generated SQL can be. We include:

  - tables and columns with data types           (INFORMATION_SCHEMA)
  - primary keys and foreign keys (join paths)   (sys.foreign_keys)
  - plain-English descriptions                   (MS_Description extended properties)
  - sample values for low-cardinality text columns, e.g.
    Status: 'Cancelled', 'Delivered', 'Failed'  -> the LLM uses the exact spelling

Reading it live (instead of hard-coding it) means the agent automatically
knows about new columns or changed descriptions after POST /schema/refresh.
The result is cached in memory because the schema rarely changes and
reading it takes a few hundred milliseconds.
"""

import logging
import re
import threading
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime

from app.config import Settings, get_settings
from app.db import run_query

logger = logging.getLogger(__name__)

# Only these types can hold "category-like" values worth sampling.
TEXT_TYPES = {"char", "varchar", "nchar", "nvarchar"}


@dataclass
class Column:
    name: str
    data_type: str                 # e.g. "varchar(10)", "decimal(10,2)"
    nullable: bool
    description: str = ""
    is_primary_key: bool = False
    references: str | None = None  # "Customers.CustomerID" if this is a foreign key
    sample_values: list[str] = field(default_factory=list)


@dataclass
class Table:
    name: str
    description: str = ""
    columns: list[Column] = field(default_factory=list)


@dataclass
class Relationship:
    from_table: str
    from_column: str
    to_table: str
    to_column: str


@dataclass
class SchemaInfo:
    database: str
    tables: list[Table]
    relationships: list[Relationship]
    loaded_at: str
    load_time_ms: int

    def to_prompt_text(self) -> str:
        """Compact, LLM-friendly description of the schema.

        Format (one line per column keeps it short - every token counts on a
        free tier with a tokens-per-minute limit):
            ## Orders: One row per food order...
            - OrderID int PK
            - CustomerID int FK->Customers.CustomerID | Customer who placed the order...
            - Status varchar(10) | Final order status... | values: 'Cancelled', 'Delivered', 'Failed'
        """
        lines = []
        for table in self.tables:
            lines.append(f"## {table.name}: {table.description}")
            for col in table.columns:
                parts = [f"- {col.name} {col.data_type}"]
                if col.is_primary_key:
                    parts.append("PK")
                if col.references:
                    parts.append(f"FK->{col.references}")
                if col.nullable:
                    parts.append("NULL")
                line = " ".join(parts)
                # The PK description ("Unique ID of ...") adds nothing - skip it to save tokens.
                # "Foreign key to X.Y." repeats the FK-> marker, so drop that phrase too.
                description = re.sub(r"\s*Foreign key to \w+\.\w+\.?", "", col.description).strip()
                if description and not col.is_primary_key:
                    line += f" | {description}"
                if col.sample_values:
                    line += " | values: " + ", ".join(f"'{v}'" for v in col.sample_values)
                lines.append(line)
            lines.append("")
        return "\n".join(lines).strip()

    def to_dict(self) -> dict:
        """JSON-friendly version for the GET /schema endpoint."""
        return asdict(self)


# ---------------------------------------------------------------------
# Queries against the catalog views
# ---------------------------------------------------------------------

TABLES_SQL = """
SELECT t.TABLE_NAME,
       CAST(ep.value AS NVARCHAR(4000)) AS Description
FROM INFORMATION_SCHEMA.TABLES AS t
LEFT JOIN sys.extended_properties AS ep
       ON ep.major_id = OBJECT_ID(t.TABLE_SCHEMA + '.' + t.TABLE_NAME)
      AND ep.minor_id = 0
      AND ep.name = 'MS_Description'
WHERE t.TABLE_TYPE = 'BASE TABLE' AND t.TABLE_SCHEMA = 'dbo'
ORDER BY t.TABLE_NAME
"""

COLUMNS_SQL = """
SELECT c.TABLE_NAME, c.COLUMN_NAME, c.DATA_TYPE, c.CHARACTER_MAXIMUM_LENGTH,
       c.NUMERIC_PRECISION, c.NUMERIC_SCALE, c.IS_NULLABLE,
       CAST(ep.value AS NVARCHAR(4000)) AS Description
FROM INFORMATION_SCHEMA.COLUMNS AS c
LEFT JOIN sys.extended_properties AS ep
       ON ep.major_id = OBJECT_ID(c.TABLE_SCHEMA + '.' + c.TABLE_NAME)
      AND ep.minor_id = COLUMNPROPERTY(OBJECT_ID(c.TABLE_SCHEMA + '.' + c.TABLE_NAME), c.COLUMN_NAME, 'ColumnId')
      AND ep.name = 'MS_Description'
WHERE c.TABLE_SCHEMA = 'dbo'
ORDER BY c.TABLE_NAME, c.ORDINAL_POSITION
"""

PRIMARY_KEYS_SQL = """
SELECT kcu.TABLE_NAME, kcu.COLUMN_NAME
FROM INFORMATION_SCHEMA.TABLE_CONSTRAINTS AS tc
JOIN INFORMATION_SCHEMA.KEY_COLUMN_USAGE AS kcu
  ON kcu.CONSTRAINT_NAME = tc.CONSTRAINT_NAME AND kcu.TABLE_SCHEMA = tc.TABLE_SCHEMA
WHERE tc.CONSTRAINT_TYPE = 'PRIMARY KEY' AND tc.TABLE_SCHEMA = 'dbo'
"""

FOREIGN_KEYS_SQL = """
SELECT OBJECT_NAME(fkc.parent_object_id)                               AS FromTable,
       COL_NAME(fkc.parent_object_id, fkc.parent_column_id)            AS FromColumn,
       OBJECT_NAME(fkc.referenced_object_id)                           AS ToTable,
       COL_NAME(fkc.referenced_object_id, fkc.referenced_column_id)    AS ToColumn
FROM sys.foreign_key_columns AS fkc
ORDER BY FromTable, FromColumn
"""


def format_data_type(data_type: str, max_length, precision, scale) -> str:
    """'varchar' + 10 -> 'varchar(10)'; 'decimal' + 10,2 -> 'decimal(10,2)'."""
    if data_type in TEXT_TYPES:
        return f"{data_type}({'max' if max_length == -1 else max_length})"
    if data_type in ("decimal", "numeric"):
        return f"{data_type}({precision},{scale})"
    return data_type


def quote_name(name: str) -> str:
    """Bracket-quote an identifier for SQL Server: Order Items -> [Order Items]."""
    return "[" + name.replace("]", "]]") + "]"


def load_sample_values(table: str, column: Column, max_distinct: int, settings: Settings) -> list[str]:
    """Return the distinct values of a text column, but only if there are few
    of them (e.g. Status, PaymentMethod, CityName). Names, emails etc. have
    thousands of values and are skipped automatically."""
    sql = (f"SELECT DISTINCT TOP ({max_distinct + 1}) {quote_name(column.name)} "
           f"FROM dbo.{quote_name(table)} WHERE {quote_name(column.name)} IS NOT NULL "
           f"ORDER BY {quote_name(column.name)}")
    values = [row[0] for row in run_query(sql, max_distinct + 1, settings).rows]
    return values if len(values) <= max_distinct else []


def load_schema(settings: Settings | None = None) -> SchemaInfo:
    """Read the full schema from SQL Server (no caching - see get_schema)."""
    settings = settings or get_settings()
    started = time.perf_counter()

    tables = {name: Table(name, description or "")
              for name, description in run_query(TABLES_SQL, 10_000, settings).rows}

    primary_keys = {(t, c) for t, c in run_query(PRIMARY_KEYS_SQL, 10_000, settings).rows}
    relationships = [Relationship(*row) for row in run_query(FOREIGN_KEYS_SQL, 10_000, settings).rows]
    fk_targets = {(r.from_table, r.from_column): f"{r.to_table}.{r.to_column}" for r in relationships}

    for table_name, col_name, dtype, max_len, precision, scale, nullable, description in \
            run_query(COLUMNS_SQL, 10_000, settings).rows:
        if table_name not in tables:
            continue
        tables[table_name].columns.append(Column(
            name=col_name,
            data_type=format_data_type(dtype, max_len, precision, scale),
            nullable=nullable == "YES",
            description=description or "",
            is_primary_key=(table_name, col_name) in primary_keys,
            references=fk_targets.get((table_name, col_name)),
        ))

    # Sample values for short text columns that are not keys.
    for table in tables.values():
        for col in table.columns:
            base_type = col.data_type.split("(")[0]
            if base_type in TEXT_TYPES and not col.is_primary_key and not col.references:
                col.sample_values = load_sample_values(table.name, col, settings.schema_sample_max_distinct, settings)

    elapsed_ms = int((time.perf_counter() - started) * 1000)
    logger.info("Schema loaded: %d tables, %d relationships in %d ms", len(tables), len(relationships), elapsed_ms)
    return SchemaInfo(
        database=settings.db_name,
        tables=list(tables.values()),
        relationships=relationships,
        loaded_at=datetime.now().isoformat(timespec="seconds"),
        load_time_ms=elapsed_ms,
    )


# ---------------------------------------------------------------------
# In-memory cache
# ---------------------------------------------------------------------
_cache: SchemaInfo | None = None
_cache_lock = threading.Lock()   # the API may serve several requests at once


def get_schema() -> SchemaInfo:
    """Return the cached schema, loading it the first time."""
    global _cache
    with _cache_lock:
        if _cache is None:
            _cache = load_schema()
        return _cache


def refresh_schema() -> SchemaInfo:
    """Throw away the cache and read the schema again (POST /schema/refresh)."""
    global _cache
    with _cache_lock:
        _cache = load_schema()
        return _cache


def is_schema_cached() -> bool:
    return _cache is not None
