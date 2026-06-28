import os
from datetime import datetime, timezone
from unittest.mock import MagicMock, patch

import pytest
from sqlalchemy import text

# Register all ORM tables with Base.metadata before conftest creates them
import incidents.models  # noqa: F401
import models.completed_match  # noqa: F401
import models.live_odds  # noqa: F401
import models.live_score  # noqa: F401
import models.tracked_match  # noqa: F401


@pytest.fixture
def db_session():
    from database import SessionLocal

    session = SessionLocal()
    from incidents.models import Incident

    Incident.metadata.create_all(bind=session.get_bind())
    yield session
    session.rollback()
    session.close()


class TestIncidentModel:
    def test_table_creation(self, db_session):
        from incidents.models import Incident

        inc = Incident(
            module="test", title="Test creation",
            incident_hash="abc123", severity="INFO",
            status="OPEN", category="Test",
        )
        db_session.add(inc)
        db_session.commit()
        row = db_session.execute(text("SELECT * FROM incidents WHERE module='test'")).fetchone()
        assert row is not None

    def test_field_defaults(self, db_session):
        from incidents.models import Incident

        inc = Incident(
            module="test_module",
            title="Default field test",
            summary="Checking defaults",
            incident_hash="hash_default_001",
        )
        db_session.add(inc)
        db_session.flush()

        assert inc.severity == "WARNING"
        assert inc.status == "OPEN"
        assert inc.category == "Unknown"
        assert inc.occurrence_count == 1
        assert inc.recovery_attempts == 0
        assert inc.first_detected_at is not None
        assert inc.last_detected_at is not None
        assert inc.created_at is not None
        assert inc.updated_at is not None

    def test_nullable_fields(self, db_session):
        from incidents.models import Incident

        inc = Incident(
            module="test_module",
            title="Nullable test",
            summary="",
            incident_hash="hash_nullable_001",
        )
        db_session.add(inc)
        db_session.flush()

        assert inc.tracked_match_id is None
        assert inc.collector_name is None
        assert inc.resolved_at is None


class TestIncidentService:
    def test_create_new_incident(self, db_session):
        from incidents.service import create_incident

        inc = create_incident(
            db_session,
            severity="ERROR",
            category="Database",
            module="database",
            title="DB connection lost",
            summary="TimescaleDB unreachable",
        )
        assert inc.incident_id is not None
        assert inc.severity == "ERROR"
        assert inc.status == "OPEN"
        assert inc.occurrence_count == 1

    def test_create_incident_with_optional_fields(self, db_session):
        from incidents.service import create_incident

        inc = create_incident(
            db_session,
            severity="WARNING",
            category="Match Collection",
            module="live_collector",
            title="Stale match data",
            summary="No score update",
            tracked_match_id=42,
            collector_name="flashscore",
        )
        assert inc.tracked_match_id == 42
        assert inc.collector_name == "flashscore"

    def test_deduplicate_same_hash(self, db_session):
        from incidents.service import create_incident

        inc1 = create_incident(
            db_session,
            severity="ERROR",
            category="Database",
            module="database",
            title="DB connection lost",
        )
        first_id = inc1.incident_id

        inc2 = create_incident(
            db_session,
            severity="CRITICAL",
            category="Database",
            module="database",
            title="DB connection lost",
            summary="Still failing",
        )
        assert inc2.incident_id == first_id
        assert inc2.occurrence_count == 2
        assert inc2.summary == "Still failing"

    def test_different_hash_creates_new(self, db_session):
        from incidents.service import create_incident

        inc1 = create_incident(
            db_session,
            severity="ERROR",
            category="Database",
            module="database",
            title="DB connection lost",
        )
        inc2 = create_incident(
            db_session,
            severity="ERROR",
            category="Network",
            module="network",
            title="API timeout",
        )
        assert inc2.incident_id != inc1.incident_id

    def test_recurrence_after_resolve(self, db_session):
        from incidents.service import create_incident, resolve_incident

        inc1 = create_incident(
            db_session,
            severity="ERROR",
            category="Database",
            module="database",
            title="DB connection lost",
        )
        first_id = inc1.incident_id
        resolve_incident(db_session, first_id)

        inc2 = create_incident(
            db_session,
            severity="ERROR",
            category="Database",
            module="database",
            title="DB connection lost",
        )
        assert inc2.incident_id != first_id
        assert inc2.occurrence_count == 1

    def test_resolve_incident(self, db_session):
        from incidents.service import create_incident, resolve_incident

        inc = create_incident(
            db_session,
            severity="WARNING",
            category="Infrastructure",
            module="system",
            title="CPU spike",
        )
        result = resolve_incident(db_session, inc.incident_id)
        assert result is not None
        assert result.status == "RESOLVED"
        assert result.resolved_at is not None

    def test_resolve_nonexistent(self, db_session):
        from incidents.service import resolve_incident

        result = resolve_incident(db_session, 99999)
        assert result is None

    def test_acknowledge_incident(self, db_session):
        from incidents.service import acknowledge_incident, create_incident

        inc = create_incident(
            db_session,
            severity="CRITICAL",
            category="Infrastructure",
            module="system",
            title="Disk full",
        )
        result = acknowledge_incident(db_session, inc.incident_id)
        assert result.status == "ACKNOWLEDGED"

    def test_get_open_incidents(self, db_session):
        from incidents.service import create_incident, get_open_incidents, resolve_incident

        create_incident(db_session, severity="WARNING", category="Database", module="db", title="Slow query")
        inc2 = create_incident(db_session, severity="ERROR", category="Infrastructure", module="sys", title="Disk")
        resolve_incident(db_session, inc2.incident_id)
        create_incident(db_session, severity="CRITICAL", category="Network", module="net", title="APi down")

        open_incs = get_open_incidents(db_session)
        assert len(open_incs) == 2

    def test_list_by_module(self, db_session):
        from incidents.service import create_incident, list_by_module

        create_incident(db_session, severity="WARNING", category="Database", module="database", title="Slow query")
        create_incident(db_session, severity="ERROR", category="Database", module="database", title="Connection lost")
        create_incident(db_session, severity="INFO", category="Collector Failure", module="live_collector", title="Stalled")

        db_results = list_by_module(db_session, "database")
        lc_results = list_by_module(db_session, "live_collector")
        assert len(db_results) == 2
        assert len(lc_results) == 1


