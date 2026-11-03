// Every call to the FastAPI backend lives in this file.
// Components never call fetch() directly - they call these functions.
// That way the backend URL and the error handling are in ONE place.

const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";

/** An error from the backend, with the HTTP status (0 = the backend could not be reached). */
export class ApiError extends Error {
  constructor(message, status) {
    super(message);
    this.status = status;
  }
}

/** Shared helper: call the API and return the parsed JSON, or throw an ApiError. */
async function request(path, options = {}) {
  let response;
  try {
    response = await fetch(`${API_URL}${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
  } catch {
    // fetch() itself only fails when there is no response at all (server down, CORS, network).
    throw new ApiError(`Cannot reach the backend at ${API_URL}. Is it running?`, 0);
  }

  const body = await response.json().catch(() => null);
  if (!response.ok) {
    // FastAPI puts error text in "detail" (a string, or a list for validation errors).
    const detail = body?.detail;
    const message = Array.isArray(detail) ? detail.map((d) => d.msg).join("; ") : detail;
    throw new ApiError(message || `Request failed with status ${response.status}`, response.status);
  }
  return body;
}

/** GET /health -> { status, database: {ok, message}, llm: {active_provider, ...}, schema_cached } */
export function getHealth() {
  return request("/health");
}

/** GET /examples -> { by_persona: [{group, questions}], by_concept: [...] } */
export function getExamples() {
  return request("/examples");
}

/** GET /schema -> { database, tables: [{name, description, columns}], relationships } */
export function getSchema() {
  return request("/schema");
}

/** POST /ask -> { question, sql, explanation, columns, rows, chart, trace, error, ... } */
export function askQuestion(question) {
  return request("/ask", { method: "POST", body: JSON.stringify({ question }) });
}
