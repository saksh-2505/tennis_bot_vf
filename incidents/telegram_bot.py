import logging
import os
from datetime import datetime, timezone

import httpx
from sqlalchemy import text
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
OFFSET_FILE = "/tmp/telegram_offset"

_enabled = bool(BOT_TOKEN)

HELP_TEXT = (
    "Available commands:\n"
    "/start, /help — Show this message\n"
    "/status — Platform health overview\n"
    "/matches — Match counts and active matches\n"
    "/match &lt;id&gt; — Full details for a match\n"
    "/scores — Current scores for live matches\n"
    "/odds — Current odds for live matches\n"
    "/incidents — Open incidents"
)


def check_commands(session: Session) -> None:
    if not _enabled:
        logger.debug("Telegram bot disabled — TELEGRAM_BOT_TOKEN not set")
        return

    offset = _read_offset()
    logger.info("Telegram bot poll start (offset=%d)", offset)
    try:
        updates = _fetch_updates(offset)
        logger.info("Telegram poll returned %d updates", len(updates))
        for update in updates:
            msg = update.get("message", {})
            chat_id = msg.get("chat", {}).get("id")
            cmd_text = msg.get("text", "").strip()
            logger.debug(
                "Telegram update: chat=%s cmd=%r",
                chat_id, cmd_text,
            )
            if cmd_text and cmd_text.startswith("/") and chat_id:
                reply = _handle_command(session, cmd_text)
                logger.info("Telegram reply to chat=%s for %r", chat_id, cmd_text)
                _send_reply(chat_id, reply)
                logger.debug("Telegram reply sent for chat=%s", chat_id)
            new_offset = update.get("update_id", offset) + 1
            if new_offset > offset:
                offset = new_offset
        _write_offset(offset)
        logger.info("Telegram bot poll done (new offset=%d)", offset)
    except Exception:
        logger.exception("Telegram bot check failed")


def _fetch_updates(offset: int) -> list[dict]:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset + 1, "timeout": 10}
    resp = httpx.get(url, params=params, timeout=15)
    data = resp.json()
    return data.get("result", []) if data.get("ok") else []


def _send_reply(chat_id: int, text: str) -> None:
    try:
        httpx.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={"chat_id": chat_id, "text": text, "parse_mode": "HTML"},
            timeout=15,
        )
    except Exception as e:
        logger.warning("Telegram reply failed: %s", e)


def _handle_command(session: Session, text: str) -> str:
    parts = text.split(maxsplit=1)
    cmd = parts[0].lower()
    arg = parts[1].strip() if len(parts) > 1 else ""

    if cmd in ("/start", "/help"):
        return HELP_TEXT
    elif cmd == "/status":
        return _status(session)
    elif cmd == "/matches":
        return _matches(session)
    elif cmd == "/match":
        return _match_detail(session, arg) if arg else "Usage: /match &lt;id&gt;"
    elif cmd == "/scores":
        return _scores(session)
    elif cmd == "/odds":
        return _odds(session)
    elif cmd == "/incidents":
        return _incidents(session)
    else:
        return f"Unknown command: {cmd}\n\n{HELP_TEXT}"


def _status(session: Session) -> str:
    now = datetime.now(timezone.utc)

    db_ok = "Unknown"
    try:
        session.execute(text("SELECT 1"))
        db_ok = "Connected"
    except Exception:
        db_ok = "Unreachable"

    live_count = 0
    try:
        live_count = session.execute(
            text("SELECT count(*) FROM tracked_matches WHERE status = 'LIVE'")
        ).scalar() or 0
    except Exception:
        pass

    score_count = odds_count = 0
    try:
        score_count = session.execute(text("SELECT count(*) FROM live_scores")).scalar() or 0
        odds_count = session.execute(text("SELECT count(*) FROM live_odds")).scalar() or 0
    except Exception:
        pass

    incident_count = 0
    try:
        incident_count = session.execute(
            text("SELECT count(*) FROM incidents WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'RECOVERING')")
        ).scalar() or 0
    except Exception:
        pass

    lines = [
        "\U0001f3be <b>Tennis Bot — Status</b>",
        f"Database: {db_ok}",
        f"Live matches: {live_count}",
        f"Score ticks: {score_count:,}",
        f"Odds ticks: {odds_count:,}",
        f"Open incidents: {incident_count}",
        f"Bot time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
    ]
    return "\n".join(lines)


