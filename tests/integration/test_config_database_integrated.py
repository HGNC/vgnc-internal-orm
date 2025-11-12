"""Database-integrated tests for configuration following sessions/factory.py success pattern."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from src.vgnc_internal_orm.config.settings import (
    DatabaseConfig,
    DatabaseDriver,
    Environment,
    Settings,
)


class TestDatabaseConfigIntegrated:
    """Database-integrated tests for DatabaseConfig functionality."""

    def test_database_config_all_drivers(self):
        """Test DatabaseConfig with all available drivers."""
        drivers = [
            DatabaseDriver.MYSQL,
            DatabaseDriver.MYSQL_ASYNC,
            DatabaseDriver.SQLITE,
            DatabaseDriver.SQLITE_ASYNC,
        ]

        for driver in drivers:
            config = DatabaseConfig(
                username="test_user",
                password="test_password",
                database="test_db",
                driver=driver,
                _env_file=None
            )

            # Test real configuration object creation
            assert config.driver == driver
            assert config.username == "test_user"
            assert config.database == "test_db"

    def test_database_config_mysql_specific(self):
        """Test DatabaseConfig MySQL-specific configuration."""
        config = DatabaseConfig(
            username="mysql_user",
            password="mysql_password",
            database="mysql_db",
            host="localhost",
            port=3306,
            driver=DatabaseDriver.MYSQL,
            ssl_ca="/path/to/ca.pem",
            ssl_cert="/path/to/cert.pem",
            ssl_key="/path/to/key.pem",
            charset="utf8mb4",
            collation="utf8mb4_unicode_ci",
            _env_file=None
        )

        # Test all MySQL-specific attributes
        assert config.driver == DatabaseDriver.MYSQL
        assert config.host == "localhost"
        assert config.port == 3306
        assert config.ssl_ca == "/path/to/ca.pem"
        assert config.charset == "utf8mb4"
        assert config.collation == "utf8mb4_unicode_ci"

    def test_database_config_sqlite_specific(self):
        """Test DatabaseConfig SQLite-specific configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="/path/to/database.db",
            timeout=30.0,
            _env_file=None
        )

        # Test SQLite-specific attributes
        assert config.driver == DatabaseDriver.SQLITE
        assert config.database == "/path/to/database.db"
        assert config.timeout == 30.0

    def test_database_config_url_generation(self):
        """Test database URL generation for different drivers."""
        # MySQL URL
        mysql_config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            host="localhost",
            port=3306,
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )
        mysql_url = mysql_config.database_url
        assert "mysql+pymysql://" in mysql_url
        assert "user:pass" in mysql_url
        assert "localhost:3306" in mysql_url
        assert "db" in mysql_url

        # SQLite URL
        sqlite_config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None
        )
        sqlite_url = sqlite_config.database_url
        assert sqlite_url == "sqlite:///test.db"

        # SQLite in-memory URL
        memory_config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        memory_url = memory_config.database_url
        assert memory_url == "sqlite:///:memory:"

    def test_database_config_async_url_generation(self):
        """Test async database URL generation."""
        async_mysql_config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            host="localhost",
            port=3306,
            driver=DatabaseDriver.MYSQL_ASYNC,
            _env_file=None
        )
        async_mysql_url = async_mysql_config.async_database_url
        assert "mysql+aiomysql://" in async_mysql_url

        async_sqlite_config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE_ASYNC,
            database="test.db",
            _env_file=None
        )
        async_sqlite_url = async_sqlite_config.async_database_url
        assert "sqlite+aiosqlite:///" in async_sqlite_url

    def test_database_config_validation(self):
        """Test DatabaseConfig validation."""
        # Test required fields validation
        with pytest.raises(ValueError):
            DatabaseConfig(
                username=None,
                password="pass",
                database="db",
                driver=DatabaseDriver.MYSQL,
                _env_file=None
            )

        # Test password is required for non-SQLite
        with pytest.raises(ValueError):
            DatabaseConfig(
                username="user",
                password=None,
                database="db",
                driver=DatabaseDriver.MYSQL,
                _env_file=None
            )

    def test_database_config_environment_precedence(self):
        """Test environment variable precedence in configuration."""
        with patch.dict(os.environ, {
            "DATABASE__USERNAME": "env_user",
            "DATABASE__PASSWORD": "env_password",
            "DATABASE__DATABASE": "env_db",
            "DATABASE__HOST": "env_host",
            "DATABASE__PORT": "5433"
        }):
            config = DatabaseConfig(
                username="default_user",
                database="default_db",
                driver=DatabaseDriver.MYSQL,
                _env_file=None
            )

            # Environment variables should override defaults
            assert config.username == "env_user"
            assert config.password.get_secret_value() == "env_password"
            assert config.database == "env_db"
            assert config.host == "env_host"
            assert config.port == 5433

    def test_database_config_ssl_configuration(self):
        """Test SSL configuration for MySQL."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            driver=DatabaseDriver.MYSQL,
            ssl_ca="/ca.pem",
            ssl_cert="/cert.pem",
            ssl_key="/key.pem",
            _env_file=None
        )

        # Test SSL attributes are set
        assert config.ssl_ca == "/ca.pem"
        assert config.ssl_cert == "/cert.pem"
        assert config.ssl_key == "/key.pem"

    def test_database_config_environment_specific(self):
        """Test environment-specific configuration."""
        development_config = DatabaseConfig(
            username="dev_user",
            driver=DatabaseDriver.MYSQL,
            environment=Environment.DEVELOPMENT,
            _env_file=None
        )

        production_config = DatabaseConfig(
            username="prod_user",
            driver=DatabaseDriver.MYSQL,
            environment=Environment.PRODUCTION,
            _env_file=None
        )

        assert development_config.environment == Environment.DEVELOPMENT
        assert production_config.environment == Environment.PRODUCTION

    def test_settings_integration_with_database_config(self):
        """Test Settings class integration with DatabaseConfig."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.env', delete=False) as env_file:
            env_file.write("""
DATABASE__USERNAME=settings_user
DATABASE__PASSWORD=settings_pass
DATABASE__DATABASE=settings_db
DATABASE__DRIVER=sqlite
APP_NAME=Test App
DEBUG=true
""")
            env_file_path = env_file.name

        try:
            settings = Settings(
                _env_file=env_file_path,
                _env_file_encoding='utf-8'
            )

            # Test that Settings properly loads DatabaseConfig
            assert settings.database.username == "settings_user"
            assert settings.database.password.get_secret_value() == "settings_pass"
            assert settings.database.database == "settings_db"
            assert settings.database.driver == DatabaseDriver.SQLITE
            assert settings.app_name == "Test App"
            assert settings.debug is True

        finally:
            import os
            os.unlink(env_file_path)


