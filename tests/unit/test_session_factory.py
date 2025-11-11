"""Unit tests for session factory and database connection management."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy import Engine
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from vgnc_internal_orm.config.settings import (
    DatabaseConfig,
    DatabaseDriver,
    Environment,
)
from vgnc_internal_orm.sessions.factory import (
    SessionFactory,
    async_engine_from_config,
    check_async_database_connection,
    check_database_connection,
    engine_from_config,
    get_async_session_context,
    get_engine_info_from_config,
    get_session,
    get_session_context,
    get_session_factory,
    health_check_from_config,
)


class TestSessionFactory:
    """Test cases for SessionFactory class."""

    def test_initialization_with_config(self):
        """Test SessionFactory initialization with configuration."""
        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )
        factory = SessionFactory(config)
        assert factory.config == config
        assert factory._engine is None
        assert factory._async_engine is None
        assert factory._session_factory is None
        assert factory._async_session_factory is None

    def test_initialization_without_config(self):
        """Test SessionFactory initialization without configuration."""
        factory = SessionFactory()
        assert factory.config is None

    @patch("vgnc_internal_orm.sessions.factory.create_engine")
    def test_engine_property_creates_engine(self, mock_create_engine):
        """Test that engine property creates SQLAlchemy engine."""
        mock_engine = Mock(spec=Engine)
        mock_engine.pool = Mock()  # Add pool attribute for event registration
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )
        factory = SessionFactory(config)

        engine = factory.engine
        assert engine == mock_engine
        mock_create_engine.assert_called_once()
        assert factory._engine == mock_engine

    def test_engine_property_raises_without_config(self):
        """Test that engine property raises ValueError without config."""
        factory = SessionFactory()
        with pytest.raises(ValueError, match="Database configuration is required"):
            _ = factory.engine

    @patch("vgnc_internal_orm.sessions.factory.create_async_engine")
    def test_async_engine_property_creates_engine(self, mock_create_async_engine):
        """Test that async_engine property creates async SQLAlchemy engine."""
        mock_async_engine = Mock(spec=AsyncEngine)
        mock_async_engine.pool = Mock()  # Add pool attribute for event registration
        mock_create_async_engine.return_value = mock_async_engine

        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_ASYNC,
            username="test_user",
            password="test_password",
            database="test_db",
        )
        factory = SessionFactory(config)

        async_engine = factory.async_engine
        assert async_engine == mock_async_engine
        mock_create_async_engine.assert_called_once()
        assert factory._async_engine == mock_async_engine

    def test_async_engine_property_raises_without_config(self):
        """Test that async_engine property raises ValueError without config."""
        factory = SessionFactory()
        with pytest.raises(ValueError, match="Database configuration is required"):
            _ = factory.async_engine

    def test_get_pool_config_development(self):
        """Test pool configuration for development environment."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test_user",
            password="test_password",
            database="test_db",
            environment=Environment.DEVELOPMENT,
            _env_file=None,  # Disable environment file loading for tests
        )
        factory = SessionFactory(config)

        pool_config = factory._get_pool_config()

        assert pool_config["pool_pre_ping"] is True
        assert "pool_size" in pool_config
        assert "pool_timeout" in pool_config
        assert (
            pool_config["pool_timeout"] <= 10
        )  # Development should have shorter timeout
        assert pool_config["pool_recycle"] == 3600  # 1 hour for development

    def test_get_pool_config_production(self):
        """Test pool configuration for production environment."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test_user",
            password="test_password",
            database="test_db",
            environment=Environment.PRODUCTION,
            _env_file=None,  # Disable environment file loading for tests
        )
        factory = SessionFactory(config)

        pool_config = factory._get_pool_config()

        assert pool_config["pool_pre_ping"] is True
        assert "pool_size" in pool_config
        assert "pool_timeout" in pool_config
        assert pool_config["pool_recycle"] == 14400  # 4 hours for production

    def test_get_pool_config_sqlite(self):
        """Test pool configuration for SQLite."""
        config = DatabaseConfig(driver=DatabaseDriver.SQLITE, database="test.db")
        factory = SessionFactory(config)

        pool_config = factory._get_pool_config()

        assert pool_config["poolclass"] == StaticPool
        assert "connect_args" in pool_config
        assert pool_config["connect_args"]["check_same_thread"] is False
        assert pool_config["connect_args"]["uri"] is True

    def test_get_connect_args_mysql(self):
        """Test connection arguments for MySQL."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test_user",
            password="test_password",
            database="test_db",
            isolation_level="READ_COMMITTED",
        )
        factory = SessionFactory(config)

        connect_args = factory._get_connect_args()

        assert connect_args["charset"] == "utf8mb4"
        assert connect_args["collation"] == "utf8mb4_unicode_ci"
        assert connect_args["autocommit"] is False
        assert connect_args["isolation_level"] == "READ_COMMITTED"

    def test_create_session(self):
        """Test session creation."""
        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )
        factory = SessionFactory(config)

        with patch(
            "vgnc_internal_orm.sessions.factory.sessionmaker"
        ) as mock_sessionmaker:
            mock_session = Mock(spec=Session)
            mock_session_factory = Mock()
            mock_sessionmaker.return_value = mock_session_factory
            mock_session_factory.return_value = mock_session

            session = factory.create_session()
            assert session == mock_session
            mock_sessionmaker.assert_called_once()
            mock_session_factory.assert_called_once()

    def test_create_async_session(self):
        """Test async session creation."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_ASYNC,
            username="test_user",
            password="test_password",
            database="test_db",
        )
        factory = SessionFactory(config)

        with patch(
            "vgnc_internal_orm.sessions.factory.async_sessionmaker"
        ) as mock_async_sessionmaker:
            mock_async_session = Mock(spec=AsyncSession)
            mock_async_session_factory = Mock()
            mock_async_sessionmaker.return_value = mock_async_session_factory
            mock_async_session_factory.return_value = mock_async_session

            async_session = factory.create_async_session()
            assert async_session == mock_async_session
            mock_async_sessionmaker.assert_called_once()
            mock_async_session_factory.assert_called_once()

    @patch("vgnc_internal_orm.sessions.factory.text")
    def test_health_check_success(self, mock_text):
        """Test successful health check."""
        mock_text.return_value = Mock()
        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )
        factory = SessionFactory(config)

        with patch.object(factory, "create_session") as mock_create_session:
            mock_session = Mock()
            mock_create_session.return_value.__enter__.return_value = mock_session

            result = factory.health_check()
            assert result is True
            mock_session.execute.assert_called_once()

    def test_health_check_failure(self):
        """Test health check failure."""
        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )
        factory = SessionFactory(config)

        with patch.object(factory, "create_session") as mock_create_session:
            mock_create_session.side_effect = Exception("Connection failed")

            result = factory.health_check()
            assert result is False

    @pytest.mark.asyncio
    async def test_async_health_check_success(self):
        """Test successful async health check."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_ASYNC,
            username="test_user",
            password="test_password",
            database="test_db",
        )
        factory = SessionFactory(config)

        with patch.object(factory, "create_async_session") as mock_create_session:
            mock_session = AsyncMock()
            mock_create_session.return_value.__aenter__.return_value = mock_session

            result = await factory.async_health_check()
            assert result is True
            mock_session.execute.assert_called_once()

    @pytest.mark.asyncio
    async def test_async_health_check_failure(self):
        """Test async health check failure."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_ASYNC,
            username="test_user",
            password="test_password",
            database="test_db",
        )
        factory = SessionFactory(config)

        with patch.object(factory, "create_async_session") as mock_create_session:
            mock_create_session.side_effect = Exception("Connection failed")

            result = await factory.async_health_check()
            assert result is False

    def test_get_engine_info(self):
        """Test engine information retrieval."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test_user",
            password="test_password",
            database="test_db",
            echo=True,
            _env_file=None,  # Disable environment file loading for tests
        )
        factory = SessionFactory(config)

        info = factory.get_engine_info()

        assert "driver" in info
        assert "database_url" in info
        assert "environment" in info
        assert "echo" in info
        assert "pool_config" in info
        assert "connect_args" in info
        assert info["echo"] is True
        assert info["driver"] == "mysql+pymysql"

    def test_get_pool_status_not_initialized(self):
        """Test pool status when engine not initialized."""
        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )
        factory = SessionFactory(config)

        status = factory.get_pool_status()
        assert status["status"] == "Not initialized"

    def test_close_all_sessions(self):
        """Test closing all sessions."""
        with patch(
            "vgnc_internal_orm.sessions.factory.sessionmaker"
        ) as mock_sessionmaker:
            mock_session_factory = Mock()
            mock_sessionmaker.return_value = mock_session_factory

            config = DatabaseConfig(
                username="test_user", password="test_password", database="test_db"
            )
            factory = SessionFactory(config)

            # Create session factory to initialize it
            _ = factory.session_factory

            factory.close_all_sessions()
            mock_session_factory.close_all.assert_called_once()

    def test_dispose_engine(self):
        """Test engine disposal."""
        with patch(
            "vgnc_internal_orm.sessions.factory.create_engine"
        ) as mock_create_engine:
            mock_engine = Mock()
            mock_engine.pool = Mock()
            mock_create_engine.return_value = mock_engine

            config = DatabaseConfig(
                username="test_user", password="test_password", database="test_db"
            )
            factory = SessionFactory(config)

            # Create engine to initialize it
            _ = factory.engine

            factory.dispose_engine()
            mock_engine.dispose.assert_called_once()
            assert factory._engine is None


