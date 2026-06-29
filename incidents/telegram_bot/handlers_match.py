"""Telegram bot handlers — match-related commands."""

import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from incidents.telegram_bot.helpers import _e, max_results

logger = logging.getLogger(__name__)


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
    has_odds = 0
    try:
        has_odds = session.execute(
            text("SELECT count(*) FROM tracked_matches WHERE betting_market_id IS NOT NULL")
        ).scalar() or 0
    except Exception:
        pass

    lines = [
        "\U0001f3be <b>Matches</b>",
        f"Total: {total} (with odds: {has_odds}, scores-only: {total - has_odds})",
    ]
    for status in ("LIVE", "SCHEDULED", "FINISHED", "DISCOVERED"):
        lines.append(f"  {status}: {counts.get(status, 0)}")

    try:
        live = session.execute(
            text("SELECT id, player1_name, player2_name, tournament FROM tracked_matches WHERE status = 'LIVE' ORDER BY id LIMIT :lim"),
            {"lim": max_results()},
        ).fetchall()
    except Exception:
        live = []

    if live:
        lines.append("")
        lines.append("<b>Live now:</b>")
        for row in live:
            _p1 = _e(row[1] or "?")
            _p2 = _e(row[2] or "?")
            lines.append(f"  [{row[0]}] {_p1} vs {_p2}")
    else:
        lines.append("")
        lines.append("No live matches.")

    return "\n".join(lines)


def _match_detail(session: Session, match_id: str) -> str:
    try:
        mid = int(match_id)
    except ValueError:
        return "Invalid match ID."

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

    _p1 = _e(tm.get("player1_name", "?"))
    _p2 = _e(tm.get("player2_name", "?"))
    _tour = _e(tm.get("tournament", "?"))
    _round = _e(tm.get("round", "?"))
    _surface = _e(tm.get("surface", "?"))
    _status = _e(tm.get("status", "?"))
    _fs_id = _e(tm.get("flashscore_match_id", "?"))
    _url = _e(tm.get("live_url", ""))

    fields = {
        "Players": f"{_p1} vs {_p2}",
        "Tournament": _tour,
        "Round": _round,
        "Surface": _surface,
        "Status": _status,
        "Tracking": "Enabled" if tm.get("tracking_enabled") else "Disabled",
        "Player1 ID": str(tm.get("player1_id", "")),
        "Player2 ID": str(tm.get("player2_id", "")),
        "FS Match ID": _fs_id,
        "Betting Market": tm.get("betting_market_id") or "\u274c None (scores only)",
        "Duration": f"{tm.get('match_duration_min', '-')} min" if tm.get("match_duration_min") else "-",
    }

    for label, value in fields.items():
        if value and str(value) not in ("?", "", "-", "\u274c None (scores only)"):
            lines.append(f"{label}: {value}")
        elif label == "Betting Market" and value == "\u274c None (scores only)":
            lines.append(f"{label}: {value}")

    if tm.get("scheduled_start"):
        lines.append(f"Scheduled: {tm['scheduled_start']}")
    if tm.get("actual_finish"):
        lines.append(f"Finished: {tm['actual_finish']}")
    if tm.get("live_url"):
        lines.append(f"URL: {_url}")

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


def _matches_by_status(session: Session, status: str) -> str:
    status = status.upper()
    if status not in ("LIVE", "SCHEDULED", "FINISHED", "DISCOVERED"):
        return "Invalid status. Use: LIVE, SCHEDULED, FINISHED, or DISCOVERED."

    try:
        rows = session.execute(
            text(
                "SELECT id, player1_name, player2_name, tournament, scheduled_start "
                "FROM tracked_matches WHERE status = :s "
                "ORDER BY scheduled_start NULLS LAST, id LIMIT :lim"
            ),
            {"s": status, "lim": max_results()},
        ).fetchall()
    except Exception:
        return f"Error querying {status} matches."

    if not rows:
        return f"No matches with status: {status}"

    total = len(rows)
    try:
        total = session.execute(
            text("SELECT count(*) FROM tracked_matches WHERE status = :s"),
            {"s": status},
        ).scalar() or 0
    except Exception:
        pass

    displayed = min(len(rows), max_results())
    lines = [
        f"\U0001f3be <b>{status} Matches</b> ({total} total, showing {displayed})",
    ]

    for row in rows:
        start = row[4].strftime("%H:%M UTC") if row[4] else "?"
        _p1 = _e(row[1] or "?")
        _p2 = _e(row[2] or "?")
        _tour = _e(row[3] or "?")
        lines.append(f"  [{row[0]}] {_p1} vs {_p2} @ {start} | {_tour}")

    if total > max_results():
        lines.append(f"... and {total - max_results()} more")

    return "\n".join(lines)


