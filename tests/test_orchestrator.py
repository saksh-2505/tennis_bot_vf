import logging
import time
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

# Force-register model tables with Base.metadata before create_all.
import models.bettingsite  # noqa: F401
import models.flashscore  # noqa: F401
import models.player  # noqa: F401
import models.tracked_match  # noqa: F401

from config import settings
from database import Base


# ============================================================================
# In-memory DB fixture (same pattern as test_match_registry.py)
# ============================================================================


@pytest.fixture
def db_session():
    """Fresh in-memory SQLite per test."""
    import database as db_mod

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess_local = sessionmaker(bind=engine)

    with patch.object(db_mod, "SessionLocal", sess_local):
        sess: Session = sess_local()
        yield sess
        sess.close()
        for table in reversed(Base.metadata.sorted_tables):
            with sess_local() as c:
                c.execute(table.delete())
                c.commit()


# ============================================================================
# Status-monitor helpers
# ============================================================================


def _insert_tracked_match(
    session: Session,
    flashscore_match_id: str = "abc",
    player1_name: str = "A",
    player2_name: str = "B",
    tournament: str = "Test",
    scheduled_start: datetime | None = None,
    status: str = "DISCOVERED",
    tracking_enabled: bool = True,
):
    from models.tracked_match import TrackedMatch

    tm = TrackedMatch(
        flashscore_match_id=flashscore_match_id,
        player1_name=player1_name,
        player2_name=player2_name,
        tournament=tournament,
        scheduled_start=scheduled_start,
        status=status,
        tracking_enabled=tracking_enabled,
    )
    session.add(tm)
    session.commit()


def _make_match(player_a: str = "A", player_b: str = "B"):
    from collector.flashscore.parser import Match

    return Match(
        flashscore_match_id="abc",
        tournament="ATP - SINGLES: Test",
        player_a=player_a,
        player_b=player_b,
        scheduled_start_time=datetime.now(timezone.utc),
        status="SCHEDULED",
    )


# ============================================================================
# TestUpdateMatchStatuses  (DB-only — transitions DISCOVERED → LIVE)
# ============================================================================


class TestUpdateMatchStatuses:
    def test_transitions_discovered_to_live_when_time_passed(self, db_session):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        _insert_tracked_match(db_session, scheduled_start=past, status="DISCOVERED")

        from orchestrator.service import update_match_statuses

        count = update_match_statuses()
        assert count == 1

        from models.tracked_match import TrackedMatch

        tm = db_session.query(TrackedMatch).first()
        assert tm.status == "LIVE"

    def test_does_not_transition_live_to_finished(self, db_session):
        past = datetime.now(timezone.utc) - timedelta(hours=5)
        _insert_tracked_match(db_session, scheduled_start=past, status="LIVE")

        from orchestrator.service import update_match_statuses

        count = update_match_statuses()
        assert count == 0

    def test_does_not_transition_if_time_not_passed(self, db_session):
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        _insert_tracked_match(db_session, scheduled_start=future, status="DISCOVERED")

        from orchestrator.service import update_match_statuses

        count = update_match_statuses()
        assert count == 0

    def test_handles_none_scheduled_start(self, db_session):
        _insert_tracked_match(
            db_session,
            flashscore_match_id="no_time",
            scheduled_start=None,
            status="DISCOVERED",
        )

        from orchestrator.service import update_match_statuses

        count = update_match_statuses()
        assert count == 0

    def test_handles_naive_datetime_as_utc(self, db_session):
        naive = datetime(2026, 6, 1, 12, 0)
        _insert_tracked_match(db_session, scheduled_start=naive, status="DISCOVERED")

        from orchestrator.service import update_match_statuses

        count = update_match_statuses()
        assert count == 1  # naive treated as UTC, so clearly in the past

    def test_skips_disabled_matches(self, db_session):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        _insert_tracked_match(
            db_session,
            flashscore_match_id="disabled",
            scheduled_start=past,
            status="DISCOVERED",
            tracking_enabled=False,
        )

        from orchestrator.service import update_match_statuses

        count = update_match_statuses()
        assert count == 0

    def test_multiple_matches_mixed(self, db_session):
        past = datetime.now(timezone.utc) - timedelta(hours=1)
        future = datetime.now(timezone.utc) + timedelta(hours=2)
        _insert_tracked_match(db_session, flashscore_match_id="m1", scheduled_start=past, status="DISCOVERED")
        _insert_tracked_match(db_session, flashscore_match_id="m2", scheduled_start=future, status="DISCOVERED")
        _insert_tracked_match(db_session, flashscore_match_id="m3", scheduled_start=past, status="LIVE")

        from orchestrator.service import update_match_statuses

        count = update_match_statuses()
        assert count == 1

        from models.tracked_match import TrackedMatch

        m1 = db_session.query(TrackedMatch).filter_by(flashscore_match_id="m1").first()
        assert m1.status == "LIVE"
        m2 = db_session.query(TrackedMatch).filter_by(flashscore_match_id="m2").first()
        assert m2.status == "DISCOVERED"
        m3 = db_session.query(TrackedMatch).filter_by(flashscore_match_id="m3").first()
        assert m3.status == "LIVE"


# ============================================================================
# TestRunDiscoveryCycle  (mocked collectors — no real network)
# ============================================================================