class TestMonitorChecks:
    def test_check_database_unreachable(self, db_session):
        from incidents.monitor import _check_database

        with patch("incidents.monitor.check_connection", return_value=False):
            results = _check_database(db_session)
            assert len(results) == 1
            assert results[0]["severity"] == "CRITICAL"
            assert results[0]["category"] == "Database"

    def test_check_database_reachable(self, db_session):
        from incidents.monitor import _check_database

        with patch("incidents.monitor.check_connection", return_value=True):
            results = _check_database(db_session)
            assert len(results) == 0

    def test_check_cpu_threshold(self):
        with patch("os.getloadavg", return_value=(10.0, 8.0, 6.0)):
            with patch("os.cpu_count", return_value=4):
                from incidents.monitor import _check_cpu
                results = _check_cpu()
                assert len(results) == 1
                assert results[0]["severity"] == "WARNING"

    def test_check_cpu_normal(self):
        with patch("os.getloadavg", return_value=(0.5, 0.3, 0.2)):
            with patch("os.cpu_count", return_value=4):
                from incidents.monitor import _check_cpu
                results = _check_cpu()
                assert len(results) == 0

    def test_check_memory_threshold(self):
        with patch("os.sysconf") as mock_conf:
            def _sysconf_mock(k):
                mapping = {
                    "SC_PAGE_SIZE": 4096,
                    "SC_PHYS_PAGES": 2_000_000,
                    "SC_AVPHYS_PAGES": 50_000,
                }
                return mapping.get(k, 0)
            mock_conf.side_effect = _sysconf_mock
            from incidents.monitor import _check_memory
            results = _check_memory()
            assert len(results) == 1
            assert results[0]["severity"] == "WARNING"

    def test_check_disk_threshold(self):
        with patch(
            "shutil.disk_usage",
            return_value=MagicMock(total=100_000_000_000, used=95_000_000_000, free=5_000_000_000),
        ):
            from incidents.monitor import _check_disk
            results = _check_disk()
            assert len(results) == 1

    def test_check_disk_normal(self):
        with patch(
            "shutil.disk_usage",
            return_value=MagicMock(total=100_000_000_000, used=30_000_000_000, free=70_000_000_000),
        ):
            from incidents.monitor import _check_disk
            results = _check_disk()
            assert len(results) == 0


