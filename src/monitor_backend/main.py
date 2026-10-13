# src/monitor_backend/main.py
from pathlib import Path
import asyncio
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

from monitor_backend.collector.psutil_collector import PsutilCollector
from monitor_backend.collector.gpu_collector import GPUCollector
from monitor_backend.aggregator import Aggregator
from monitor_backend.broadcaster import Broadcaster
from monitor_backend.config import settings

THIS_FILE = Path(__file__).resolve()
SRC_DIR = THIS_FILE.parents[1]        # .../src
PROJECT_ROOT = THIS_FILE.parents[2]   # project root

# Look for static folder under src/monitor_frontend/static, fallback to project root monitor_frontend/static
static_path = SRC_DIR / "monitor_frontend" / "static"
if not static_path.exists():
    alt = PROJECT_ROOT / "monitor_frontend" / "static"
    if alt.exists():
        static_path = alt

app = FastAPI(title="System Monitor")

# Mount static at /static if present
if static_path.exists():
    app.mount("/static", StaticFiles(directory=str(static_path)), name="static")
else:
    print(f"Warning: static frontend folder not found. Checked:\n - {SRC_DIR / 'monitor_frontend' / 'static'}\n - {PROJECT_ROOT / 'monitor_frontend' / 'static'}")

# Serve index.html at root (if present)
@app.get("/")
async def root():
    idx = static_path / "index.html"
    if idx.exists():
        return FileResponse(idx)
    return {"message": "Frontend not found. Place static files in the static folder."}

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Runtime singletons
collector = PsutilCollector()
gpu_collector = GPUCollector()
aggregator = Aggregator()
broadcaster = Broadcaster()

app.state.collector = collector
app.state.gpu_collector = gpu_collector
app.state.aggregator = aggregator
app.state.broadcaster = broadcaster
app.state.latest_snapshot = None

_latest_snapshot_lock = asyncio.Lock()


def get_latest_snapshot():
    return app.state.latest_snapshot


def get_broadcaster():
    return app.state.broadcaster


def get_aggregator():
    return app.state.aggregator


@app.on_event("startup")
async def startup_event():
    app.state.poller_task = asyncio.create_task(_poller_loop())
    await gpu_collector.try_init()


@app.on_event("shutdown")
async def shutdown_event():
    tasks = []
    if hasattr(app.state, "poller_task") and app.state.poller_task:
        app.state.poller_task.cancel()
        tasks.append(app.state.poller_task)
    await asyncio.gather(*tasks, return_exceptions=True)


async def _poller_loop():
    interval = settings.POLL_INTERVAL
    while True:
        try:
            ts = await collector.sample()
            gpu_info = await gpu_collector.sample()
            ts["gpus"] = gpu_info
            snapshot = aggregator.update_and_aggregate(ts)
            async with _latest_snapshot_lock:
                app.state.latest_snapshot = snapshot
            await broadcaster.broadcast(snapshot)
        except Exception as e:
            print("Poller loop error:", e)
        await asyncio.sleep(interval)


# Import routes after app/state are ready (prevents circular import)
from monitor_backend.api.routes import router as api_router  # noqa: E402
app.include_router(api_router, prefix="/api")