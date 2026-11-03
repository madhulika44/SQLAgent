import { formatDuration } from "../utils/format";
import "./TraceTimeline.css";

// Friendly names for the step ids the backend uses (backend/app/agent.py).
const STEP_LABELS = {
  load_schema: "Load schema",
  build_prompt: "Build prompt",
  call_llm: "Ask the LLM",
  llm_fallback: "Switched LLM provider",
  rate_limit_wait: "Waited for rate limit",
  parse_response: "Read the LLM's reply",
  validate_sql: "Validate SQL (guardrail)",
  execute_sql: "Run on SQL Server",
  agent: "Agent",
};

/**
 * Decide how a step should look. The "interesting" moments for a demo -
 * a provider fallback, a rate-limit wait, a retry - get their own style.
 */
function kindOf(step) {
  if (step.step === "llm_fallback") return "fallback";
  if (step.step === "rate_limit_wait") return "wait";
  if (step.status === "error") return "error";
  if (step.attempt > 1) return "retry";
  if (step.status === "info") return "info";
  return "ok";
}

const ICONS = { ok: "✓", error: "✕", info: "ℹ", fallback: "⇄", wait: "⏱", retry: "↻" };
const BADGES = { fallback: "Fallback", wait: "Rate limit", retry: "Retry", error: "Problem" };

/** A one-line story of the run, e.g. "2 attempts · switched to gemini once · 1 problem fixed". */
function summarize(trace, attempts) {
  const fallbacks = trace.filter((s) => s.step === "llm_fallback").length;
  const waits = trace.filter((s) => s.step === "rate_limit_wait").length;
  const problems = trace.filter((s) => s.status === "error").length;
  const parts = [`${attempts} attempt${attempts === 1 ? "" : "s"}`];
  if (fallbacks) parts.push(`${fallbacks} provider fallback${fallbacks === 1 ? "" : "s"}`);
  if (waits) parts.push(`${waits} rate-limit wait${waits === 1 ? "" : "s"}`);
  if (problems) parts.push(`${problems} problem${problems === 1 ? "" : "s"} caught`);
  return parts.join(" · ");
}

/**
 * Vertical timeline of everything the agent did.
 * Props: trace (array of steps from POST /ask), attempts, totalTimeMs
 */
export default function TraceTimeline({ trace, attempts, totalTimeMs }) {
  // Width of each step's duration bar, relative to the slowest step.
  const longest = Math.max(1, ...trace.map((s) => s.duration_ms));

  return (
    <div className="trace">
      <div className="trace__summary">
        <strong>{summarize(trace, attempts)}</strong>
        <span>Total {formatDuration(totalTimeMs)}</span>
      </div>

      <ol className="trace__list">
        {trace.map((step, index) => {
          const kind = kindOf(step);
          return (
            <li key={index} className={`trace__step trace__step--${kind}`}>
              <span className="trace__icon" aria-hidden="true">{ICONS[kind]}</span>
              <div className="trace__body">
                <div className="trace__header">
                  <span className="trace__name">{STEP_LABELS[step.step] || step.step}</span>
                  {step.attempt && <span className="trace__attempt">attempt {step.attempt}</span>}
                  {BADGES[kind] && <span className="trace__badge">{BADGES[kind]}</span>}
                  <span className="trace__duration">{formatDuration(step.duration_ms)}</span>
                </div>
                <div className="trace__detail">{step.detail}</div>
                {step.duration_ms > 0 && (
                  <div className="trace__bar" style={{ width: `${(step.duration_ms / longest) * 100}%` }} />
                )}
                {/* SQL is shown for failed attempts (open) and successful runs (collapsed). */}
                {step.sql && (step.step === "execute_sql" || step.status === "error") && (
                  <details className="trace__sql" open={step.status === "error"}>
                    <summary>SQL tried in this step</summary>
                    <pre>{step.sql}</pre>
                  </details>
                )}
              </div>
            </li>
          );
        })}
      </ol>
    </div>
  );
}
