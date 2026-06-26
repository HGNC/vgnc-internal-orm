"""Unit tests for the db-common-delegating session factory.

T3 rewrote the session layer to delegate engine/session creation to
``db_common.EngineFactory`` / ``db_common.SessionFactory`` and removed all
async code and the bespoke MySQL/env pool plumbing. These tests pin that
delegation behaviour against a real in-memory SQLite engine (no mocks).
"""

import inspect

import db_common
import pytest
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

import vgnc_internal_orm.sessions.factory as factory_module
from vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver
from vgnc_internal_orm.sessions.factory import (
    SessionFactory,
    check_database_connection,
    create_session_factory_with_config,
    engine_from_config,
    get_session,
    get_session_context,
    get_session_factory,
    health_check_from_config,
    reset_global_session_factory,
)
from vgnc_internal_orm.sessions.manager import SessionManager


def _sqlite_config() -> DatabaseConfig:
    """A minimal, env-file-free in-memory SQLite DatabaseConfig."""
    return DatabaseConfig(
        driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
    )


def _dead_sqlite_config() -> DatabaseConfig:
    """A SQLite config whose path cannot be created, so connections fail."""
    return DatabaseConfig(
        driver=DatabaseDriver.SQLITE,
        database="/this/path/does/not/exist/test.db",
        _env_file=None,
    )


# Symbols that must NOT exist on the module once async is removed.
ASYNC_SYMBOLS = [
    "create_async_engine",
    "AsyncEngine",
    "AsyncSession",
    "async_sessionmaker",
    "async_engine",
    "create_async_session",
    "async_session_factory",
    "async_health_check",
    "async_engine_from_config",
    "get_async_session",
    "get_async_session_context",
    "async_health_check_from_config",
    "check_async_database_connection",
    "_create_async_engine",
    "_async_engine",
    "_async_session_factory",
]


class TestAsyncRemoved:
    """Gate (e): no async surface remains in the session module."""

    def test_no_async_symbols_on_module(self):
        present = [name for name in ASYNC_SYMBOLS if hasattr(factory_module, name)]
        assert present == [], f"async symbols still present on module: {present}"

    def test_no_async_imports_in_module_source(self):
        source = inspect.getsource(factory_module)
        forbidden = ("create_async_engine", "AsyncSession", "async_sessionmaker")
        found = [token for token in forbidden if token in source]
        assert found == [], f"async tokens still in module source: {found}"

    def test_no_async_def_in_module_source(self):
        source = inspect.getsource(factory_module)
        assert "async def" not in source


class TestDbCommonDelegation:
    """Engine/session creation delegates to db-common singletons."""

    def test_factory_uses_db_common_engine_factory(self):
        factory = SessionFactory(_sqlite_config())
        # touching .engine builds the db_common.EngineFactory
        _ = factory.engine
        assert isinstance(factory._engine_factory, db_common.EngineFactory)

    def test_get_readonly_session_rejects_commit(self):
        """db_common.SessionFactory.get_readonly_session is exposed and rejects writes."""
        factory = SessionFactory(_sqlite_config())

        with pytest.raises(db_common.ReadOnlySessionError):
            with factory.get_readonly_session() as session:
                session.commit()

    def test_session_exceptions_reexported_from_sessions_package(self):
        from vgnc_internal_orm import sessions

        assert sessions.ReadOnlySessionError is db_common.ReadOnlySessionError
        assert sessions.SessionError is db_common.SessionError