class TestEnvironmentIntegrated:
    """Database-integrated tests for Environment enum."""

    def test_environment_values(self):
        """Test Environment enum values."""
        assert Environment.DEVELOPMENT.value == "development"
        assert Environment.TESTING.value == "testing"
        assert Environment.STAGING.value == "staging"
        assert Environment.PRODUCTION.value == "production"

    def test_environment_comparison(self):
        """Test Environment enum comparisons."""
        dev = Environment.DEVELOPMENT
        prod = Environment.PRODUCTION

        assert dev != prod
        assert dev == Environment.DEVELOPMENT
        assert str(dev) == "development"

    def test_environment_in_config(self):
        """Test Environment usage in DatabaseConfig."""
        for env in Environment:
            config = DatabaseConfig(
                username="user",
                password="pass",
                database="db",
                driver=DatabaseDriver.MYSQL,
                environment=env,
                _env_file=None
            )
            assert config.environment == env


class TestDatabaseConfigEdgeCases:
    """Test DatabaseConfig edge cases and error handling."""

    def test_sqlite_with_host_warning(self):
        """Test SQLite configuration with host (should not error but may warn)."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            host="localhost",  # SQLite typically doesn't use host
            _env_file=None
        )
        # Should still work (host may be ignored)
        assert config.driver == DatabaseDriver.SQLITE

    def test_unicode_configuration(self):
        """Test configuration with Unicode characters."""
        config = DatabaseConfig(
            username="测试用户",
            password="密码",
            database="数据库",
            driver=DatabaseDriver.MYSQL,
            charset="utf8mb4",
            _env_file=None
        )
        assert "测试用户" in config.username
        assert config.charset == "utf8mb4"

    def test_port_validation(self):
        """Test port validation in configuration."""
        # Valid port
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            driver=DatabaseDriver.MYSQL,
            port=3306,
            _env_file=None
        )
        assert config.port == 3306

        # Port as string should be converted
        config_str_port = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            driver=DatabaseDriver.MYSQL,
            port="5432",
            _env_file=None
        )
        assert config_str_port.port == 5432