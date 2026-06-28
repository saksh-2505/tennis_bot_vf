import datetime
from unittest.mock import AsyncMock, patch

import pytest

from collector.flashscore.client import fetch_match_details_batch, fetch_mobile_listing
from collector.flashscore.parser import (
    Match,
    RawMatch,
    build_match,
    extract_full_names_from_title,
    filter_singles,
    parse_mobile_listing,
)


MOBILE_HTML = """
<html>
<body>
<div id="score-data">
<h4>ATP - SINGLES: Eastbourne (United Kingdom), grass</h4>
<span>15:30</span>Bergs Z. (Bel) - Humbert U. (Fra) <a href="/match/hvrXnqVO/" class="sched">&nbsp;-&nbsp;</a><br />
<h4>ATP - SINGLES: Mallorca (Spain), grass</h4>
<span>15:00</span>Quinn E. (Usa) - Davidovich Fokina A. (Esp) <a href="/match/f1iwb9wQ/" class="sched">&nbsp;-&nbsp;</a><br />
<h4>WTA - SINGLES: Bad Homburg (Germany), grass</h4>
<span>11:10</span>Muchova K. (Cze) - Osaka N. (Jpn) RETIRED <a href="/match/jZLv4s5N/" class="fin">1-0</a><br />
<h4>WTA - SINGLES: Eastbourne (United Kingdom), grass</h4>
<span class="live">Set 2</span>Maria T. (Ger) - Keys M. (Usa) <a href="/match/tx6iHElf/" class="live">0-1</a><br />
<h4>ATP - DOUBLES: Mallorca (Spain), grass</h4>
<span>12:10</span>Goransson A./King E. - Arribage T./Olivetti A. <a href="/match/lCvwZUdD/" class="fin">1-2</a><br />
<h4>CHALLENGER MEN - SINGLES: Plovdiv (Bulgaria), clay</h4>
<span>16:00</span>Montes-De La Torre I. (Esp) - Kopp S. (Aut) <a href="/match/6NqPl50C/" class="sched">&nbsp;-&nbsp;</a><br />
<h4>ITF MEN - SINGLES: M15 Alkmaar (Netherlands), clay</h4>
<span>11:00</span>De Lange P. (Ned) - Lazaro Juncadella M. (Esp) <a href="/match/dSC7DWmJ/" class="sched">&nbsp;-&nbsp;</a><br />
<h4>EXHIBITION - MEN: Hurlingham (United Kingdom), grass</h4>
<span>15:30</span>Cobolli F. (Ita) - Etcheverry T. M. (Arg) <a href="/match/hp3ifXd3/" class="sched">&nbsp;-&nbsp;</a><br />
</div>
</body>
</html>
"""

MATCH_DETAIL_HTML = """
<html><head>
<title>Zizou Bergs v Ugo Humbert LIVE 27/06/2026 | Tennis - Flashscore</title>
</head><body></body></html>
"""

MATCH_DETAIL_NO_DATE = """
<html><head>
<title>Karolina Muchova v Naomi Osaka | Tennis - Flashscore</title>
</head><body></body></html>
"""


class TestParseMobileListing:
    def test_parses_all_matches(self) -> None:
        matches = parse_mobile_listing(MOBILE_HTML)
        assert len(matches) >= 6

    def test_extracts_match_id(self) -> None:
        matches = parse_mobile_listing(MOBILE_HTML)
        ids = {m.flashscore_match_id for m in matches}
        assert "hvrXnqVO" in ids
        assert "6NqPl50C" in ids

    def test_no_duplicate_ids(self) -> None:
        matches = parse_mobile_listing(MOBILE_HTML)
        ids = [m.flashscore_match_id for m in matches]
        assert len(ids) == len(set(ids))

    def test_player_names_exist(self) -> None:
        matches = parse_mobile_listing(MOBILE_HTML)
        for m in matches:
            assert m.player_a_abbr, f"player_a missing for {m.flashscore_match_id}"
            assert m.player_b_abbr, f"player_b missing for {m.flashscore_match_id}"

    def test_parses_tournament_names(self) -> None:
        matches = parse_mobile_listing(MOBILE_HTML)
        tournaments = {m.tournament for m in matches}
        assert "ATP - SINGLES: Eastbourne (United Kingdom), grass" in tournaments

    def test_determines_status(self) -> None:
        matches = parse_mobile_listing(MOBILE_HTML)
        statuses = {m.flashscore_match_id: m.status for m in matches}
        assert statuses["hvrXnqVO"] == "SCHEDULED"
        assert statuses["tx6iHElf"] == "LIVE"
        assert statuses["jZLv4s5N"] == "FINISHED"

    def test_parses_scheduled_time(self) -> None:
        matches = parse_mobile_listing(MOBILE_HTML)
        times = {m.flashscore_match_id: m.scheduled_time_str for m in matches}
        assert times["hvrXnqVO"] == "15:30"
        assert times["f1iwb9wQ"] == "15:00"


