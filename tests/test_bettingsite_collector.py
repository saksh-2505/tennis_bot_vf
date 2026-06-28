import datetime
from unittest.mock import Mock, patch

import pytest

from collector.betting_site.parser import (
    BettingsiteMatch,
    _extract_last_name,
    _names_match,
    _word_matches,
    filter_tennis_matches,
    match_events_to_flashscore,
    parse_odds_for_runners,
    parse_odds_pipe,
)
from collector.flashscore.parser import Match as FlashscoreMatch


SAMPLE_EVENTS = [
    {
        "event_id": 35763753,
        "name": "Et Quinn v Davidovich Fokina",
        "event_type_id": 2,
        "competition_id": 12811055,
        "open_date": "2026-06-27 06:35:00",
    },
    {
        "event_id": 35762982,
        "name": "T Maria v Keys",
        "event_type_id": 2,
        "competition_id": 12810997,
        "open_date": "2026-06-27 06:55:00",
    },
    {
        "event_id": 35763242,
        "name": "Balshaw v Nagal",
        "event_type_id": 2,
        "competition_id": 12811247,
        "open_date": "2026-06-27 13:00:00",
    },
    {
        "event_id": 35764685,
        "name": "Mat Pucinelli de Almeid v Villanueva",
        "event_type_id": 2,
        "competition_id": 12811373,
        "open_date": "2026-06-27 13:00:00",
    },
    {
        "event_id": 99999999,
        "name": "ATP Eastbourne 2026 - Winner",
        "event_type_id": 2,
        "competition_id": 999999993,
        "open_date": "2026-06-22 00:00:00",
    },
    {
        "event_id": 12345678,
        "name": "Cricket Match",
        "event_type_id": 4,
        "competition_id": 111,
        "open_date": "2026-06-27 10:00:00",
    },
    {
        "event_id": 35764765,
        "name": "Th Seyboth Wild v J La Serna",
        "event_type_id": 2,
        "competition_id": 12811373,
        "open_date": "2026-06-27 15:00:00",
    },
]

FLASHSCORE_MATCHES = [
    FlashscoreMatch(
        flashscore_match_id="abc123",
        tournament="ATP - SINGLES: Mallorca",
        player_a="ETHAN QUINN",
        player_b="ALEJANDRO DAVIDOVICH FOKINA",
        scheduled_start_time=datetime.datetime(2026, 6, 27, 15, 0),
        status="SCHEDULED",
    ),
    FlashscoreMatch(
        flashscore_match_id="abc456",
        tournament="WTA - SINGLES: Eastbourne",
        player_a="TATJANA MARIA",
        player_b="MADISON KEYS",
        scheduled_start_time=datetime.datetime(2026, 6, 27, 15, 0),
        status="LIVE",
    ),
    FlashscoreMatch(
        flashscore_match_id="abc789",
        tournament="CHALLENGER MEN - SINGLES: Piracicaba",
        player_a="FELIX BALSHAW",
        player_b="SUMIT NAGAL",
        scheduled_start_time=datetime.datetime(2026, 6, 27, 15, 0),
        status="SCHEDULED",
    ),
    FlashscoreMatch(
        flashscore_match_id="abc000",
        tournament="CHALLENGER MEN - SINGLES: Piracicaba",
        player_a="MATHEUS PUCINELLI DE ALMEIDA",
        player_b="GONZALO VILLANUEVA",
        scheduled_start_time=datetime.datetime(2026, 6, 27, 15, 0),
        status="SCHEDULED",
    ),
    FlashscoreMatch(
        flashscore_match_id="abc111",
        tournament="ATP - SINGLES: Test",
        player_a="UNMATCHED PLAYER",
        player_b="UNKNOWN OPPONENT",
        scheduled_start_time=None,
        status="SCHEDULED",
    ),
    FlashscoreMatch(
        flashscore_match_id="abc222",
        tournament="CHALLENGER MEN - SINGLES: Piracicaba",
        player_a="THIAGO SEYBOTH WILD",
        player_b="JUAN MANUEL LA SERNA",
        scheduled_start_time=datetime.datetime(2026, 6, 27, 15, 0),
        status="SCHEDULED",
    ),
]

