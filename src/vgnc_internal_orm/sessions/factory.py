"""Database session factory for VGNC ORM.

The session layer delegates engine/session creation to ``db_common``:

* :class:`db_common.EngineFactory` owns engine creation, connection pooling
  (``QueuePool`` for network backends, ``StaticPool`` for SQLite) and engine
  disposal.
* :class:`db_common.SessionFactory` owns the read-write and read-only session
  context managers (read-only sessions reject commits with
  :class:`db_common.ReadOnlySessionError`).
* :func:`db_common.health_check` owns the connectivity probe.

The vgnc :class:`SessionFactory` is a thin wrapper over those singletons,
preserving the public sync function names that existing callers
(``SessionManager``, the CLI, the tests) rely on.

All async code and the bespoke MySQL/env pool plumbing (``SET NAMES utf8mb4``
connect listeners, dev/staging/prod pool overrides, MySQL ``connect_args``)
were removed as part of the db-common migration.
"""

import logging
from collections.abc import Generator
from contextlib import contextmanager
from typing import Any

import db_common
from sqlalchemy import Engine, text
from sqlalchemy.orm import Session, sessionmaker

from ..config.settings import DatabaseConfig

logger = logging.getLogger(__name__)


class SessionFactory:
    """Factory for creating database sessions, delegating to ``db_common``.

    Wraps a :class:`db_common.EngineFactory` (engine creation + pooling) and a
    :class:`db_common.SessionFactory` (read-only session support). The public
    sync surface (``engine``, ``create_session``, ``health_check``,
    ``get_readonly_session``, ``get_engine_info``, ``get_pool_status``,
    ``dispose_engine``) is preserved so existing callers keep working.

    Note:
        DatabaseConfig is now a db_common.DatabaseSettings subclass, so it
        can be passed directly to db_common.EngineFactory without an adapter.
    """

    def __init__(self, config: DatabaseConfig | None = None) -> None:
        self.config = config
        self._engine_factory: db_common.EngineFactory | None = None
        self._db_session_factory: db_common.SessionFactory | None = None
        self._engine: Engine | None = None
        self._session_factory: sessionmaker[Any] | None = None

    # -- Internal db_common singletons --------------------------------------

    def _require_config(self) -> DatabaseConfig:
        if self.config is None:
            raise ValueError("Database configuration is required")
        return self.config

    def _get_engine_factory(self) -> db_common.EngineFactory:
        if self._engine_factory is None:
            # DatabaseConfig is now a db_common.DatabaseSettings subclass
            # so it can be passed directly to db_common.EngineFactory
            self._engine_factory = db_common.EngineFactory(self._require_config())
        return self._engine_factory

    def _get_db_session_factory(self) -> db_common.SessionFactory:
        if self._db_session_factory is None:
            self._db_session_factory = db_common.SessionFactory(
                self._get_engine_factory()
            )
        return self._db_session_factory

    # -- Engine / session access --------------------------------------------

    @property
    def engine(self) -> Engine:
        """Get or create the SQLAlchemy engine via ``db_common.EngineFactory``."""
        if self._engine is None:
            self._engine = self._get_engine_factory().get_engine()
        return self._engine

    @property
    def session_factory(self) -> sessionmaker[Any]:
        """Get or create the ``sessionmaker`` bound to the engine."""
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_factory

    def create_session(self) -> Session:
        """Create a new database session (manual lifecycle management)."""
        return self.session_factory()  # type: ignore[no-any-return]

    @contextmanager
    def get_session(self) -> Generator[Session, None, None]:
        """Read-write session: commits on clean exit, rolls back on exception.

        Delegates the commit/rollback contract to ``db_common.SessionFactory``.
        """
        with self._get_db_session_factory().get_session() as session:
            yield session

    @contextmanager
    def get_readonly_session(self) -> Generator[Session, None, None]:
        """Read-only session; any commit raises ``ReadOnlySessionError``.

        Delegated to ``db_common.SessionFactory.get_readonly_session``.
        """
        with self._get_db_session_factory().get_readonly_session() as session:
            yield session

    def close_all_sessions(self) -> None:
        """Close all sessions in memory (globally)."""
        self._get_db_session_factory().close_all_sessions()

    def dispose_engine(self) -> None:
        """Dispose the engine and reset all cached singletons."""
        if self._engine_factory is not None:
            self._engine_factory.dispose()
        self._engine_factory = None
        self._db_session_factory = None
        self._session_factory = None
        self._engine = None

    def health_check(self) -> bool:
        """Return ``True`` if the engine can execute ``SELECT 1``.

        Delegated to :func:`db_common.health_check` (never raises).
        """
        if self.config is None:
            return False
        return bool(db_common.health_check(self.engine))

    def get_engine_info(self) -> dict[str, Any]:
        """Get a summary of the engine configuration."""
        if self.config is None:
            return {}
        config = self.config
        database_url = config.database_url.get_secret_value()
        return {
            "driver": config.driver,
            "database_url": database_url[:50] + "...",  # truncated for safety
            "pool": {"class": self.engine.pool.__class__.__name__},
        }

    def get_pool_status(self) -> dict[str, Any]:
        """Get current pool status information from the live engine."""
        if self._engine is None:
            return {"status": "Not initialized"}

        # SQLAlchemy types the engine pool as the base ``Pool``; the
        # QueuePool-specific accessors (``size``/``checkedout``/``overflow``)
        # only exist on concrete pool classes, so access them via ``Any``.
        pool: Any = self._engine.pool
        if hasattr(pool, "size"):  # QueuePool and similar
            return {
                "status": "Active",
                "size": pool.size(),
                "checked_out": pool.checkedout(),
                "overflow": pool.overflow(),
            }
        # StaticPool (SQLite) and others
        return {
            "status": f"{pool.__class__.__name__} (SQLite/no-pool)",
            "pool_type": pool.__class__.__name__,
        }


