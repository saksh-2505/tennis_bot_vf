"""Telegram bot handlers — live data commands (scores, odds)."""

import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from incidents.telegram_bot.helpers import _e, max_results

logger = logging.getLogger(__name__)


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
        _p1 = _e(row[2] or "?")
        _p2 = _e(row[3] or "?")

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

        lines.append("")
        lines.append(f"[{mid}] {_p1} vs {_p2}")

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
            text("SELECT id, betting_market_id, player1_name, player2_name FROM tracked_matches WHERE status = 'LIVE' AND betting_market_id IS NOT NULL")
        ).fetchall()
    except Exception:
        return "Error querying live matches."

    if not live_matches:
        return "No live matches with odds."

    lines = ["\U0001f4b0 <b>Live Odds</b>"]

    for row in live_matches:
        mid = row[0]
        _p1 = _e(row[2] or "?")
        _p2 = _e(row[3] or "?")

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

        lines.append("")
        lines.append(f"[{mid}] {_p1} vs {_p2}")

        if odds_row:
            oa = f"{odds_row[0]:.2f}" if odds_row[0] else "?"
            ob = f"{odds_row[1]:.2f}" if odds_row[1] else "?"
            lines.append(f"  {_p1}: {oa}  \u2014  {_p2}: {ob}")
        else:
            lines.append("  No odds data yet")

    return "\n".join(lines)


def _scores_history(session: Session, match_id: str) -> str:
    try:
        mid = int(match_id)
    except ValueError:
        return "Invalid match ID."

    try:
        tm = session.execute(
            text("SELECT player1_name, player2_name, tournament FROM tracked_matches WHERE id = :id"),
            {"id": mid},
        ).fetchone()
    except Exception:
        tm = None

    if not tm:
        return f"Match {mid} not found."

    try:
        rows = session.execute(
            text(
                "SELECT timestamp, set_score_a, set_score_b, game_score_a, game_score_b, "
                "point_score, is_tiebreak, match_finished "
                "FROM live_scores WHERE tracked_match_id = :mid "
                "ORDER BY timestamp DESC LIMIT 20"
            ),
            {"mid": mid},
        ).fetchall()
    except Exception:
        return f"Error reading scores for match {mid}."

    total = 0
    try:
        total = session.execute(
            text("SELECT count(*) FROM live_scores WHERE tracked_match_id = :mid"),
            {"mid": mid},
        ).scalar() or 0
    except Exception:
        pass

    _p1 = _e(tm[0] or "?")
    _p2 = _e(tm[1] or "?")
    _tour = _e(tm[2] or "?")
    lines = [
        f"\U0001f4be <b>Scores History \u2014 Match {mid}</b>",
        f"{_p1} vs {_p2} ({_tour})",
        f"Total ticks: {total} (showing last {min(total, 20)})",
    ]

    if not rows:
        lines.append("No score data.")
        return "\n".join(lines)

    for row in rows:
        ts = row[0].strftime("%H:%M:%S") if row[0] else "?"
        sets = f"{row[1]}-{row[2]}" if row[1] is not None else "?-?"
        games = f"{row[3]}-{row[4]}" if row[3] is not None else "?-?"
        extra = ""
        if row[5]:
            extra += f" pt:{row[5]}"
        if row[6]:
            extra += " TB"
        if row[7]:
            extra += " FINISHED"
        lines.append(f"  {ts} | Set {sets} Game {games}{extra}")

    return "\n".join(lines)


