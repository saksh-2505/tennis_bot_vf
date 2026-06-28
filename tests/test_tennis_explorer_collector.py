from datetime import datetime, timezone
from unittest.mock import Mock, patch

import pytest

from collector.tennis_explorer.parser import (
    PlayerData,
    _extract_full_name,
    _parse_career_wl,
    _parse_profile_divs,
    _parse_surface_row,
    _parse_wl_table,
    _split_name,
    parse_player_profile,
)


SAMPLE_HTML = """<!DOCTYPE html>
<html>
<head><title>Zizou Bergs - Tennis Explorer</title></head>
<body>
<h1>Bergs Zizou - profile</h1>
<div>
    <div>
        <div><h3>Bergs Zizou</h3></div>
        <div>Country: Belgium</div>
        <div>Height / Weight: 185 cm / 83 kg</div>
        <div>Age: 27 (3. 6. 1999)</div>
        <div>Current/Highest rank - singles: 48. / 38.</div>
        <div>Current/Highest rank - doubles: 410. / 265.</div>
        <div>Sex: man</div>
        <div>Plays: right</div>
    </div>
</div>
<h2>Player's record</h2>
<div>
<table class="result balance">
<thead>
<tr class="head">
<th class="year">Year</th><th>Summary</th><th>Clay</th><th>Hard</th>
<th>Indoors</th><th>Grass</th><th>Not set</th>
</tr>
</thead>
<tbody>
<tr class="first">
<td>Summary:</td><td>372/239</td><td>144/92</td><td>103/68</td>
<td>87/55</td><td>28/16</td><td>10/8</td>
</tr>
<tr>
<td>2026</td><td>17/16</td><td>7/7</td><td>6/6</td>
<td>0/1</td><td>4/2</td><td>-</td>
</tr>
</tbody>
</table>
</div>
</body>
</html>"""

WTA_HTML = """<!DOCTYPE html>
<html>
<head><title>Karolina Muchova - Tennis Explorer</title></head>
<body>
<h1>Muchova Karolina - profile</h1>
<div>
    <div>
        <h3>Muchova Karolina</h3>
        <div>Country: Czech Republic</div>
        <div>Height / Weight: 180 cm / 80 kg</div>
        <div>Age: 29 (21. 8. 1996)</div>
        <div>Current/Highest rank - singles: 11. / 8.</div>
        <div>Sex: woman</div>
        <div>Plays: right</div>
    </div>
</div>
<h2>Player's record</h2>
<div>
<table class="result balance">
<thead>
<tr class="head">
<th class="year">Year</th><th>Summary</th><th>Clay</th><th>Hard</th>
<th>Indoors</th><th>Grass</th><th>Not set</th>
</tr>
</thead>
<tbody>
<tr class="first">
<td>Summary:</td><td>377/182</td><td>135/67</td><td>162/68</td>
<td>53/30</td><td>25/16</td><td>2/1</td>
</tr>
</tbody>
</table>
</div>
</body>
</html>"""

NO_MATCH_HTML = """<!DOCTYPE html>
<html>
<head><title>TennisExplorer.com</title></head>
<body>
<h1>Player's profile</h1>
<p>Player does not exist.</p>
</body>
</html>"""

NO_TABLE_HTML = """<!DOCTYPE html>
<html>
<head><title>New Player - Tennis Explorer</title></head>
<body>
<h1>New Player - profile</h1>
<div>
    <div>Country: Unknown</div>
    <div>Height / Weight: 180 cm / 75 kg</div>
    <div>Age: 25 (1. 1. 2001)</div>
    <div>Sex: man</div>
    <div>Plays: left</div>
</div>
</body>
</html>"""


class TestExtractFullName:
    def test_extracts_from_h1(self) -> None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(SAMPLE_HTML, "html.parser")
        assert _extract_full_name(soup) == "BERGS ZIZOU"

    def test_extracts_wta_name(self) -> None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(WTA_HTML, "html.parser")
        assert _extract_full_name(soup) == "MUCHOVA KAROLINA"

    def test_returns_none_for_no_match(self) -> None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(NO_MATCH_HTML, "html.parser")
        assert _extract_full_name(soup) is None

    def test_title_fallback(self) -> None:
        html_no_h1 = """<html><head><title>Player Name - Tennis Explorer</title></head><body></body></html>"""
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(html_no_h1, "html.parser")
        assert _extract_full_name(soup) == "PLAYER NAME"


