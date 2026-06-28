import hashlib
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

import models.completed_match  # noqa: F401
import models.live_odds  # noqa: F401
import models.live_score  # noqa: F401
import models.player  # noqa: F401
import models.tracked_match  # noqa: F401

from database import Base


@pytest.fixture
def db_session():
    import database as db_mod
    from sqlalchemy import create_engine
    from sqlalchemy.orm import Session, sessionmaker

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


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_tracked_match(
    db_session,
    flashscore_match_id="m1",
    betting_market_id="mkt1",
    player1_name="PLAYER_A",
    player2_name="PLAYER_B",
    status="FINISHED",
    scheduled_start=None,
    player1_id=101,
    player2_id=102,
    match_duration_min=135,
):
    from models.tracked_match import TrackedMatch

    if scheduled_start is None:
        scheduled_start = datetime.now(timezone.utc) - timedelta(hours=2)
    finish = datetime.now(timezone.utc)
    tm = TrackedMatch(
        flashscore_match_id=flashscore_match_id,
        betting_market_id=betting_market_id,
        player1_id=player1_id,
        player2_id=player2_id,
        player1_name=player1_name,
        player2_name=player2_name,
        tournament="Test Tournament",
        round="Final",
        surface="Hard",
        scheduled_start=scheduled_start,
        actual_finish=finish,
        match_duration_min=match_duration_min,
        status=status,
        tracking_enabled=True,
        created_at=datetime.now(timezone.utc),
        updated_at=datetime.now(timezone.utc),
    )
    db_session.add(tm)
    db_session.commit()
    return tm


def _insert_score_tick(
    db_session,
    tracked_match_id,
    set_score_a=2,
    set_score_b=1,
    timestamp=None,
    content_hash=None,
):
    from models.live_score import LiveScore

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    if content_hash is None:
        content_hash = hashlib.sha256(
            f"{set_score_a}-{set_score_b}-{timestamp}".encode()
        ).hexdigest()
    ls = LiveScore(
        tracked_match_id=tracked_match_id,
        flashscore_match_id="m1",
        timestamp=timestamp,
        set_score_a=set_score_a,
        set_score_b=set_score_b,
        game_score_a=6,
        game_score_b=4,
        content_hash=content_hash,
    )
    db_session.add(ls)
    db_session.commit()


def _insert_odds_tick(
    db_session,
    tracked_match_id,
    back_odds_a=1.5,
    back_odds_b=2.5,
    timestamp=None,
    content_hash=None,
):
    from models.live_odds import LiveOdds

    if timestamp is None:
        timestamp = datetime.now(timezone.utc)
    if content_hash is None:
        content_hash = hashlib.sha256(
            f"{back_odds_a}-{back_odds_b}-{timestamp}".encode()
        ).hexdigest()
    lo = LiveOdds(
        tracked_match_id=tracked_match_id,
        betting_market_id="mkt1",
        timestamp=timestamp,
        back_odds_a=back_odds_a,
        back_odds_b=back_odds_b,
        content_hash=content_hash,
    )
    db_session.add(lo)
    db_session.commit()


# ============================================================================
# Core finalization
# ============================================================================


class TestFinalizeMatch:
    def test_finalizes_match(self, db_session):
        tm = _make_tracked_match(db_session)
        _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1)
        _insert_odds_tick(db_session, tm.id)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)

        assert cm.tracked_match_id == tm.id
        assert cm.flashscore_match_id == "m1"
        assert cm.player1_id == 101
        assert cm.player2_id == 102
        assert cm.validation_passed is True
        assert cm.exported is False

    def test_idempotent_raises_on_second_call(self, db_session):
        tm = _make_tracked_match(db_session)
        _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1)
        _insert_odds_tick(db_session, tm.id)

        from finalizer.service import AlreadyFinalized, finalize_match

        finalize_match(db_session, tm.id)
        with pytest.raises(AlreadyFinalized):
            finalize_match(db_session, tm.id)

    def test_not_finished_raises(self, db_session):
        tm = _make_tracked_match(db_session, status="LIVE")

        from finalizer.service import NotFinished, finalize_match

        with pytest.raises(NotFinished):
            finalize_match(db_session, tm.id)

    def test_nonexistent_match_raises(self, db_session):
        from finalizer.service import finalize_match

        with pytest.raises(ValueError, match="not found"):
            finalize_match(db_session, 999)


# ============================================================================
# Tick counts
# ============================================================================


class TestTickCounts:
    def test_score_tick_count_correct(self, db_session):
        tm = _make_tracked_match(db_session)
        base = datetime.now(timezone.utc)
        for i in range(5):
            ts = base + timedelta(seconds=i * 10)
            h = hashlib.sha256(f"score-{i}".encode()).hexdigest()
            _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1, timestamp=ts, content_hash=h)
        _insert_odds_tick(db_session, tm.id)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.score_tick_count == 5

    def test_odds_tick_count_correct(self, db_session):
        tm = _make_tracked_match(db_session)
        _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1)
        base = datetime.now(timezone.utc)
        for i in range(3):
            ts = base + timedelta(seconds=i * 2)
            h = hashlib.sha256(f"odds-{i}".encode()).hexdigest()
            _insert_odds_tick(db_session, tm.id, timestamp=ts, content_hash=h)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.odds_tick_count == 3

    def test_duration_correct(self, db_session):
        tm = _make_tracked_match(db_session, match_duration_min=120)
        _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1)
        _insert_odds_tick(db_session, tm.id)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.duration_minutes == 120


# ============================================================================
# Winner determination
# ============================================================================


