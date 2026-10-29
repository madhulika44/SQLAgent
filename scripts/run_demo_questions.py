"""
Dress rehearsal: run every curated demo question and report what happened.

Run from the repository root (with the venv active):
    python scripts/run_demo_questions.py
    python scripts/run_demo_questions.py --persona Marketing --delay 10
    python scripts/run_demo_questions.py --limit 3

For each question it prints PASS/FAIL, provider, attempts, rows and timing,
and it writes a full report (SQL, explanation, sample rows) to
demo_results.md. Run it the day before AND the morning of the demo: LLM
answers can vary, and free-tier providers can be overloaded.

PASS = SQL ran without error and returned at least one row.
"""

import argparse
import logging
import sys
import time
from datetime import datetime
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT / "backend"))   # so `import app...` works from the repo root

from app.agent import AgentResult, SQLAgent  # noqa: E402
from app.chart import suggest_chart  # noqa: E402
from app.config import get_settings  # noqa: E402
from app.examples import EXAMPLES  # noqa: E402

SAMPLE_ROWS_IN_REPORT = 5


def status_of(result: AgentResult) -> str:
    if result.error or not result.sql or result.row_count == 0:
        return "FAIL"
    return "PASS (retried)" if result.attempts > 1 else "PASS"


def md_cell(value) -> str:
    """Make a value safe to put inside a Markdown table cell."""
    return ("NULL" if value is None else str(value)).replace("|", "\\|").replace("\n", " ")


def markdown_table(columns: list[str], rows: list[list]) -> str:
    lines = ["| " + " | ".join(md_cell(c) for c in columns) + " |",
             "|" + "---|" * len(columns)]
    lines += ["| " + " | ".join(md_cell(v) for v in row) + " |" for row in rows]
    return "\n".join(lines)


def write_report(path: Path, runs: list[tuple[dict, AgentResult]], total_seconds: float) -> None:
    settings = get_settings()
    passed = sum(1 for _, r in runs if status_of(r).startswith("PASS"))
    out = [
        "# Demo rehearsal results",
        "",
        f"- **Run at:** {datetime.now():%Y-%m-%d %H:%M}",
        f"- **Primary LLM:** {settings.llm_provider} "
        f"({settings.groq_model if settings.llm_provider == 'groq' else settings.gemini_model}), "
        f"fallback enabled: {settings.llm_fallback_enabled}",
        f"- **Result:** {passed}/{len(runs)} passed in {total_seconds:.0f}s",
        "",
        "| # | Persona | Question | Status | Provider | Attempts | Rows | Time (s) |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for i, (ex, r) in enumerate(runs, start=1):
        out.append(f"| {i} | {ex['persona']} | {md_cell(ex['question'])} | {status_of(r)} | "
                   f"{r.provider or '-'} | {r.attempts} | {r.row_count} | {r.total_time_ms / 1000:.1f} |")

    for i, (ex, r) in enumerate(runs, start=1):
        chart = suggest_chart(r.columns, r.rows)
        out += [
            "", "---", "",
            f"## {i}. {ex['question']}",
            "",
            f"**Status:** {status_of(r)} &nbsp; **Persona:** {ex['persona']} &nbsp; "
            f"**Concepts:** {', '.join(ex['concepts'])} &nbsp; **Chart:** {chart['type']}",
            "",
            f"**Expected insight:** {ex['insight']}",
        ]
        if r.sql:
            out += ["", "```sql", r.sql, "```"]
        if r.explanation:
            out += ["", f"**Explanation:** {r.explanation}"]
        if r.columns:
            shown = r.rows[:SAMPLE_ROWS_IN_REPORT]
            out += ["", f"**First {len(shown)} of {r.row_count} row(s):**", "", markdown_table(r.columns, shown)]
        if r.error:
            out += ["", f"**Error:** {r.error}"]
        problems = [s for s in r.trace if s.status != "ok"]
        if problems:
            out += ["", "**Trace notes:**"] + [f"- attempt {s.attempt}: `{s.step}` - {s.detail}" for s in problems]

    path.write_text("\n".join(out) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description="Run all demo questions and write demo_results.md")
    parser.add_argument("--delay", type=float, default=20,
                        help="seconds to wait between questions (free-tier rate limits; default 20)")
    parser.add_argument("--persona", help="only run questions for this persona, e.g. Marketing")
    parser.add_argument("--limit", type=int, help="only run the first N questions")
    parser.add_argument("--output", default=str(REPO_ROOT / "demo_results.md"), help="report file path")
    args = parser.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.ERROR)     # keep the console readable

    examples = [e for e in EXAMPLES if not args.persona or e["persona"].lower() == args.persona.lower()]
    examples = examples[: args.limit] if args.limit else examples
    if not examples:
        print("No questions match those filters.")
        return 1

    agent = SQLAgent()
    runs, started = [], time.perf_counter()
    print(f"Running {len(examples)} demo question(s), {args.delay:.0f}s apart...\n")

    for i, example in enumerate(examples, start=1):
        if i > 1:
            time.sleep(args.delay)
        result = agent.ask(example["question"])
        runs.append((example, result))
        print(f"[{i:>2}/{len(examples)}] {status_of(result):<14} {result.total_time_ms / 1000:5.1f}s  "
              f"{(result.provider or '-'):<7} attempts={result.attempts} rows={result.row_count:<4} "
              f"{example['question']}")
        if result.error:
            print(f"        ERROR: {result.error[:200]}")

    total = time.perf_counter() - started
    output = Path(args.output)
    write_report(output, runs, total)

    failed = [ex["question"] for ex, r in runs if status_of(r) == "FAIL"]
    print(f"\n{len(runs) - len(failed)}/{len(runs)} passed in {total:.0f}s. Report written to {output}")
    if failed:
        print("Failed questions (re-run them, or rephrase / drop them from the demo):")
        for question in failed:
            print(f"  - {question}")
    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
