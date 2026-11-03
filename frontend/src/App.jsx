import { useCallback, useEffect, useState } from "react";
import { askQuestion, getHealth } from "./api";
import DataTable from "./components/DataTable";
import InfoBar from "./components/InfoBar";
import LoadingSteps from "./components/LoadingSteps";
import MessageBox from "./components/MessageBox";
import QuestionBox from "./components/QuestionBox";
import StatusPill from "./components/StatusPill";

const HEALTH_CHECK_INTERVAL_MS = 30_000;

/**
 * The top-level component. It owns the app's state and passes pieces of it
 * down to smaller components as props:
 *
 *   question   - text in the question box
 *   result     - the last POST /ask response (or null)
 *   loading    - true while waiting for the backend
 *   askError   - set when the request itself failed (backend down, 422, ...)
 *   health     - last GET /health response; healthOffline = it couldn't be reached
 */
export default function App() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [askError, setAskError] = useState(null);
  const [health, setHealth] = useState(null);
  const [healthOffline, setHealthOffline] = useState(false);

  // Check /health on start-up and then every 30 seconds, so the pill turns
  // red if the backend is stopped mid-demo (and green again when it's back).
  useEffect(() => {
    async function checkHealth() {
      try {
        setHealth(await getHealth());
        setHealthOffline(false);
      } catch {
        setHealthOffline(true);
      }
    }
    checkHealth();
    const timer = setInterval(checkHealth, HEALTH_CHECK_INTERVAL_MS);
    return () => clearInterval(timer);
  }, []);

  // useCallback keeps the same function between renders; the sidebar (Phase 2)
  // will call it when an example question is clicked.
  const handleAsk = useCallback(async (text) => {
    setQuestion(text);
    setLoading(true);
    setAskError(null);
    setResult(null);
    try {
      setResult(await askQuestion(text));
    } catch (error) {
      setAskError(error.message);
    } finally {
      setLoading(false); // runs whether the request succeeded or failed
    }
  }, []);

  return (
    <div className="app">
      <header className="app-header">
        <h1 className="app-title">
          SQL Agent <span>- Food Delivery Analytics</span>
        </h1>
        <div className="app-header-actions">
          <StatusPill health={health} offline={healthOffline} />
        </div>
      </header>

      <aside className="app-sidebar">
        <p className="placeholder">Example questions and history arrive in UI Phase 2.</p>
      </aside>

      <main className="app-main">
        <QuestionBox value={question} onChange={setQuestion} onSubmit={handleAsk} loading={loading} />

        {loading && <LoadingSteps />}

        {askError && (
          <MessageBox variant="error" title="Could not get an answer">
            {askError}
          </MessageBox>
        )}

        {result && <ResultView result={result} />}

        {!loading && !result && !askError && (
          <div className="empty-state">
            <h2>Ask anything about orders, restaurants, riders or customers</h2>
            <p>The agent writes the SQL, runs it on SQL Server and shows you the answer.</p>
          </div>
        )}
      </main>
    </div>
  );
}

/** What to show for one /ask response (Phase 2 turns this into tabs). */
function ResultView({ result }) {
  const declined = !result.error && !result.sql;

  return (
    <>
      <InfoBar result={result} />

      {result.error && (
        <MessageBox variant="error" title="The agent could not answer this question">
          {result.error}
        </MessageBox>
      )}

      {declined && (
        <MessageBox variant="info" title="No query was run">
          {result.explanation || "The agent decided this question can't be answered from the database."}
        </MessageBox>
      )}

      {result.sql && result.explanation && <p className="result-explanation">{result.explanation}</p>}

      {result.sql && !result.error && (
        <DataTable columns={result.columns} rows={result.rows} truncated={result.truncated} />
      )}
    </>
  );
}
