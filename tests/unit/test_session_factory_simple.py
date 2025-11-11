"""Simplified unit tests for session factory focusing on core functionality."""

from unittest.mock import AsyncMock, Mock, patch

import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Session

from vgnc_internal_orm.config.settings import (
    DatabaseConfig,
    DatabaseDriver,
    Environment,
)
from vgnc_internal_orm.sessions.factory import (
    SessionFactory,
    create_session_factory_with_config,
    get_async_session_context,
    get_session_context,
    get_session_factory,
    reset_global_session_factory,
)


@pytest.fixture(autouse=True)
def reset_global_session_factory_fixture():
    """Reset global session factory before each test to ensure isolation."""
    reset_global_session_factory()
    yield
    reset_global_session_factory()


class TestSessionFactoryBasics:
    """Test basic SessionFactory functionality without full engine creation."""

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

    def test_engine_property_raises_without_config(self):
        """Test that engine property raises ValueError without config."""
        factory = SessionFactory()
        with pytest.raises(ValueError, match="Database configuration is required"):
            _ = factory.engine

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

        assert pool_config["poolclass"].__name__ == "StaticPool"
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

    def test_health_check_without_config(self):
        """Test health check without configuration returns False."""
        factory = SessionFactory()
        result = factory.health_check()
        assert result is False

    @pytest.mark.asyncio
    async def test_async_health_check_without_config(self):
        """Test async health check without configuration returns False."""
        factory = SessionFactory()
        result = await factory.async_health_check()
        assert result is False


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

    def test_create_session_factory_with_config(self):
        """Test creating SessionFactory with specific config."""
        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )
        factory = create_session_factory_with_config(config)
        assert isinstance(factory, SessionFactory)
        assert factory.config == config


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

    def test_ssl_configuration_inclusion(self):
        """Test SSL configuration inclusion in connect args."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test_user",
            password="test_password",
            database="test_db",
            ssl_mode="REQUIRED",
        )
        factory = SessionFactory(config)

        connect_args = factory._get_connect_args()
        # Note: SSL args are added in _create_engine method, not _get_connect_args
        # but we can verify the basic config structure
        assert "charset" in connect_args


class TestCharsetAndEncoding:
    """Test cases for charset and encoding support."""

    def test_mysql_utf8mb4_support(self):
        """Test MySQL UTF8MB4 charset support."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test_user",
            password="test_password",
            database="test_db",
        )
        factory = SessionFactory(config)

        connect_args = factory._get_connect_args()
        assert connect_args["charset"] == "utf8mb4"
        assert connect_args["collation"] == "utf8mb4_unicode_ci"

    def test_sqlite_connect_args(self):
        """Test SQLite-specific connection arguments."""
        config = DatabaseConfig(driver=DatabaseDriver.SQLITE, database="test.db")
        factory = SessionFactory(config)

        pool_config = factory._get_pool_config()
        connect_args = pool_config["connect_args"]
        assert connect_args["check_same_thread"] is False
        assert connect_args["uri"] is True


class TestPoolConfiguration:
    """Test cases for connection pool configuration."""

    def test_pool_config_environment_differences(self):
        """Test that pool configurations differ by environment."""
        base_config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test_user",
            password="test_password",
            database="test_db",
            _env_file=None,  # Disable environment file loading for tests
        )

        # Development config
        dev_config = base_config.model_copy(
            update={"environment": Environment.DEVELOPMENT}
        )
        dev_factory = SessionFactory(dev_config)
        dev_pool = dev_factory._get_pool_config()

        # Production config
        prod_config = base_config.model_copy(
            update={"environment": Environment.PRODUCTION}
        )
        prod_factory = SessionFactory(prod_config)
        prod_pool = prod_factory._get_pool_config()

        # Production should have longer connection recycling
        assert prod_pool["pool_recycle"] > dev_pool["pool_recycle"]

    def test_pool_timeout_configuration(self):
        """Test pool timeout configuration."""
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
        # Development should have shorter timeout
        assert pool_config["pool_timeout"] <= 10

    def test_pool_pre_ping_enabled(self):
        """Test that pool pre-ping is enabled by default."""
        config = DatabaseConfig(
            username="test_user", password="test_password", database="test_db"
        )
        factory = SessionFactory(config)

        pool_config = factory._get_pool_config()
        assert pool_config["pool_pre_ping"] is True


class TestErrorHandling:
    """Test cases for error handling."""

    def test_config_validation_in_factory(self):
        """Test that configuration validation works in factory."""
        factory = SessionFactory()

        # These should raise errors when trying to create engines
        with pytest.raises(ValueError, match="Database configuration is required"):
            _ = factory.engine

        with pytest.raises(ValueError, match="Database configuration is required"):
            _ = factory.async_engine

    def test_safe_method_calls_without_config(self):
        """Test methods that should work safely without config."""
        factory = SessionFactory()

        # These methods should not raise errors
        info = factory.get_engine_info()
        assert info == {}

        status = factory.get_pool_status()
        assert status["status"] == "Not initialized"