SAMPLE_ODDS_PIPE = (
    "1.259524159||OPEN|0||70950.54|7470889447|1782565881|"
    "38310228|ACTIVE|2.6|4.05|2.58|217.78|2.56|1310.57|"
    "9953368|ACTIVE|1.62|11.42|1.61|473.31|1.6|440.05"
)

SAMPLE_ODDS_PIPE_SUSPENDED = (
    "1.259524159||SUSPENDED|0||0|0|1782565881|"
    "38310228|SUSPENDED|0|0|0|0|"
    "9953368|SUSPENDED|0|0|0|0"
)


class TestFilterTennisMatches:
    def test_filters_by_type_id(self) -> None:
        result = filter_tennis_matches(SAMPLE_EVENTS)
        ids = {e["event_id"] for e in result}
        assert 12345678 not in ids

    def test_excludes_winner_markets(self) -> None:
        result = filter_tennis_matches(SAMPLE_EVENTS)
        ids = {e["event_id"] for e in result}
        assert 99999999 not in ids

    def test_includes_match_events(self) -> None:
        result = filter_tennis_matches(SAMPLE_EVENTS)
        ids = {e["event_id"] for e in result}
        assert 35763753 in ids
        assert 35763242 in ids

    def test_returns_list(self) -> None:
        result = filter_tennis_matches(SAMPLE_EVENTS)
        assert isinstance(result, list)
        assert len(result) >= 4


class TestNameMatching:
    def test_exact_match(self) -> None:
        assert _names_match("et quinn v davidovich fokina", "quinn", "davidovich fokina")

    def test_fuzzy_match_truncated(self) -> None:
        assert _names_match(
            "mat pucinelli de almeid v villanueva", "de almeida", "villanueva"
        )

    def test_no_match(self) -> None:
        assert not _names_match("balshaw v nagal", "quinn", "fokina")

    def test_word_matches_exact(self) -> None:
        assert _word_matches("quinn", "et quinn v fokina")

    def test_word_matches_prefix(self) -> None:
        assert _word_matches("almeida", "de almeid v villanueva")

    def test_word_matches_small_word(self) -> None:
        assert _word_matches("de", "pucinelli de almeid")

    def test_extract_last_name_simple(self) -> None:
        assert _extract_last_name("ETHAN QUINN") == "quinn"

    def test_extract_last_name_compound(self) -> None:
        assert _extract_last_name("MATHEUS PUCINELLI DE ALMEIDA") == "de almeida"

    def test_extract_last_name_single(self) -> None:
        assert _extract_last_name("NAGAL") == "nagal"


class TestMatchEventsToFlashscore:
    def test_returns_matched_pairs(self) -> None:
        tennis = filter_tennis_matches(SAMPLE_EVENTS)
        pairs = match_events_to_flashscore(tennis, FLASHSCORE_MATCHES)
        assert len(pairs) >= 4

    def test_each_flashscore_match_mapped_once(self) -> None:
        tennis = filter_tennis_matches(SAMPLE_EVENTS)
        pairs = match_events_to_flashscore(tennis, FLASHSCORE_MATCHES)
        fs_ids = [p[1].flashscore_match_id for p in pairs]
        assert len(fs_ids) == len(set(fs_ids))

    def test_each_event_used_once(self) -> None:
        tennis = filter_tennis_matches(SAMPLE_EVENTS)
        pairs = match_events_to_flashscore(tennis, FLASHSCORE_MATCHES)
        event_ids = [p[0]["event_id"] for p in pairs]
        assert len(event_ids) == len(set(event_ids))

    def test_unmatched_player_returns_no_pair(self) -> None:
        tennis = filter_tennis_matches(SAMPLE_EVENTS)
        pairs = match_events_to_flashscore(tennis, FLASHSCORE_MATCHES)
        unmatched = [
            p for p in pairs if p[1].player_a == "UNMATCHED PLAYER"
        ]
        assert len(unmatched) == 0

    def test_truncated_names_match(self) -> None:
        tennis = filter_tennis_matches(SAMPLE_EVENTS)
        pairs = match_events_to_flashscore(tennis, FLASHSCORE_MATCHES)
        matched_names = [p[0]["name"] for p in pairs]
        assert "Mat Pucinelli de Almeid v Villanueva" in matched_names
        assert "Th Seyboth Wild v J La Serna" in matched_names


