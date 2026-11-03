import { useState } from "react";
import "./ExampleSidebar.css";

const TABS = [
  { id: "by_persona", label: "By Persona" },
  { id: "by_concept", label: "By SQL Concept" },
];

// Icon + text for each history status, so status is never shown by colour alone.
const HISTORY_STATUS = {
  ok: { icon: "✓", label: "answered" },
  declined: { icon: "ℹ", label: "declined" },
  error: { icon: "✕", label: "failed" },
};

/**
 * Left sidebar: recent questions + the curated examples from GET /examples.
 *
 * Props:
 *   examples  - { by_persona: [{group, questions}], by_concept: [...] } or null while loading
 *   loadError - message if /examples failed
 *   history   - [{question, status: "ok" | "declined" | "error"}], newest first
 *   onSelect  - called with a question string when one is clicked
 *   disabled  - true while a question is being answered
 */
export default function ExampleSidebar({ examples, loadError, history, onSelect, disabled }) {
  const [activeTab, setActiveTab] = useState("by_persona");

  return (
    <nav className="sidebar" aria-label="Example questions">
      {history.length > 0 && (
        <section className="sidebar__section">
          <h2 className="sidebar__heading">Recent questions</h2>
          <ul className="sidebar__list">
            {history.map((item) => {
              const status = HISTORY_STATUS[item.status];
              return (
                <li key={item.question}>
                  <button
                    className={`sidebar__question sidebar__question--history sidebar__question--${item.status}`}
                    onClick={() => onSelect(item.question)}
                    disabled={disabled}
                    title={`${item.question} (${status.label})`}
                  >
                    <span className="sidebar__status" aria-label={status.label}>{status.icon}</span>
                    <span className="sidebar__text">{item.question}</span>
                  </button>
                </li>
              );
            })}
          </ul>
        </section>
      )}

      <section className="sidebar__section">
        <h2 className="sidebar__heading">Example questions</h2>

        {/* role="tablist" + aria-selected tell screen readers these buttons act as tabs. */}
        <div className="sidebar__tabs" role="tablist">
          {TABS.map((tab) => (
            <button
              key={tab.id}
              role="tab"
              aria-selected={activeTab === tab.id}
              className={`sidebar__tab ${activeTab === tab.id ? "sidebar__tab--active" : ""}`}
              onClick={() => setActiveTab(tab.id)}
            >
              {tab.label}
            </button>
          ))}
        </div>

        {loadError && <p className="sidebar__note">Could not load examples: {loadError}</p>}
        {!examples && !loadError && <p className="sidebar__note">Loading examples...</p>}

        {examples?.[activeTab].map((group) => (
          <div key={group.group} className="sidebar__group">
            <h3 className="sidebar__group-title">
              {group.group} <span className="sidebar__count">{group.questions.length}</span>
            </h3>
            <ul className="sidebar__list">
              {group.questions.map((example) => (
                <li key={example.question}>
                  <button
                    className="sidebar__question"
                    onClick={() => onSelect(example.question)}
                    disabled={disabled}
                    title={example.insight}
                  >
                    {example.question}
                  </button>
                </li>
              ))}
            </ul>
          </div>
        ))}
      </section>
    </nav>
  );
}