# Global session factory instance, initialized lazily.
session_factory: SessionFactory | None = None


def get_session_factory() -> SessionFactory:
    """Get or create the global session factory instance."""
    global session_factory
    if session_factory is None:
        session_factory = SessionFactory()
    return session_factory


def reset_global_session_factory() -> None:
    """Reset the global session factory instance (test teardown)."""
    global session_factory
    if session_factory is not None:
        session_factory.dispose_engine()
        session_factory = None


# -- Module-level thin-delegating helper functions --------------------------


def engine_from_config(config: DatabaseConfig) -> Engine:
    """Create a SQLAlchemy engine from a database configuration."""
    return SessionFactory(config).engine


def create_session_factory_with_config(config: DatabaseConfig) -> SessionFactory:
    """Create a new ``SessionFactory`` bound to ``config``."""
    return SessionFactory(config)


def get_session(config: DatabaseConfig | None = None) -> Session:
    """Get a database session using global or provided configuration."""
    factory = get_session_factory() if config is None else SessionFactory(config)
    return factory.create_session()


def health_check_from_config(config: DatabaseConfig) -> bool:
    """Run :func:`db_common.health_check` against an engine built from ``config``."""
    return bool(db_common.health_check(engine_from_config(config)))


def get_engine_info_from_config(config: DatabaseConfig) -> dict[str, Any]:
    """Get engine information for ``config``."""
    return SessionFactory(config).get_engine_info()


def get_pool_status_from_config(config: DatabaseConfig) -> dict[str, Any]:
    """Get pool status for ``config`` (initializes the engine)."""
    factory = SessionFactory(config)
    _ = factory.engine
    return factory.get_pool_status()


def check_database_connection(config: DatabaseConfig) -> bool:
    """Test database connectivity by round-tripping ``SELECT 1`` in a session."""
    try:
        with get_session_context(config) as session:
            session.execute(text("SELECT 1"))
            return True
    except Exception as e:  # exercised by the dead-engine test
        logger.error("Database connection test failed: %s", e)
        return False


@contextmanager
def get_session_context(
    config: DatabaseConfig | None = None,
) -> Generator[Session, None, None]:
    """Context manager: commit on clean exit, rollback on exception."""
    factory = get_session_factory() if config is None else SessionFactory(config)
    with factory.get_session() as session:
        yield session