class TestParseOdds:
    def test_parse_odds_pipe_returns_dict(self) -> None:
        result = parse_odds_pipe(SAMPLE_ODDS_PIPE)
        assert isinstance(result, dict)
        assert "38310228" in result
        assert "9953368" in result

    def test_odds_are_numeric(self) -> None:
        result = parse_odds_pipe(SAMPLE_ODDS_PIPE)
        assert isinstance(result["38310228"], float)
        assert result["38310228"] > 0
        assert isinstance(result["9953368"], float)
        assert result["9953368"] > 0

    def test_parse_odds_for_runners_returns_tuple(self) -> None:
        odds_a, odds_b = parse_odds_for_runners(
            SAMPLE_ODDS_PIPE, "38310228", "9953368"
        )
        assert odds_a is not None
        assert odds_b is not None
        assert odds_a > 0
        assert odds_b > 0

    def test_none_pipe_returns_nones(self) -> None:
        odds_a, odds_b = parse_odds_for_runners(None, "38310228", "9953368")
        assert odds_a is None
        assert odds_b is None

    def test_empty_pipe_returns_nones(self) -> None:
        odds_a, odds_b = parse_odds_for_runners("", "38310228", "9953368")
        assert odds_a is None
        assert odds_b is None

    def test_unknown_selection_ids_return_none(self) -> None:
        odds_a, odds_b = parse_odds_for_runners(
            SAMPLE_ODDS_PIPE, "99999999", "88888888"
        )
        assert odds_a is None
        assert odds_b is None

    def test_suspended_odds_handled(self) -> None:
        result = parse_odds_pipe(SAMPLE_ODDS_PIPE_SUSPENDED)
        assert "38310228" not in result
        assert "9953368" not in result


class TestBettingsiteMatch:
    def test_create_match_objects(self) -> None:
        match = BettingsiteMatch(
            market_id="1.12345",
            match_url="https://reddybook.green/sports/detail/123",
            player_a="PLAYER ONE",
            player_b="PLAYER TWO",
            odds_player_a=2.5,
            odds_player_b=1.8,
        )
        assert match.market_id == "1.12345"
        assert match.odds_player_a == 2.5
        assert match.odds_player_b == 1.8

    def test_none_odds_allowed(self) -> None:
        match = BettingsiteMatch(
            market_id="1.12345",
            match_url="https://reddybook.green/sports/detail/123",
            player_a="PLAYER ONE",
            player_b="PLAYER TWO",
            odds_player_a=None,
            odds_player_b=1.8,
        )
        assert match.odds_player_a is None
        assert match.odds_player_b == 1.8


