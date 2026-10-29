"""
FastAPI application - the web layer around the SQL Agent.

Run from the backend/ folder:
    uvicorn app.main:app --reload
Then open http://localhost:8000/docs for interactive API docs.

Endpoints:
    GET  /health           API status, DB connectivity, active LLM provider
    GET  /schema           tables, columns, descriptions, relationships
    POST /schema/refresh   re-read the schema from the database
    POST /ask              {"question": "..."} -> SQL, results, chart, trace
    GET  /examples         curated demo questions by persona and SQL concept

Error-handling policy: the client never sees a Python stack trace. Expected
problems (bad SQL, LLM down) come back inside the /ask response's `error`
field; unexpected crashes become a generic 500 and are logged server-side.
"""

import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.agent import SQLAgent
from app.chart import suggest_chart
from app.config import get_settings
from app.db import DatabaseError, check_connection
from app.examples import get_examples
from app.llm import LLMRouter
from app.models import AskRequest, AskResponse, ExamplesResponse, HealthResponse, SchemaResponse
from app.schema_loader import get_schema, is_schema_cached, refresh_schema

settings = get_settings()
logging.basicConfig(level=settings.log_level.upper(),
                    format="%(asctime)s %(levelname)-7s %(name)s: %(message)s", datefmt="%H:%M:%S")
logger = logging.getLogger("app.api")


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Runs once when the server starts (before the first request)."""
    # Warm the schema cache so the first demo question isn't slower than the rest.
    try:
        schema = get_schema()
        logger.info("Schema cache warmed: %d tables", len(schema.tables))
    except DatabaseError as exc:
        # Don't crash: /health will report the problem and /ask retries the load.
        logger.error("Could not load schema at startup: %s", exc)

    # Build the agent once and reuse it for every request.
    try:
        app.state.agent = SQLAgent(settings, LLMRouter(settings))
        logger.info("LLM providers: %s", ", ".join(p.name for p in app.state.agent.router.providers))
    except ValueError as exc:          # no API keys configured
        app.state.agent = None
        logger.error("Agent not available: %s", exc)
    yield


app = FastAPI(
    title="SQL Agent - Food Delivery",
    description="Ask business questions in plain English; get T-SQL, results and a chart suggestion.",
    version="1.0.0",
    lifespan=lifespan,
)

# CORS: browsers block calls from http://localhost:5173 (the React dev server)
# to http://localhost:8000 unless the API explicitly allows that origin.
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    """Log every request with a short ID, status code and duration."""
    request_id = uuid.uuid4().hex[:8]
    started = time.perf_counter()
    response = await call_next(request)
    duration_ms = int((time.perf_counter() - started) * 1000)
    logger.info("[%s] %s %s -> %d (%d ms)", request_id, request.method, request.url.path,
                response.status_code, duration_ms)
    response.headers["X-Request-ID"] = request_id
    return response


@app.exception_handler(Exception)
async def unhandled_exception(request: Request, exc: Exception):
    """Safety net: log the full error, but only tell the client something generic."""
    logger.exception("Unhandled error on %s %s", request.method, request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error. Check the server logs."})


# ---------------------------------------------------------------------
# Endpoints
# ---------------------------------------------------------------------
# Note: endpoints that call the database or an LLM are plain `def`, not
# `async def`. pyodbc and the LLM SDKs block while waiting, and FastAPI runs
# plain `def` endpoints in a thread pool, so one slow question doesn't
# freeze the whole server.

@app.get("/", include_in_schema=False)
def root():
    return {"message": "SQL Agent API is running", "docs": "/docs"}


@app.get("/health", response_model=HealthResponse, tags=["System"])
def health(request: Request):
    db_ok, db_message = check_connection(settings)
    agent: SQLAgent | None = request.app.state.agent
    providers = agent.router.providers if agent else []
    return HealthResponse(
        status="ok" if db_ok and providers else "degraded",
        database={"ok": db_ok, "message": db_message},
        llm={
            "configured": bool(providers),
            "active_provider": providers[0].name if providers else None,
            "active_model": providers[0].model if providers else None,
            "fallback_providers": [p.name for p in providers[1:]],
        },
        schema_cached=is_schema_cached(),
    )


@app.get("/schema", response_model=SchemaResponse, tags=["Schema"])
def schema():
    try:
        return get_schema().to_dict()
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=f"Could not read the schema: {exc}") from exc


@app.post("/schema/refresh", response_model=SchemaResponse, tags=["Schema"])
def schema_refresh():
    try:
        return refresh_schema().to_dict()
    except DatabaseError as exc:
        raise HTTPException(status_code=503, detail=f"Could not read the schema: {exc}") from exc


@app.post("/ask", response_model=AskResponse, tags=["Agent"])
def ask(body: AskRequest, request: Request):
    agent: SQLAgent | None = request.app.state.agent
    if agent is None:
        raise HTTPException(status_code=503, detail="No LLM provider configured. Set GROQ_API_KEY or GEMINI_API_KEY.")

    result = agent.ask(body.question)
    logger.info("ask: provider=%s attempts=%d rows=%d error=%s time=%dms",
                result.provider, result.attempts, result.row_count, result.error, result.total_time_ms)
    # 200 even when result.error is set: the request itself worked, and the
    # UI shows the error together with the trace so the user can see why.
    return {**result.to_dict(), "chart": suggest_chart(result.columns, result.rows)}


@app.get("/examples", response_model=ExamplesResponse, tags=["Agent"])
def examples():
    return get_examples()
