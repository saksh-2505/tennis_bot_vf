import os

INCIDENT_PACKAGES_DIR = os.getenv("INCIDENT_PACKAGES_DIR", "incident_packages")
MONITOR_INTERVAL_SECONDS = int(os.getenv("INCIDENT_MONITOR_INTERVAL", "60"))
MATCH_SCORE_STALE_SECONDS = int(os.getenv("INCIDENT_SCORE_STALE", "120"))
MATCH_ODDS_STALE_SECONDS = int(os.getenv("INCIDENT_ODDS_STALE", "60"))
COLLECTOR_STALE_SECONDS = int(os.getenv("INCIDENT_COLLECTOR_STALE", "7200"))
UNFINALIZED_STALE_SECONDS = int(os.getenv("INCIDENT_UNFINALIZED_STALE", "1800"))
CPU_THRESHOLD_PERCENT = float(os.getenv("INCIDENT_CPU_THRESHOLD", "90"))
MEMORY_THRESHOLD_PERCENT = float(os.getenv("INCIDENT_MEMORY_THRESHOLD", "90"))
DISK_THRESHOLD_PERCENT = float(os.getenv("INCIDENT_DISK_THRESHOLD", "90"))
DB_CONNECTION_TIMEOUT_SECONDS = int(os.getenv("INCIDENT_DB_TIMEOUT", "10"))
TELEGRAM_ENABLED = os.getenv("TELEGRAM_BOT_TOKEN", "") != ""

COLLECTOR_COLUMNS = {
    "flashscore": ("flashscorefoundmatches", "discovered_at"),
    "bettingsite": ("bettingsitefoundmatches", "discovered_at"),
    "players": ("players", "last_updated"),
    "registry": ("tracked_matches", "updated_at"),
}

COLLECTOR_LABELS = {
    "flashscore": "Flashscore Discovery",
    "bettingsite": "Betting Site Discovery",
    "players": "Player Collector",
    "registry": "Match Registry",
    "live_collector": "Live Collector",
    "finalizer": "Match Finalizer",
}

SEVERITY_LEVELS = ["INFO", "WARNING", "ERROR", "CRITICAL"]
CATEGORIES = [
    "Collector Failure",
    "Database",
    "Network",
    "Infrastructure",
    "Data Validation",
    "Match Collection",
    "Unknown",
]
STATUSES = ["OPEN", "ACKNOWLEDGED", "RECOVERING", "RESOLVED", "CLOSED"]

SECRET_KEY_PATTERNS = {"token", "password", "secret", "key", "api_key"}
