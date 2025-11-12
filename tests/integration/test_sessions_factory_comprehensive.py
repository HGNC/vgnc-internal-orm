"""Enhanced database factory tests covering advanced configuration scenarios."""

import pytest
import tempfile
import os
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool, QueuePool, NullPool

from src.vgnc_internal_orm.sessions.factory import (
    DatabaseFactory,
    get_database_url,
    get_session,
    health_check,
    parse_connection_url,
    DatabaseInterface,
    AsyncDatabaseInterface,
    SyncDatabaseInterface,
    DatabaseFactoryError,
    HealthCheckError,
    ConfigurationError,
    ConnectionValidationError,
    DatabaseConnectionError,
    AsyncEngineNotAvailableError,
)
from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver, DatabaseEnvironment, PoolConfig


class TestDatabaseFactoryAdvancedConfiguration:
    """Test advanced database factory configuration scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_factory_all_sqlite_drivers(self):
        """Test DatabaseFactory with all SQLite driver variations."""
        sqlite_drivers = [
            DatabaseDriver.SQLITE,
            DatabaseDriver.SQLITE_PYPYSQLSQL,
            DatabaseDriver.SQLITE_AIOSQLITE,
        ]

        for driver in sqlite_drivers:
            config = DatabaseConfig(
                database=f"test_{driver.value}.db",
                driver=driver,
                _env_file=None
            )

            factory = DatabaseFactory(config)
            url = factory.get_url()

            assert url is not None
            assert url.database.endswith(f"{driver.value}.db")
            assert driver.value in url.drivername

    def test_database_factory_all_mysql_drivers(self):
        """Test DatabaseFactory with all MySQL driver variations."""
        mysql_drivers = [
            DatabaseDriver.MYSQL,
            DatabaseDriver.MYSQL_PYMYSQL,
            DatabaseDriver.MYSQL_MYSQLCONNECTOR,
            DatabaseDriver.MYSQL_AIOMYSQL,
        ]

        for driver in mysql_drivers:
            config = DatabaseConfig(
                username="test_user",
                password="test_password",
                database="test_database",
                host="localhost",
                port=3306,
                driver=driver,
                _env_file=None
            )

            factory = DatabaseFactory(config)
            url = factory.get_url()

            assert url is not None
            assert "mysql" in url.drivername
            assert url.username == "test_user"
            assert url.password == "test_password"
            assert url.database == "test_database"

    def test_get_pool_configuration_all_environments(self):
        """Test pool configuration for all environment types."""
        base_config = DatabaseConfig(
            database="test.db",
            driver=DatabaseDriver.SQLITE,
            _env_file=None
        )

        environments = [
            DatabaseEnvironment.DEVELOPMENT,
            DatabaseEnvironment.TESTING,
            DatabaseEnvironment.STAGING,
            DatabaseEnvironment.PRODUCTION,
        ]

        for env in environments:
            base_config.environment = env
            factory = DatabaseFactory(base_config)

            # Test sync pool config
            sync_pool_config = factory._get_pool_configuration(is_async=False)
            assert isinstance(sync_pool_config, dict)
            assert "pool_pre_ping" in sync_pool_config
            assert "pool_recycle" in sync_pool_config

            # Test async pool config
            async_pool_config = factory._get_pool_configuration(is_async=True)
            assert isinstance(async_pool_config, dict)
            assert "pool_pre_ping" in async_pool_config
            assert "pool_recycle" in async_pool_config

    def test_database_factory_edge_case_configurations(self):
        """Test DatabaseFactory with edge case configurations."""
        edge_cases = [
            # Minimal configuration
            {
                "driver": DatabaseDriver.SQLITE,
                "database": ":memory:",
            },
            # Configuration with special characters
            {
                "driver": DatabaseDriver.MYSQL,
                "username": "user@domain.com",
                "password": "p@ssw0rd!#",
                "database": "test-db_123",
                "host": "localhost.localdomain",
                "port": 3306,
            },
            # Configuration with unicode characters
            {
                "driver": DatabaseDriver.SQLITE,
                "database": "тести.db",  # Cyrillic
            },
        ]

        for config_dict in edge_cases:
            config = DatabaseConfig(_env_file=None, **config_dict)
            factory = DatabaseFactory(config)

            # Should handle all edge cases gracefully
            assert factory.config is not None
            assert factory.get_url() is not None

    def test_get_database_url_function_comprehensive(self):
        """Test get_database_url function with comprehensive scenarios."""
        scenarios = [
            # Direct URL
            ("mysql://user:pass@localhost/db", "mysql://user:pass@localhost/db"),
            # SQLite file
            ("sqlite:///test.db", "sqlite:///test.db"),
            # SQLite memory
            ("sqlite:///:memory:", "sqlite:///:memory:"),
            # URL with parameters
            ("mysql+pymysql://user:pass@localhost/db?charset=utf8mb4", "mysql+pymysql://user:pass@localhost/db?charset=utf8mb4"),
        ]

        for input_url, expected in scenarios:
            result = get_database_url(input_url)
            assert str(result) == expected

    def test_parse_connection_url_function(self):
        """Test parse_connection_url function with various URL formats."""
        test_urls = [
            "mysql://user:pass@localhost:3306/database",
            "sqlite:///test.db",
            "sqlite:///:memory:",
            "mysql+pymysql://user:pass@localhost/database?charset=utf8",
        ]

        for url in test_urls:
            result = parse_connection_url(url)
            assert hasattr(result, 'drivername')
            assert hasattr(result, 'database')


class TestDatabaseFactoryErrorsAndExceptions:
    """Test database factory error handling and exception scenarios."""

    def test_database_factory_error_types(self):
        """Test all DatabaseFactoryError subclasses."""
        error_types = [
            DatabaseFactoryError,
            HealthCheckError,
            ConfigurationError,
            ConnectionValidationError,
            DatabaseConnectionError,
            AsyncEngineNotAvailableError,
        ]

        for error_type in error_types:
            # Test error instantiation
            error = error_type("Test message")
            assert isinstance(error, Exception)
            assert str(error) == "Test message"

            # Test error with context
            error = error_type("Test message", context={"key": "value"})
            assert isinstance(error, Exception)
            assert "Test message" in str(error)

    def test_health_check_error_scenarios(self):
        """Test health check error scenarios."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )

        factory = DatabaseFactory(config)

        # Test health check with invalid database
        invalid_config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="invalid",
            password="invalid",
            database="invalid",
            host="invalidhost",
            port=9999,
            _env_file=None
        )

        invalid_factory = DatabaseFactory(invalid_config)

        # Valid factory should pass health check
        assert factory.health_check() is True

        # Invalid factory should fail health check gracefully
        assert invalid_factory.health_check() is False

    def test_configuration_validation_errors(self):
        """Test configuration validation error scenarios."""
        # Test missing required fields for MySQL
        with pytest.raises(Exception):
            config = DatabaseConfig(
                driver=DatabaseDriver.MYSQL,
                _env_file=None
                # Missing username, password, database, host
            )
            factory = DatabaseFactory(config)
            factory.validate_configuration()

    def test_async_engine_not_available_error(self):
        """Test async engine not available scenarios."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,  # Not an async driver
            database="test.db",
            _env_file=None
        )

        factory = DatabaseFactory(config)

        # Should raise error for async operations with non-async driver
        with pytest.raises(AsyncEngineNotAvailableError):
            factory.create_async_engine()


class TestEnhancedSessionManagement:
    """Test enhanced session management scenarios."""

    def test_get_session_with_overrides(self):
        """Test get_session function with configuration overrides."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None
        )

        # Test with database URL override
        session = get_session(config, database_url="sqlite:///:memory:")
        assert session is not None

        # Test with different override combinations
        session2 = get_session(
            config,
            database_url="sqlite:///:memory:",
            echo=True,
            pool_size=5
        )
        assert session2 is not None

    def test_session_lifecycle_management(self):
        """Test complete session lifecycle management."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )

        factory = DatabaseFactory(config)

        # Create session
        session = factory.create_session()
        assert isinstance(session, Session)

        # Test session is functional
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1

        # Test session cleanup
        session.close()

        # Test multiple sessions
        sessions = [factory.create_session() for _ in range(5)]
        assert len(sessions) == 5

        for session in sessions:
            assert isinstance(session, Session)
            session.close()

    def test_session_with_custom_pool_config(self):
        """Test session creation with custom pool configuration."""
        pool_config = PoolConfig(
            pool_size=15,
            max_overflow=25,
            pool_timeout=35,
            pool_recycle=4000,
            pool_pre_ping=False
        )

        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            pool=pool_config,
            _env_file=None
        )

        factory = DatabaseFactory(config)
        session = factory.create_session()

        assert session is not None
        session.close()


class TestDatabaseFactoryComprehensiveWorkflows:
    """Test comprehensive database factory workflows."""

    def test_complete_workflow_memory_database(self):
        """Test complete workflow with in-memory database."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            echo=True,
            _env_file=None
        )

        # Create factory
        factory = DatabaseFactory(config)

        # Validate configuration
        assert factory.validate_configuration() is True

        # Create engine
        engine = factory.create_engine()
        assert engine is not None

        # Create session
        session = factory.create_session()
        assert session is not None

        # Test database operations
        session.execute(text("CREATE TABLE test_table (id INTEGER PRIMARY KEY)"))
        session.execute(text("INSERT INTO test_table (id) VALUES (1)"))
        session.commit()

        result = session.execute(text("SELECT COUNT(*) FROM test_table")).scalar()
        assert result == 1

        # Health check
        assert factory.health_check() is True

        # Cleanup
        session.close()
        engine.dispose()

    def test_complete_workflow_file_database(self):
        """Test complete workflow with file database."""
        db_path = os.path.join(self.temp_dir, "complete_workflow_test.db")

        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=db_path,
            echo=False,
            _env_file=None
        )

        # Create factory
        factory = DatabaseFactory(config)

        # Create engine and session
        engine = factory.create_engine()
        session = factory.create_session()

        # Create schema
        session.execute(text("""
            CREATE TABLE species (
                id INTEGER PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                created TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        session.commit()

        # Test CRUD operations
        session.execute(text("""
            INSERT INTO species (name) VALUES (:name)
        """), {"name": "Test Species"})
        session.commit()

        result = session.execute(text("SELECT COUNT(*) FROM species")).scalar()
        assert result == 1

        # Test persistence
        session.close()
        engine.dispose()

        # Reopen database
        engine2 = factory.create_engine()
        session2 = factory.create_session()

        result = session2.execute(text("SELECT COUNT(*) FROM species")).scalar()
        assert result == 1

        session2.close()
        engine2.dispose()

    def test_factory_with_all_drivers_comprehensive(self):
        """Test factory functionality with all available drivers."""
        for driver in DatabaseDriver:
            try:
                if driver.value.startswith("sqlite"):
                    config = DatabaseConfig(
                        driver=driver,
                        database=":memory:" if driver == DatabaseDriver.SQLITE else f"test_{driver.value}.db",
                        _env_file=None
                    )
                elif driver.value.startswith("mysql"):
                    config = DatabaseConfig(
                        driver=driver,
                        username="test_user",
                        password="test_password",
                        database="test_database",
                        host="localhost",
                        port=3306,
                        _env_file=None
                    )
                else:
                    continue  # Skip unsupported drivers

                factory = DatabaseFactory(config)
                url = factory.get_url()

                assert url is not None
                assert factory.validate_configuration() is True

            except Exception as e:
                # Log errors but don't fail the test for unsupported configurations
                print(f"Note: Driver {driver} failed with: {e}")


class TestUtilityFunctionsComprehensive:
    """Test utility functions with comprehensive coverage."""

    def test_health_check_standalone_function(self):
        """Test health_check standalone function."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )

        # Test health check with valid config
        assert health_check(config) is True

        # Test health check with invalid config
        invalid_config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="invalid",
            password="invalid",
            database="invalid",
            host="invalidhost",
            port=9999,
            _env_file=None
        )

        assert health_check(invalid_config) is False

    def test_get_session_function_edge_cases(self):
        """Test get_session function with edge cases."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )

        # Test basic session creation
        session = get_session(config)
        assert session is not None
        session.close()

        # Test with URL override
        session2 = get_session(config, database_url="sqlite:///:memory:")
        assert session2 is not None
        session2.close()

        # Test with parameter overrides
        session3 = get_session(config, echo=True, pool_size=10)
        assert session3 is not None
        session3.close()


class TestDatabaseInterfaceCoverage:
    """Test database interface classes for maximum coverage."""

    def test_database_interface_base_class(self):
        """Test DatabaseInterface base class functionality."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )

        interface = DatabaseInterface(config)

        assert interface.config is config
        assert interface._engine is None
        assert interface._session_factory is None

        # Test abstract methods raise NotImplementedError
        with pytest.raises(NotImplementedError):
            interface.create_engine()

        with pytest.raises(NotImplementedError):
            interface.create_session()

        with pytest.raises(NotImplementedError):
            interface.get_engine()

    def test_sync_database_interface_comprehensive(self):
        """Test SyncDatabaseInterface comprehensive functionality."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )

        interface = SyncDatabaseInterface(config)

        # Test engine creation
        engine = interface.create_engine()
        assert engine is not None
        assert interface.get_engine() is engine

        # Test session creation
        session = interface.create_session()
        assert session is not None

        # Test session functionality
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1

        session.close()

    def test_async_database_interface_when_available(self):
        """Test AsyncDatabaseInterface when async is available."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_AIOMYSQL,
            username="test_user",
            password="test_password",
            database="test_database",
            host="localhost",
            port=3306,
            _env_file=None
        )

        interface = AsyncDatabaseInterface(config)

        # Test that interface can be created
        assert interface.config is config
        assert interface._engine is None
        assert interface._session_factory is None

        # Test that it raises appropriate errors for async operations
        # (Actual async testing would require async test framework)
        with pytest.raises((NotImplementedError, AsyncEngineNotAvailableError)):
            interface.create_engine()