class TestSqliteBehaviour:
    """Verify (a)-(b),(d): real SQLite engine + session round-trips."""

    def test_engine_from_config_is_usable(self):
        engine = engine_from_config(_sqlite_config())
        assert isinstance(engine, Engine)
        assert engine.url.drivername == "sqlite"

    def test_factory_engine_is_usable_sqlite(self):
        factory = SessionFactory(_sqlite_config())
        engine = factory.engine
        assert engine is not None
        # db_common.EngineFactory uses StaticPool for SQLite
        assert isinstance(engine.pool, StaticPool)

    def test_get_session_context_roundtrips_select_one(self):
        with get_session_context(_sqlite_config()) as session:
            result = session.execute(text("SELECT 1")).fetchone()
            assert result[0] == 1

    def test_get_session_context_rolls_back_on_exception(self):
        config = _sqlite_config()

        with pytest.raises(ValueError, match="boom"):
            with get_session_context(config) as session:
                session.execute(text("SELECT 1"))
                raise ValueError("boom")

        # Still usable afterwards
        with get_session_context(config) as session:
            assert session.execute(text("SELECT 1")).fetchone()[0] == 1

    def test_session_manager_commits_on_clean_exit(self):
        manager = SessionManager(SessionFactory(_sqlite_config()))

        with manager.get_session() as session:
            session.execute(text("SELECT 1"))

    def test_session_manager_rolls_back_on_error(self):
        manager = SessionManager(SessionFactory(_sqlite_config()))

        with pytest.raises(RuntimeError):
            with manager.get_session():
                raise RuntimeError("fail")


class TestHealthCheck:
    """Verify (c): health_check_from_config True on live, False on dead."""

    def test_health_check_true_on_live_sqlite(self):
        assert health_check_from_config(_sqlite_config()) is True

    def test_health_check_false_on_dead_engine(self):
        # A SQLite path that cannot be created -> connect fails -> False.
        assert health_check_from_config(_dead_sqlite_config()) is False

    def test_factory_health_check_delegates_to_db_common(self):
        factory = SessionFactory(_sqlite_config())
        # engine is live
        assert factory.health_check() is True


class TestPublicHelpers:
    """The preserved thin-delegating public functions keep working."""

    def test_get_session_with_config(self):
        session = get_session(_sqlite_config())
        assert isinstance(session, Session)
        session.close()

    def test_create_session_factory_with_config(self):
        factory = create_session_factory_with_config(_sqlite_config())
        assert isinstance(factory, SessionFactory)
        assert factory.config is not None

    def test_check_database_connection_true(self):
        assert check_database_connection(_sqlite_config()) is True

    def test_check_database_connection_false_on_dead(self):
        assert check_database_connection(_dead_sqlite_config()) is False

    def test_global_session_factory_singleton_and_reset(self):
        reset_global_session_factory()
        first = get_session_factory()
        second = get_session_factory()
        assert first is second
        assert isinstance(first, SessionFactory)
        reset_global_session_factory()

    def test_get_session_without_config_raises_when_global_unset(self):
        reset_global_session_factory()
        # global factory has no config -> engine creation is impossible
        with pytest.raises(ValueError):
            get_session()
        reset_global_session_factory()


class TestEngineLifecycle:
    def test_engine_cached(self):
        factory = SessionFactory(_sqlite_config())
        assert factory.engine is factory.engine

    def test_dispose_engine_clears_cache(self):
        factory = SessionFactory(_sqlite_config())
        _ = factory.engine
        factory.dispose_engine()
        assert factory._engine is None

    def test_engine_info_reports_driver(self):
        factory = SessionFactory(_sqlite_config())
        info = factory.get_engine_info()
        assert info["driver"] == "sqlite"

    def test_pool_status_reports_staticpool(self):
        factory = SessionFactory(_sqlite_config())
        _ = factory.engine
        status = factory.get_pool_status()
        assert "StaticPool" in status["status"]

    def test_pool_status_not_initialized(self):
        factory = SessionFactory(_sqlite_config())
        status = factory.get_pool_status()
        assert status["status"] == "Not initialized"


class TestNoConfigErrorHandling:
    """A ``SessionFactory(None)`` fails fast with a clear error, never silently.

    Restores coverage that was lost when the old ``TestErrorHandling`` was
    removed alongside the removed-behavior classes in the integration suite.
    """

    def test_engine_without_config_raises(self):
        factory = SessionFactory(None)
        with pytest.raises(ValueError, match="Database configuration is required"):
            _ = factory.engine

    def test_session_factory_without_config_raises(self):
        factory = SessionFactory(None)
        with pytest.raises(ValueError, match="Database configuration is required"):
            _ = factory.session_factory

    def test_health_check_without_config_returns_false(self):
        # health_check is a probe, so it reports False rather than raising;
        # it must never succeed or silently pretend connectivity.
        factory = SessionFactory(None)
        assert factory.health_check() is False