class TestFilterSingles:
    def test_filters_out_doubles(self) -> None:
        all_matches = parse_mobile_listing(MOBILE_HTML)
        singles = filter_singles(all_matches)
        ids = {m.flashscore_match_id for m in singles}
        assert "lCvwZUdD" not in ids  # ATP Doubles

    def test_filters_out_itf(self) -> None:
        all_matches = parse_mobile_listing(MOBILE_HTML)
        singles = filter_singles(all_matches)
        ids = {m.flashscore_match_id for m in singles}
        assert "dSC7DWmJ" not in ids  # ITF Men

    def test_filters_out_exhibition(self) -> None:
        all_matches = parse_mobile_listing(MOBILE_HTML)
        singles = filter_singles(all_matches)
        ids = {m.flashscore_match_id for m in singles}
        assert "hp3ifXd3" not in ids  # Exhibition

    def test_keeps_atp_wta_challenger_singles(self) -> None:
        all_matches = parse_mobile_listing(MOBILE_HTML)
        singles = filter_singles(all_matches)
        ids = {m.flashscore_match_id for m in singles}
        assert "hvrXnqVO" in ids  # ATP Singles
        assert "f1iwb9wQ" in ids  # ATP Singles
        assert "jZLv4s5N" in ids  # WTA Singles
        assert "tx6iHElf" in ids  # WTA Singles
        assert "6NqPl50C" in ids  # Challenger Men Singles


class TestExtractFullNames:
    def test_extracts_from_title(self) -> None:
        result = extract_full_names_from_title(MATCH_DETAIL_HTML)
        assert result == ("Zizou Bergs", "Ugo Humbert")

    def test_returns_none_for_unparseable(self) -> None:
        result = extract_full_names_from_title("<html></html>")
        assert result is None


class TestBuildMatch:
    def test_normalizes_names_to_uppercase(self) -> None:
        raw = RawMatch(
            flashscore_match_id="test123",
            tournament="ATP - SINGLES: Test",
            player_a_abbr="Test P.",
            player_b_abbr="Opponent Q.",
            scheduled_time_str="14:00",
            status="SCHEDULED",
        )
        match = build_match(raw, ("Test Player", "Opponent Quick"))
        assert match.player_a == "TEST PLAYER"
        assert match.player_b == "OPPONENT QUICK"

    def test_falls_back_to_abbreviated_names(self) -> None:
        raw = RawMatch(
            flashscore_match_id="test456",
            tournament="ATP - SINGLES: Test",
            player_a_abbr="Smith J.",
            player_b_abbr="Jones K.",
            scheduled_time_str="14:00",
            status="SCHEDULED",
        )
        match = build_match(raw, None)
        assert match.player_a == "SMITH J"
        assert match.player_b == "JONES K"

    def test_parses_scheduled_start_time(self) -> None:
        raw = RawMatch(
            flashscore_match_id="test789",
            tournament="ATP - SINGLES: Test",
            player_a_abbr="A B.",
            player_b_abbr="C D.",
            scheduled_time_str="14:30",
            status="SCHEDULED",
        )
        match_date = datetime.date(2026, 6, 27)
        match = build_match(raw, ("A B", "C D"), match_date)
        assert match.scheduled_start_time is not None
        assert match.scheduled_start_time.hour == 14
        assert match.scheduled_start_time.minute == 30

    def test_none_time_for_empty_string(self) -> None:
        raw = RawMatch(
            flashscore_match_id="test000",
            tournament="ATP - SINGLES: Test",
            player_a_abbr="A B.",
            player_b_abbr="C D.",
            scheduled_time_str="",
            status="SCHEDULED",
        )
        match = build_match(raw, ("A B", "C D"))
        assert match.scheduled_start_time is None


