from fastapi import APIRouter, WebSocket, WebSocketDisconnect, Depends, Request, HTTPException, status, Body
from typing import Optional
from monitor_backend.main import get_latest_snapshot, get_broadcaster
from monitor_backend.services.process_service import list_processes, kill_process
from monitor_backend.config import settings

router = APIRouter()


@router.get("/metrics/snapshot")
async def snapshot():
    s = get_latest_snapshot()
    if s is None:
        raise HTTPException(status_code=503, detail="No snapshot yet")
    return s


@router.get("/processes")
async def processes(page: int = 1, per_page: int = 50, sort: Optional[str] = "cpu"):
    procs = list_processes()
    if sort == "cpu":
        procs.sort(key=lambda x: x.get("cpu_percent", 0.0), reverse=True)
    elif sort == "mem":
        procs.sort(key=lambda x: x.get("memory_percent", 0.0), reverse=True)
    # paging
    start = (page - 1) * per_page
    end = start + per_page
    return {"total": len(procs), "page": page, "per_page": per_page, "items": procs[start:end]}


@router.post("/processes/{pid}/kill")
async def kill(pid: int, request: Request, reason: Optional[str] = Body(None)):
    # Simple token auth via header
    token = request.headers.get("X-Admin-Token")
    if not token or token != settings.ADMIN_TOKEN:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Invalid admin token")
    try:
        kill_process(pid)
        return {"status": "ok", "pid": pid}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/metrics")
async def websocket_metrics(ws: WebSocket):
    broadcaster = get_broadcaster()
    await broadcaster.connect(ws)
    try:
        while True:
            # Keep connection alive; we don't expect messages from client, but allow ping/pong
            data = await ws.receive_text()
            # if client sends "snapshot" respond with current snapshot
            if data == "snapshot":
                s = get_latest_snapshot()
                if s:
                    await ws.send_json(s)
    except WebSocketDisconnect:
        await broadcaster.disconnect(ws)
    except Exception:
        await broadcaster.disconnect(ws)