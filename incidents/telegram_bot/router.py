"""Telegram bot router — polls updates, dispatches commands, manages offset."""

import logging
import os

import httpx
from sqlalchemy.orm import Session

from incidents.telegram_bot.helpers import init_bot, is_enabled, send_reply
from incidents.telegram_bot.offset_store import read_offset, write_offset
from incidents.telegram_bot.handlers_match import (
    _matches,
    _match_detail,
    _matches_by_status,
    _matches_by_tournament,
    _today,
    _scores_only,
    _tournaments,
)
from incidents.telegram_bot.handlers_live import (
    _scores,
    _odds,
    _scores_history,
    _odds_history,
    _latest_scores,
    _latest_odds,
)
from incidents.telegram_bot.handlers_player import (
    _players,
    _player_detail,
)
from incidents.telegram_bot.handlers_system import (
    _status,
    _completed,
    _incidents,
    _db_stats,
    _discovery,
    _stats_summary,
)

logger = logging.getLogger(__name__)

BOT_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN", "")
init_bot(BOT_TOKEN)

HELP_TEXT = (
    "\U0001f916 <b>Tennis Bot \u2014 Commands</b>\n\n"
    "<b>General</b>\n"
    "/start, /help \u2014 This message\n"
    "/status \u2014 Platform health overview\n\n"
    "<b>Matches</b>\n"
    "/matches \u2014 Match counts and live list\n"
    "/match &lt;id&gt; \u2014 Full details for a match\n"
    "/matches_by_status &lt;s&gt; \u2014 Filter by status (LIVE/SCHEDULED/FINISHED)\n"
    "/matches_by_tournament &lt;name&gt; \u2014 Search by tournament name\n"
    "/today \u2014 Matches scheduled today\n"
    "/scores_only \u2014 Matches without betting market (scores only)\n"
    "/tournaments \u2014 List all tournaments\n\n"
    "<b>Live Data</b>\n"
    "/scores \u2014 Current scores for live matches\n"
    "/odds \u2014 Current odds for live matches\n"
    "/scores_history &lt;id&gt; \u2014 Score tick history for a match\n"
    "/odds_history &lt;id&gt; \u2014 Odds tick history for a match\n"
    "/latest_scores \u2014 Last 50 score ticks across all matches\n"
    "/latest_odds \u2014 Last 50 odds ticks across all matches\n\n"
    "<b>Players</b>\n"
    "/players [search] \u2014 List or search players\n"
    "/player &lt;id|name&gt; \u2014 Full player stats\n\n"
    "<b>System</b>\n"
    "/completed \u2014 Finalized matches\n"
    "/incidents \u2014 Open incidents\n"
    "/db_stats \u2014 Table row counts and DB status\n"
    "/discovery \u2014 Discovery cycle summary\n"
    "/stats_summary \u2014 Aggregate collection stats"
)


def check_commands(session: Session) -> None:
    if not is_enabled():
        logger.debug("Telegram bot disabled \u2014 TELEGRAM_BOT_TOKEN not set")
        return

    offset = read_offset()
    updates = _fetch_updates(offset)
    for update in updates:
        msg = update.get("message", {})
        chat_id = msg.get("chat", {}).get("id")
        cmd_text = msg.get("text", "").strip()
        update_id = update.get("update_id", offset)

        if cmd_text and cmd_text.startswith("/") and chat_id:
            try:
                reply = _handle_command(session, cmd_text)
                send_reply(chat_id, reply)
            except Exception:
                logger.exception("Failed to process command: %s", cmd_text)
                write_offset(offset)
                return

        new_offset = update_id + 1
        if new_offset > offset:
            offset = new_offset
    write_offset(offset)


def _fetch_updates(offset: int) -> list[dict]:
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/getUpdates"
    params = {"offset": offset + 1, "timeout": 10}
    resp = httpx.get(url, params=params, timeout=15)
    data = resp.json()
    return data.get("result", []) if data.get("ok") else []


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
    elif cmd == "/matches_by_status":
        return _matches_by_status(session, arg) if arg else "Usage: /matches_by_status &lt;LIVE|SCHEDULED|FINISHED|DISCOVERED&gt;"
    elif cmd == "/matches_by_tournament":
        return _matches_by_tournament(session, arg) if arg else "Usage: /matches_by_tournament &lt;name&gt;"
    elif cmd == "/today":
        return _today(session)
    elif cmd == "/scores_only":
        return _scores_only(session)
    elif cmd == "/tournaments":
        return _tournaments(session)
    elif cmd in ("/scores", "/live_scores"):
        return _scores(session)
    elif cmd in ("/odds", "/live_odds"):
        return _odds(session)
    elif cmd == "/scores_history":
        return _scores_history(session, arg) if arg else "Usage: /scores_history &lt;match_id&gt;"
    elif cmd == "/odds_history":
        return _odds_history(session, arg) if arg else "Usage: /odds_history &lt;match_id&gt;"
    elif cmd == "/latest_scores":
        return _latest_scores(session)
    elif cmd == "/latest_odds":
        return _latest_odds(session)
    elif cmd == "/players":
        return _players(session, arg)
    elif cmd == "/player":
        return _player_detail(session, arg) if arg else "Usage: /player &lt;id|name&gt;"
    elif cmd in ("/completed", "/finalized"):
        return _completed(session)
    elif cmd == "/incidents":
        return _incidents(session)
    elif cmd == "/db_stats":
        return _db_stats(session)
    elif cmd == "/discovery":
        return _discovery(session)
    elif cmd == "/stats_summary":
        return _stats_summary(session)
    else:
        return f"Unknown command: {cmd}\n\n{HELP_TEXT}"