class TestWinner:
    def test_winner_player1(self, db_session):
        tm = _make_tracked_match(db_session, player1_id=101, player2_id=102)
        _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=0)
        _insert_odds_tick(db_session, tm.id)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.winner_player_id == 101
        assert cm.final_set_score == "2-0"
        assert cm.total_sets == 2

    def test_winner_player2(self, db_session):
        tm = _make_tracked_match(db_session, player1_id=101, player2_id=102)
        _insert_score_tick(db_session, tm.id, set_score_a=1, set_score_b=3)
        _insert_odds_tick(db_session, tm.id)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.winner_player_id == 102
        assert cm.final_set_score == "1-3"
        assert cm.total_sets == 4

    def test_no_winner_when_sets_tied(self, db_session):
        tm = _make_tracked_match(db_session)
        _insert_score_tick(db_session, tm.id, set_score_a=1, set_score_b=1)
        _insert_odds_tick(db_session, tm.id)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.winner_player_id is None
        assert cm.validation_passed is False


# ============================================================================
# Validation
# ============================================================================


class TestValidation:
    def test_no_score_ticks_fails_validation(self, db_session):
        tm = _make_tracked_match(db_session)
        _insert_odds_tick(db_session, tm.id)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.score_tick_count == 0
        assert cm.has_complete_score_data is False
        assert cm.validation_passed is False

    def test_no_odds_ticks_sets_flag(self, db_session):
        tm = _make_tracked_match(db_session)
        _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.odds_tick_count == 0
        assert cm.has_complete_odds_data is False

    def test_zero_duration_fails_validation(self, db_session):
        tm = _make_tracked_match(
            db_session, match_duration_min=0
        )
        _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1)
        _insert_odds_tick(db_session, tm.id)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.validation_passed is False

    def test_validation_passed_with_good_data(self, db_session):
        tm = _make_tracked_match(db_session)
        base = datetime.now(timezone.utc)
        for i in range(12):
            ts = base + timedelta(seconds=i * 10)
            h = hashlib.sha256(f"vs-{i}".encode()).hexdigest()
            _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1, timestamp=ts, content_hash=h)
        base2 = datetime.now(timezone.utc)
        for i in range(60):
            ts = base2 + timedelta(seconds=i * 2)
            h = hashlib.sha256(f"vo-{i}".encode()).hexdigest()
            _insert_odds_tick(db_session, tm.id, timestamp=ts, content_hash=h)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.validation_passed is True
        assert cm.ready_for_backtesting is True


# ============================================================================
# Timestamp gaps
# ============================================================================


class TestGaps:
    def test_largest_score_gap_correct(self, db_session):
        tm = _make_tracked_match(db_session)
        base = datetime.now(timezone.utc)
        _insert_score_tick(db_session, tm.id, set_score_a=0, set_score_b=0, timestamp=base, content_hash="h1")
        _insert_score_tick(db_session, tm.id, set_score_a=1, set_score_b=1, timestamp=base + timedelta(seconds=5), content_hash="h2")
        _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1, timestamp=base + timedelta(seconds=120), content_hash="h3")
        _insert_odds_tick(db_session, tm.id)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.largest_score_gap_seconds == 115.0

    def test_largest_odds_gap_correct(self, db_session):
        tm = _make_tracked_match(db_session)
        _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1)
        base = datetime.now(timezone.utc)
        _insert_odds_tick(db_session, tm.id, timestamp=base, content_hash="h1")
        _insert_odds_tick(db_session, tm.id, timestamp=base + timedelta(seconds=3), content_hash="h2")
        _insert_odds_tick(db_session, tm.id, timestamp=base + timedelta(seconds=90), content_hash="h3")

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.largest_odds_gap_seconds == 87.0

    def test_duplicate_ticks_counted(self, db_session):
        tm = _make_tracked_match(db_session)
        base = datetime.now(timezone.utc)
        common_hash = hashlib.sha256(b"same").hexdigest()
        _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1, timestamp=base, content_hash=common_hash)
        _insert_score_tick(db_session, tm.id, set_score_a=2, set_score_b=1, timestamp=base + timedelta(seconds=10), content_hash=common_hash)
        _insert_odds_tick(db_session, tm.id)

        from finalizer.service import finalize_match

        cm = finalize_match(db_session, tm.id)
        assert cm.duplicate_score_ticks == 1


# ============================================================================
# run_match_finalizer
# ============================================================================


class TestRunMatchFinalizer:
    def test_scans_and_finalizes_multiple_matches(self, db_session):
        tm1 = _make_tracked_match(db_session, flashscore_match_id="m1")
        _insert_score_tick(db_session, tm1.id, set_score_a=2, set_score_b=0, content_hash="h1")
        _insert_odds_tick(db_session, tm1.id, content_hash="h2")

        tm2 = _make_tracked_match(db_session, flashscore_match_id="m2", betting_market_id="mkt2")
        _insert_score_tick(db_session, tm2.id, set_score_a=1, set_score_b=2, content_hash="h3")
        _insert_odds_tick(db_session, tm2.id, content_hash="h4")

        from finalizer.service import run_match_finalizer

        results = run_match_finalizer(db_session)
        assert len(results) == 2

        # second call — no new matches
        results2 = run_match_finalizer(db_session)
        assert len(results2) == 0

    def test_skips_not_finished_and_already_finalized(self, db_session):
        tm_finished = _make_tracked_match(db_session, flashscore_match_id="m1")
        _insert_score_tick(db_session, tm_finished.id, set_score_a=2, set_score_b=0, content_hash="h1")
        _insert_odds_tick(db_session, tm_finished.id, content_hash="h2")

        tm_live = _make_tracked_match(
            db_session, flashscore_match_id="m2", betting_market_id="mkt2", status="LIVE"
        )

        from finalizer.service import run_match_finalizer

        results = run_match_finalizer(db_session)
        assert len(results) == 1
        assert results[0].tracked_match_id == tm_finished.id
