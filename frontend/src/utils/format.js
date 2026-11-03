// Number and value formatting for the result table and charts.
//
// Indian number format groups digits as 12,34,567.89 (lakhs and crores),
// not 1,234,567.89. The browser's built-in Intl.NumberFormat with the
// "en-IN" locale does this for us - no library needed.

const indianNumber = new Intl.NumberFormat("en-IN", { maximumFractionDigits: 2 });

// Column-name hints. The backend returns plain values, so we guess the
// meaning of a number from its column name (e.g. "TotalRevenueINR").
const MONEY_PATTERN = /inr|revenue|amount|fee|price|gmv|discount|spend|paid|sales/i;
const PERCENT_PATTERN = /pct|percent/i;
// Numbers that must NOT get thousands separators: IDs, and time keys like
// Year = 2026 (not "2,026") or HourOfDay = 13.
const ID_PATTERN = /id$|pincode/i;
const TIME_KEY_PATTERN = /year|hour|month|day|week/i;

function isPlainNumber(value, columnName) {
  if (ID_PATTERN.test(columnName)) return true;
  // "OrderYear" 2026 is plain, but "OrdersPerDay" 187.3 or "RevenueThisMonth" 568027 are measures.
  return TIME_KEY_PATTERN.test(columnName) && Number.isInteger(value) && value >= 0 && value <= 2100
    && !MONEY_PATTERN.test(columnName) && !/orders|count|total|avg|per/i.test(columnName);
}

export function isMoneyColumn(name) {
  return MONEY_PATTERN.test(name) && !PERCENT_PATTERN.test(name);
}

export function isNumber(value) {
  return typeof value === "number" && Number.isFinite(value);
}

/** Format one cell for display, using the column name as a hint. */
export function formatValue(value, columnName = "") {
  if (value === null || value === undefined) return "—";
  if (typeof value === "boolean") return value ? "Yes" : "No";

  if (isNumber(value)) {
    if (isPlainNumber(value, columnName)) return String(value);
    if (isMoneyColumn(columnName)) return `₹${indianNumber.format(value)}`;
    if (PERCENT_PATTERN.test(columnName)) return `${indianNumber.format(value)}%`;
    return indianNumber.format(value);
  }

  // Dates arrive as ISO strings: "2026-03-15T19:42:10" -> "2026-03-15 19:42"
  if (typeof value === "string" && /^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}/.test(value)) {
    return value.slice(0, 16).replace("T", " ");
  }
  return String(value);
}

// Words inside a column name: "MoM"/"YoY", runs of capitals (INR, COD), normal words, numbers.
const WORD_PATTERN = /MoM|YoY|[A-Z]+(?![a-z])|[A-Z]?[a-z]+|\d+/g;

/** "TotalRevenueINR" -> "Total Revenue INR", "MoMGrowthPct" -> "MoM Growth Pct" (nicer headers). */
export function prettyColumnName(name) {
  return (name.match(WORD_PATTERN) || [name]).join(" ");
}

/** 4180 -> "4.2 s", 850 -> "850 ms" */
export function formatDuration(ms) {
  return ms >= 1000 ? `${(ms / 1000).toFixed(1)} s` : `${ms} ms`;
}
