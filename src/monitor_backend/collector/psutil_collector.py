import psutil
import time
import platform
import sys
import os
from typing import Dict, Any, List

class PsutilCollector:
    def __init__(self):
        self._last_proc_cpu_times = {}
        # psutil.cpu_percent with interval=0 performs non-blocking sampling using cached values
        psutil.cpu_percent(interval=None)

    async def sample(self) -> Dict[str, Any]:
        ts = time.time()
        cpu = self._collect_cpu()
        memory = self._collect_memory()
        disks = self._collect_disks()
        network = self._collect_network()
        temps = self._collect_temps()
        processes_summary = self._collect_processes_summary()
        system = self._collect_system_info()
        return {
            "timestamp": ts,
            "cpu": cpu,
            "memory": memory,
            "disks": disks,
            "network": network,
            "temps": temps,
            "processes_summary": processes_summary,
            "system": system,
        }

    def _collect_cpu(self) -> Dict[str, Any]:
        # overall and per-core percentages (non-blocking)
        percent = psutil.cpu_percent(interval=None)
        per_core = psutil.cpu_percent(interval=None, percpu=True)
        freqs = psutil.cpu_freq(percpu=False)
        freq = {
            "current": freqs.current if freqs else None,
            "min": freqs.min if freqs else None,
            "max": freqs.max if freqs else None,
        }
        return {"percent": percent, "per_core": per_core, "freq": freq}

    def _collect_memory(self) -> Dict[str, Any]:
        vm = psutil.virtual_memory()
        swap = psutil.swap_memory()
        return {
            "total": vm.total,
            "available": vm.available,
            "used": vm.used,
            "free": getattr(vm, "free", None),
            "percent": vm.percent,
            "swap_total": swap.total,
            "swap_used": swap.used,
            "swap_percent": swap.percent,
        }

    def _collect_disks(self) -> List[Dict]:
        parts = []
        for p in psutil.disk_partitions(all=False):
            try:
                usage = psutil.disk_usage(p.mountpoint)
            except PermissionError:
                continue
            parts.append(
                {
                    "device": p.device,
                    "mountpoint": p.mountpoint,
                    "fstype": p.fstype,
                    "total": usage.total,
                    "used": usage.used,
                    "free": usage.free,
                    "percent": usage.percent,
                }
            )
        # Also return total io counters
        io = psutil.disk_io_counters(perdisk=False)
        parts_meta = {"io_read_bytes": io.read_bytes if io else 0, "io_write_bytes": io.write_bytes if io else 0}
        return {"partitions": parts, "counters": parts_meta}

    def _collect_network(self) -> Dict:
        # per-interface cumulative counters
        nic = psutil.net_io_counters(pernic=True)
        result = {}
        for ifname, stats in nic.items():
            result[ifname] = {
                "bytes_sent": stats.bytes_sent,
                "bytes_recv": stats.bytes_recv,
                "packets_sent": stats.packets_sent,
                "packets_recv": stats.packets_recv,
                "errin": stats.errin,
                "errout": stats.errout,
                "dropin": stats.dropin,
                "dropout": stats.dropout,
            }
        return result

    def _collect_temps(self) -> List[Dict]:
        try:
            raw = psutil.sensors_temperatures()
            out = []
            for name, entries in raw.items():
                for e in entries:
                    out.append(
                        {
                            "sensor": name,
                            "label": e.label,
                            "current": e.current,
                            "high": getattr(e, "high", None),
                            "critical": getattr(e, "critical", None),
                        }
                    )
            return out
        except (AttributeError, Exception):
            return []

    def _collect_processes_summary(self, topn: int = 30) -> List[Dict]:
        procs = []
        # iterate processes and collect lightweight info
        for p in psutil.process_iter(attrs=["pid", "name", "username", "cpu_percent", "memory_percent", "cmdline"]):
            info = p.info
            procs.append(
                {
                    "pid": info.get("pid"),
                    "name": info.get("name"),
                    "username": info.get("username"),
                    "cpu_percent": info.get("cpu_percent") or 0.0,
                    "memory_percent": info.get("memory_percent") or 0.0,
                    "cmdline": info.get("cmdline"),
                }
            )
        # sort by cpu desc
        procs.sort(key=lambda x: x["cpu_percent"], reverse=True)
        return procs[:topn]

    def _get_cpu_name(self) -> str:
        # Windows: read registry ProcessorNameString
        try:
            if os.name == "nt":
                import winreg

                try:
                    key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, r"HARDWARE\DESCRIPTION\System\CentralProcessor\0")
                    name, _ = winreg.QueryValueEx(key, "ProcessorNameString")
                    return str(name).strip()
                except Exception:
                    # fallback to platform.processor
                    pass
            # Linux: parse /proc/cpuinfo
            if sys.platform.startswith("linux"):
                try:
                    with open("/proc/cpuinfo", "r", encoding="utf-8") as f:
                        for line in f:
                            if "model name" in line:
                                return line.split(":", 1)[1].strip()
                except Exception:
                    pass
            # Mac or others
            proc = platform.processor() or platform.machine() or ""
            if proc:
                return proc
        except Exception:
            pass
        return "Unknown CPU"

    def _collect_system_info(self) -> Dict[str, Any]:
        physical = psutil.cpu_count(logical=False) or 0
        logical = psutil.cpu_count(logical=True) or 0
        vm = psutil.virtual_memory()
        cpu_name = self._get_cpu_name()
        os_info = platform.platform()
        return {
            "cpu_name": cpu_name,
            "physical_cores": int(physical),
            "logical_cores": int(logical),
            "ram_total": int(vm.total),
            "os": os_info,
        }