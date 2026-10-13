import asyncio
import platform
import subprocess

class GPUCollector:
    def __init__(self):
        self._has_nvml = False
        self._nvml = None

    async def try_init(self):
        # lazy init to avoid import-time failure
        try:
            import pynvml
            self._nvml = pynvml
            self._nvml.nvmlInit()
            self._has_nvml = True
        except Exception:
            self._has_nvml = False

    async def sample(self):
        # Return list of GPUs as dicts with name + optional fields
        if self._has_nvml:
            try:
                handle = self._nvml
                count = handle.nvmlDeviceGetCount()
                out = []
                for i in range(count):
                    h = handle.nvmlDeviceGetHandleByIndex(i)
                    mem = handle.nvmlDeviceGetMemoryInfo(h)
                    util = handle.nvmlDeviceGetUtilizationRates(h)
                    temp = None
                    try:
                        temp = handle.nvmlDeviceGetTemperature(h, handle.NVML_TEMPERATURE_GPU)
                    except Exception:
                        temp = None
                    name = ""
                    try:
                        raw_name = handle.nvmlDeviceGetName(h)
                        # nvmlDeviceGetName may return bytes on some platforms
                        name = raw_name.decode() if isinstance(raw_name, bytes) else str(raw_name)
                    except Exception:
                        name = f"nvml_gpu_{i}"
                    out.append(
                        {
                            "index": i,
                            "name": name,
                            "memory_total": getattr(mem, "total", None),
                            "memory_used": getattr(mem, "used", None),
                            "utilization_gpu": getattr(util, "gpu", None),
                            "utilization_mem": getattr(util, "memory", None),
                            "temperature": temp,
                        }
                    )
                return out
            except Exception:
                # If NVML suddenly errors, fall back to platform detection
                pass

        # Fallback: on Windows try WMIC to get GPU names
        try:
            if platform.system() == "Windows":
                # wmic output example:
                # Name
                # NVIDIA GeForce ...
                out = subprocess.check_output(
                    ["wmic", "path", "win32_VideoController", "get", "name"], stderr=subprocess.DEVNULL, text=True
                )
                lines = [l.strip() for l in out.splitlines() if l.strip()]
                # First line is header 'Name' usually; skip header
                if len(lines) >= 2:
                    gpu_lines = lines[1:]
                    gpus = []
                    for idx, g in enumerate(gpu_lines):
                        gpus.append({"index": idx, "name": g})
                    return gpus
        except Exception:
            pass

        # final fallback: empty list
        return []