def _odds_history(session: Session, match_id: str) -> str:
    try:
        mid = int(match_id)
    except ValueError:
        return "Invalid match ID."

    try:
        tm = session.execute(
            text("SELECT player1_name, player2_name, tournament FROM tracked_matches WHERE id = :id"),
            {"id": mid},
        ).fetchone()
    except Exception:
        tm = None

    if not tm:
        return f"Match {mid} not found."

    try:
        rows = session.execute(
            text(
                "SELECT timestamp, back_odds_a, back_odds_b, lay_odds_a, lay_odds_b "
                "FROM live_odds WHERE tracked_match_id = :mid "
                "ORDER BY timestamp DESC LIMIT 20"
            ),
            {"mid": mid},
        ).fetchall()
    except Exception:
        return f"Error reading odds for match {mid}."

    total = 0
    try:
        total = session.execute(
            text("SELECT count(*) FROM live_odds WHERE tracked_match_id = :mid"),
            {"mid": mid},
        ).scalar() or 0
    except Exception:
        pass

    _p1 = _e(tm[0] or "?")
    _p2 = _e(tm[1] or "?")
    _tour = _e(tm[2] or "?")
    lines = [
        f"\U0001f4b0 <b>Odds History \u2014 Match {mid}</b>",
        f"{_p1} vs {_p2} ({_tour})",
        f"Total ticks: {total} (showing last {min(total, 20)})",
    ]

    if not rows:
        lines.append("No odds data.")
        return "\n".join(lines)

    for row in rows:
        ts = row[0].strftime("%H:%M:%S") if row[0] else "?"
        ba = f"{row[1]:.2f}" if row[1] else "-"
        bb = f"{row[2]:.2f}" if row[2] else "-"
        la = f"{row[3]:.2f}" if row[3] else "-"
        lb = f"{row[4]:.2f}" if row[4] else "-"
        lines.append(f"  {ts} | Back: {ba} / {bb} | Lay: {la} / {lb}")

    return "\n".join(lines)


def _latest_scores(session: Session) -> str:
    try:
        rows = session.execute(
            text(
                "SELECT ls.tracked_match_id, tm.player1_name, tm.player2_name, "
                "ls.timestamp, ls.set_score_a, ls.set_score_b, "
                "ls.game_score_a, ls.game_score_b, ls.match_finished "
                "FROM live_scores ls "
                "JOIN tracked_matches tm ON tm.id = ls.tracked_match_id "
                "ORDER BY ls.timestamp DESC LIMIT 50"
            ),
        ).fetchall()
    except Exception:
        return "Error querying latest scores."

    if not rows:
        return "No score data."

    lines = ["\U0001f4be <b>Latest Score Ticks</b>"]
    for row in rows:
        ts = row[3].strftime("%H:%M:%S") if row[3] else "?"
        mid = row[0]
        _p1 = _e(row[1] or "?")
        _p2 = _e(row[2] or "?")
        sets = f"{row[4]}-{row[5]}" if row[4] is not None else "?-?"
        games = f"{row[6]}-{row[7]}" if row[6] is not None else "?-?"
        fin = " FINISHED" if row[8] else ""
        lines.append(f"  [{mid}] {ts} | {_p1} vs {_p2} | Set {sets} Game {games}{fin}")

    return "\n".join(lines)


def _latest_odds(session: Session) -> str:
    try:
        rows = session.execute(
            text(
                "SELECT lo.tracked_match_id, tm.player1_name, tm.player2_name, "
                "lo.timestamp, lo.back_odds_a, lo.back_odds_b "
                "FROM live_odds lo "
                "JOIN tracked_matches tm ON tm.id = lo.tracked_match_id "
                "ORDER BY lo.timestamp DESC LIMIT 50"
            ),
        ).fetchall()
    except Exception:
        return "Error querying latest odds."

    if not rows:
        return "No odds data."

    lines = ["\U0001f4b0 <b>Latest Odds Ticks</b>"]
    for row in rows:
        ts = row[3].strftime("%H:%M:%S") if row[3] else "?"
        mid = row[0]
        _p1 = _e(row[1] or "?")
        _p2 = _e(row[2] or "?")
        ba = f"{row[4]:.2f}" if row[4] else "?"
        bb = f"{row[5]:.2f}" if row[5] else "?"
        lines.append(f"  [{mid}] {ts} | {_p1}: {ba}  {_p2}: {bb}")

    return "\n".join(lines)
