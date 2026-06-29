"""Telegram bot handlers — player commands."""

import logging

from sqlalchemy import text
from sqlalchemy.orm import Session

from incidents.telegram_bot.helpers import _e, max_results

logger = logging.getLogger(__name__)


def _players(session: Session, search: str) -> str:
    try:
        if search:
            rows = session.execute(
                text(
                    "SELECT player_id, full_name, current_rank, nationality, gender "
                    "FROM players WHERE full_name ILIKE :pat "
                    "ORDER BY current_rank NULLS LAST LIMIT :lim"
                ),
                {"pat": f"%{search}%", "lim": max_results()},
            ).fetchall()
        else:
            rows = session.execute(
                text(
                    "SELECT player_id, full_name, current_rank, nationality, gender "
                    "FROM players ORDER BY current_rank NULLS LAST LIMIT :lim"
                ),
                {"lim": max_results()},
            ).fetchall()
    except Exception:
        return f"Error searching players: {_e(search or 'all')}"

    total = 0
    if not search:
        try:
            total = session.execute(text("SELECT count(*) FROM players")).scalar() or 0
        except Exception:
            pass

    if not rows:
        return f"No players found matching: {_e(search)}" if search else "No players in database."

    displayed = len(rows)
    lines = [
        "\U0001f3c6 <b>Players</b>",
    ]
    if search:
        lines.append(f"Search: \"{_e(search)}\" ({displayed} results)")
    else:
        lines.append(f"Total: {total} (showing {min(total, max_results())})")

    for row in rows:
        rank = f"#{row[2]}" if row[2] else "-"
        nat = _e(row[3] or "-")
        gender = _e(row[4] or "-")
        lines.append(f"  [{row[0]}] {_e(row[1])} ({nat}, {gender}) Rank {rank}")

    if total > max_results():
        lines.append(f"... and {total - max_results()} more")

    return "\n".join(lines)


def _player_detail(session: Session, identifier: str) -> str:
    try:
        pid = int(identifier)
        player = session.execute(
            text("SELECT * FROM players WHERE player_id = :id"),
            {"id": pid},
        ).mappings().fetchone()
    except ValueError:
        player = session.execute(
            text("SELECT * FROM players WHERE full_name ILIKE :name LIMIT 1"),
            {"name": f"%{identifier}%"},
        ).mappings().fetchone()

    if not player:
        return f"Player not found: {_e(identifier)}"

    _fn = _e(player.get("full_name", "?"))
    lines = [
        f"\U0001f3c6 <b>{_fn}</b>",
    ]

    _first = _e(player.get("first_name") or "")
    _last = _e(player.get("last_name") or "")
    _nationality = _e(player.get("nationality") or "")
    _dob = str(player.get("date_of_birth") or "")
    _plays = _e(player.get("plays") or "")
    _backhand = _e(player.get("backhand") or "")
    _gender = _e(player.get("gender") or "")
    _atp_wta = _e(player.get("atp_or_wta") or "")

    fields = {
        "Full Name": _fn,
        "First Name": _first,
        "Last Name": _last,
        "Nationality": _nationality,
        "Date of Birth": _dob,
        "Age": str(player.get("age", "")),
        "Height": f"{player.get('height', '')} cm" if player.get("height") else None,
        "Weight": f"{player.get('weight', '')} kg" if player.get("weight") else None,
        "Plays": _plays,
        "Backhand": _backhand,
        "Gender": _gender,
        "ATP/WTA": _atp_wta,
        "Current Rank": f"#{player.get('current_rank')}" if player.get("current_rank") else None,
        "Career High": f"#{player.get('career_high_rank')}" if player.get("career_high_rank") else None,
        "Ranking Points": str(player.get("ranking_points", "")),
    }

    lines.append("--- <b>Identity</b> ---")
    for label, value in fields.items():
        if value and value.strip():
            lines.append(f"{label}: {value}")

    win_pct = player.get("career_win_percentage")
    if win_pct:
        lines.append(f"Career W/L: {player.get('total_wins', '?')}-{player.get('total_losses', '?')} ({win_pct:.1f}%)")

    surfaces = []
    for s in ("hard", "clay", "grass", "indoor"):
        wp = player.get(f"{s}_win_percentage")
        if wp:
            w = player.get(f"{s}_wins", 0) or 0
            l = player.get(f"{s}_losses", 0) or 0
            surfaces.append(f"  {s.title()}: {w}-{l} ({wp:.1f}%)")
    if surfaces:
        lines.append("--- <b>Surface W/L</b> ---")
        lines.extend(surfaces)

    serve_fields = []
    for label, key in [
        ("1st Serve %", "first_serve_percentage"),
        ("1st Serve Won", "first_serve_points_won"),
        ("2nd Serve Won", "second_serve_points_won"),
        ("Service Games Won", "service_games_won"),
        ("Break Points Saved", "break_points_saved"),
        ("Return Points Won", "return_points_won"),
        ("Return Games Won", "return_games_won"),
        ("Break Points Conv", "break_points_converted"),
    ]:
        val = player.get(key)
        if val:
            serve_fields.append(f"  {label}: {val*100:.1f}%")

    if serve_fields:
        lines.append("--- <b>Serve/Return</b> ---")
        lines.extend(serve_fields)

    return "\n".join(lines)