def _matches_by_tournament(session: Session, name: str) -> str:
    try:
        rows = session.execute(
            text(
                "SELECT id, player1_name, player2_name, status, scheduled_start "
                "FROM tracked_matches WHERE tournament ILIKE :pat "
                "ORDER BY scheduled_start NULLS LAST LIMIT :lim"
            ),
            {"pat": f"%{name}%", "lim": max_results()},
        ).fetchall()
    except Exception:
        return f"Error searching tournaments for: {name}"

    if not rows:
        return f"No matches found matching: {name}"

    total = 0
    try:
        total = session.execute(
            text("SELECT count(*) FROM tracked_matches WHERE tournament ILIKE :pat"),
            {"pat": f"%{name}%"},
        ).scalar() or 0
    except Exception:
        pass

    displayed = min(len(rows), max_results())
    lines = [
        f"\U0001f3be <b>Tournament: {_e(name)}</b> ({total} matches, showing {displayed})",
    ]

    for row in rows:
        start = row[4].strftime("%m/%d %H:%M") if row[4] else "?"
        _p1 = _e(row[1] or "?")
        _p2 = _e(row[2] or "?")
        lines.append(f"  [{row[0]}] {_p1} vs {_p2} [{row[3]}] @ {start}")

    if total > max_results():
        lines.append(f"... and {total - max_results()} more")

    return "\n".join(lines)


def _today(session: Session) -> str:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    try:
        rows = session.execute(
            text(
                "SELECT id, player1_name, player2_name, status, scheduled_start, tournament "
                "FROM tracked_matches WHERE date(scheduled_start) = :today "
                "ORDER BY scheduled_start, id LIMIT :lim"
            ),
            {"today": today, "lim": max_results()},
        ).fetchall()
    except Exception:
        return "Error querying today's matches."

    total = 0
    try:
        total = session.execute(
            text("SELECT count(*) FROM tracked_matches WHERE date(scheduled_start) = :today"),
            {"today": today},
        ).scalar() or 0
    except Exception:
        pass

    if not rows:
        return "No matches scheduled for today."

    displayed = min(len(rows), max_results())
    lines = [
        f"\U0001f3be <b>Today's Matches</b> ({total} total, showing {displayed})",
    ]
    for row in rows:
        start = row[4].strftime("%H:%M") if row[4] else "?"
        _p1 = _e(row[1] or "?")
        _p2 = _e(row[2] or "?")
        lines.append(f"  [{row[0]}] {start} | {_p1} vs {_p2} [{row[3]}]")

    if total > max_results():
        lines.append(f"... and {total - max_results()} more")

    return "\n".join(lines)


def _scores_only(session: Session) -> str:
    try:
        rows = session.execute(
            text(
                "SELECT id, player1_name, player2_name, status, flashscore_match_id "
                "FROM tracked_matches WHERE betting_market_id IS NULL "
                "ORDER BY status, id LIMIT :lim"
            ),
            {"lim": max_results()},
        ).fetchall()
    except Exception:
        return "Error querying scores-only matches."

    total = 0
    try:
        total = session.execute(
            text("SELECT count(*) FROM tracked_matches WHERE betting_market_id IS NULL"),
        ).scalar() or 0
    except Exception:
        pass

    if not rows:
        return "No scores-only matches (all have betting markets)."

    displayed = min(len(rows), max_results())
    lines = [
        f"\U0001f3be <b>Scores-Only Matches</b> ({total} total, showing {displayed})",
        "(No betting market \u2014 scores collected, no odds)",
    ]
    for row in rows:
        _p1 = _e(row[1] or "?")
        _p2 = _e(row[2] or "?")
        lines.append(f"  [{row[0]}] {_p1} vs {_p2} [{row[3]}] (FS: {_e(row[4] or '?')})")

    if total > max_results():
        lines.append(f"... and {total - max_results()} more")

    return "\n".join(lines)


def _tournaments(session: Session) -> str:
    try:
        rows = session.execute(
            text(
                "SELECT tournament, count(*) as cnt, "
                "count(*) FILTER (WHERE betting_market_id IS NOT NULL) as with_odds, "
                "count(*) FILTER (WHERE status = 'LIVE') as live "
                "FROM tracked_matches GROUP BY tournament ORDER BY cnt DESC LIMIT 30"
            ),
        ).fetchall()
    except Exception:
        return "Error querying tournaments."

    if not rows:
        return "No tournaments found."

    lines = [
        "\U0001f3be <b>Tournaments</b>",
    ]
    for row in rows:
        lines.append(f"  {_e(row[0])}: {row[1]} matches ({row[2]} with odds, {row[3]} live)")

    return "\n".join(lines)