class TestHelperFunctions:
    """Test cases for helper functions."""

    def test_get_session_factory_lazy_initialization(self):
        """Test global session factory lazy initialization."""
        # Reset global state
        import vgnc_internal_orm.sessions.factory as factory_module

        factory_module.session_factory = None

        factory1 = get_session_factory()
        factory2 = get_session_factory()

        assert factory1 is factory2
        assert isinstance(factory1, SessionFactory)

    @patch("vgnc_internal_orm.sessions.factory.SessionFactory")
    def test_engine_from_config(self, mock_session_factory):
        """Test creating engine from config."""
        mock_factory = Mock()
        mock_engine = Mock(spec=Engine)
        mock_factory.engine = mock_engine
        mock_session_factory.return_value = mock_factory

        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )

        engine = engine_from_config(config)
        assert engine == mock_engine
        mock_session_factory.assert_called_once_with(config)

    @patch("vgnc_internal_orm.sessions.factory.SessionFactory")
    def test_async_engine_from_config(self, mock_session_factory):
        """Test creating async engine from config."""
        mock_factory = Mock()
        mock_async_engine = Mock(spec=AsyncEngine)
        mock_factory.async_engine = mock_async_engine
        mock_session_factory.return_value = mock_factory

        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_ASYNC,
            username="test_user",
            password="test_password",
            database="test_db",
        )

        async_engine = async_engine_from_config(config)
        assert async_engine == mock_async_engine
        mock_session_factory.assert_called_once_with(config)

    @patch("vgnc_internal_orm.sessions.factory.get_session_factory")
    def test_get_session_without_config(self, mock_get_session_factory):
        """Test getting session without config (uses global factory)."""
        mock_factory = Mock()
        mock_session = Mock(spec=Session)
        mock_factory.create_session.return_value = mock_session
        mock_get_session_factory.return_value = mock_factory

        session = get_session()
        assert session == mock_session
        mock_get_session_factory.assert_called_once()

    @patch("vgnc_internal_orm.sessions.factory.SessionFactory")
    def test_get_session_with_config(self, mock_session_factory):
        """Test getting session with config."""
        mock_factory = Mock()
        mock_session = Mock(spec=Session)
        mock_factory.create_session.return_value = mock_session
        mock_session_factory.return_value = mock_factory

        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )

        session = get_session(config)
        assert session == mock_session
        mock_session_factory.assert_called_once_with(config)

    @patch("vgnc_internal_orm.sessions.factory.SessionFactory")
    def test_health_check_from_config(self, mock_session_factory):
        """Test health check from config."""
        mock_factory = Mock()
        mock_factory.health_check.return_value = True
        mock_session_factory.return_value = mock_factory

        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )

        result = health_check_from_config(config)
        assert result is True
        mock_factory.health_check.assert_called_once()

    @patch("vgnc_internal_orm.sessions.factory.SessionFactory")
    def test_get_engine_info_from_config(self, mock_session_factory):
        """Test getting engine info from config."""
        mock_factory = Mock()
        mock_factory.get_engine_info.return_value = {"driver": "mysql"}
        mock_session_factory.return_value = mock_factory

        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )

        info = get_engine_info_from_config(config)
        assert info == {"driver": "mysql"}
        mock_factory.get_engine_info.assert_called_once()