class TestSplitName:
    def test_splits_last_first_format(self) -> None:
        first, last = _split_name("BERGS ZIZOU")
        assert first == "ZIZOU"
        assert last == "BERGS"

    def test_splits_wta_last_first(self) -> None:
        first, last = _split_name("MUCHOVA KAROLINA")
        assert first == "KAROLINA"
        assert last == "MUCHOVA"

    def test_handles_single_word(self) -> None:
        first, last = _split_name("MONFILS")
        assert first is None
        assert last == "MONFILS"

    def test_handles_three_words(self) -> None:
        first, last = _split_name("DAVIDOVICH FOKINA ALEJANDRO")
        assert first == "FOKINA"
        assert last == "DAVIDOVICH"


class TestParseProfileDivs:
    def test_extracts_all_profile_fields(self) -> None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(SAMPLE_HTML, "html.parser")
        data = PlayerData(full_name="BERGS ZIZOU")
        _parse_profile_divs(soup, data)

        assert data.nationality == "Belgium"
        assert data.height == 185
        assert data.weight == 83
        assert data.age == 27
        assert data.date_of_birth == "1999-06-03"
        assert data.current_rank == 48
        assert data.career_high_rank == 38
        assert data.gender == "man"
        assert data.atp_or_wta == "ATP"
        assert data.plays == "right"

    def test_extracts_wta_fields(self) -> None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(WTA_HTML, "html.parser")
        data = PlayerData(full_name="MUCHOVA KAROLINA")
        _parse_profile_divs(soup, data)

        assert data.nationality == "Czech Republic"
        assert data.gender == "woman"
        assert data.atp_or_wta == "WTA"
        assert data.current_rank == 11
        assert data.career_high_rank == 8
        assert data.date_of_birth == "1996-08-21"

    def test_handles_no_h1(self) -> None:
        from bs4 import BeautifulSoup
        html = "<html><body><div>Country: France</div></body></html>"
        soup = BeautifulSoup(html, "html.parser")
        data = PlayerData(full_name="TEST")
        _parse_profile_divs(soup, data)
        assert data.nationality == "France"


class TestParseWLTable:
    def test_parses_career_stats(self) -> None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(SAMPLE_HTML, "html.parser")
        data = PlayerData(full_name="BERGS ZIZOU")
        _parse_wl_table(soup, data)

        assert data.total_wins == 372
        assert data.total_losses == 239
        assert data.total_matches == 611
        assert data.career_win_percentage == 60.9

    def test_parses_surface_stats(self) -> None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(SAMPLE_HTML, "html.parser")
        data = PlayerData(full_name="BERGS ZIZOU")
        _parse_wl_table(soup, data)

        assert data.clay_wins == 144
        assert data.clay_losses == 92
        assert data.clay_matches == 236
        assert data.clay_win_percentage == 61.0

        assert data.hard_wins == 103
        assert data.hard_losses == 68
        assert data.hard_matches == 171

        assert data.indoor_wins == 87
        assert data.indoor_losses == 55

        assert data.grass_wins == 28
        assert data.grass_losses == 16

    def test_no_table_does_nothing(self) -> None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(NO_TABLE_HTML, "html.parser")
        data = PlayerData(full_name="NEW PLAYER")
        _parse_wl_table(soup, data)

        assert data.total_wins is None
        assert data.total_losses is None

    def test_parses_wta_career(self) -> None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(WTA_HTML, "html.parser")
        data = PlayerData(full_name="MUCHOVA KAROLINA")
        _parse_wl_table(soup, data)

        assert data.total_wins == 377
        assert data.total_losses == 182
        assert data.total_matches == 559
        assert data.career_win_percentage == 67.4

    def test_parses_wta_surface(self) -> None:
        from bs4 import BeautifulSoup
        soup = BeautifulSoup(WTA_HTML, "html.parser")
        data = PlayerData(full_name="MUCHOVA KAROLINA")
        _parse_wl_table(soup, data)

        assert data.hard_wins == 162
        assert data.hard_losses == 68
        assert data.clay_wins == 135
        assert data.clay_losses == 67
        assert data.grass_wins == 25
        assert data.grass_losses == 16
        assert data.indoor_wins == 53
        assert data.indoor_losses == 30


