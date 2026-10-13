name=scripts/run_dev.sh
#!/usr/bin/env bash
export PYTHONPATH=src
export POLL_INTERVAL=1.0
uvicorn monitor_backend.main:app --reload --host 0.0.0.0 --port 8000