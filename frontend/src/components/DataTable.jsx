import { formatValue, isNumber, prettyColumnName } from "../utils/format";
import "./DataTable.css";

/**
 * The query result as a table.
 * Numbers are right-aligned (so digits line up) and shown in Indian format;
 * money columns get a ₹ sign (see utils/format.js).
 *
 * Props: columns (string[]), rows (array of arrays), truncated (bool)
 */
export default function DataTable({ columns, rows, truncated }) {
  if (!columns.length) return null;

  // A column is "numeric" if all its non-empty values are numbers -> right-align it.
  const numericColumns = columns.map((_, i) =>
    rows.every((row) => row[i] === null || isNumber(row[i]))
  );

  return (
    <div className="data-table">
      <div className="data-table__scroll">
        <table>
          <thead>
            <tr>
              <th className="data-table__index">#</th>
              {columns.map((col, i) => (
                <th key={col} className={numericColumns[i] ? "data-table__num" : ""} title={col}>
                  {prettyColumnName(col)}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, rowIndex) => (
              // Rows have no stable id, so the index is the key. Fine for a read-only table.
              <tr key={rowIndex}>
                <td className="data-table__index">{rowIndex + 1}</td>
                {row.map((value, i) => (
                  <td key={columns[i]} className={numericColumns[i] ? "data-table__num" : ""}>
                    {formatValue(value, columns[i])}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="data-table__footer">
        {rows.length} row{rows.length === 1 ? "" : "s"}
        {truncated && " - showing the first rows only (the backend limits results to 200)"}
      </div>
    </div>
  );
}
