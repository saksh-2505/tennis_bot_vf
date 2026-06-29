"""Telegram bot handlers — system commands (status, incidents, stats)."""

import logging
from datetime import datetime, timezone

from sqlalchemy import text
from sqlalchemy.orm import Session

from incidents.telegram_bot.helpers import _e, max_results

logger = logging.getLogger(__name__)


def _status(session: Session) -> str:
    now = datetime.now(timezone.utc)

    db_ok = "Unknown"
    try:
        session.execute(text("SELECT 1"))
        db_ok = "Connected"
    except Exception:
        db_ok = "Unreachable"

    counts = {}
    try:
        rows = session.execute(
            text("SELECT status, count(*) FROM tracked_matches GROUP BY status")
        ).fetchall()
        counts = {row[0]: row[1] for row in rows}
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

    total_matches = sum(counts.values())
    live = counts.get("LIVE", 0)
    scheduled = counts.get("SCHEDULED", 0)
    finished = counts.get("FINISHED", 0)

    lines = [
        "\U0001f3be <b>Tennis Bot \u2014 Status</b>",
        f"Database: {db_ok}",
        f"Matches: {total_matches} (LIVE: {live}, SCHEDULED: {scheduled}, FINISHED: {finished})",
        f"Score ticks: {score_count:,}",
        f"Odds ticks: {odds_count:,}",
        f"Open incidents: {incident_count}",
        f"Bot time: {now.strftime('%Y-%m-%d %H:%M:%S UTC')}",
    ]
    return "\n".join(lines)


def _completed(session: Session) -> str:
    try:
        rows = session.execute(
            text(
                "SELECT cm.id, cm.tracked_match_id, tm.player1_name, tm.player2_name, "
                "cm.final_set_score, cm.score_tick_count, cm.odds_tick_count, "
                "cm.finalized_at, cm.validation_passed "
                "FROM completed_matches cm "
                "JOIN tracked_matches tm ON tm.id = cm.tracked_match_id "
                "ORDER BY cm.finalized_at DESC LIMIT :lim"
            ),
            {"lim": max_results()},
        ).fetchall()
    except Exception:
        return "Error querying completed matches."

    total = 0
    try:
        total = session.execute(text("SELECT count(*) FROM completed_matches")).scalar() or 0
    except Exception:
        pass

    if not rows:
        return "No completed matches."

    displayed = min(len(rows), max_results())
    lines = [
        f"\U0001f3c6 <b>Completed Matches</b> ({total} total, showing {displayed})",
    ]
    for row in rows:
        ts = row[7].strftime("%m/%d %H:%M") if row[7] else "?"
        valid = "\u2705" if row[8] else "\u274c"
        _p1 = _e(row[2] or "?")
        _p2 = _e(row[3] or "?")
        lines.append(
            f"  [{row[1]}] {_p1} vs {_p2} "
            f"| Score: {row[4] or '?'} | Ticks: {row[5] or 0}s/{row[6] or 0}o "
            f"| {ts} {valid}"
        )

    if total > max_results():
        lines.append(f"... and {total - max_results()} more")

    return "\n".join(lines)


def _incidents(session: Session) -> str:
    try:
        rows = session.execute(
            text(
                "SELECT incident_id, severity, category, title, status, occurrence_count, "
                "first_detected_at, last_detected_at, module "
                "FROM incidents WHERE status IN ('OPEN', 'ACKNOWLEDGED', 'RECOVERING') "
                "ORDER BY severity DESC, first_detected_at DESC"
            ),
        ).fetchall()
    except Exception:
        return "Error querying incidents."

    if not rows:
        return "No open incidents."

    lines = ["\u26a0\ufe0f <b>Open Incidents</b>"]
    for row in rows:
        first = row[6].strftime("%m/%d %H:%M") if row[6] else "?"
        _title = _e(row[3])
        _module = _e(row[8])
        lines.append(
            f"  INC_{row[0]} [{row[1]}] {_title}"
            f"\n    Module: {_module} | Count: {row[5]} | Since: {first}"
        )

    try:
        resolved = session.execute(
            text(
                "SELECT incident_id, severity, title, resolved_at "
                "FROM incidents WHERE status = 'RESOLVED' "
                "ORDER BY resolved_at DESC LIMIT 5"
            ),
        ).fetchall()
    except Exception:
        resolved = []

    if resolved:
        lines.append("")
        lines.append("<b>Recently Resolved:</b>")
        for row in resolved:
            rs = row[3].strftime("%H:%M") if row[3] else "?"
            lines.append(f"  INC_{row[0]} [{row[1]}] {_e(row[2])} @ {rs}")

    return "\n".join(lines)


