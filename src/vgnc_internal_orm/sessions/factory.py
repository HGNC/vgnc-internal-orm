"""Database session factory for VGNC ORM."""

import logging
from collections.abc import AsyncGenerator, Generator
from contextlib import asynccontextmanager, contextmanager
from typing import Any

from sqlalchemy import create_engine, event, text
from sqlalchemy.engine import Engine
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool, StaticPool

from ..config.settings import DatabaseConfig, Environment

logger = logging.getLogger(__name__)


class SessionFactory:
    """Factory for creating database sessions with proper configuration.

    This factory manages database connection lifecycle, connection pooling,
    and provides both synchronous and asynchronous session creation. It handles
    MySQL-specific UTF8MB4 charset configuration and environment-specific
    optimization for development, testing, and production deployments.

    Attributes:
        config (DatabaseConfig | None): Database configuration instance.
            If None, uses default configuration.
        _engine (Engine | None): Synchronous SQLAlchemy engine instance.
        _async_engine (AsyncEngine | None): Asynchronous SQLAlchemy engine.
        _session_factory (sessionmaker | None): Factory for creating sessions.
        _async_session_factory (async_sessionmaker | None): Factory for async sessions.

    Note:
        The factory implements lazy initialization - engines are created on
        first access. This ensures fast startup and allows configuration
        changes before first database connection.

    Example:
        >>> config = DatabaseConfig(driver=DatabaseDriver.MYSQL, host='localhost', ...)
        >>> factory = SessionFactory(config)
        >>> with factory.get_session() as session:
        ...     # Use session for database operations
    """

    def __init__(self, config: DatabaseConfig | None = None):
        """Initialize session factory with database configuration.

        Args:
            config (DatabaseConfig | None): Database configuration object.
                If None, attempts to load configuration from environment
                variables or uses sensible defaults.
        """
        self.config = config
        self._engine: Engine | None = None
        self._async_engine: AsyncEngine | None = None
        self._session_factory: sessionmaker[Any] | None = None
        self._async_session_factory: async_sessionmaker[Any] | None = None

    def _get_pool_config(self, is_async: bool = False) -> dict[str, Any]:
        """Get environment-specific pool configuration.

        Retrieves and validates database connection pool settings based on the
        current environment and database driver. This method handles
        environment-specific overrides and applies sensible defaults for
        connection pooling parameters.

        Args:
            is_async (bool): Whether the pool configuration is for an async
                engine. Affects pool size and behavior recommendations.
                Default is False.

        Returns:
            dict[str, Any]: Pool configuration dictionary containing
                SQLAlchemy pool settings like 'pool_size', 'max_overflow',
                'pool_timeout', and 'pool_recycle'.

        Note:
            Production environments typically use larger pool sizes and
            shorter recycle intervals. SQLite uses StaticPool/NullPool
            instead of QueuePool. Async engines may have different
            optimal pool configurations.
        """
        if self.config is None:
            return {}

        env = self.config.environment

        # Base pool configuration
        pool_config: dict[str, Any] = {
            "pool_pre_ping": self.config.pool.pool_pre_ping,
            "pool_recycle": self.config.pool.pool_recycle,
        }

        if self.config.driver.value.startswith("sqlite"):
            # SQLite uses StaticPool
            pool_config.update(
                {
                    "poolclass": StaticPool,
                    "connect_args": {
                        "check_same_thread": False,
                        "timeout": self.config.connect_timeout,
                        "uri": True,
                    },
                }
            )
        else:
            # MySQL uses QueuePool for sync, NullPool for async
            if is_async:
                # Async engines don't use connection pooling in the same way
                # The connection pooling is handled by the async driver
                pool_config.update(
                    {
                        "poolclass": NullPool,
                    }
                )
            else:
                pool_config.update(
                    {
                        "poolclass": QueuePool,
                        "pool_size": self.config.pool.pool_size,
                        "max_overflow": self.config.pool.max_overflow,
                        "pool_timeout": self.config.pool.pool_timeout,
                    }
                )

            # Environment-specific adjustments (only for sync engines)
            if not is_async:
                if env == Environment.DEVELOPMENT:
                    # Development: smaller pool, faster timeouts
                    pool_config.update(
                        {
                            "pool_size": max(1, self.config.pool.pool_size // 2),
                            "max_overflow": max(5, self.config.pool.max_overflow // 2),
                            "pool_timeout": min(10, self.config.pool.pool_timeout),
                            "pool_recycle": 3600,  # 1 hour
                        }
                    )
                elif env == Environment.STAGING:
                    # Staging: medium pool, moderate timeouts
                    pool_config.update(
                        {
                            "pool_size": self.config.pool.pool_size,
                            "max_overflow": self.config.pool.max_overflow,
                            "pool_timeout": self.config.pool.pool_timeout,
                            "pool_recycle": 7200,  # 2 hours
                        }
                    )
                elif env == Environment.PRODUCTION:
                    # Production: large pool, longer timeouts
                    pool_config.update(
                        {
                            "pool_size": self.config.pool.pool_size,
                            "max_overflow": self.config.pool.max_overflow,
                            "pool_timeout": self.config.pool.pool_timeout,
                            "pool_recycle": 14400,  # 4 hours
                        }
                    )

        return pool_config

    def _get_connect_args(self) -> dict[str, Any]:
        """Get connection arguments with charset and isolation level support."""
        if self.config is None:
            return {}

        connect_args: dict[str, Any] = {
            "connect_timeout": self.config.connect_timeout,
        }

        if self.config.driver.value.startswith("mysql"):
            # MySQL-specific configuration with configurable charset
            connect_args.update(
                {
                    "charset": self.config.charset,  # UTF8MB4 for full Unicode support
                    "autocommit": False,
                }
            )

            # Add collation if specified
            if self.config.collation:
                connect_args["collation"] = self.config.collation

            # Add isolation level if specified
            if self.config.isolation_level:
                connect_args["isolation_level"] = self.config.isolation_level

        return connect_args

    def _create_engine(self) -> Engine:
        """Create SQLAlchemy engine based on configuration."""
        if self.config is None:
            raise ValueError("Database configuration is required to create engine")

        database_url = self.config.database_url.get_secret_value()
        pool_config = self._get_pool_config()
        connect_args = self._get_connect_args()

        # Engine configuration
        engine_kwargs = {
            "echo": self.config.echo,
            **pool_config,
        }

        if not self.config.driver.value.startswith("sqlite"):
            engine_kwargs["connect_args"] = connect_args

        logger.info(
            f"Creating SQLAlchemy engine for {self.config.driver.value} "
            f"with pool_size={pool_config.get('pool_size', 'N/A')}"
        )

        engine = create_engine(database_url, **engine_kwargs)

        # Register event listeners for connection management
        self._register_engine_events(engine)

        return engine

    def _create_async_engine(self) -> AsyncEngine:
        """Create async SQLAlchemy engine based on configuration."""
        if self.config is None:
            raise ValueError(
                "Database configuration is required to create async engine"
            )

        # Get async database URL
        async_url = self.config.async_database_url
        if async_url is None:
            raise ValueError("Async database URL not available for this driver")

        database_url = async_url.get_secret_value()
        pool_config = self._get_pool_config(is_async=True)
        connect_args = self._get_connect_args()

        # Async engine configuration
        engine_kwargs = {
            "echo": self.config.echo,
            **pool_config,
        }

        if not self.config.driver.value.startswith("sqlite"):
            engine_kwargs["connect_args"] = connect_args

        logger.info(f"Creating async SQLAlchemy engine for {self.config.driver.value}")

        engine = create_async_engine(database_url, **engine_kwargs)
        return engine

    def _register_engine_events(self, engine: Engine) -> None:
        """Register SQLAlchemy engine event listeners."""

        # Only register events on real engines that support them
        # Mock engines (used in tests) don't support event registration
        if not hasattr(engine, "dispatch") or hasattr(engine, "_mock_name"):
            return

        @event.listens_for(engine, "connect")
        def set_sqlite_pragma(dbapi_connection: Any, connection_record: Any) -> None:
            """Set SQLite pragmas for better performance."""
            if self.config and self.config.driver.value.startswith("sqlite"):
                cursor = dbapi_connection.cursor()
                cursor.execute("PRAGMA foreign_keys=ON")
                cursor.execute("PRAGMA journal_mode=WAL")
                cursor.execute("PRAGMA synchronous=NORMAL")
                cursor.execute("PRAGMA cache_size=10000")
                cursor.execute("PRAGMA temp_store=memory")
                cursor.close()

        @event.listens_for(engine, "connect")
        def set_mysql_charset(dbapi_connection: Any, connection_record: Any) -> None:
            """Set MySQL charset for UTF8MB4 support."""
            if self.config and self.config.driver.value.startswith("mysql"):
                cursor = dbapi_connection.cursor()
                try:
                    # Set charset with configurable values
                    charset_stmt = f"SET NAMES {self.config.charset}"
                    if self.config.collation:
                        charset_stmt += f" COLLATE {self.config.collation}"
                    cursor.execute(charset_stmt)

                    # Set character set
                    cursor.execute(f"SET CHARACTER SET {self.config.charset}")

                    # Set autocommit if configured
                    if self.config.autocommit:
                        cursor.execute("SET autocommit=1")

                except Exception as e:
                    logger.warning(f"Failed to set MySQL charset: {e}")
                finally:
                    cursor.close()

        # Only register events on real engines that support them
        # Mock engines (used in tests) don't support event registration
        if hasattr(engine, "dispatch") and not hasattr(engine, "_mock_name"):

            @event.listens_for(engine, "before_cursor_execute")
            def receive_before_cursor_execute(
                conn: Any,
                cursor: Any,
                statement: str,
                parameters: Any,
                context: Any,
                executemany: bool,
            ) -> None:
                """Log queries if in development mode."""
                if (
                    self.config
                    and self.config.echo
                    and self.config.environment.value == "development"
                ):
                    logger.debug(f"SQL: {statement}")
                    if parameters:
                        logger.debug(f"Parameters: {parameters}")

            @event.listens_for(engine, "checkout")
            def receive_checkout(
                dbapi_connection: Any, connection_record: Any, connection_proxy: Any
            ) -> None:
                """Log connection checkouts in development mode."""
                if self.config and self.config.environment.value == "development":
                    logger.debug("New database connection checked out")

            @event.listens_for(engine, "checkin")
            def receive_checkin(dbapi_connection: Any, connection_record: Any) -> None:
                """Log connection checkins in development mode."""
                if self.config and self.config.environment.value == "development":
                    logger.debug("Database connection checked in")

    @property
    def engine(self) -> Engine:
        """Get or create SQLAlchemy engine."""
        if self.config is None:
            raise ValueError("Database configuration is required")
        if self._engine is None:
            self._engine = self._create_engine()
        return self._engine

    @property
    def async_engine(self) -> AsyncEngine:
        """Get or create async SQLAlchemy engine."""
        if self.config is None:
            raise ValueError("Database configuration is required")
        if self._async_engine is None:
            self._async_engine = self._create_async_engine()
        return self._async_engine

    @property
    def session_factory(self) -> sessionmaker[Any]:
        """Get or create session factory."""
        if self.config is None:
            raise ValueError("Database configuration is required")
        if self._session_factory is None:
            self._session_factory = sessionmaker(
                bind=self.engine,
                autocommit=False,
                autoflush=False,
                expire_on_commit=False,
            )
        return self._session_factory

    @property
    def async_session_factory(self) -> async_sessionmaker[Any]:
        """Get or create async session factory."""
        if self.config is None:
            raise ValueError("Database configuration is required")
        if self._async_session_factory is None:
            self._async_session_factory = async_sessionmaker(
                bind=self.async_engine, class_=AsyncSession, expire_on_commit=False
            )
        return self._async_session_factory

    def create_session(self) -> Session:
        """Create a new database session."""
        return self.session_factory()  # type: ignore[no-any-return]

    def create_async_session(self) -> AsyncSession:
        """Create a new async database session."""
        return self.async_session_factory()  # type: ignore[no-any-return]

    def close_all_sessions(self) -> None:
        """Close all database sessions."""
        if self._session_factory:
            self._session_factory.close_all()
        if self._async_session_factory:
            # Note: AsyncSessionManager handles async sessions differently
            pass

    def dispose_engine(self) -> None:
        """Dispose the database engines."""
        if self._engine:
            self._engine.dispose()
            self._engine = None
        if self._async_engine:
            self._async_engine.sync_engine.dispose()
            self._async_engine = None

    def health_check(self) -> bool:
        """Perform health check on database connectivity.

        Executes a simple query against the database to verify connectivity and
        responsiveness. This synchronous health check returns immediately with
        True if the database is accessible or raises an exception if unavailable.
        Useful for liveness probes in Kubernetes or application startup validation.

        Returns:
            bool: True if database health check succeeds.

        Raises:
            Exception: If database is unreachable, authentication fails, or
                the database server is unavailable.

        Note:
            The health check executes a minimal query (SELECT 1) to verify
            connectivity without significant overhead. For production systems,
            consider timeout configuration and retry logic when using this
            method in health check endpoints.

        Example:
            >>> factory = SessionFactory()
            >>> try:
            ...     if factory.health_check():
            ...         print("Database is healthy")
            ... except Exception as e:
            ...     print(f"Database health check failed: {e}")
        """
        try:
            with self.create_session() as session:
                session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
            return False

    async def async_health_check(self) -> bool:
        """Perform an async health check on the database connection."""
        try:
            async with self.create_async_session() as session:
                await session.execute(text("SELECT 1"))
                return True
        except Exception as e:
            logger.error(f"Async database health check failed: {e}")
            return False

    def get_engine_info(self) -> dict[str, Any]:
        """Get information about the engine configuration."""
        if self.config is None:
            return {}

        pool_config = self._get_pool_config()
        connect_args = self._get_connect_args()

        return {
            "driver": self.config.driver.value,
            "database_url": self.config.database_url.get_secret_value()[:50]
            + "...",  # Truncated for security
            "environment": self.config.environment.value,
            "echo": self.config.echo,
            "pool_config": pool_config,
            "connect_args": connect_args,
        }

    def get_pool_status(self) -> dict[str, Any]:
        """Get current pool status information."""
        if self._engine is None:
            return {"status": "Not initialized"}

        pool = self._engine.pool
        if pool is None:
            return {"status": "No pooling (SQLite)"}

        # Handle different pool types
        if hasattr(pool, "size"):  # QueuePool and similar
            return {
                "status": "Active",
                "size": pool.size(),
                "checked_in": pool.checkedout,  # type: ignore[attr-defined]
                "checked_out": pool.checkedout,  # type: ignore[attr-defined]
                "overflow": pool.overflow,  # type: ignore[attr-defined]
            }
        else:  # StaticPool (SQLite) and others
            return {
                "status": "StaticPool (SQLite)",
                "pool_type": pool.__class__.__name__,
            }


# Global session factory instance will be initialized lazily
session_factory: SessionFactory | None = None


def get_session_factory() -> SessionFactory:
    """Get or create global session factory instance."""
    global session_factory
    if session_factory is None:
        session_factory = SessionFactory()
    return session_factory


def reset_global_session_factory() -> None:
    """Reset the global session factory instance.

    This function should be called in test teardown to ensure test isolation.
    """
    global session_factory
    if session_factory is not None:
        # Clean up any cached engines
        if session_factory._engine is not None:
            session_factory._engine.dispose()
            session_factory._engine = None
        if session_factory._async_engine is not None:
            session_factory._async_engine.sync_engine.dispose()
            session_factory._async_engine = None
        session_factory._session_factory = None
        session_factory._async_session_factory = None
        session_factory = None


# Helper functions for convenient access


def engine_from_config(config: DatabaseConfig) -> Engine:
    """Create SQLAlchemy engine from database configuration.

    Args:
        config: Database configuration object

    Returns:
        Configured SQLAlchemy engine
    """
    factory = SessionFactory(config)
    return factory.engine


def async_engine_from_config(config: DatabaseConfig) -> AsyncEngine:
    """Create async SQLAlchemy engine from database configuration.

    Args:
        config: Database configuration object

    Returns:
        Configured async SQLAlchemy engine
    """
    factory = SessionFactory(config)
    return factory.async_engine


def get_session(config: DatabaseConfig | None = None) -> Session:
    """Get a database session using global or provided configuration.

    Args:
        config: Optional database configuration. If not provided, uses global factory.

    Returns:
        Database session
    """
    if config is None:
        factory = get_session_factory()
        return factory.create_session()
    else:
        factory = SessionFactory(config)
        return factory.create_session()


def get_async_session(config: DatabaseConfig | None = None) -> AsyncSession:
    """Get an async database session using global or provided configuration.

    Args:
        config: Optional database configuration. If not provided, uses global factory.

    Returns:
        Async database session
    """
    if config is None:
        factory = get_session_factory()
        return factory.create_async_session()
    else:
        factory = SessionFactory(config)
        return factory.create_async_session()


def create_session_factory_with_config(config: DatabaseConfig) -> SessionFactory:
    """Create a new SessionFactory instance with specific configuration.

    Args:
        config: Database configuration

    Returns:
        Configured SessionFactory instance
    """
    return SessionFactory(config)


def health_check_from_config(config: DatabaseConfig) -> bool:
    """Perform health check using provided configuration.

    Args:
        config: Database configuration

    Returns:
        True if health check passes, False otherwise
    """
    factory = SessionFactory(config)
    return factory.health_check()


async def async_health_check_from_config(config: DatabaseConfig) -> bool:
    """Perform async health check using provided configuration.

    Args:
        config: Database configuration

    Returns:
        True if health check passes, False otherwise
    """
    factory = SessionFactory(config)
    return await factory.async_health_check()


def get_engine_info_from_config(config: DatabaseConfig) -> dict[str, Any]:
    """Get engine information using provided configuration.

    Args:
        config: Database configuration

    Returns:
        Dictionary containing engine configuration information
    """
    factory = SessionFactory(config)
    return factory.get_engine_info()


def get_pool_status_from_config(config: DatabaseConfig) -> dict[str, Any]:
    """Get pool status using provided configuration.

    Args:
        config: Database configuration

    Returns:
        Dictionary containing current pool status
    """
    factory = SessionFactory(config)
    return factory.get_pool_status()


# Context managers for session management


@contextmanager
def get_session_context(
    config: DatabaseConfig | None = None,
) -> Generator[Session, None, None]:
    """Context manager for database session with automatic cleanup.

    Args:
        config: Optional database configuration

    Yields:
        Database session
    """
    if config is None:
        factory = get_session_factory()
        session = factory.create_session()
    else:
        factory = SessionFactory(config)
        session = factory.create_session()

    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


@asynccontextmanager
async def get_async_session_context(
    config: DatabaseConfig | None = None,
) -> AsyncGenerator[AsyncSession, None]:
    """Async context manager for database session with automatic cleanup.

    Args:
        config: Optional database configuration

    Yields:
        Async database session
    """
    if config is None:
        factory = get_session_factory()
        session = factory.create_async_session()
    else:
        factory = SessionFactory(config)
        session = factory.create_async_session()

    try:
        yield session
        await session.commit()
    except Exception:
        await session.rollback()
        raise
    finally:
        await session.close()


# Database connection testing utilities


def check_database_connection(config: DatabaseConfig) -> bool:
    """Test database connection with simple query.

    Args:
        config: Database configuration

    Returns:
        True if connection successful, False otherwise
    """
    try:
        with get_session_context(config) as session:
            session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Database connection test failed: {e}")
        return False


async def check_async_database_connection(config: DatabaseConfig) -> bool:
    """Test async database connection with simple query.

    Args:
        config: Database configuration

    Returns:
        True if connection successful, False otherwise
    """
    try:
        async with get_async_session_context(config) as session:
            await session.execute(text("SELECT 1"))
            return True
    except Exception as e:
        logger.error(f"Async database connection test failed: {e}")
        return False