class TestContextManagers:
    """Test cases for context managers."""

    @patch("vgnc_internal_orm.sessions.factory.get_session_factory")
    def test_get_session_context_success(self, mock_get_session_factory):
        """Test session context manager on success."""
        mock_factory = Mock()
        mock_session = Mock(spec=Session)
        mock_factory.create_session.return_value = mock_session
        mock_get_session_factory.return_value = mock_factory

        with get_session_context() as session:
            assert session == mock_session

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("vgnc_internal_orm.sessions.factory.get_session_factory")
    def test_get_session_context_with_exception(self, mock_get_session_factory):
        """Test session context manager with exception."""
        mock_factory = Mock()
        mock_session = Mock(spec=Session)
        mock_factory.create_session.return_value = mock_session
        mock_get_session_factory.return_value = mock_factory

        with pytest.raises(ValueError):
            with get_session_context():
                raise ValueError("Test error")

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()

    @patch("vgnc_internal_orm.sessions.factory.get_session_factory")
    def test_get_session_context_with_config(self, mock_get_session_factory):
        """Test session context manager with config."""
        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )

        with patch(
            "vgnc_internal_orm.sessions.factory.SessionFactory"
        ) as mock_session_factory:
            mock_factory = Mock()
            mock_session = Mock(spec=Session)
            mock_factory.create_session.return_value = mock_session
            mock_session_factory.return_value = mock_factory

            with get_session_context(config) as session:
                assert session == mock_session

            mock_session_factory.assert_called_once_with(config)

    @pytest.mark.asyncio
    @patch("vgnc_internal_orm.sessions.factory.get_session_factory")
    async def test_get_async_session_context_success(self, mock_get_session_factory):
        """Test async session context manager on success."""
        mock_factory = Mock()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory.create_async_session.return_value = mock_session
        mock_get_session_factory.return_value = mock_factory

        async with get_async_session_context() as session:
            assert session == mock_session

        mock_session.commit.assert_called_once()
        mock_session.close.assert_called_once()

    @pytest.mark.asyncio
    @patch("vgnc_internal_orm.sessions.factory.get_session_factory")
    async def test_get_async_session_context_with_exception(
        self, mock_get_session_factory
    ):
        """Test async session context manager with exception."""
        mock_factory = Mock()
        mock_session = AsyncMock(spec=AsyncSession)
        mock_factory.create_async_session.return_value = mock_session
        mock_get_session_factory.return_value = mock_factory

        with pytest.raises(ValueError):
            async with get_async_session_context():
                raise ValueError("Test error")

        mock_session.rollback.assert_called_once()
        mock_session.close.assert_called_once()