def _db_stats(session: Session) -> str:
    tables = [
        "tracked_matches", "flashscorefoundmatches", "bettingsitefoundmatches",
        "players", "live_scores", "live_odds", "completed_matches", "incidents",
    ]
    lines = ["\U0001f5c4 <b>Database Stats</b>"]

    for table in tables:
        try:
            count = session.execute(text(f"SELECT count(*) FROM {table}")).scalar() or 0
        except Exception:
            count = "?"

        has_odds = ""
        if table == "tracked_matches":
            try:
                no_odds = session.execute(
                    text("SELECT count(*) FROM tracked_matches WHERE betting_market_id IS NULL")
                ).scalar() or 0
                has_odds = f" ({no_odds} scores-only)"
            except Exception:
                pass

        lines.append(f"  {table}: {count:,}{has_odds}")

    try:
        result = session.execute(text("SELECT version()")).scalar()
        lines.append(f"\nDB: {result.split(',')[0]}")
    except Exception:
        pass

    return "\n".join(lines)


def _discovery(session: Session) -> str:
    try:
        fs = session.execute(text("SELECT count(*) FROM flashscorefoundmatches")).scalar() or 0
        bt = session.execute(text("SELECT count(*) FROM bettingsitefoundmatches")).scalar() or 0
        players = session.execute(text("SELECT count(*) FROM players")).scalar() or 0
        tracked = session.execute(text("SELECT count(*) FROM tracked_matches")).scalar() or 0
        with_odds = session.execute(
            text("SELECT count(*) FROM tracked_matches WHERE betting_market_id IS NOT NULL")
        ).scalar() or 0
    except Exception:
        return "Error querying discovery stats."

    lines = [
        "\U0001f50d <b>Discovery Summary</b>",
        f"Flashscore matches: {fs}",
        f"Betting site markets: {bt}",
        f"Players: {players}",
        f"Tracked matches: {tracked}",
        f"  With odds: {with_odds}",
        f"  Scores-only: {tracked - with_odds}",
    ]

    try:
        last_fs = session.execute(
            text("SELECT MAX(discovered_at) FROM flashscorefoundmatches")
        ).scalar()
        if last_fs:
            lines.append(f"Last Flashscore disc: {last_fs}")
    except Exception:
        pass

    try:
        last_bt = session.execute(
            text("SELECT MAX(discovered_at) FROM bettingsitefoundmatches")
        ).scalar()
        if last_bt:
            lines.append(f"Last Betting site disc: {last_bt}")
    except Exception:
        pass

    return "\n".join(lines)


def _stats_summary(session: Session) -> str:
    lines = ["\U0001f4ca <b>Stats Summary</b>"]

    try:
        avg_scores = session.execute(
            text(
                "SELECT AVG(cnt)::int, MAX(cnt), MIN(cnt) FROM ("
                "SELECT count(*) as cnt FROM live_scores GROUP BY tracked_match_id"
                ") sub"
            ),
        ).fetchone()
        if avg_scores and avg_scores[0]:
            lines.append(f"Scores per match: avg {avg_scores[0]}, max {avg_scores[1]}, min {avg_scores[2]}")
    except Exception:
        pass

    try:
        avg_odds = session.execute(
            text(
                "SELECT AVG(cnt)::int, MAX(cnt), MIN(cnt) FROM ("
                "SELECT count(*) as cnt FROM live_odds GROUP BY tracked_match_id"
                ") sub"
            ),
        ).fetchone()
        if avg_odds and avg_odds[0]:
            lines.append(f"Odds per match: avg {avg_odds[0]}, max {avg_odds[1]}, min {avg_odds[2]}")
    except Exception:
        pass

    try:
        finished = session.execute(
            text("SELECT count(*) FROM completed_matches WHERE validation_passed = TRUE")
        ).scalar() or 0
        failed = session.execute(
            text("SELECT count(*) FROM completed_matches WHERE validation_passed = FALSE")
        ).scalar() or 0
        lines.append(f"Finalized: {finished + failed} ({finished} passed, {failed} failed)")
    except Exception:
        pass

    try:
        has_betting = session.execute(
            text("SELECT count(*) FROM tracked_matches WHERE betting_market_id IS NOT NULL")
        ).scalar() or 0
        total = session.execute(text("SELECT count(*) FROM tracked_matches")).scalar() or 0
        pct = (has_betting / total * 100) if total > 0 else 0
        lines.append(f"Betting coverage: {has_betting}/{total} ({pct:.0f}%)")
    except Exception:
        pass

    return "\n".join(lines)
