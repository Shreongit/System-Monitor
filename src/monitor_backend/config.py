# src/monitor_backend/config.py
import os

class Settings:
    POLL_INTERVAL: float = float(os.getenv("POLL_INTERVAL", "1.0"))
    TOP_PROCESSES: int = int(os.getenv("TOP_PROCESSES", "30"))
    ADMIN_TOKEN: str = os.getenv("ADMIN_TOKEN", "admin-token")

settings = Settings()