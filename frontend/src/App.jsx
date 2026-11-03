import { useCallback, useEffect, useState } from "react";
import { askQuestion, getExamples, getHealth } from "./api";
import ExampleSidebar from "./components/ExampleSidebar";
import InfoBar from "./components/InfoBar";
import LoadingSteps from "./components/LoadingSteps";
import MessageBox from "./components/MessageBox";
import QuestionBox from "./components/QuestionBox";
import ResultTabs from "./components/ResultTabs";
import SchemaPanel from "./components/SchemaPanel";
import StatusPill from "./components/StatusPill";

const HEALTH_CHECK_INTERVAL_MS = 30_000;
const MAX_HISTORY = 10;

/** Classify an answer for the history list: "ok", "declined" or "error". */
function statusOf(result) {
  if (!result || result.error) return "error";
  return result.sql ? "ok" : "declined";
}

/**
 * The top-level component. It owns the app's state and passes pieces of it
 * down to smaller components as props:
 *
 *   question   - text in the question box
 *   result     - the last POST /ask response (or null); answerId changes with each answer
 *   loading    - true while waiting for the backend
 *   askError   - set when the request itself failed (backend down, 422, ...)
 *   history    - last 10 questions, newest first (in memory: gone after a page reload)
 *   examples   - GET /examples response, for the sidebar
 *   health     - last GET /health response; healthOffline = it couldn't be reached
 */
export default function App() {
  const [question, setQuestion] = useState("");
  const [result, setResult] = useState(null);
  const [answerId, setAnswerId] = useState(0);
  const [loading, setLoading] = useState(false);
  const [askError, setAskError] = useState(null);
  const [history, setHistory] = useState([]);
  const [examples, setExamples] = useState(null);
  const [examplesError, setExamplesError] = useState(null);
  const [health, setHealth] = useState(null);
  const [healthOffline, setHealthOffline] = useState(false);
  const [schemaOpen, setSchemaOpen] = useState(false);
  // Stable function so SchemaPanel's Escape-key listener isn't re-created on every render.
  const closeSchema = useCallback(() => setSchemaOpen(false), []);

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

  // Load the example questions once. If the backend was down, try again when it comes back.
  useEffect(() => {
    if (examples || healthOffline) return;
    getExamples()
      .then((data) => {
        setExamples(data);
        setExamplesError(null);
      })
      .catch((error) => setExamplesError(error.message));
  }, [examples, healthOffline]);

  function addToHistory(text, status) {
    setHistory((previous) => {
      // Asking the same question again moves it to the top instead of duplicating it.
      const others = previous.filter((item) => item.question !== text);
      return [{ question: text, status }, ...others].slice(0, MAX_HISTORY);
    });
  }

  // useCallback keeps the same function between renders, so child components
  // that receive it as a prop don't see a "new" function every time.
  const handleAsk = useCallback(async (text) => {
    setQuestion(text);
    setLoading(true);
    setAskError(null);
    setResult(null);
    try {
      const answer = await askQuestion(text);
      setResult(answer);
      setAnswerId((id) => id + 1);
      addToHistory(text, statusOf(answer));
    } catch (error) {
      setAskError(error.message);
      addToHistory(text, "error");
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
          <button className="header-button" onClick={() => setSchemaOpen(true)}>
            ☰ Schema
          </button>
        </div>
      </header>

      <SchemaPanel open={schemaOpen} onClose={closeSchema} />

      <aside className="app-sidebar">
        <ExampleSidebar
          examples={examples}
          loadError={examplesError}
          history={history}
          onSelect={handleAsk}
          disabled={loading}
        />
      </aside>

      <main className="app-main">
        <QuestionBox value={question} onChange={setQuestion} onSubmit={handleAsk} loading={loading} />

        {loading && <LoadingSteps />}

        {askError && (
          <MessageBox variant="error" title="Could not get an answer">
            {askError}
          </MessageBox>
        )}

        {result && <ResultView key={answerId} result={result} />}

        {!loading && !result && !askError && (
          <div className="empty-state">
            <h2>Ask anything about orders, restaurants, riders or customers</h2>
            <p>Type a question above, or pick an example on the left. The agent writes the SQL,
              runs it on SQL Server and shows you the answer.</p>
          </div>
        )}
      </main>
    </div>
  );
}

/** Everything shown for one /ask response. */
function ResultView({ result }) {
  const declined = !result.error && !result.sql;

  return (
    <>
      <InfoBar result={result} />

      {result.error && (
        <MessageBox variant="error" title="The agent could not answer this question">
          {result.error}
          {"\n"}The Agent Trace tab shows each step it tried.
        </MessageBox>
      )}

      {declined && (
        <MessageBox variant="info" title="No query was run">
          {result.explanation || "The agent decided this question can't be answered from the database."}
        </MessageBox>
      )}

      <ResultTabs result={result} />
    </>
  );
}
