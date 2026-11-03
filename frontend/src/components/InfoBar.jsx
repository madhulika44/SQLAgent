import { formatDuration } from "../utils/format";
import "./InfoBar.css";

/** One-line summary under the question: who answered, how many tries, how long, how many rows. */
export default function InfoBar({ result }) {
  const items = [
    { label: "Provider", value: result.provider || "—" },
    { label: "Attempts", value: result.attempts, highlight: result.attempts > 1 },
    { label: "Total time", value: formatDuration(result.total_time_ms) },
    { label: "Rows", value: result.truncated ? `${result.row_count} (truncated)` : result.row_count },
  ];

  return (
    <div className="info-bar">
      {items.map((item) => (
        <span key={item.label} className={`info-bar__item ${item.highlight ? "info-bar__item--highlight" : ""}`}>
          <span className="info-bar__label">{item.label}</span>
          <strong>{item.value}</strong>
        </span>
      ))}
    </div>
  );
}