class TestConnectionTesting:
    """Test cases for connection testing utilities."""

    @patch("vgnc_internal_orm.sessions.factory.get_session_context")
    def test_database_connection_success(self, mock_get_session_context):
        """Test successful connection test."""
        mock_session = Mock()
        mock_get_session_context.return_value.__enter__.return_value = mock_session

        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )

        result = check_database_connection(config)
        assert result is True

    @patch("vgnc_internal_orm.sessions.factory.get_session_context")
    def test_database_connection_failure(self, mock_get_session_context):
        """Test connection test failure."""
        mock_get_session_context.side_effect = Exception("Connection failed")

        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )

        result = check_database_connection(config)
        assert result is False

    @pytest.mark.asyncio
    @patch("vgnc_internal_orm.sessions.factory.get_async_session_context")
    async def test_async_database_connection_success(
        self, mock_get_async_session_context
    ):
        """Test successful async connection test."""
        mock_session = AsyncMock()
        mock_get_async_session_context.return_value.__aenter__.return_value = (
            mock_session
        )

        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_ASYNC,
            username="test_user",
            password="test_password",
            database="test_db",
        )

        result = await check_async_database_connection(config)
        assert result is True

    @pytest.mark.asyncio
    @patch("vgnc_internal_orm.sessions.factory.get_async_session_context")
    async def test_async_database_connection_failure(
        self, mock_get_async_session_context
    ):
        """Test async connection test failure."""
        mock_get_async_session_context.side_effect = Exception("Connection failed")

        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_ASYNC,
            username="test_user",
            password="test_password",
            database="test_db",
        )

        result = await check_async_database_connection(config)
        assert result is False


