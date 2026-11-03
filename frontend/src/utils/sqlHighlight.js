// A tiny SQL syntax highlighter - about 30 lines, so you can see exactly how
// it works (a library like Prism would do the same with far more code).
//
// Idea: one regular expression with a named group per token type. We walk
// through the SQL, and every match becomes { type, text }. The SqlView
// component then renders each token as a <span> with a CSS class per type.

const KEYWORDS = [
  "SELECT", "FROM", "WHERE", "JOIN", "INNER", "LEFT", "RIGHT", "FULL", "OUTER", "CROSS", "ON",
  "GROUP", "BY", "ORDER", "HAVING", "AS", "AND", "OR", "NOT", "IN", "IS", "NULL", "LIKE", "BETWEEN",
  "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END", "DISTINCT", "TOP", "WITH", "UNION", "ALL",
  "OVER", "PARTITION", "ASC", "DESC", "OFFSET", "FETCH", "NEXT", "ROWS", "ONLY", "CAST",
];

// Order matters: comments and strings first, so keywords inside them are not highlighted.
const TOKEN_PATTERN = new RegExp(
  [
    "(?<comment>--[^\\n]*)",
    "(?<string>N?'(?:[^']|'')*')",                  // 'Delivered', N'Text', 'it''s'
    "(?<identifier>\\[[^\\]]+\\])",                 // [Order Date]
    "(?<number>\\b\\d+(?:\\.\\d+)?\\b)",
    `(?<keyword>\\b(?:${KEYWORDS.join("|")})\\b)`,
    "(?<function>\\b[A-Za-z_]\\w*(?=\\s*\\())",     // a word followed by "(" is a function call
  ].join("|"),
  "gi"
);

/** Split SQL text into [{type: "keyword" | "string" | ... | "plain", text}] tokens. */
export function tokenizeSql(sql) {
  const tokens = [];
  let lastIndex = 0;
  for (const match of sql.matchAll(TOKEN_PATTERN)) {
    if (match.index > lastIndex) tokens.push({ type: "plain", text: sql.slice(lastIndex, match.index) });
    const type = Object.keys(match.groups).find((name) => match.groups[name] !== undefined);
    tokens.push({ type, text: match[0] });
    lastIndex = match.index + match[0].length;
  }
  if (lastIndex < sql.length) tokens.push({ type: "plain", text: sql.slice(lastIndex) });
  return tokens;
}
