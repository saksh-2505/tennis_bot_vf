import logging
from datetime import datetime, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Force-register all models with Base.metadata *before* we call create_all.
import models.bettingsite  # noqa: F401
import models.flashscore  # noqa: F401
import models.player  # noqa: F401
import models.tracked_match  # noqa: F401

from database import Base


@pytest.fixture
def db_session():
    """Create a fresh in-memory SQLite database + session per test.

    Patches ``database.SessionLocal`` so that ``build_match_registry()``
    (which imports the module and reads ``SessionLocal`` at runtime) sees
    the same in-memory database.

    The patch is kept alive during *both* the test and the teardown
    cleanup so that the row-wipe uses the in-memory DB too.
    """
    import database as db_mod

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess_local = sessionmaker(bind=engine)

    with (
        patch.object(db_mod, "engine", engine),
        patch.object(db_mod, "SessionLocal", sess_local),
    ):
        sess: Session = sess_local()
        yield sess
        sess.close()
        # Wipe all rows so the next test starts clean.
        for table in reversed(Base.metadata.sorted_tables):
            with sess_local() as c:
                c.execute(table.delete())
                c.commit()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _insert_flashscore(
    session: Session,
    match_id: str = "abc123",
    player_a: str = "ZIZOU BERGS",
    player_b: str = "UGO HUMBERT",
    tournament: str = "ATP - SINGLES: Eastbourne (United Kingdom), grass",
    status: str = "SCHEDULED",
    scheduled_start: datetime | None = None,
):
    from models.flashscore import FlashscoreFoundMatch

    rec = FlashscoreFoundMatch(
        flashscore_match_id=match_id,
        tournament=tournament,
        player_a=player_a,
        player_b=player_b,
        scheduled_start_time=scheduled_start,
        status=status,
    )
    session.add(rec)
    session.commit()


def _insert_bettingsite(
    session: Session,
    market_id: str = "mkt001",
    player_a: str = "ZIZOU BERGS",
    player_b: str = "UGO HUMBERT",
    odds_a: float | None = 1.5,
    odds_b: float | None = 2.5,
):
    from models.bettingsite import BettingsiteFoundMatch

    rec = BettingsiteFoundMatch(
        market_id=market_id,
        match_url=f"https://example.com/{market_id}",
        player_a=player_a,
        player_b=player_b,
        odds_player_a=odds_a,
        odds_player_b=odds_b,
    )
    session.add(rec)
    session.commit()


def _insert_player(
    session: Session,
    full_name: str,
):
    from models.player import Player

    rec = Player(full_name=full_name)
    session.add(rec)
    session.commit()


# ===================================================================
# Tests
# ===================================================================


