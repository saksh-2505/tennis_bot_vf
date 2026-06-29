from __future__ import annotations

import os
import shutil
import time


def get_cpu_usage() -> float:
    try:
        load_avg = os.getloadavg()[0]
        cpu_count = os.cpu_count() or 1
        return (load_avg / cpu_count) * 100.0
    except OSError:
        return 0.0


def get_memory_usage() -> float:
    try:
        import psutil
        return psutil.virtual_memory().percent
    except ImportError:
        pass
    try:
        page_size = os.sysconf(os.sysconf_names["SC_PAGE_SIZE"])
        phys_pages = os.sysconf(os.sysconf_names["SC_PHYS_PAGES"])
        avail_pages = os.sysconf(os.sysconf_names["SC_AVPHYS_PAGES"])
        if phys_pages > 0:
            return (1.0 - avail_pages / phys_pages) * 100.0
    except (ValueError, KeyError, OSError):
        pass
    return 0.0


def get_disk_usage(path: str = "/") -> float:
    try:
        usage = shutil.disk_usage(path)
        return (usage.used / usage.total) * 100.0
    except OSError:
        return 0.0


def format_bytes(n: int) -> str:
    for unit in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{unit}"
        n /= 1024
    return f"{n:.1f}PB"
