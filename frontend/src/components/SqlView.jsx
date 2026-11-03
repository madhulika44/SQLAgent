import { useState } from "react";
import { tokenizeSql } from "../utils/sqlHighlight";
import "./SqlView.css";

/**
 * The generated SQL with syntax colours and a Copy button.
 * Props: sql (string)
 */
export default function SqlView({ sql }) {
  const [copied, setCopied] = useState(false);

  async function copyToClipboard() {
    try {
      await navigator.clipboard.writeText(sql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000); // show "Copied!" for 2 seconds
    } catch {
      // The clipboard API can be blocked (e.g. a non-HTTPS page that isn't localhost).
      setCopied(false);
      window.prompt("Copy the SQL:", sql);
    }
  }

  return (
    <div className="sql-view">
      <div className="sql-view__toolbar">
        <span>T-SQL · runs on SQL Server as the read-only user</span>
        <button className="sql-view__copy" onClick={copyToClipboard}>
          {copied ? "✓ Copied!" : "Copy SQL"}
        </button>
      </div>
      <pre className="sql-view__code">
        <code>
          {tokenizeSql(sql).map((token, i) => (
            <span key={i} className={`sql-token--${token.type}`}>
              {token.text}
            </span>
          ))}
        </code>
      </pre>
    </div>
  );
}
