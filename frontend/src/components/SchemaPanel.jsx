import { useEffect, useState } from "react";
import { getSchema, refreshSchema } from "../api";
import "./SchemaPanel.css";

/**
 * Slide-in panel (from the right) listing every table and column, with the
 * plain-English descriptions the LLM receives. Great for the demo moment
 * "this is all the agent knows about our database".
 *
 * Props: open (bool), onClose (function)
 */
export default function SchemaPanel({ open, onClose }) {
  const [schema, setSchema] = useState(null);
  const [error, setError] = useState(null);
  const [refreshing, setRefreshing] = useState(false);
  const [filter, setFilter] = useState("");

  // Load the schema the first time the panel is opened (not on page load).
  useEffect(() => {
    if (!open || schema) return;
    getSchema().then(setSchema).catch((e) => setError(e.message));
  }, [open, schema]);

  // Escape closes the panel - expected behaviour for any overlay.
  useEffect(() => {
    if (!open) return;
    const onKey = (event) => event.key === "Escape" && onClose();
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  async function handleRefresh() {
    setRefreshing(true);
    setError(null);
    try {
      setSchema(await refreshSchema());
    } catch (e) {
      setError(e.message);
    } finally {
      setRefreshing(false);
    }
  }

  const tables = filterTables(schema?.tables ?? [], filter);

  return (
    <>
      {/* The dimmed backdrop: clicking it closes the panel. */}
      <div className={`schema-backdrop ${open ? "schema-backdrop--open" : ""}`} onClick={onClose} />

      {/* inert = while closed, nothing inside can be focused or clicked (keyboard users can't tab into it). */}
      <aside className={`schema-panel ${open ? "schema-panel--open" : ""}`} inert={!open}
             aria-label="Database schema">
        <header className="schema-panel__header">
          <div>
            <h2>Database schema</h2>
            {schema && (
              <p className="schema-panel__meta">
                {schema.database} · {schema.tables.length} tables · {schema.relationships.length} relationships
                · loaded {schema.loaded_at.replace("T", " ")}
              </p>
            )}
          </div>
          <button className="schema-panel__close" onClick={onClose} aria-label="Close schema panel">✕</button>
        </header>

        <div className="schema-panel__tools">
          <input
            type="search"
            className="schema-panel__search"
            placeholder="Filter tables and columns, e.g. status, rating, INR"
            value={filter}
            onChange={(e) => setFilter(e.target.value)}
          />
          <button className="schema-panel__refresh" onClick={handleRefresh} disabled={refreshing}
                  title="Re-read the schema from SQL Server (POST /schema/refresh)">
            {refreshing ? "Refreshing..." : "↻ Refresh"}
          </button>
        </div>

        <div className="schema-panel__body">
          {error && <p className="schema-panel__error">Could not load the schema: {error}</p>}
          {!schema && !error && <p className="schema-panel__note">Loading schema...</p>}
          {schema && tables.length === 0 && <p className="schema-panel__note">Nothing matches "{filter}".</p>}

          {tables.map((table) => (
            // <details> gives a collapsible section with no JavaScript. Open all while filtering.
            <details key={table.name} className="schema-table" open={Boolean(filter)}>
              <summary>
                <span className="schema-table__name">{table.name}</span>
                <span className="schema-table__count">{table.columns.length} columns</span>
                <span className="schema-table__desc">{table.description}</span>
              </summary>
              <ul className="schema-columns">
                {table.columns.map((col) => (
                  <li key={col.name} className="schema-column">
                    <div className="schema-column__head">
                      <code className="schema-column__name">{col.name}</code>
                      <span className="schema-column__type">{col.data_type}</span>
                      {col.is_primary_key && <span className="schema-tag schema-tag--pk">PK</span>}
                      {col.references && <span className="schema-tag schema-tag--fk">FK → {col.references}</span>}
                      {col.nullable && <span className="schema-tag">NULL allowed</span>}
                    </div>
                    {col.description && <div className="schema-column__desc">{col.description}</div>}
                    {col.sample_values.length > 0 && (
                      <div className="schema-column__values">
                        {col.sample_values.map((v) => <span key={v} className="schema-value">{v}</span>)}
                      </div>
                    )}
                  </li>
                ))}
              </ul>
            </details>
          ))}
        </div>
      </aside>
    </>
  );
}

/** Keep tables whose name/description matches, or that have a matching column (only those columns). */
function filterTables(tables, filter) {
  const text = filter.trim().toLowerCase();
  if (!text) return tables;
  const matches = (s) => (s || "").toLowerCase().includes(text);
  return tables
    .map((table) => {
      if (matches(table.name) || matches(table.description)) return table;
      const columns = table.columns.filter(
        (c) => matches(c.name) || matches(c.description) || c.sample_values.some(matches)
      );
      return columns.length ? { ...table, columns } : null;
    })
    .filter(Boolean);
}
