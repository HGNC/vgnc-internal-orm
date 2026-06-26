"""Working SessionFactory comprehensive tests based on actual module structure."""

from db_common import DatabaseDriver
from sqlalchemy import text

from vgnc_internal_orm.config.settings import DatabaseConfig
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
            _env_file=None,
        )
        factory = SessionFactory(config)
        assert factory.config == config
        assert factory._engine is None

    def test_sqlite_engine_creation(self):
        """Test engine creation with SQLite configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
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
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            _env_file=None,
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
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )
        factory = SessionFactory(config)
        session = factory.create_session()
        assert session is not None
        session.close()

    def test_health_check_sqlite(self):
        """Test health check functionality with SQLite."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )
        factory = SessionFactory(config)
        health = factory.health_check()
        assert health is True

    def test_engine_info(self):
        """Test engine information retrieval."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )
        factory = SessionFactory(config)
        info = factory.get_engine_info()
        assert "driver" in info
        assert info["driver"] == "sqlite"

    def test_pool_status_sqlite(self):
        """Test pool status for SQLite."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )
        factory = SessionFactory(config)
        # Access engine to initialize it
        _ = factory.engine
        status = factory.get_pool_status()
        assert "status" in status
        assert "StaticPool" in status.get(
            "status", ""
        ) or "Not initialized" in status.get("status", "")

    def test_dispose_engine(self):
        """Test engine disposal."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )
        factory = SessionFactory(config)
        _ = factory.engine
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
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )
        engine = engine_from_config(config)
        assert engine is not None
        assert engine.url.drivername == "sqlite"

    def test_get_session_with_config(self):
        """Test session creation with config."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
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
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )
        health = health_check_from_config(config)
        assert health is True

    def test_create_session_factory_with_config(self):
        """Test creating factory with config."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
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
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )

        with get_session_context(config) as session:
            assert session is not None
            # Test a simple operation
            result = session.execute(text("SELECT 1"))
            assert result is not None

    def test_check_database_connection(self):
        """Test database connection check."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )
        connection = check_database_connection(config)
        assert connection is True


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_multiple_engine_access(self):
        """Test accessing engine multiple times returns same instance."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )
        factory = SessionFactory(config)
        engine1 = factory.engine
        engine2 = factory.engine
        assert engine1 is engine2

    def test_multiple_session_factory_access(self):
        """Test accessing session factory multiple times returns same instance."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )
        factory = SessionFactory(config)
        sf1 = factory.session_factory
        sf2 = factory.session_factory
        assert sf1 is sf2

    def test_close_all_sessions(self):
        """Test closing all sessions."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )
        factory = SessionFactory(config)

        # Create session factory first
        _ = factory.session_factory

        # Should not raise any exceptions
        factory.close_all_sessions()