class TestDiscoverMatchesIntegration:
    @patch("collector.betting_site.__init__.get_event_list")
    @patch("collector.betting_site.__init__.get_event_detail")
    @patch("collector.betting_site.__init__.get_market_odds")
    def test_returns_matches_with_odds(
        self, mock_odds, mock_detail, mock_events
    ) -> None:
        from collector.betting_site import discover_matches

        mock_events.return_value = SAMPLE_EVENTS
        mock_detail.side_effect = lambda eid: {
            35763753: {
                "match_odds": {
                    "market_id": "1.259524159",
                    "runners": [
                        {
                            "selection_id": "38310228",
                            "name": "Ethan Quinn",
                        },
                        {
                            "selection_id": "9953368",
                            "name": "Alejandro Davidovich Fokina",
                        },
                    ],
                }
            },
            35762982: {},
            35763242: {
                "match_odds": {
                    "market_id": "1.259521602",
                    "runners": [
                        {"selection_id": "11111111", "name": "Felix Balshaw"},
                        {"selection_id": "22222222", "name": "Sumit Nagal"},
                    ],
                }
            },
        }.get(eid, {})
        mock_odds.return_value = SAMPLE_ODDS_PIPE

        fs_matches = [
            FlashscoreMatch(
                flashscore_match_id="abc123",
                tournament="ATP Mallorca",
                player_a="ETHAN QUINN",
                player_b="ALEJANDRO DAVIDOVICH FOKINA",
                scheduled_start_time=None,
                status="SCHEDULED",
            ),
            FlashscoreMatch(
                flashscore_match_id="abc456",
                tournament="WTA Eastbourne",
                player_a="TATJANA MARIA",
                player_b="MADISON KEYS",
                scheduled_start_time=None,
                status="LIVE",
            ),
        ]

        matches = discover_matches(fs_matches)
        assert len(matches) >= 1
        for m in matches:
            assert m.market_id
            assert m.match_url
            assert m.player_a
            assert m.player_b
            assert m.odds_player_a is not None
            assert m.odds_player_b is not None

    def test_returns_empty_on_no_match(self) -> None:
        tennis = filter_tennis_matches(SAMPLE_EVENTS)
        unmatchable = [
            m for m in FLASHSCORE_MATCHES
            if m.player_a == "UNMATCHED PLAYER"
        ]
        pairs = match_events_to_flashscore(tennis, unmatchable)
        assert len(pairs) == 0

    def test_handles_empty_events(self) -> None:
        pairs = match_events_to_flashscore([], FLASHSCORE_MATCHES)
        assert pairs == []

    @patch("collector.betting_site.__init__.get_event_list")
    @patch("collector.betting_site.__init__.get_event_detail")
    @patch("collector.betting_site.__init__.get_market_odds")
    def test_no_duplicate_market_ids(
        self, mock_odds, mock_detail, mock_events
    ) -> None:
        from collector.betting_site import discover_matches

        mock_events.return_value = SAMPLE_EVENTS
        mock_detail.return_value = {
            "match_odds": {
                "market_id": "1.259524159",
                "runners": [
                    {"selection_id": "38310228", "name": "Player A"},
                    {"selection_id": "9953368", "name": "Player B"},
                ],
            }
        }
        mock_odds.return_value = SAMPLE_ODDS_PIPE

        matches = discover_matches(FLASHSCORE_MATCHES[:2])
        ids = [m.market_id for m in matches]
        assert len(ids) == len(set(ids))


class TestDatabaseSave:
    def test_save_creates_table_and_inserts(self) -> None:
        from collector.betting_site import save_matches_to_db
        from database import SessionLocal
        from models.bettingsite import BettingsiteFoundMatch

        test_matches = [
            BettingsiteMatch(
                market_id="1.test001",
                match_url="https://reddybook.green/sports/detail/123",
                player_a="PLAYER A",
                player_b="PLAYER B",
                odds_player_a=2.0,
                odds_player_b=1.5,
            ),
            BettingsiteMatch(
                market_id="1.test002",
                match_url="https://reddybook.green/sports/detail/456",
                player_a="PLAYER C",
                player_b="PLAYER D",
                odds_player_a=1.8,
                odds_player_b=2.2,
            ),
        ]

        saved = save_matches_to_db(test_matches)
        assert saved == 2

        with SessionLocal() as session:
            rows = session.query(BettingsiteFoundMatch).filter(
                BettingsiteFoundMatch.market_id.like("1.test%")
            ).all()
            assert len(rows) == 2
            for r in rows:
                assert isinstance(r.odds_player_a, float)
                assert isinstance(r.odds_player_b, float)

        with SessionLocal() as session:
            saved_again = save_matches_to_db(test_matches)
            assert saved_again == 0

        with SessionLocal() as session:
            session.query(BettingsiteFoundMatch).filter(
                BettingsiteFoundMatch.market_id.like("1.test%")
            ).delete()
            session.commit()
