# System Monitor — FastAPI + WebSocket (Windows-friendly)

A minimal real-time system monitor (Task-Manager-like) implemented in Python with a FastAPI backend and a small browser frontend (Chart.js). It shows CPU, RAM, Disk, Network, Temperatures, Processes and system information (CPU name, cores, threads, RAM installed, GPU name, OS).

This README explains how to run the project on Windows, what each part does, configuration, and common troubleshooting steps specific to issues you may have encountered.

---

## Features
- CPU usage (total + per-core)
- Memory usage (total, used, percent)
- Disk usage and IO rates
- Network interface rates (bytes/sec)
- Temperatures (where supported)
- Processes list (top by CPU)
- System info: CPU name, physical cores, logical threads, RAM installed, OS
- GPU name: NVML if available; on Windows, falls back to `wmic` when NVML missing
- Real-time dashboard using WebSocket and Chart.js

---

## Project layout (important files)
- README.md
- requirements.txt
- .env.example
- scripts/run_dev.sh
- src/
  - monitor_backend/
    - main.py
    - config.py
    - aggregator.py
    - broadcaster.py
    - collector/
      - psutil_collector.py
      - gpu_collector.py
    - api/
      - routes.py
    - services/
      - process_service.py
  - monitor_frontend/
    - static/
      - index.html
      - app.js
      - styles.css

The FastAPI app serves the frontend at `/` and static files under `/static`.

---

## Install Package

- pip install -r requirements.txt

---

## HOW TO RUN 

- python -m uvicorn monitor_backend.main:app --reload

---

## Quick start (Windows — PowerShell recommended)

1. Open PowerShell in the project root.

2. Create & activate the virtual environment (if not already):
   - python -m venv .venv
   - .\.venv\Scripts\Activate.ps1
   - If execution policy blocks activation script for the session:
     - Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope Process

3. Install dependencies:
   - pip install -r requirements.txt
   - (Optional) GPU support: pip install pynvml

4. Ensure `.env` (optional):
   - Copy example: Copy-Item .env.example .env
   - Edit `.env` to set `POLL_INTERVAL` or `ADMIN_TOKEN` as desired.

5. Start the server:
   - cd .\src
   - python -m uvicorn monitor_backend.main:app --reload --host 127.0.0.1 --port 8000

6. Open the dashboard in your browser:
   - http://127.0.0.1:8000

---

## Important usage notes

- Process-kill endpoint requires `X-Admin-Token` header equal to `ADMIN_TOKEN` (set in `.env` or defaults to `admin-token`). Example:
  - PowerShell:
    Invoke-RestMethod -Uri http://127.0.0.1:8000/api/processes/123/kill -Method Post -Headers @{ "X-Admin-Token" = "admin-token" }
- Some fields depend on platform support:
  - Temperatures and some GPU metrics require system drivers and libraries.
  - GPU name is retrieved via NVML (pynvml) when available; on Windows it uses `wmic` fallback.
- Killing certain processes may require elevated privileges — run PowerShell as Administrator if needed.

---

## Common issues & troubleshooting

1. Uvicorn import/circular import error:
   - If you see `ImportError: cannot import name ... from partially initialized module 'monitor_backend.main' (most likely due to a circular import)`, ensure `main.py` creates collector/aggregator/broadcaster and defines helper functions before importing `monitor_backend.api.routes`. The provided `main.py` already follows this ordering.

2. Pydantic BaseSettings import error:
   - If you get a pydantic error about `BaseSettings` moved to `pydantic-settings`, use the provided `config.py` which does not require pydantic, or install a compatible pydantic version:
     - pip install "pydantic<2.0.0" (not recommended long term) or install `pydantic-settings` and adapt config.

3. Static files 404 (page unstyled / JS missing):
   - Ensure `index.html` references assets under `/static`:
     - `<link rel="stylesheet" href="/static/styles.css" />`
     - `<script src="/static/app.js"></script>`
   - Confirm files are located in `src/monitor_frontend/static/`.
   - The server mounts static at `/static`; after changing files restart uvicorn.

4. Files accidentally include "name=" headers:
   - If files were pasted from the README or assistant output, the first line may be `name=...` (invalid). Remove any leading lines like `name=src/...` from .py, .js, .html, .css files.
   - To detect such files:
     - PowerShell (run in project root):
       Get-ChildItem -Recurse -Path .\src | Select-String -Pattern '^name=' | Select-Object Path, LineNumber, Line

5. “No snapshot yet” or empty charts:
   - Wait 1–2 seconds after server startup for the first poll.
   - Check backend logs for poller errors. Snapshot endpoint:
     - curl http://127.0.0.1:8000/api/metrics/snapshot

6. WebSocket not connecting:
   - Browser console (DevTools) will show WS connection errors. Confirm front-end connects to `/api/ws/metrics` (the code uses `ws://<host>/api/ws/metrics` or `wss://` for HTTPS).

---

## Development tips

- Run the app from the `src` folder (`cd src`) to avoid needing to set PYTHONPATH.
- Restart the server when changing Python files. FastAPI `--reload` watches for file changes but restart is sometimes required after structural changes.
- Use a small `POLL_INTERVAL` (default 1.0s). Increase to reduce load.

---

## Security & deployment

- Do not expose the server publicly without adding authentication, TLS, and network restrictions.
- For production, run behind a reverse proxy (nginx) and use an application server without `--reload`.
- Consider containerizing with Docker and using secrets for admin tokens.

---

## Example `.env` (copy from .env.example)
