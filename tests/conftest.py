"""Shared test fixtures — in-memory SQLite for all tests."""

import sys
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from database import Base


@pytest.fixture(autouse=True)
def _sqlite_test_engine():
    """Replace the PostgreSQL engine with in-memory SQLite for ALL tests.

    Patches ``database.engine``, ``database.SessionLocal``, AND any
    module that imported these at module level (collectors, registry).
    """
    import database as db_mod

    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    sess_local = sessionmaker(bind=engine)

    patches = []

    # Core database module
    patches.append(patch.object(db_mod, "engine", engine))
    patches.append(patch.object(db_mod, "SessionLocal", sess_local))

    # Modules that imported SessionLocal / engine at module level
    for mod_name in (
        "collector.flashscore",
        "collector.betting_site",
        "collector.tennis_explorer",
        "registry.service",
        "orchestrator.service",
        "live_collector.service",
        "live_collector.flashscore_live",
        "live_collector.betting_live",
        "finalizer.service",
    ):
        mod = sys.modules.get(mod_name)
        if mod is None:
            continue
        if hasattr(mod, "SessionLocal"):
            patches.append(patch.object(mod, "SessionLocal", sess_local))
        if hasattr(mod, "engine"):
            patches.append(patch.object(mod, "engine", engine))

    for p in patches:
        p.start()

    yield

    for p in reversed(patches):
        p.stop()
