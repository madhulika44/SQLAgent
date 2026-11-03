import "./StatusPill.css";

/**
 * Small coloured badge in the header showing whether the backend is healthy.
 *
 * Props:
 *   health  - the JSON from GET /health, or null while we haven't heard back yet
 *   offline - true when the last /health call failed (backend not reachable)
 */
export default function StatusPill({ health, offline }) {
  let state = "checking";
  let label = "Checking...";
  let tooltip = "Waiting for the backend";

  if (offline) {
    state = "offline";
    label = "Backend offline";
    tooltip = "Start it with: uvicorn app.main:app --reload (in the backend folder)";
  } else if (health) {
    const provider = health.llm.active_provider;
    tooltip = health.database.message;
    if (health.status === "ok") {
      state = "ok";
      label = `Connected - ${provider}`;
    } else {
      // The API answered but something behind it is wrong (DB down or no LLM key).
      state = "degraded";
      label = !health.database.ok ? "Database offline" : "No LLM configured";
    }
  }

  return (
    <span className={`status-pill status-pill--${state}`} title={tooltip}>
      <span className="status-pill__dot" />
      {label}
    </span>
  );
}
