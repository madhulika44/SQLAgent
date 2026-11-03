# Starts the whole demo: backend (FastAPI) and frontend (Vite) in two new
# PowerShell windows, then opens the browser.
#
# Run from the repository root:
#     .\scripts\start_demo.ps1
# Stop everything by closing the two windows (or Ctrl+C in each).

$root = Split-Path -Parent $PSScriptRoot

# Window 1: backend on http://localhost:8000
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "Set-Location '$root\backend'; & '$root\venv\Scripts\Activate.ps1'; uvicorn app.main:app --reload"

# Window 2: frontend on http://localhost:5173
Start-Process powershell -ArgumentList "-NoExit", "-Command",
    "Set-Location '$root\frontend'; npm run dev"

# Give both servers a few seconds to start, then open the app.
Write-Host "Starting backend and frontend..."
Start-Sleep -Seconds 6
Start-Process "http://localhost:5173"
Write-Host "Opened http://localhost:5173 - API docs at http://localhost:8000/docs"
