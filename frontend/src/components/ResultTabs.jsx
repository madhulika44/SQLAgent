import { lazy, Suspense, useState } from "react";
import DataTable from "./DataTable";
import SqlView from "./SqlView";
import TraceTimeline from "./TraceTimeline";
import "./ResultTabs.css";

// Recharts is big (~400 kB). lazy() loads ChartView - and Recharts with it -
// only the first time the Chart tab is opened, so the app starts faster.
const ChartView = lazy(() => import("./ChartView"));

/**
 * The four views of one answer: Result, Chart, SQL, Agent Trace.
 *
 * Which tabs exist depends on the answer:
 *   - success           -> all four, starting on Result
 *   - error             -> SQL (if any was generated) + Trace, starting on Trace
 *   - declined (no SQL) -> Trace only
 *
 * The parent gives this component a new `key` for every answer, so React
 * creates it fresh and the selected tab resets to the default.
 */
export default function ResultTabs({ result }) {
  const hasData = Boolean(result.sql && !result.error);
  // Fallbacks, waits and failed steps are worth pointing at: count them for a badge.
  const traceEvents = result.trace.filter(
    (s) => s.status !== "ok" || s.step === "llm_fallback" || s.step === "rate_limit_wait"
  ).length;

  const tabs = [
    hasData && { id: "result", label: "Result" },
    hasData && { id: "chart", label: "Chart" },
    result.sql && { id: "sql", label: "SQL" },
    { id: "trace", label: "Agent Trace", badge: traceEvents || null },
  ].filter(Boolean);

  const [activeTab, setActiveTab] = useState(hasData ? "result" : "trace");

  return (
    <div className="result-tabs">
      <div className="result-tabs__bar" role="tablist">
        {tabs.map((tab) => (
          <button
            key={tab.id}
            role="tab"
            aria-selected={activeTab === tab.id}
            className={`result-tabs__tab ${activeTab === tab.id ? "result-tabs__tab--active" : ""}`}
            onClick={() => setActiveTab(tab.id)}
          >
            {tab.label}
            {tab.badge && <span className="result-tabs__badge" title="Steps worth a look">{tab.badge}</span>}
          </button>
        ))}
      </div>

      <div className="result-tabs__panel" role="tabpanel">
        {activeTab === "result" && (
          <>
            {result.explanation && <p className="result-explanation">{result.explanation}</p>}
            <DataTable columns={result.columns} rows={result.rows} truncated={result.truncated} />
          </>
        )}
        {activeTab === "chart" && (
          // Suspense shows the fallback while the chart code is still downloading.
          <Suspense fallback={<p className="placeholder">Loading chart...</p>}>
            <ChartView chart={result.chart} columns={result.columns} rows={result.rows} />
          </Suspense>
        )}
        {activeTab === "sql" && <SqlView sql={result.sql} />}
        {activeTab === "trace" && (
          <TraceTimeline trace={result.trace} attempts={result.attempts} totalTimeMs={result.total_time_ms} />
        )}
      </div>
    </div>
  );
}
