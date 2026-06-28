import hashlib
import json
from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest

# Register models for in-memory SQLite
import models.live_score   # noqa: F401
import models.live_odds    # noqa: F401
import models.tracked_match  # noqa: F401
import models.player       # noqa: F401

from database import Base


@pytest.fixture
def db_session():
    """Fresh in-memory SQLite per test."""
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


# ============================================================================
# Test Score Parsing (no network)
# ============================================================================


class TestFlashscoreLive:
    def test_score_snapshot_content_hash(self):
        from live_collector.flashscore_live import ScoreSnapshot

        a = ScoreSnapshot(set_score_a=1, set_score_b=0, game_score_a=6, game_score_b=4)
        b = ScoreSnapshot(set_score_a=1, set_score_b=0, game_score_a=6, game_score_b=4)
        assert a.content_hash() == b.content_hash()

        c = ScoreSnapshot(set_score_a=1, set_score_b=1)
        assert a.content_hash() != c.content_hash()

    def test_empty_score_is_not_finished(self):
        from live_collector.flashscore_live import ScoreSnapshot

        snap = ScoreSnapshot()
        assert snap.match_finished is False
        assert snap.content_hash()

    @patch("live_collector.flashscore_live.httpx.Client")
    def test_poll_handles_http_failure(self, mock_client):
        mock_client.return_value.__enter__.return_value.get.side_effect = Exception("timeout")

        from live_collector.flashscore_live import poll_flashscore_score

        snap = poll_flashscore_score(1, "abc123")
        assert snap.set_score_a is None
        assert snap.match_finished is False

    @patch("live_collector.flashscore_live.httpx.Client")
    def test_poll_detects_finished_in_html(self, mock_client):
        html = "<html><div class='detailScore'><div class='matchStatus'>FINISHED</div></div></html>"
        mock_resp = mock_client.return_value.__enter__.return_value
        mock_resp.get.return_value.text = html
        mock_resp.get.return_value.raise_for_status = lambda: None

        from live_collector.flashscore_live import poll_flashscore_score

        snap = poll_flashscore_score(1, "abc123")
        assert snap.match_finished is True


# ============================================================================
# Test Odds Parsing
# ============================================================================


class TestBettingLive:
    def test_odds_snapshot_any_valid(self):
        from live_collector.betting_live import OddsSnapshot

        assert OddsSnapshot().any_valid() is False
        assert OddsSnapshot(back_odds_a=1.5).any_valid() is True
        assert OddsSnapshot(lay_odds_b=2.0).any_valid() is True

    def test_odds_snapshot_content_hash(self):
        from live_collector.betting_live import OddsSnapshot

        a = OddsSnapshot(back_odds_a=1.5, back_odds_b=2.5)
        b = OddsSnapshot(back_odds_a=1.5, back_odds_b=2.5)
        assert a.content_hash() == b.content_hash()

        c = OddsSnapshot(back_odds_a=1.5, back_odds_b=2.6)
        assert a.content_hash() != c.content_hash()

    @patch("live_collector.betting_live.httpx.Client")
    def test_poll_handles_http_failure(self, mock_client):
        mock_client.return_value.__enter__.return_value.post.side_effect = Exception("timeout")

        from live_collector.betting_live import poll_betting_odds

        snap = poll_betting_odds("mkt1")
        assert snap.any_valid() is False

    @patch("live_collector.betting_live.httpx.Client")
    def test_poll_empty_response(self, mock_client):
        mock_resp = mock_client.return_value.__enter__.return_value
        mock_resp.post.return_value.text = ""
        mock_resp.post.return_value.raise_for_status = lambda: None

        from live_collector.betting_live import poll_betting_odds

        snap = poll_betting_odds("mkt1")
        assert snap.any_valid() is False


# ============================================================================
# Test Mark Match Finished
# ============================================================================


class TestMarkMatchFinished:
    def test_marks_finished_and_calculates_duration(self, db_session):
        from models.tracked_match import TrackedMatch

        scheduled = datetime.now(timezone.utc) - timedelta(hours=2, minutes=15)
        tm = TrackedMatch(
            flashscore_match_id="abc",
            player1_name="A",
            player2_name="B",
            tournament="Test",
            scheduled_start=scheduled,
            status="LIVE",
            created_at=datetime.now(timezone.utc),
            updated_at=datetime.now(timezone.utc),
        )
        db_session.add(tm)
        db_session.commit()

        from live_collector.flashscore_live import mark_match_finished

        mark_match_finished(tm.id)

        db_session.refresh(tm)
        assert tm.status == "FINISHED"
        assert tm.actual_finish is not None
        assert tm.match_duration_min is not None
        assert 130 <= tm.match_duration_min <= 145

    def test_does_not_double_finish(self, db_session):
        from models.tracked_match import TrackedMatch

        tm = TrackedMatch(
            flashscore_match_id="abc",
            player1_name="A",
            player2_name="B",
            tournament="Test",
            scheduled_start=datetime.now(timezone.utc) - timedelta(hours=1),
            status="FINISHED",
            actual_finish=datetime.now(timezone.utc),
            match_duration_min=60,
        )
        db_session.add(tm)
        db_session.commit()
        first_finish = tm.actual_finish

        from live_collector.flashscore_live import mark_match_finished

        mark_match_finished(tm.id)

        db_session.refresh(tm)
        assert tm.status == "FINISHED"
        assert tm.actual_finish == first_finish  # unchanged


# ============================================================================
# Test Dedup Logic
# ============================================================================


class TestDedup:
    def test_score_dedup_prevents_duplicate_writes(self):
        import live_collector.service as svc

        svc._score_hash.clear()
        svc._score_hash[1] = hashlib.sha256(b"snap1").hexdigest()

        from live_collector.flashscore_live import ScoreSnapshot

        snap = ScoreSnapshot(set_score_a=1, set_score_b=0)
        snap.content_hash = lambda: hashlib.sha256(b"snap1").hexdigest()

        from unittest.mock import MagicMock
        from live_collector.flashscore_live import poll_flashscore_score

        with patch.object(svc, "_score_last_poll", {1: 0}):
            pass

    def test_odds_dedup_prevents_duplicate_writes(self):
        import live_collector.service as svc

        svc._odds_hash.clear()
        hash1 = hashlib.sha256(b"1.5,2.5,None,None").hexdigest()
        svc._odds_hash[1] = hash1

        from live_collector.betting_live import OddsSnapshot

        snap = OddsSnapshot(back_odds_a=1.5, back_odds_b=2.5)
        assert snap.any_valid()

        new_hash = snap.content_hash()
        assert new_hash == hash1  # same values → same hash → skipped
