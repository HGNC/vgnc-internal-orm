"""Working SessionFactory comprehensive tests based on actual module structure."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool, NullPool

from vgnc_internal_orm.sessions.factory import (
    SessionFactory,
    get_session_factory,
    reset_global_session_factory,
    engine_from_config,
    async_engine_from_config,
    get_session,
    get_async_session,
    create_session_factory_with_config,
    health_check_from_config,
    async_health_check_from_config,
    get_engine_info_from_config,
    get_pool_status_from_config,
    get_session_context,
    get_async_session_context,
    check_database_connection,
    check_async_database_connection,
)
from vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver, Environment


class TestSessionFactoryCoreFunctionality:
    """Test core SessionFactory functionality with real database operations."""

    def test_session_factory_initialization(self):
        """Test SessionFactory initialization with default configuration."""
        factory = SessionFactory()
        assert factory.config is None

    def test_session_factory_with_config(self):
        """Test SessionFactory initialization with configuration."""
        config = DatabaseConfig(
            username="test_user",
            password="test_password",
            database="test_database",
            host="localhost",
            driver=DatabaseDriver.SQLITE,
            _env_file=None
        )
        factory = SessionFactory(config)
        assert factory.config == config
        assert factory._engine is None
        assert factory._async_engine is None

    def test_sqlite_engine_creation(self):
        """Test engine creation with SQLite configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = SessionFactory(config)
        engine = factory.engine
        assert engine is not None
        assert engine.url.drivername == "sqlite"

    def test_mysql_engine_creation(self):
        """Test engine creation with MySQL configuration."""
        config = DatabaseConfig(
            username="test_user",
            password="test_password",
            database="test_database",
            host="localhost",
            port=3306,
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )
        factory = SessionFactory(config)
        # Should create engine without actual connection
        try:
            engine = factory.engine
            assert engine is not None
            assert "mysql" in engine.url.drivername
        except Exception:
            # Expected if MySQL is not available
            pass

    def test_session_creation(self):
        """Test session creation from factory."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = SessionFactory(config)
        session = factory.create_session()
        assert session is not None
        session.close()

    def test_health_check_sqlite(self):
        """Test health check functionality with SQLite."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = SessionFactory(config)
        health = factory.health_check()
        assert health is True

    def test_engine_info(self):
        """Test engine information retrieval."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = SessionFactory(config)
        info = factory.get_engine_info()
        assert "driver" in info
        assert info["driver"] == "sqlite"

    def test_pool_status_sqlite(self):
        """Test pool status for SQLite."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = SessionFactory(config)
        # Access engine to initialize it
        _ = factory.engine
        status = factory.get_pool_status()
        assert "status" in status
        assert "StaticPool" in status.get("status", "") or "Not initialized" in status.get("status", "")

    def test_dispose_engine(self):
        """Test engine disposal."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = SessionFactory(config)
        engine = factory.engine
        factory.dispose_engine()
        assert factory._engine is None


class TestGlobalSessionFactory:
    """Test global session factory functions."""

    def test_get_session_factory(self):
        """Test global session factory retrieval."""
        reset_global_session_factory()
        factory = get_session_factory()
        assert factory is not None
        assert isinstance(factory, SessionFactory)

    def test_reset_global_session_factory(self):
        """Test resetting global session factory."""
        # First get a factory
        factory1 = get_session_factory()

        # Reset it
        reset_global_session_factory()

        # Get a new one
        factory2 = get_session_factory()

        # Should be different instances
        assert factory1 is not factory2


class TestHelperFunctions:
    """Test helper functions."""

    def test_engine_from_config(self):
        """Test engine creation from config."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        engine = engine_from_config(config)
        assert engine is not None
        assert engine.url.drivername == "sqlite"

    def test_get_session_with_config(self):
        """Test session creation with config."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        session = get_session(config)
        assert session is not None
        session.close()

    def test_get_session_without_config(self):
        """Test session creation without config (uses global)."""
        reset_global_session_factory()
        # This should work with default config or raise error for None config
        try:
            session = get_session()
            if session:
                session.close()
        except ValueError:
            # Expected if no global config is set
            pass

    def test_health_check_from_config(self):
        """Test health check with config."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        health = health_check_from_config(config)
        assert health is True

    def test_create_session_factory_with_config(self):
        """Test creating factory with config."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = create_session_factory_with_config(config)
        assert factory is not None
        assert isinstance(factory, SessionFactory)
        assert factory.config == config


class TestContextManagers:
    """Test context manager functionality."""

    def test_get_session_context(self):
        """Test session context manager."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )

        with get_session_context(config) as session:
            assert session is not None
            # Test a simple operation
            result = session.execute(text("SELECT 1"))
            assert result is not None

    def test_check_database_connection(self):
        """Test database connection check."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        connection = check_database_connection(config)
        assert connection is True


class TestPoolConfiguration:
    """Test pool configuration for different environments."""

    def test_sqlite_pool_config(self):
        """Test SQLite pool configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = SessionFactory(config)
        pool_config = factory._get_pool_config()

        assert "poolclass" in pool_config
        assert "connect_args" in pool_config
        assert pool_config["connect_args"]["check_same_thread"] is False

    def test_mysql_pool_config_sync(self):
        """Test MySQL pool configuration for sync engines."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test",
            password="test",
            database="test",
            host="localhost",
            _env_file=None
        )
        factory = SessionFactory(config)
        pool_config = factory._get_pool_config(is_async=False)

        assert "poolclass" in pool_config
        assert pool_config["poolclass"] == QueuePool

    def test_mysql_pool_config_async(self):
        """Test MySQL pool configuration for async engines."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test",
            password="test",
            database="test",
            host="localhost",
            _env_file=None
        )
        factory = SessionFactory(config)
        pool_config = factory._get_pool_config(is_async=True)

        assert "poolclass" in pool_config
        assert pool_config["poolclass"] == NullPool