class TestParseCareerWL:
    def test_parses_wl_slash_format(self) -> None:
        data = PlayerData(full_name="TEST")
        _parse_career_wl(["372/239"], data)

        assert data.total_wins == 372
        assert data.total_losses == 239
        assert data.total_matches == 611
        assert data.career_win_percentage == 60.9

    def test_handles_empty(self) -> None:
        data = PlayerData(full_name="TEST")
        _parse_career_wl([], data)
        assert data.total_wins is None

    def test_handles_invalid(self) -> None:
        data = PlayerData(full_name="TEST")
        _parse_career_wl(["abc/def"], data)
        assert data.total_wins is None


class TestParseSurfaceRow:
    def test_parses_valid(self) -> None:
        data = PlayerData(full_name="TEST")
        _parse_surface_row("144/92", data, "clay")
        assert data.clay_wins == 144
        assert data.clay_losses == 92
        assert data.clay_matches == 236
        assert data.clay_win_percentage == 61.0

    def test_skips_dash(self) -> None:
        data = PlayerData(full_name="TEST")
        _parse_surface_row("-", data, "hard")
        assert data.hard_wins is None

    def test_skips_empty(self) -> None:
        data = PlayerData(full_name="TEST")
        _parse_surface_row("", data, "grass")
        assert data.grass_wins is None

    def test_handles_zero_matches(self) -> None:
        data = PlayerData(full_name="TEST")
        _parse_surface_row("0/0", data, "indoor")
        assert data.indoor_wins == 0
        assert data.indoor_losses == 0
        assert data.indoor_matches == 0
        assert data.indoor_win_percentage is None


class TestParsePlayerProfile:
    def test_full_profile_atp(self) -> None:
        result = parse_player_profile(SAMPLE_HTML, "https://example.com/bergs/")
        assert result is not None
        assert result.full_name == "BERGS ZIZOU"
        assert result.first_name == "ZIZOU"
        assert result.last_name == "BERGS"
        assert result.nationality == "Belgium"
        assert result.gender == "man"
        assert result.atp_or_wta == "ATP"
        assert result.current_rank == 48
        assert result.career_high_rank == 38
        assert result.total_wins == 372
        assert result.clay_win_percentage == 61.0

    def test_full_profile_wta(self) -> None:
        result = parse_player_profile(WTA_HTML, "https://example.com/muchova/")
        assert result is not None
        assert result.full_name == "MUCHOVA KAROLINA"
        assert result.gender == "woman"
        assert result.atp_or_wta == "WTA"
        assert result.current_rank == 11
        assert result.total_wins == 377
        assert result.hard_win_percentage == 70.4

    def test_returns_none_on_no_match(self) -> None:
        result = parse_player_profile(NO_MATCH_HTML, "https://example.com/none/")
        assert result is None

    def test_no_table_no_error(self) -> None:
        result = parse_player_profile(NO_TABLE_HTML, "https://example.com/new/")
        assert result is not None
        assert result.full_name == "NEW PLAYER"
        assert result.plays == "left"
        assert result.total_wins is None