class TestDiscoverMatchesIntegration:
    @patch("collector.flashscore.client.fetch_mobile_listing")
    @patch("collector.flashscore.__init__.asyncio.run")
    def test_returns_match_objects(self, mock_async_run: AsyncMock, mock_fetch: AsyncMock) -> None:
        from collector.flashscore import discover_matches

        mock_fetch.return_value = MOBILE_HTML
        mock_async_run.return_value = {
            "hvrXnqVO": MATCH_DETAIL_HTML,
            "f1iwb9wQ": MATCH_DETAIL_NO_DATE,
            "jZLv4s5N": MATCH_DETAIL_NO_DATE,
            "tx6iHElf": MATCH_DETAIL_NO_DATE,
            "6NqPl50C": MATCH_DETAIL_NO_DATE,
        }

        matches = discover_matches()
        assert len(matches) >= 4
        assert all(isinstance(m, Match) for m in matches)

    @patch("collector.flashscore.client.fetch_mobile_listing")
    @patch("collector.flashscore.__init__.asyncio.run")
    def test_no_duplicate_match_ids(self, mock_async_run: AsyncMock, mock_fetch: AsyncMock) -> None:
        from collector.flashscore import discover_matches

        mock_fetch.return_value = MOBILE_HTML
        mock_async_run.return_value = {}

        matches = discover_matches()
        ids = [m.flashscore_match_id for m in matches]
        assert len(ids) == len(set(ids))

    @patch("collector.flashscore.client.fetch_mobile_listing")
    @patch("collector.flashscore.__init__.asyncio.run")
    def test_all_players_have_names(self, mock_async_run: AsyncMock, mock_fetch: AsyncMock) -> None:
        from collector.flashscore import discover_matches

        mock_fetch.return_value = MOBILE_HTML
        mock_async_run.return_value = {}

        matches = discover_matches()
        for m in matches:
            assert m.player_a, f"Empty player_a for {m.flashscore_match_id}"
            assert m.player_b, f"Empty player_b for {m.flashscore_match_id}"

    @patch("collector.flashscore.client.fetch_mobile_listing")
    @patch("collector.flashscore.__init__.asyncio.run")
    def test_normalized_names_are_uppercase(self, mock_async_run: AsyncMock, mock_fetch: AsyncMock) -> None:
        from collector.flashscore import discover_matches

        mock_fetch.return_value = MOBILE_HTML
        mock_async_run.return_value = {
            "hvrXnqVO": MATCH_DETAIL_HTML,
            "f1iwb9wQ": MATCH_DETAIL_NO_DATE,
            "jZLv4s5N": MATCH_DETAIL_NO_DATE,
            "tx6iHElf": MATCH_DETAIL_NO_DATE,
            "6NqPl50C": MATCH_DETAIL_NO_DATE,
        }

        matches = discover_matches()
        for m in matches:
            assert m.player_a == m.player_a.upper(), f"{m.player_a} not uppercase"
            assert m.player_b == m.player_b.upper(), f"{m.player_b} not uppercase"

    @patch("collector.flashscore.client.fetch_mobile_listing")
    @patch("collector.flashscore.__init__.asyncio.run")
    def test_scheduled_time_parsed(self, mock_async_run: AsyncMock, mock_fetch: AsyncMock) -> None:
        from collector.flashscore import discover_matches

        mock_fetch.return_value = MOBILE_HTML
        mock_async_run.return_value = {
            "hvrXnqVO": MATCH_DETAIL_HTML,
            "f1iwb9wQ": MATCH_DETAIL_NO_DATE,
            "jZLv4s5N": MATCH_DETAIL_NO_DATE,
            "tx6iHElf": MATCH_DETAIL_NO_DATE,
            "6NqPl50C": MATCH_DETAIL_NO_DATE,
        }

        matches = discover_matches()
        scheduled = [m for m in matches if m.scheduled_start_time is not None]
        assert len(scheduled) >= 1, "Expected at least one match with parsed start time"
        for m in scheduled:
            assert isinstance(m.scheduled_start_time, datetime.datetime)


class TestDatabaseSave:
    def test_save_creates_table_and_inserts(self) -> None:
        from collector.flashscore import save_matches_to_db
        from database import SessionLocal
        from models.flashscore import FlashscoreFoundMatch

        test_matches = [
            Match(
                flashscore_match_id="dbtest001",
                tournament="ATP - SINGLES: Test Tournament",
                player_a="PLAYER ONE",
                player_b="PLAYER TWO",
                scheduled_start_time=datetime.datetime(2026, 6, 27, 15, 0),
                status="SCHEDULED",
            ),
            Match(
                flashscore_match_id="dbtest002",
                tournament="WTA - SINGLES: Test Tournament",
                player_a="PLAYER THREE",
                player_b="PLAYER FOUR",
                scheduled_start_time=None,
                status="LIVE",
            ),
        ]

        saved = save_matches_to_db(test_matches)
        assert saved == 2

        with SessionLocal() as session:
            rows = session.query(FlashscoreFoundMatch).filter(
                FlashscoreFoundMatch.flashscore_match_id.like("dbtest%")
            ).all()
            assert len(rows) == 2

        with SessionLocal() as session:
            saved_again = save_matches_to_db(test_matches)
            assert saved_again == 0

        with SessionLocal() as session:
            session.query(FlashscoreFoundMatch).filter(
                FlashscoreFoundMatch.flashscore_match_id.like("dbtest%")
            ).delete()
            session.commit()
