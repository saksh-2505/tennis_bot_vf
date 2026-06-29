#!/usr/bin/env python3
"""External health monitor: downtime alerts, error digests, DuckDNS."""
"""Tennis Bot monitor — health checks, alerts, daily reports, DuckDNS update.

Runs via cron every 5 minutes. Sends Telegram notifications for:
  - Downtime alerts (with recent error logs)
  - Recovery notices (with downtime duration)
  - Error digests (new warnings/errors in app logs)
  - Daily summary reports (match stats, tick counts)
"""

import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from urllib.request import Request, urlopen
from urllib.error import URLError

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.environ.get("TELEGRAM_CHAT_ID", "")
if not BOT_TOKEN or not CHAT_ID:
    print("ERROR: TELEGRAM_BOT_TOKEN and TELEGRAM_CHAT_ID must be set in environment")
    sys.exit(1)
COMPOSE_DIR = os.path.expanduser("~/tennis_bot")
MONITOR_DIR = os.path.join(COMPOSE_DIR, "monitor")
STATE_FILE = os.path.join(MONITOR_DIR, "state.json")
LOG_FILE = "/tmp/tennis_bot_monitor.log"

DUCKDNS_DOMAIN = os.environ.get("DUCKDNS_DOMAIN", "tennisbotdata")
DUCKDNS_TOKEN = os.environ.get("DUCKDNS_TOKEN", "")
DUCKDNS_IP = os.environ.get("DUCKDNS_IP", "161.118.182.103")


def log(msg: str) -> None:
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    line = f"[{ts}] {msg}"
    print(line)
    with open(LOG_FILE, "a") as f:
        f.write(line + "\n")


def send_telegram(text: str) -> bool:
    import urllib.parse

    data = urllib.parse.urlencode({"chat_id": CHAT_ID, "text": text, "parse_mode": "HTML"}).encode()
    req = Request(
        f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
    )
    try:
        resp = urlopen(req, timeout=15)
        return resp.status == 200
    except URLError as e:
        log(f"Telegram send failed: {e}")
        return False


def update_duckdns() -> None:
    url = f"https://www.duckdns.org/update?domains={DUCKDNS_DOMAIN}&token={DUCKDNS_TOKEN}&ip={DUCKDNS_IP}"
    try:
        resp = urlopen(url, timeout=10)
        body = resp.read().decode().strip()
        log(f"DuckDNS: {body}")
    except URLError as e:
        log(f"DuckDNS update failed: {e}")


def load_state() -> dict:
    if os.path.exists(STATE_FILE):
        try:
            return json.loads(Path(STATE_FILE).read_text())
        except (json.JSONDecodeError, OSError):
            pass
    return {"prev_healthy": True, "down_since": None, "last_error_check": 0, "last_daily": "", "reported_errors": []}


def save_state(state: dict) -> None:
    Path(STATE_FILE).write_text(json.dumps(state, indent=2))


def check_containers() -> tuple[bool, bool, str | None]:
    try:
        result = subprocess.run(
            ["docker", "compose", "ps", "--format", "json"],
            capture_output=True, text=True, timeout=30, cwd=COMPOSE_DIR,
        )
        if result.returncode != 0:
            return False, False, f"docker compose ps failed: {result.stderr.strip()}"

        app_ok = False
        db_ok = False
        for line in result.stdout.strip().split("\n"):
            if not line.strip():
                continue
            try:
                entry = json.loads(line)
                svc = entry.get("Service")
                state = entry.get("State")
                if svc == "app" and state == "running":
                    app_ok = True
                if svc == "timescaledb" and state == "running":
                    db_ok = True
            except json.JSONDecodeError:
                continue
        return app_ok, db_ok, None
    except subprocess.TimeoutExpired:
        return False, False, "docker compose ps timed out"
    except FileNotFoundError:
        return False, False, "docker command not found"


def get_recent_logs(since_seconds: int = 300) -> str:
    try:
        since_ts = datetime.now(timezone.utc).timestamp() - since_seconds
        result = subprocess.run(
            ["docker", "compose", "logs", "app", f"--since={int(since_ts)}"],
            capture_output=True, text=True, timeout=15, cwd=COMPOSE_DIR,
        )
        return result.stdout or result.stderr or ""
    except Exception:
        return ""


def extract_errors(log_text: str) -> list[str]:
    lines = log_text.split("\n")
    errors = []
    for line in lines:
        lower = line.lower()
        if any(kw in lower for kw in ["error", "exception", "traceback", "failed with", "unreachable"]):
            errors.append(line.strip())
    return errors