class TestDiscoverMatchesIntegration:
    @patch("collector.tennis_explorer.search_player")
    @patch("collector.tennis_explorer.fetch_player_profile")
    def test_update_player_inserts(self, mock_fetch: Mock, mock_search: Mock) -> None:
        mock_search.return_value = {
            "url": "bergs",
            "name": "Bergs, Zizou (BEL)",
            "sex": "man",
        }
        mock_fetch.return_value = SAMPLE_HTML

        from collector.tennis_explorer import update_player

        result = update_player("Zizou Bergs")
        assert result is True

        from database import SessionLocal
        from models.player import Player

        with SessionLocal() as session:
            player = session.query(Player).filter_by(full_name="BERGS ZIZOU").first()
            assert player is not None
            assert player.nationality == "Belgium"
            assert player.atp_or_wta == "ATP"
            assert player.total_wins == 372

    @patch("collector.tennis_explorer.search_player")
    def test_update_player_not_found(self, mock_search: Mock) -> None:
        mock_search.return_value = None

        from collector.tennis_explorer import update_player

        result = update_player("Nonexistent Player")
        assert result is False

    @patch("collector.tennis_explorer.search_player")
    @patch("collector.tennis_explorer.fetch_player_profile")
    def test_update_player_no_duplicates(
        self, mock_fetch: Mock, mock_search: Mock
    ) -> None:
        mock_search.return_value = {
            "url": "bergs",
            "name": "Bergs, Zizou (BEL)",
            "sex": "man",
        }
        mock_fetch.return_value = SAMPLE_HTML

        from collector.tennis_explorer import update_player
        from database import SessionLocal
        from models.player import Player

        update_player("Zizou Bergs")
        update_player("Zizou Bergs")

        with SessionLocal() as session:
            count = session.query(Player).filter_by(full_name="BERGS ZIZOU").count()
            assert count == 1

    @patch("collector.tennis_explorer.search_player")
    @patch("collector.tennis_explorer.fetch_player_profile")
    def test_update_player_updates_existing(
        self, mock_fetch: Mock, mock_search: Mock
    ) -> None:
        mock_search.return_value = {
            "url": "bergs",
            "name": "Bergs, Zizou (BEL)",
            "sex": "man",
        }
        mock_fetch.return_value = SAMPLE_HTML

        from collector.tennis_explorer import update_player
        from database import SessionLocal
        from models.player import Player

        update_player("Zizou Bergs")

        updated_html = SAMPLE_HTML.replace(
            "Current/Highest rank - singles: 48. / 38.",
            "Current/Highest rank - singles: 30. / 30.",
        )
        updated_html = updated_html.replace(
            "<td>372/239</td>", "<td>400/200</td>"
        )
        mock_fetch.return_value = updated_html

        update_player("Zizou Bergs")

        with SessionLocal() as session:
            player = session.query(Player).filter_by(full_name="BERGS ZIZOU").first()
            assert player is not None
            assert player.current_rank == 30
            assert player.total_wins == 400
            assert player.total_losses == 200
            count = session.query(Player).filter_by(full_name="BERGS ZIZOU").count()
            assert count == 1

    @patch("collector.tennis_explorer.search_player")
    @patch("collector.tennis_explorer.fetch_player_profile")
    def test_update_players_batch(
        self, mock_fetch: Mock, mock_search: Mock
    ) -> None:
        mock_search.side_effect = [
            {"url": "bergs", "name": "Bergs, Zizou (BEL)", "sex": "man"},
            None,
        ]

        def fetch_side_effect(url_path: str) -> str:
            if url_path == "bergs":
                return SAMPLE_HTML
            return NO_MATCH_HTML

        mock_fetch.side_effect = fetch_side_effect

        from collector.tennis_explorer import update_players

        results = update_players(["Zizou Bergs", "Nonexistent"])
        assert results["Zizou Bergs"] is True
        assert results["Nonexistent"] is False

    @patch("collector.tennis_explorer.search_player")
    @patch("collector.tennis_explorer.fetch_player_profile")
    def test_update_player_exception_handled(
        self, mock_fetch: Mock, mock_search: Mock
    ) -> None:
        mock_search.side_effect = Exception("Network error")

        from collector.tennis_explorer import update_players

        results = update_players(["Failing Player"])
        assert results["Failing Player"] is False


class TestPlayerModel:
    def test_unique_full_name_constraint(self) -> None:
        from models.player import Player
        from database import SessionLocal, engine
        import uuid

        Player.metadata.create_all(bind=engine)

        unique_name = f"UNIQUE PLAYER {uuid.uuid4().hex[:8]}"
        p1 = Player(full_name=unique_name, source="Tennis Explorer")
        p2 = Player(full_name=unique_name, source="Tennis Explorer")

        with SessionLocal() as session:
            session.add(p1)
            session.commit()

            session.add(p2)
            with pytest.raises(Exception):
                session.commit()
            session.rollback()

    def test_nullable_fields_default_none(self) -> None:
        from models.player import Player

        p = Player(full_name="MINIMAL PLAYER")
        assert p.first_name is None
        assert p.ranking_points is None
        assert p.first_serve_percentage is None
        assert p.tie_break_record is None