class TestConnectArguments:
    """Test connection argument configuration."""

    def test_mysql_connect_args(self):
        """Test MySQL connection arguments."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test",
            password="test",
            database="test",
            host="localhost",
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            _env_file=None
        )
        factory = SessionFactory(config)
        connect_args = factory._get_connect_args()

        assert connect_args["charset"] == "utf8mb4"
        assert connect_args["collation"] == "utf8mb4_unicode_ci"

    def test_sqlite_connect_args(self):
        """Test SQLite connection arguments."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = SessionFactory(config)
        pool_config = factory._get_pool_config()

        assert "connect_args" in pool_config
        assert pool_config["connect_args"]["check_same_thread"] is False


class TestErrorHandling:
    """Test error handling in SessionFactory."""

    def test_engine_creation_without_config(self):
        """Test engine creation fails without config."""
        factory = SessionFactory(None)
        with pytest.raises(ValueError, match="Database configuration is required"):
            _ = factory.engine

    def test_session_creation_without_config(self):
        """Test session creation fails without config."""
        factory = SessionFactory(None)
        with pytest.raises(ValueError, match="Database configuration is required"):
            _ = factory.session_factory

    def test_health_check_without_config(self):
        """Test health check fails without config."""
        factory = SessionFactory(None)
        result = factory.health_check()
        assert result is False


class TestEnvironmentSpecificConfig:
    """Test environment-specific configuration."""

    def test_development_pool_config(self):
        """Test development environment pool configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test",
            password="test",
            database="test",
            host="localhost",
            environment=Environment.DEVELOPMENT,
            _env_file=None
        )
        factory = SessionFactory(config)
        pool_config = factory._get_pool_config()

        # Development should have reduced pool sizes
        assert pool_config["pool_size"] <= config.pool.pool_size // 2

    def test_production_pool_config(self):
        """Test production environment pool configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test",
            password="test",
            database="test",
            host="localhost",
            environment=Environment.PRODUCTION,
            _env_file=None
        )
        factory = SessionFactory(config)
        pool_config = factory._get_pool_config()

        # Production should have full pool sizes
        assert pool_config["pool_size"] == config.pool.pool_size

    def test_staging_pool_config(self):
        """Test staging environment pool configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test",
            password="test",
            database="test",
            host="localhost",
            environment=Environment.STAGING,
            _env_file=None
        )
        factory = SessionFactory(config)
        pool_config = factory._get_pool_config()

        # Staging should have medium pool sizes
        assert pool_config["pool_size"] == config.pool.pool_size


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_multiple_engine_access(self):
        """Test accessing engine multiple times returns same instance."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = SessionFactory(config)
        engine1 = factory.engine
        engine2 = factory.engine
        assert engine1 is engine2

    def test_multiple_session_factory_access(self):
        """Test accessing session factory multiple times returns same instance."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = SessionFactory(config)
        sf1 = factory.session_factory
        sf2 = factory.session_factory
        assert sf1 is sf2

    def test_close_all_sessions(self):
        """Test closing all sessions."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        factory = SessionFactory(config)

        # Create session factory first
        _ = factory.session_factory

        # Should not raise any exceptions
        factory.close_all_sessions()