class TestBuildMatchRegistry:
    def test_creates_tracked_match(self, db_session):
        _insert_flashscore(db_session)
        _insert_bettingsite(db_session)

        from registry.service import build_match_registry

        results = build_match_registry()

        assert len(results) == 1
        tm = results[0]
        assert tm.flashscore_match_id == "abc123"
        assert tm.betting_market_id == "mkt001"
        assert tm.player1_name == "ZIZOU BERGS"
        assert tm.player2_name == "UGO HUMBERT"
        assert tm.tournament == "ATP - SINGLES: Eastbourne (United Kingdom), grass"
        assert tm.status == "SCHEDULED"

    def test_duplicate_execution_does_not_create_duplicates(self, db_session):
        _insert_flashscore(db_session, match_id="abc")
        _insert_bettingsite(db_session, market_id="mkt1")

        from registry.service import build_match_registry

        results1 = build_match_registry()
        assert len(results1) == 1

        results2 = build_match_registry()
        assert len(results2) == 1
        assert results2[0].id == results1[0].id

    def test_resolves_player_ids(self, db_session):
        _insert_player(db_session, full_name="ZIZOU BERGS")
        _insert_player(db_session, full_name="UGO HUMBERT")
        _insert_flashscore(db_session)
        _insert_bettingsite(db_session)

        from registry.service import build_match_registry

        results = build_match_registry()
        tm = results[0]
        assert tm.player1_id is not None
        assert tm.player2_id is not None

    def test_references_one_each(self, db_session):
        _insert_flashscore(db_session, match_id="abc")
        _insert_bettingsite(db_session, market_id="mkt1")

        from registry.service import build_match_registry

        results = build_match_registry()
        assert len(results) == 1
        tm = results[0]
        assert tm.flashscore_match_id == "abc"
        assert tm.betting_market_id == "mkt1"

    def test_missing_betting_market_logged_and_skipped(self, db_session, caplog):
        caplog.set_level(logging.WARNING)
        _insert_flashscore(db_session, match_id="abc")

        from registry.service import build_match_registry

        results = build_match_registry()
        assert len(results) == 0
        assert "no matching betting market" in caplog.text

    def test_missing_player_logged(self, db_session, caplog):
        caplog.set_level(logging.WARNING)
        _insert_flashscore(db_session, match_id="abc")
        _insert_bettingsite(db_session, market_id="mkt1")

        from registry.service import build_match_registry

        results = build_match_registry()
        assert len(results) == 1
        assert "not found in players table" in caplog.text

    def test_skip_when_duplicate_betting_markets(self, db_session, caplog):
        caplog.set_level(logging.ERROR)
        _insert_flashscore(db_session, match_id="abc")
        _insert_bettingsite(db_session, market_id="mkt1")
        _insert_bettingsite(db_session, market_id="mkt2")

        from registry.service import build_match_registry

        results = build_match_registry()
        assert len(results) == 0
        assert "2 matching betting markets" in caplog.text

    def test_reversed_player_order_still_matches(self, db_session):
        _insert_flashscore(db_session, match_id="abc", player_a="ZIZOU BERGS", player_b="UGO HUMBERT")
        _insert_bettingsite(db_session, market_id="mkt1", player_a="UGO HUMBERT", player_b="ZIZOU BERGS")

        from registry.service import build_match_registry

        results = build_match_registry()
        assert len(results) == 1
        tm = results[0]
        assert tm.player1_name == "ZIZOU BERGS"

    def test_multiple_flashscore_matches(self, db_session):
        _insert_flashscore(db_session, match_id="m1", player_a="PLAYER A", player_b="PLAYER B")
        _insert_flashscore(db_session, match_id="m2", player_a="PLAYER C", player_b="PLAYER D")
        _insert_bettingsite(db_session, market_id="bt1", player_a="PLAYER A", player_b="PLAYER B")
        _insert_bettingsite(db_session, market_id="bt2", player_a="PLAYER C", player_b="PLAYER D")

        from registry.service import build_match_registry

        results = build_match_registry()
        assert len(results) == 2

    def test_betting_market_with_no_flashscore_match_logged(self, db_session, caplog):
        caplog.set_level(logging.WARNING)
        _insert_bettingsite(db_session, market_id="orphan", player_a="NOBODY", player_b="NOWHERE")

        from registry.service import build_match_registry

        build_match_registry()
        assert "no matching Flashscore match" in caplog.text

    def test_updates_existing_tracked_match_on_rerun(self, db_session):
        _insert_flashscore(db_session, match_id="abc", tournament="ATP - SINGLES: Wimbledon", player_a="A", player_b="B")
        _insert_bettingsite(db_session, market_id="mkt1", player_a="A", player_b="B")

        from registry.service import build_match_registry

        r1 = build_match_registry()
        assert r1[0].tournament == "ATP - SINGLES: Wimbledon"

        from models.flashscore import FlashscoreFoundMatch

        fs = db_session.query(FlashscoreFoundMatch).first()
        fs.tournament = "ATP - SINGLES: US Open"
        db_session.commit()

        r2 = build_match_registry()
        assert r2[0].tournament == "ATP - SINGLES: US Open"
        assert r2[0].id == r1[0].id
