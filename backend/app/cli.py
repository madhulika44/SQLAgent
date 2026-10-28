"""
Command-line interface for testing the agent without the API.

Run from the backend/ folder:
    python -m app.cli "Which city had the most orders last month?"
    python -m app.cli "Top 5 restaurants by revenue" --rows 5
    python -m app.cli "..." --json            # full result as JSON (same shape as POST /ask)
    python -m app.cli --show-schema           # print the schema text sent to the LLM
"""

import argparse
import json
import logging
import sys

from app.agent import AgentResult, SQLAgent
from app.config import get_settings
from app.schema_loader import get_schema

STATUS_ICON = {"ok": "[ok]   ", "error": "[FAIL] ", "info": "[info] "}


def format_cell(value, width: int) -> str:
    text = "NULL" if value is None else str(value)
    return text if len(text) <= width else text[: width - 3] + "..."


def print_table(columns: list[str], rows: list[list], max_rows: int, max_width: int = 32) -> None:
    """Print rows as a simple aligned text table."""
    shown = rows[:max_rows]
    widths = [min(max_width, max([len(c)] + [len(format_cell(r[i], max_width)) for r in shown]))
              for i, c in enumerate(columns)]
    line = "+-" + "-+-".join("-" * w for w in widths) + "-+"
    print(line)
    print("| " + " | ".join(c[:w].ljust(w) for c, w in zip(columns, widths)) + " |")
    print(line)
    for row in shown:
        print("| " + " | ".join(format_cell(v, w).ljust(w) for v, w in zip(row, widths)) + " |")
    print(line)
    if len(rows) > len(shown):
        print(f"... {len(rows) - len(shown)} more row(s) not shown (use --rows to show more)")


def print_result(result: AgentResult, max_rows: int, show_trace: bool) -> None:
    print(f"\nQUESTION   : {result.question}")
    print(f"PROVIDER   : {result.provider or '-'}   ATTEMPTS: {result.attempts}   TIME: {result.total_time_ms} ms")

    if result.sql:
        print("\nSQL:\n" + result.sql)
    if result.explanation:
        print(f"\nEXPLANATION: {result.explanation}")

    if result.columns:
        print(f"\nRESULT ({result.row_count} row(s){', truncated' if result.truncated else ''}):")
        print_table(result.columns, result.rows, max_rows)
    if result.error:
        print(f"\nERROR: {result.error}")

    if show_trace:
        print("\nTRACE:")
        for i, step in enumerate(result.trace, start=1):
            attempt = f"(attempt {step.attempt}) " if step.attempt else ""
            print(f"  {i:>2}. {STATUS_ICON.get(step.status, step.status)}{step.step:<15} "
                  f"{step.duration_ms:>6} ms  {attempt}{step.detail}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Ask the SQL Agent a question in plain English.")
    parser.add_argument("question", nargs="?", help="the business question (in quotes)")
    parser.add_argument("--rows", type=int, default=20, help="how many result rows to print (default 20)")
    parser.add_argument("--json", action="store_true", help="print the full result as JSON")
    parser.add_argument("--no-trace", action="store_true", help="hide the step-by-step trace")
    parser.add_argument("--show-schema", action="store_true", help="print the schema text the LLM sees")
    args = parser.parse_args()

    # Windows terminals default to a legacy code page; force UTF-8 so names print correctly.
    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=get_settings().log_level.upper(),
                        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")

    if args.show_schema:
        text = get_schema().to_prompt_text()
        print(text)
        print(f"\n({len(text):,} characters, roughly {len(text) // 4:,} tokens)")
        return 0
    if not args.question:
        parser.error("please provide a question, e.g. python -m app.cli \"How many orders per city?\"")

    result = SQLAgent().ask(args.question)
    if args.json:
        print(json.dumps(result.to_dict(), indent=2, ensure_ascii=False))
    else:
        print_result(result, args.rows, show_trace=not args.no_trace)
    return 1 if result.error else 0


if __name__ == "__main__":
    sys.exit(main())