class TestRunDiscoveryCycle:
    @pytest.fixture(autouse=True)
    def _patch(self):
        with (
            patch("collector.flashscore.discover_matches") as fs_discover,
            patch("collector.flashscore.save_matches_to_db") as fs_save,
            patch("collector.betting_site.discover_matches") as bt_discover,
            patch("collector.betting_site.save_matches_to_db") as bt_save,
            patch("collector.tennis_explorer.update_players") as te_update,
            patch("registry.service.build_match_registry") as build_reg,
        ):
            fs_discover.return_value = []
            fs_save.return_value = 0
            bt_discover.return_value = []
            bt_save.return_value = 0
            te_update.return_value = {}
            build_reg.return_value = []
            yield {
                "fs_discover": fs_discover,
                "fs_save": fs_save,
                "bt_discover": bt_discover,
                "bt_save": bt_save,
                "te_update": te_update,
                "build_reg": build_reg,
            }

    def test_calls_all_modules_in_order(self, _patch):
        from orchestrator.service import run_discovery_cycle

        result = run_discovery_cycle()

        _patch["fs_discover"].assert_called_once()
        _patch["fs_save"].assert_called_once()
        _patch["bt_discover"].assert_called_once()
        _patch["bt_save"].assert_called_once()
        _patch["build_reg"].assert_called_once()
        assert result["flashscore_discovered"] == 0

    def test_flashscore_failure_still_continues(self, _patch, caplog):
        caplog.set_level(logging.ERROR)
        _patch["fs_discover"].side_effect = RuntimeError("down")

        from orchestrator.service import run_discovery_cycle

        result = run_discovery_cycle()
        assert result["flashscore_discovered"] == 0
        _patch["build_reg"].assert_called_once()

    def test_betting_site_failure_still_continues(self, _patch, caplog):
        caplog.set_level(logging.ERROR)
        _patch["bt_discover"].side_effect = RuntimeError("down")

        from orchestrator.service import run_discovery_cycle

        result = run_discovery_cycle()
        assert result["bettingsite_discovered"] == 0
        _patch["build_reg"].assert_called_once()

    def test_registry_failure_not_fatal(self, _patch, caplog):
        caplog.set_level(logging.ERROR)
        _patch["build_reg"].side_effect = RuntimeError("down")

        from orchestrator.service import run_discovery_cycle

        result = run_discovery_cycle()
        assert result["registry_count"] == 0

    def test_passes_flashscore_matches_to_betting_site(self, _patch):
        match = _make_match()
        _patch["fs_discover"].return_value = [match]

        from orchestrator.service import run_discovery_cycle

        run_discovery_cycle()
        _patch["bt_discover"].assert_called_once_with([match])

    def test_players_added_count(self, _patch):
        match = _make_match(player_a="PLAYER X", player_b="PLAYER Y")
        _patch["fs_discover"].return_value = [match]

        from orchestrator.service import run_discovery_cycle

        with patch("orchestrator.service._update_missing_players", return_value=(2, 0)):
            result = run_discovery_cycle()

        assert result["players_added"] == 2
        assert result["players_failed"] == 0


# ============================================================================
# TestRunPlatform  (mock status monitor + discovery inside the loop)
# ============================================================================


class TestRunPlatform:
    def test_runs_discovery_at_startup(self):
        with (
            patch("orchestrator.service._run_and_log_discovery") as disc,
            patch("orchestrator.service.update_match_statuses") as status,
            patch.object(time, "sleep", side_effect=StopIteration),
        ):
            status.return_value = 0

            with pytest.raises(StopIteration):
                from orchestrator.service import run_platform

                run_platform()

        disc.assert_called_once()

    def test_enters_status_monitor_loop(self):
        call_count = 0

        def _stop_after_one(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count >= 1:
                raise StopIteration

        with (
            patch("orchestrator.service._run_and_log_discovery"),
            patch("orchestrator.service.update_match_statuses") as status,
            patch.object(time, "sleep", side_effect=_stop_after_one),
        ):
            status.return_value = 0

            with pytest.raises(StopIteration):
                from orchestrator.service import run_platform

                # Temporarily speed up discovery interval so the loop
                # doesn't try to schedule it during this short test.
                with patch.object(settings, "DISCOVERY_ENABLED", False):
                    run_platform()

        status.assert_called_once()

    def test_discovery_scheduled_when_time_elapsed(self):
        """Discovery runs at startup AND on every tick when interval=0."""
        ticks = 0

        def _sleep_and_maybe_stop(_seconds):
            nonlocal ticks
            ticks += 1
            if ticks >= 3:
                raise SystemExit(0)

        with (
            patch("orchestrator.service._run_and_log_discovery") as disc,
            patch("orchestrator.service.update_match_statuses", return_value=0),
            patch("orchestrator.service._count_by_status", return_value=0),
            patch.object(time, "sleep", side_effect=_sleep_and_maybe_stop),
            patch.object(settings, "DISCOVERY_INTERVAL_SECONDS", 0),
            patch.object(settings, "STATUS_CHECK_INTERVAL_SECONDS", 0),
            patch.object(settings, "DISCOVERY_ENABLED", True),
        ):
            with pytest.raises(SystemExit):
                from orchestrator.service import run_platform

                run_platform()

        assert disc.call_count >= 3  # startup + at least 2 loop-triggered