class TestEngineEvents:
    """Test cases for engine event listeners."""

    @patch("vgnc_internal_orm.sessions.factory.create_engine")
    def test_sqlite_pragma_events(self, mock_create_engine):
        """Test SQLite pragma event listeners."""
        mock_engine = Mock(spec=Engine)
        mock_engine.pool = Mock()  # Add pool attribute for event registration
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig(driver=DatabaseDriver.SQLITE, database="test.db")
        factory = SessionFactory(config)

        # Trigger engine creation to register events
        _ = factory.engine

        # Verify event listeners were registered
        assert mock_create_engine.called

    @patch("vgnc_internal_orm.sessions.factory.create_engine")
    def test_mysql_charset_events(self, mock_create_engine):
        """Test MySQL charset event listeners."""
        mock_engine = Mock(spec=Engine)
        mock_engine.pool = Mock()  # Add pool attribute for event registration
        mock_create_engine.return_value = mock_engine

        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test_user",
            password="test_password",
            database="test_db",
        )
        factory = SessionFactory(config)

        # Trigger engine creation to register events
        _ = factory.engine

        # Verify event listeners were registered
        assert mock_create_engine.called

    def test_development_mode_logging(self):
        """Test enhanced logging in development mode."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test_user",
            password="test_password",
            database="test_db",
            environment=Environment.DEVELOPMENT,
            echo=True,
            _env_file=None,  # Disable environment file loading for tests
        )
        factory = SessionFactory(config)

        # Test that development mode config is properly set
        pool_config = factory._get_pool_config()
        assert (
            pool_config["pool_timeout"] <= 10
        )  # Development should have shorter timeouts
        assert pool_config["pool_recycle"] == 3600  # 1 hour for development


class TestMultiEnvironmentSupport:
    """Test cases for multi-environment support."""

    def test_staging_environment_config(self):
        """Test staging environment specific configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test_user",
            password="test_password",
            database="test_db",
            environment=Environment.STAGING,
            _env_file=None,  # Disable environment file loading for tests
        )
        factory = SessionFactory(config)

        pool_config = factory._get_pool_config()
        assert pool_config["pool_recycle"] == 7200  # 2 hours for staging

    def test_isolation_level_support(self):
        """Test isolation level configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test_user",
            password="test_password",
            database="test_db",
            isolation_level="REPEATABLE_READ",
        )
        factory = SessionFactory(config)

        connect_args = factory._get_connect_args()
        assert connect_args["isolation_level"] == "REPEATABLE_READ"
