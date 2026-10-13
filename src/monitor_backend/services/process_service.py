import psutil
from typing import List, Dict


def list_processes() -> List[Dict]:
    procs = []
    for p in psutil.process_iter(attrs=["pid", "name", "username", "cpu_percent", "memory_percent", "cmdline"]):
        info = p.info
        procs.append(
            {
                "pid": info.get("pid"),
                "name": info.get("name"),
                "username": info.get("username"),
                "cpu_percent": info.get("cpu_percent") or 0.0,
                "memory_percent": info.get("memory_percent") or 0.0,
                "cmdline": info.get("cmdline") or [],
            }
        )
    return procs


def kill_process(pid: int):
    p = psutil.Process(pid)
    p.terminate()
    try:
        p.wait(timeout=3)
    except psutil.TimeoutExpired:
        p.kill()