class TestMatchHealth:
    def test_stale_scores_generates_incident(self, db_session):
        from incidents.monitor import _check_live_matches
        from models.tracked_match import TrackedMatch
        from models.live_score import LiveScore

        now = datetime.now(timezone.utc)
        stale_time = now.timestamp() - 999  # well past 120s threshold

        tm = TrackedMatch(
            id=999,
            flashscore_match_id="fs_stale_001",
            player1_name="Player A",
            player2_name="Player B",
            tournament="Test Event",
            status="LIVE",
            tracking_enabled=True,
            created_at=now,
            updated_at=now,
        )
        db_session.add(tm)
        db_session.flush()

        ls = LiveScore(
            tracked_match_id=999,
            timestamp=datetime.fromtimestamp(stale_time, tz=timezone.utc),
            content_hash="hash_old",
            flashscore_match_id="fs_stale_001",
        )
        db_session.add(ls)
        db_session.commit()

        results = _check_live_matches(db_session)
        score_incidents = [i for i in results if "Stale scores" in i.get("title", "")]
        assert len(score_incidents) >= 1

    def test_unfinalized_finished_match(self, db_session):
        from incidents.monitor import _check_unfinalized_finished
        from models.tracked_match import TrackedMatch

        now = datetime.now(timezone.utc)
        finish_time = now.timestamp() - 9999  # well past 1800s threshold

        tm = TrackedMatch(
            id=88001,
            flashscore_match_id="fs_unf_001",
            player1_name="P1",
            player2_name="P2",
            tournament="Test Event",
            status="FINISHED",
            tracking_enabled=True,
            actual_finish=datetime.fromtimestamp(finish_time, tz=timezone.utc),
            created_at=now,
            updated_at=now,
        )
        db_session.add(tm)
        db_session.commit()

        results = _check_unfinalized_finished(db_session)
        assert len(results) >= 1
        assert results[0]["severity"] == "ERROR"


class TestPackageGenerator:
    def test_package_generated(self, db_session, tmp_path):
        from incidents.package_generator import generate_incident_package
        from incidents.service import create_incident

        inc = create_incident(
            db_session,
            severity="CRITICAL",
            category="Database",
            module="database",
            title="DB connection lost",
            summary="Test package generation",
        )

        with patch("incidents.package_generator.INCIDENT_PACKAGES_DIR", str(tmp_path)):
            package_dir = generate_incident_package(db_session, inc)

        assert os.path.isdir(package_dir)
        assert os.path.isfile(os.path.join(package_dir, "incident.json"))

        with open(os.path.join(package_dir, "incident.json")) as f:
            import json
            data = json.load(f)
            assert data["incident_id"] == inc.incident_id
            assert data["severity"] == "CRITICAL"

    def test_secrets_redacted_in_config(self, db_session, tmp_path):
        from incidents.package_generator import _sanitize_value

        assert _sanitize_value("DB_PASSWORD", "secret123") == "<REDACTED>"
        assert _sanitize_value("TELEGRAM_BOT_TOKEN", "abc123") == "<REDACTED>"
        assert _sanitize_value("API_KEY", "key123") == "<REDACTED>"
        assert _sanitize_value("SECRET_THING", "hidden") == "<REDACTED>"
        assert _sanitize_value("DATABASE_URL", "postgresql://...") == "postgresql://..."
        assert _sanitize_value("LOG_LEVEL", "INFO") == "INFO"


class TestNotifier:
    def test_message_format_no_stack_trace(self, db_session):
        from incidents.notifier import _format_incident_alert
        from incidents.service import create_incident

        inc = create_incident(
            db_session,
            severity="CRITICAL",
            category="Database",
            module="database",
            title="DB connection lost",
            summary="Traceback (most recent call last):\n  File ...\nException: boom",
        )

        msg = _format_incident_alert(inc)
        assert "INC_" in msg
        assert inc.severity in msg
        assert inc.module in msg

    def test_critical_only_sends(self, db_session):
        from incidents.notifier import SEVERITY_ICONS

        assert "CRITICAL" in SEVERITY_ICONS
        assert "INFO" in SEVERITY_ICONS

    @patch("incidents.notifier.httpx.post")
    def test_telegram_disabled_without_token(self, mock_post, db_session):
        from incidents.service import create_incident

        with patch("incidents.notifier._enabled", False):
            from incidents.notifier import send_notification
            inc = create_incident(db_session, severity="CRITICAL", category="Database",
                                  module="database", title="test")
            result = send_notification(inc)
            assert result is False
            mock_post.assert_not_called()


