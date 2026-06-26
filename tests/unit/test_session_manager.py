"""Unit tests for SessionManager using an in-memory SQLite SessionFactory.

Exercises the commit/rollback contract, no-commit context, manual session
creation, health check, and session/engine lifecycle methods.
"""

from datetime import datetime

from db_common import DatabaseDriver, DeclarativeBase
from sqlalchemy import select

from vgnc_internal_orm.config.settings import DatabaseConfig
from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from vgnc_internal_orm.sessions.factory import SessionFactory
from vgnc_internal_orm.sessions.manager import SessionManager


def _make_manager() -> tuple[SessionManager, SessionFactory]:
    factory = SessionFactory(DatabaseConfig(driver=DatabaseDriver.SQLITE))
    DeclarativeBase.metadata.create_all(factory.engine)
    return SessionManager(factory), factory


def _species(taxon_id: int = 1) -> Species:
    return Species(
        taxon_id=taxon_id,
        genefam_prefix="P",
        display_name="x",
        scientific_name="x",
        is_live=SpeciesLiveStatus.YES,
        created=datetime.now(),
    )


class TestSessionManager:
    def test_get_session_commits_on_clean_exit(self):
        manager, factory = _make_manager()
        try:
            with manager.get_session() as session:
                session.add(_species(9606))
            # Committed -> visible in a fresh session
            with manager.get_session() as session:
                result = session.execute(
                    select(Species).where(Species.taxon_id == 9606)
                ).scalar_one_or_none()
                assert result is not None
        finally:
            manager.dispose_engine()

    def test_get_session_rolls_back_on_exception(self):
        manager, factory = _make_manager()
        try:
            import pytest

            with pytest.raises(ValueError):
                with manager.get_session() as session:
                    session.add(_species(1111))
                    raise ValueError("boom")
            # Rolled back -> not visible
            with manager.get_session() as session:
                result = session.execute(
                    select(Species).where(Species.taxon_id == 1111)
                ).scalar_one_or_none()
                assert result is None
        finally:
            manager.dispose_engine()

    def test_get_session_no_commit(self):
        manager, factory = _make_manager()
        try:
            with manager.get_session_no_commit() as session:
                session.add(_species(2222))
            # Not committed -> not visible in a fresh session
            with manager.get_session_no_commit() as session:
                result = session.execute(
                    select(Species).where(Species.taxon_id == 2222)
                ).scalar_one_or_none()
                assert result is None
        finally:
            manager.dispose_engine()

    def test_create_session_manual(self):
        manager, factory = _make_manager()
        try:
            session = manager.create_session()
            assert session is not None
            session.close()
        finally:
            manager.dispose_engine()

    def test_health_check_true_when_engine_alive(self):
        manager, factory = _make_manager()
        try:
            assert manager.health_check() is True
        finally:
            manager.dispose_engine()

    def test_close_all_sessions(self):
        manager, factory = _make_manager()
        try:
            manager.create_session()
            manager.close_all_sessions()  # should not raise
        finally:
            manager.dispose_engine()