def _matches(session: Session) -> str:
    counts = {}
    try:
        rows = session.execute(
            text("SELECT status, count(*) FROM tracked_matches GROUP BY status")
        ).fetchall()
        counts = {row[0]: row[1] for row in rows}
    except Exception:
        return "Error querying matches."

    total = sum(counts.values())
    lines = [
        f"\U0001f3be <b>Matches</b>",
        f"Total: {total}",
    ]
    for status in ("LIVE", "DISCOVERED", "FINISHED"):
        lines.append(f"  {status}: {counts.get(status, 0)}")

    try:
        live = session.execute(
            text("SELECT id, player1_name, player2_name, tournament FROM tracked_matches WHERE status = 'LIVE' ORDER BY id")
        ).fetchall()
    except Exception:
        live = []

    if live:
        lines.append("")
        lines.append("<b>Live now:</b>")
        for row in live:
            lines.append(f"  [{row[0]}] {row[1]} vs {row[2]} ({row[3]})")
    else:
        lines.append("")
        lines.append("No live matches.")

    return "\n".join(lines)


def _match_detail(session: Session, match_id: str) -> str:
    try:
        mid = int(match_id)
    except ValueError:
        return "Invalid match ID. Usage: /match &lt;id&gt;"

    try:
        tm = session.execute(
            text("SELECT * FROM tracked_matches WHERE id = :id"),
            {"id": mid},
        ).mappings().fetchone()
    except Exception:
        tm = None

    if not tm:
        return f"Match {mid} not found."

    lines = [
        f"\U0001f3be <b>Match {mid}</b>",
    ]

    fields = {
        "Players": f"{tm.get('player1_name', '?')} vs {tm.get('player2_name', '?')}",
        "Tournament": tm.get("tournament", "?"),
        "Round": tm.get("round", "?"),
        "Surface": tm.get("surface", "?"),
        "Status": tm.get("status", "?"),
        "Tracking": "Enabled" if tm.get("tracking_enabled") else "Disabled",
        "Duration": f"{tm.get('match_duration_min', '-')} min" if tm.get("match_duration_min") else "-",
    }
    for label, value in fields.items():
        if value and value != "?":
            lines.append(f"{label}: {value}")

    if tm.get("scheduled_start"):
        lines.append(f"Scheduled: {tm['scheduled_start']}")
    if tm.get("actual_finish"):
        lines.append(f"Finished: {tm['actual_finish']}")

    try:
        score_info = session.execute(
            text("SELECT MAX(timestamp) as ts, count(*) as cnt FROM live_scores WHERE tracked_match_id = :mid"),
            {"mid": mid},
        ).fetchone()
        if score_info:
            lines.append(f"Scores: {score_info[1]} ticks, last at {score_info[0] or '-'}")
    except Exception:
        pass

    try:
        odds_info = session.execute(
            text("SELECT MAX(timestamp) as ts, count(*) as cnt FROM live_odds WHERE tracked_match_id = :mid"),
            {"mid": mid},
        ).fetchone()
        if odds_info:
            lines.append(f"Odds: {odds_info[1]} ticks, last at {odds_info[0] or '-'}")
    except Exception:
        pass

    try:
        finalized = session.execute(
            text("SELECT id FROM completed_matches WHERE tracked_match_id = :mid"),
            {"mid": mid},
        ).fetchone()
        lines.append(f"Finalized: {'Yes (ID: ' + str(finalized[0]) + ')' if finalized else 'No'}")
    except Exception:
        pass

    return "\n".join(lines)