def get_db_stats() -> dict:
    stats = {}
    try:
        for query, key in [
            ("SELECT status, count(*) FROM tracked_matches GROUP BY status;", "matches_by_status"),
            ("SELECT count(*) FROM live_scores;", "score_ticks"),
            ("SELECT count(*) FROM live_odds;", "odds_ticks"),
            ("SELECT count(*) FROM completed_matches;", "completed_matches"),
        ]:
            result = subprocess.run(
                ["docker", "compose", "exec", "-T", "timescaledb", "psql", "-U", "tennis", "-d", "tennis_bot",
                 "-t", "-A", "-c", query],
                capture_output=True, text=True, timeout=15, cwd=COMPOSE_DIR,
            )
            output = result.stdout.strip()
            if key == "matches_by_status":
                lines = output.split("\n")
                counts = {}
                for ln in lines:
                    parts = ln.split("|")
                    if len(parts) == 2:
                        counts[parts[0].strip()] = int(parts[1].strip())
                stats[key] = counts
            else:
                stats[key] = int(output.split("\n")[0]) if output else 0
    except Exception as e:
        log(f"DB stats query failed: {e}")
    return stats


def format_duration(seconds: float) -> str:
    if seconds < 60:
        return f"{int(seconds)}s"
    mins = int(seconds // 60)
    secs = int(seconds % 60)
    if mins < 60:
        return f"{mins}m {secs}s"
    hours = mins // 60
    mins = mins % 60
    return f"{hours}h {mins}m"


def run() -> None:
    os.makedirs(MONITOR_DIR, exist_ok=True)
    state = load_state()

    # -- DuckDNS update -------------------------------------------------
    update_duckdns()

    # -- Container health check -----------------------------------------
    app_ok, db_ok, err_msg = check_containers()
    now_utc = datetime.now(timezone.utc)
    now_ts = now_utc.timestamp()
    currently_healthy = app_ok and db_ok

    if err_msg:
        log(f"Health check error: {err_msg}")

    # DOWN transition
    if state.get("prev_healthy", True) and not currently_healthy:
        state["down_since"] = now_ts
        state["prev_healthy"] = False

        logs = get_recent_logs(600)
        errors = extract_errors(logs)
        error_snippet = "\n".join(errors[-10:]) if errors else "(no recent errors)"

        msg = (
            f"\U0001f534 Tennis Bot DOWN\n"
            f"App: {'running' if app_ok else 'STOPPED'}\n"
            f"DB: {'running' if db_ok else 'STOPPED'}\n"
            f"Time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        if err_msg:
            msg += f"\nError: {err_msg}"
        if error_snippet:
            msg += f"\n\nRecent logs:\n<code>{error_snippet[:800]}</code>"
        send_telegram(msg)
        log("Sent DOWN alert")

    # RECOVERY transition
    elif not state.get("prev_healthy", True) and currently_healthy:
        down_since = state.get("down_since")
        if down_since:
            duration = now_ts - down_since
            dur_str = format_duration(duration)
        else:
            dur_str = "unknown"

        state["prev_healthy"] = True
        state["down_since"] = None

        msg = (
            f"\u2705 Tennis Bot RECOVERED\n"
            f"Downtime: {dur_str}\n"
            f"App: running\n"
            f"DB: running\n"
            f"Time: {now_utc.strftime('%Y-%m-%d %H:%M:%S UTC')}"
        )
        send_telegram(msg)
        log(f"Sent RECOVERY alert (downtime: {dur_str})")

    # -- Error digest ---------------------------------------------------
    if currently_healthy:
        last_check = state.get("last_error_check", now_ts - 3600)
        since_duration = max(300, int(now_ts - last_check))

        logs = get_recent_logs(since_duration)
        errors = extract_errors(logs)
        reported = set(state.get("reported_errors", []))

        new_errors = [e for e in errors if e not in reported]
        if new_errors:
            # Keep reported errors manageable
            all_reported = reported | set(new_errors)
            if len(all_reported) > 100:
                all_reported = set(list(all_reported)[-100:])
            state["reported_errors"] = list(all_reported)

            msg = (
                f"\u26a0\ufe0f {len(new_errors)} new issue(s) in app logs\n"
                f"<code>{chr(10).join(new_errors[:8])}</code>"
            )
            send_telegram(msg)
            log(f"Sent error digest: {len(new_errors)} new issues")

        state["last_error_check"] = now_ts

    # -- Daily report at midnight ---------------------------------------
    today = now_utc.strftime("%Y-%m-%d")
    if today != state.get("last_daily"):
        state["last_daily"] = today

        stats = get_db_stats()
        match_strs = []
        for status, count in stats.get("matches_by_status", {}).items():
            match_strs.append(f"{count} {status}")
        match_line = " \u00b7 ".join(match_strs) if match_strs else "0 matches"

        msg = (
            f"\U0001f4ca Daily Report \u2014 {today}\n"
            f"\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\u2501\n"
            f"Matches: {match_line}\n"
            f"Score ticks: {stats.get('score_ticks', 0):,}\n"
            f"Odds ticks: {stats.get('odds_ticks', 0):,}\n"
            f"Completed: {stats.get('completed_matches', 0)}\n"
            f"Status: {'All healthy' if currently_healthy else 'Degraded'}"
        )
        send_telegram(msg)
        log("Sent daily report")

    # -- Update state ---------------------------------------------------
    save_state(state)


if __name__ == "__main__":
    try:
        run()
    except Exception as e:
        log(f"Monitor crashed: {e}")
        import traceback
        log(traceback.format_exc())