class TestRecovery:
    def test_recovery_increments_attempts(self, db_session):
        from incidents.recovery import attempt_recovery
        from incidents.service import create_incident

        inc = create_incident(
            db_session,
            severity="ERROR",
            category="Database",
            module="database",
            title="DB connection lost",
        )
        assert inc.recovery_attempts == 0
        attempt_recovery(db_session, inc)
        assert inc.recovery_attempts == 1

    def test_recovery_db_retry_success(self, db_session):
        from incidents.service import create_incident

        inc = create_incident(
            db_session,
            severity="ERROR",
            category="Database",
            module="database",
            title="DB connection lost",
        )

        from incidents.recovery import attempt_recovery
        import incidents.recovery as recovery_mod

        with patch.object(recovery_mod, "engine", db_session.get_bind()):
            result = attempt_recovery(db_session, inc)
            assert result is True

    def test_no_unsafe_recovery_actions(self, db_session):
        from incidents.recovery import attempt_recovery
        from incidents.service import create_incident

        inc = create_incident(
            db_session,
            severity="WARNING",
            category="Unknown",
            module="unknown",
            title="Some issue",
        )
        result = attempt_recovery(db_session, inc)
        assert result is False


class TestIncidentLifecycle:
    def test_full_lifecycle(self, db_session):
        from incidents.service import (
            acknowledge_incident,
            create_incident,
            get_open_incidents,
            resolve_incident,
        )

        inc = create_incident(
            db_session,
            severity="CRITICAL",
            category="Database",
            module="database",
            title="DB connection lost",
        )
        assert inc.status == "OPEN"
        assert len(get_open_incidents(db_session)) == 1

        result = acknowledge_incident(db_session, inc.incident_id)
        assert result.status == "ACKNOWLEDGED"

        result = resolve_incident(db_session, inc.incident_id)
        assert result.status == "RESOLVED"
        assert result.resolved_at is not None
        assert len(get_open_incidents(db_session)) == 0

    def test_auto_resolve_healed(self, db_session):
        from incidents.service import create_incident, get_open_incidents
        from incidents.monitor import _auto_resolve_healed

        inc = create_incident(
            db_session,
            severity="WARNING",
            category="Database",
            module="database",
            title="Slow query",
        )
        assert len(get_open_incidents(db_session)) == 1

        _auto_resolve_healed(db_session, [])

        from incidents.models import Incident
        refreshed = db_session.query(Incident).filter_by(incident_id=inc.incident_id).first()
        assert refreshed.status == "RESOLVED"

    def test_auto_resolve_keeps_active(self, db_session):
        from incidents.service import create_incident, get_open_incidents
        from incidents.monitor import _auto_resolve_healed

        inc = create_incident(
            db_session,
            severity="WARNING",
            category="Database",
            module="database",
            title="Slow query",
        )
        assert len(get_open_incidents(db_session)) == 1

        current = [{"category": "Database", "module": "database", "title": "Slow query"}]
        _auto_resolve_healed(db_session, current)

        from incidents.models import Incident
        refreshed = db_session.query(Incident).filter_by(incident_id=inc.incident_id).first()
        assert refreshed.status == "OPEN"


class TestIntegration:
    def test_detect_create_package_resolve(self, db_session, tmp_path):
        from incidents.service import create_incident, get_open_incidents, resolve_incident

        with patch("incidents.monitor.check_connection", return_value=False):
            from incidents.monitor import _check_database

            incidents_data = _check_database(db_session)
            assert len(incidents_data) == 1
            assert incidents_data[0]["severity"] == "CRITICAL"

            inc = create_incident(
                db_session,
                severity=incidents_data[0]["severity"],
                category=incidents_data[0]["category"],
                module=incidents_data[0]["module"],
                title=incidents_data[0]["title"],
            )
            assert inc.status == "OPEN"

            resolve_incident(db_session, inc.incident_id)
            assert inc.status == "RESOLVED"

        assert len(get_open_incidents(db_session)) == 0