def _scores(session: Session) -> str:
    try:
        live_matches = session.execute(
            text("SELECT id, flashscore_match_id, player1_name, player2_name FROM tracked_matches WHERE status = 'LIVE'")
        ).fetchall()
    except Exception:
        return "Error querying live matches."

    if not live_matches:
        return "No live matches."

    lines = ["\U0001f4be <b>Live Scores</b>"]

    for row in live_matches:
        mid = row[0]
        fs_id = row[1]
        p1 = row[2] or "?"
        p2 = row[3] or "?"

        try:
            snap = session.execute(
                text(
                    "SELECT set_score_a, set_score_b, game_score_a, game_score_b, "
                    "point_score, server, is_tiebreak, match_finished "
                    "FROM live_scores WHERE tracked_match_id = :mid "
                    "ORDER BY timestamp DESC LIMIT 1"
                ),
                {"mid": mid},
            ).fetchone()
        except Exception:
            snap = None

        lines.append(f"")
        lines.append(f"[{mid}] {p1} vs {p2}")

        if snap:
            parts = []
            if snap[0] is not None:
                parts.append(f"Set: {snap[0]}-{snap[1]}")
            if snap[2] is not None:
                parts.append(f"Game: {snap[2]}-{snap[3]}")
            if snap[4]:
                parts.append(f"Point: {snap[4]}")
            if snap[6]:
                parts.append("Tiebreak")
            if snap[7]:
                parts.append("FINISHED")
            if parts:
                lines.append(f"  {', '.join(parts)}")
            else:
                lines.append("  No score data yet")
        else:
            lines.append("  No score data yet")

    return "\n".join(lines)


def _odds(session: Session) -> str:
    try:
        live_matches = session.execute(
            text("SELECT id, betting_market_id, player1_name, player2_name FROM tracked_matches WHERE status = 'LIVE'")
        ).fetchall()
    except Exception:
        return "Error querying live matches."

    if not live_matches:
        return "No live matches."

    lines = ["\U0001f4b0 <b>Live Odds</b>"]

    for row in live_matches:
        mid = row[0]
        mid_id = row[1]
        p1 = row[2] or "?"
        p2 = row[3] or "?"

        try:
            odds_row = session.execute(
                text(
                    "SELECT back_odds_a, back_odds_b, timestamp "
                    "FROM live_odds WHERE tracked_match_id = :mid "
                    "ORDER BY timestamp DESC LIMIT 1"
                ),
                {"mid": mid},
            ).fetchone()
        except Exception:
            odds_row = None

        lines.append(f"")
        lines.append(f"[{mid}] {p1} vs {p2}")

        if odds_row:
            oa = f"{odds_row[0]:.2f}" if odds_row[0] else "?"
            ob = f"{odds_row[1]:.2f}" if odds_row[1] else "?"
            lines.append(f"  {p1}: {oa}  —  {p2}: {ob}")
        else:
            lines.append("  No odds data yet")

        if mid_id:
            lines.append(f"  Market: {mid_id}")

    return "\n".join(lines)


def _incidents(session: Session) -> str:
    try:
        rows = session.execute(
            text(
                "SELECT incident_id, severity, category, title, status, occurrence_count "
                "FROM incidents WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'RECOVERING') "
                "ORDER BY severity DESC, first_detected_at DESC"
            )
        ).fetchall()
    except Exception:
        return "Error querying incidents."

    if not rows:
        return "No open incidents."

    lines = ["\u26a0\ufe0f <b>Open Incidents</b>"]

    for row in rows:
        lines.append(
            f"  INC_{row[0]} [{row[1]}] {row[2]} — {row[3]} "
            f"({row[4]}, occurred {row[5]}x)"
        )

    return "\n".join(lines)


def _read_offset() -> int:
    try:
        with open(OFFSET_FILE) as f:
            return int(f.read().strip())
    except (FileNotFoundError, ValueError, OSError):
        return 0


def _write_offset(offset: int) -> None:
    try:
        with open(OFFSET_FILE, "w") as f:
            f.write(str(offset))
    except OSError:
        pass
