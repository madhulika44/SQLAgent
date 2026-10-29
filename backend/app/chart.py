"""
Suggest a simple chart for a query result - by looking at the SHAPE of the
data only (no LLM call, so it's instant and free).

Rules, checked in order:
  1. Fewer than 2 rows, or no numeric column            -> none
  2. A time-like column (date, month, hour...) + numbers -> line
  3. A text (category) column + exactly one number that
     adds up (a count/total, not an average or rate),
     at most 6 rows, all values >= 0                     -> pie
  4. A text (category) column + numbers, <= 30 rows      -> bar
  5. Anything else                                       -> none

The React UI can follow the suggestion or let the user switch chart type.
"""

import re
from datetime import date, datetime

# Column names that usually mean "this is a time axis".
TIME_NAME_PATTERN = re.compile(r"date|month|year|week|day|hour|time|period", re.IGNORECASE)
# Values like "2026-03" or "2026-03-15" or "2026-03-15T10:00:00".
ISO_DATE_PATTERN = re.compile(r"^\d{4}-\d{2}(-\d{2})?([T ]\d{2}:\d{2}(:\d{2})?)?$")
# Measures that can't be summed into a whole (so a pie chart would mislead).
NOT_ADDITIVE_PATTERN = re.compile(r"avg|average|mean|rate|min|max|median", re.IGNORECASE)

MAX_PIE_SLICES = 6
MAX_BAR_CATEGORIES = 30
MAX_Y_SERIES = 3
SCALE_RATIO_LIMIT = 10   # series whose peaks differ more than 10x don't share an axis


def is_number(value) -> bool:
    # bool is a subclass of int in Python, but a True/False column is not a measure.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def column_values(rows: list[list], index: int) -> list:
    return [row[index] for row in rows if row[index] is not None]


def is_numeric_column(rows, index) -> bool:
    values = column_values(rows, index)
    return bool(values) and all(is_number(v) for v in values)


def is_text_column(rows, index) -> bool:
    values = column_values(rows, index)
    return bool(values) and all(isinstance(v, str) for v in values)


def is_time_column(name: str, rows, index) -> bool:
    values = column_values(rows, index)
    if not values:
        return False
    if all(isinstance(v, (date, datetime)) or (isinstance(v, str) and ISO_DATE_PATTERN.match(v)) for v in values):
        return True
    # e.g. "OrderMonth" = 'Jan', "HourOfDay" = 13
    return bool(TIME_NAME_PATTERN.search(name)) and not name.lower().endswith("id")


def is_id_column(name: str) -> bool:
    """CustomerID, RestaurantID ... are numbers, but plotting them is meaningless."""
    return name.endswith("ID") or name.endswith("Id") or name.lower() == "id"


def plottable_together(rows: list[list], numeric_cols: list[int]) -> list[int]:
    """Keep several series only if they're on a similar scale.

    OrderCount (73,632) and SharePct (91.31) on one axis would squash the
    percentage into an invisible line at zero, so when the largest values
    differ by more than SCALE_RATIO_LIMIT we plot only the first number."""
    if len(numeric_cols) < 2:
        return numeric_cols
    peaks = [max(abs(v) for v in column_values(rows, i)) for i in numeric_cols]
    smallest, largest = min(peaks), max(peaks)
    if smallest == 0 or largest / smallest > SCALE_RATIO_LIMIT:
        return numeric_cols[:1]
    return numeric_cols


def suggest_chart(columns: list[str], rows: list[list]) -> dict:
    none = {"type": "none", "x": None, "y": []}
    if len(rows) < 2 or len(columns) < 2:
        return none

    time_cols = [i for i, c in enumerate(columns) if is_time_column(c, rows, i)]
    numeric_cols = [i for i, c in enumerate(columns)
                    if is_numeric_column(rows, i) and not is_id_column(c) and i not in time_cols]
    text_cols = [i for i, c in enumerate(columns)
                 if is_text_column(rows, i) and i not in time_cols]
    if not numeric_cols:
        return none
    y = [columns[i] for i in plottable_together(rows, numeric_cols[:MAX_Y_SERIES])]

    # Rule 2: something over time -> line chart.
    if time_cols:
        return {"type": "line", "x": columns[time_cols[0]], "y": y}

    if not text_cols:
        return none
    x = columns[text_cols[0]]

    # Rule 3: a handful of categories sharing one total -> pie chart.
    # Averages and rates are not "parts of a whole", so they never become a pie.
    if len(numeric_cols) == 1 and len(rows) <= MAX_PIE_SLICES \
            and not NOT_ADDITIVE_PATTERN.search(y[0]) \
            and all(v >= 0 for v in column_values(rows, numeric_cols[0])):
        return {"type": "pie", "x": x, "y": y}

    # Rule 4: comparing categories -> bar chart.
    if len(rows) <= MAX_BAR_CATEGORIES:
        return {"type": "bar", "x": x, "y": y}
    return none
