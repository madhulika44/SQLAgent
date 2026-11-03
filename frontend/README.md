# SQL Agent: React UI

A dashboard for the SQL Agent, built for presenting on a projector. You ask a question in plain English and get:
- the answer as a table;
- a chart;
- the generated SQL;
- a step-by-step trace of what the agent did.

**Stack:** React 19 + Vite (JavaScript), plain CSS with CSS variables, and Recharts for charts. There's no UI library and no TypeScript, so every piece is easy to follow.

## Run it

You need **Node.js 20.19 or later** and the backend running on port 8000 (see the root [README](../README.md)).

```powershell
cd frontend
npm install            # first time only
npm run dev            # http://localhost:5173
```

`frontend/.env` tells the app where the backend is:
```
VITE_API_URL=http://localhost:8000
```
Vite only passes variables that start with `VITE_` to browser code. After you change `.env`, restart `npm run dev`.

| Command | What it does |
|---|---|
| `npm run dev` | Development server with instant reload on save |
| `npm run build` | Production build into `dist/` |
| `npm run preview` | Serves the production build locally |

To start the backend **and** frontend together, run `.\scripts\start_demo.ps1` from the repository root.

## How the code is organised

```
src/
├── main.jsx              entry point: mounts <App /> into index.html
├── App.jsx               all app state + layout (header, sidebar, main area)
├── api.js                every fetch() to the backend, in one place
├── index.css             design tokens (CSS variables), page grid, shared styles
├── utils/
│   ├── format.js         Indian number format (₹5,68,027.95), %, compact axis labels (7.4L)
│   └── sqlHighlight.js   tiny regex-based SQL syntax highlighter
└── components/           one .jsx + one .css per component
    ├── StatusPill        green "Connected - groq" / red "Backend offline" (polls GET /health)
    ├── QuestionBox       big input + Ask button (Enter submits)
    ├── LoadingSteps      animated "Loading schema -> Asking LLM -> ..." while waiting
    ├── InfoBar           provider · attempts · total time · rows
    ├── MessageBox        blue info / red error boxes
    ├── ExampleSidebar    examples by persona / SQL concept + last 10 questions
    ├── ResultTabs        Result · Chart · SQL · Agent Trace
    ├── DataTable         formatted result table
    ├── ChartView         bar / line / pie from the backend's chart suggestion (lazy-loaded)
    ├── SqlView           highlighted SQL + Copy button
    ├── TraceTimeline     vertical timeline of the agent's steps
    └── SchemaPanel       slide-in list of tables, columns and descriptions (GET /schema)
```

### How data flows
1. **`App.jsx` holds the state.** That's the question, the latest answer, loading/error flags, history, examples and health. It passes values down to components as props.
2. **Components report actions back** through callback props, such as `onSubmit` and `onSelect`. That way, clicking an example in the sidebar can fill the question box, even though the two components don't know about each other.
3. **Only `api.js` talks to the backend.** Each call returns parsed JSON or throws an `ApiError` with a readable message.

### Things worth knowing
- **The loading animation is simulated.** `POST /ask` returns one response, so the browser can't see which step the agent is on. `LoadingSteps` advances on a timer, and the **real** step timings appear in the Agent Trace tab.
- **The backend chooses the chart type** from the result's shape (`backend/app/chart.py`). `ChartView` only draws it. Bars switch to horizontal when category names are long, and the series colours always come in the same colour-blind-safe order.
- **Numbers are formatted from the column name.** `...INR` / `Revenue` / `Amount` get ₹, `...Pct` gets %, and IDs and years get no commas. See `utils/format.js`.
- **Recharts is lazy-loaded.** It's only downloaded the first time someone opens the Chart tab, which keeps the first page load small.
- **History is kept in memory only.** Reloading the page clears it, by design for a demo.

## Troubleshooting

| What you see | Fix |
|---|---|
| Red **"Backend offline"** pill | Start the backend: `cd backend` then `uvicorn app.main:app --reload`. The pill re-checks every 30 s. |
| "Cannot reach the backend at ..." | Same as above. Also check `VITE_API_URL` in `frontend/.env`, and restart `npm run dev` after editing it. |
| A CORS error in the browser console | The page's address must be listed in the backend's `CORS_ORIGINS` (`.env` in the repo root). Defaults are `http://localhost:5173` and `http://localhost:3000`. Use `localhost`, not `127.0.0.1`. |
| Port 5173 already in use | Another `npm run dev` is running. Close it, or use the new port Vite prints and add it to `CORS_ORIGINS`. |
| Amber **Fallback** / **Rate limit** steps in the trace | Not a bug: Groq's free tier hit its per-minute limit and the agent switched to Gemini or waited. Leave 20–30 s between questions during a demo. |
