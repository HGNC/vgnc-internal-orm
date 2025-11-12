"""Working config/settings.py comprehensive tests based on actual module structure."""

import pytest
import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from vgnc_internal_orm.config.settings import (
    DatabaseConfig,
    DatabaseDriver,
    Environment,
    ConnectionPoolSettings,
    get_settings,
    settings,
)


class TestDatabaseConfigCore:
    """Test DatabaseConfig core functionality."""

    def test_sqlite_config_creation(self):
        """Test creating SQLite database config."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        assert config.driver == DatabaseDriver.SQLITE
        assert config.database == ":memory:"
        assert config.database_url.get_secret_value().startswith("sqlite:///")

    def test_mysql_config_creation(self):
        """Test creating MySQL database config."""
        config = DatabaseConfig(
            username="test_user",
            password="test_password",
            database="test_database",
            host="localhost",
            port=3306,
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )
        assert config.driver == DatabaseDriver.MYSQL
        assert config.username == "test_user"
        assert config.password.get_secret_value() == "test_password"
        assert config.database == "test_database"
        assert config.host == "localhost"
        assert config.port == 3306
        assert "mysql+pymysql://" in config.database_url.get_secret_value()

    def test_postgresql_config_creation(self):
        """Test creating PostgreSQL database config."""
        config = DatabaseConfig(
            username="pg_user",
            password="pg_password",
            database="pg_database",
            host="localhost",
            port=5432,
            driver=DatabaseDriver.POSTGRESQL,
            _env_file=None
        )
        assert config.driver == DatabaseDriver.POSTGRESQL
        assert "postgresql://" in config.database_url.get_secret_value()

    def test_environment_configuration(self):
        """Test environment-specific configuration."""
        for env in [Environment.DEVELOPMENT, Environment.STAGING, Environment.PRODUCTION]:
            config = DatabaseConfig(
                driver=DatabaseDriver.SQLITE,
                database=":memory:",
                environment=env,
                _env_file=None
            )
            assert config.environment == env

    def test_charset_and_collation_configuration(self):
        """Test charset and collation configuration."""
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
        assert config.charset == "utf8mb4"
        assert config.collation == "utf8mb4_unicode_ci"

    def test_connection_timeout_configuration(self):
        """Test connection timeout configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            connect_timeout=30,
            _env_file=None
        )
        assert config.connect_timeout == 30

    def test_echo_configuration(self):
        """Test echo configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            echo=True,
            _env_file=None
        )
        assert config.echo is True

    def test_autocommit_configuration(self):
        """Test autocommit configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test",
            password="test",
            database="test",
            host="localhost",
            autocommit=True,
            _env_file=None
        )
        assert config.autocommit is True

    def test_isolation_level_configuration(self):
        """Test isolation level configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test",
            password="test",
            database="test",
            host="localhost",
            isolation_level="READ_COMMITTED",
            _env_file=None
        )
        assert config.isolation_level == "READ_COMMITTED"

    def test_pool_configuration(self):
        """Test pool configuration."""
        pool_config = ConnectionPoolSettings(
            pool_size=20,
            max_overflow=30,
            pool_timeout=60,
            pool_recycle=7200,
            pool_pre_ping=True
        )
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test",
            password="test",
            database="test",
            host="localhost",
            pool=pool_config,
            _env_file=None
        )
        assert config.pool.pool_size == 20
        assert config.pool.max_overflow == 30
        assert config.pool.pool_timeout == 60
        assert config.pool.pool_recycle == 7200
        assert config.pool.pool_pre_ping is True


class TestDatabaseConfigProperties:
    """Test DatabaseConfig properties and methods."""

    def test_database_url_generation_sqlite(self):
        """Test database URL generation for SQLite."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None
        )
        url = config.database_url.get_secret_value()
        assert url == "sqlite:///test.db"

    def test_database_url_generation_mysql(self):
        """Test database URL generation for MySQL."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            host="localhost",
            port=3306,
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )
        url = config.database_url.get_secret_value()
        assert url == "mysql+pymysql://user:pass@localhost:3306/db"

    def test_database_url_generation_postgresql(self):
        """Test database URL generation for PostgreSQL."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            host="localhost",
            port=5432,
            driver=DatabaseDriver.POSTGRESQL,
            _env_file=None
        )
        url = config.database_url.get_secret_value()
        assert url == "postgresql://user:pass@localhost:5432/db"

    def test_async_database_url_mysql(self):
        """Test async database URL for MySQL."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            host="localhost",
            port=3306,
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )
        async_url = config.async_database_url.get_secret_value()
        assert "mysql+aiomysql://" in async_url

    def test_async_database_url_postgresql(self):
        """Test async database URL for PostgreSQL."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            host="localhost",
            port=5432,
            driver=DatabaseDriver.POSTGRESQL,
            _env_file=None
        )
        async_url = config.async_database_url.get_secret_value()
        assert "postgresql+asyncpg://" in async_url

    def test_async_database_url_sqlite_none(self):
        """Test async database URL is None for SQLite."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None
        )
        async_url = config.async_database_url
        assert async_url is None

    def test_config_validation_sqlite_minimal(self):
        """Test config validation for minimal SQLite config."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        # Should not raise any exceptions
        assert config.database_url.get_secret_value().startswith("sqlite://")

    def test_config_validation_mysql_required_fields(self):
        """Test config validation for MySQL with required fields."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            host="localhost",
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )
        # Should not raise any exceptions
        assert "mysql+pymysql://" in config.database_url.get_secret_value()


class TestConnectionPoolSettings:
    """Test ConnectionPoolSettings functionality."""

    def test_pool_config_creation(self):
        """Test ConnectionPoolSettings creation."""
        pool = ConnectionPoolSettings(
            pool_size=10,
            max_overflow=20,
            pool_timeout=30,
            pool_recycle=3600,
            pool_pre_ping=True
        )
        assert pool.pool_size == 10
        assert pool.max_overflow == 20
        assert pool.pool_timeout == 30
        assert pool.pool_recycle == 3600
        assert pool.pool_pre_ping is True

    def test_pool_config_defaults(self):
        """Test ConnectionPoolSettings default values."""
        pool = ConnectionPoolSettings()
        assert pool.pool_size == 5
        assert pool.max_overflow == 10
        assert pool.pool_timeout == 30
        assert pool.pool_recycle == 3600
        assert pool.pool_pre_ping is True


class TestEnvironmentConfiguration:
    """Test environment-specific configuration."""

    def test_development_configuration(self):
        """Test development environment configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="dev_user",
            password="dev_pass",
            database="dev_db",
            host="localhost",
            environment=Environment.DEVELOPMENT,
            _env_file=None
        )
        assert config.environment == Environment.DEVELOPMENT

    def test_staging_configuration(self):
        """Test staging environment configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="staging_user",
            password="staging_pass",
            database="staging_db",
            host="staging.example.com",
            environment=Environment.STAGING,
            _env_file=None
        )
        assert config.environment == Environment.STAGING

    def test_production_configuration(self):
        """Test production environment configuration."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="prod_user",
            password="prod_pass",
            database="prod_db",
            host="prod.example.com",
            environment=Environment.PRODUCTION,
            _env_file=None
        )
        assert config.environment == Environment.PRODUCTION


class TestConfigLoading:
    """Test configuration loading functions."""

    def test_get_default_config(self):
        """Test getting default configuration."""
        config = get_default_config()
        assert config is not None
        assert isinstance(config, DatabaseConfig)
        assert config.driver == DatabaseDriver.SQLITE
        assert config.database == ":memory:"
        assert config.environment == Environment.DEVELOPMENT

    def test_load_config_from_env_with_mock(self):
        """Test loading config from environment variables."""
        with patch.dict(os.environ, {
            'DATABASE_DRIVER': 'sqlite',
            'DATABASE_NAME': ':memory:',
            'DATABASE_ECHO': 'false'
        }):
            config = load_config_from_env()
            assert config.driver == DatabaseDriver.SQLITE
            assert config.database == ":memory:"

    def test_load_config_from_file_toml(self):
        """Test loading config from TOML file."""
        toml_content = """
[database]
driver = "sqlite"
database = ":memory:"
echo = true
environment = "development"

[database.pool]
pool_size = 10
max_overflow = 20
"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write(toml_content)
            f.flush()

            try:
                config = load_config_from_file(f.name)
                assert config.driver == DatabaseDriver.SQLITE
                assert config.database == ":memory:"
                assert config.echo is True
                assert config.pool.pool_size == 10
                assert config.pool.max_overflow == 20
            finally:
                os.unlink(f.name)


class TestConfigValidation:
    """Test configuration validation."""

    def test_validate_valid_sqlite_config(self):
        """Test validation of valid SQLite config."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        # Should not raise
        validate_config(config)

    def test_validate_valid_mysql_config(self):
        """Test validation of valid MySQL config."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            host="localhost",
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )
        # Should not raise
        validate_config(config)

    def test_validate_invalid_mysql_missing_username(self):
        """Test validation of MySQL config missing username."""
        config = DatabaseConfig(
            password="pass",
            database="db",
            host="localhost",
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )
        with pytest.raises(DatabaseConfigError):
            validate_config(config)

    def test_validate_invalid_pool_config(self):
        """Test validation of invalid pool config."""
        pool = PoolConfig(pool_size=0)  # Invalid
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            pool=pool,
            _env_file=None
        )
        with pytest.raises(PoolConfigError):
            validate_config(config)

    def test_validate_invalid_environment(self):
        """Test validation with invalid environment configuration."""
        # This would need to be tested with actual invalid environment
        # but since we use enum, it's mostly type validation
        pass


class TestConfigEdgeCases:
    """Test configuration edge cases."""

    def test_empty_database_name_sqlite(self):
        """Test empty database name for SQLite."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="",
            _env_file=None
        )
        assert config.database == ""
        assert config.database_url.get_secret_value() == "sqlite:///"

    def test_special_characters_in_password(self):
        """Test special characters in password."""
        config = DatabaseConfig(
            username="user",
            password="p@ssw0rd!@#$%^&*()",
            database="db",
            host="localhost",
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )
        url = config.database_url.get_secret_value()
        assert "mysql+pymysql://user:" in url

    def test_unicode_characters_in_database_name(self):
        """Test unicode characters in database name."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="тест_база_данных.db",
            _env_file=None
        )
        url = config.database_url.get_secret_value()
        assert "тест_база_данных.db" in url

    def test_port_configuration(self):
        """Test custom port configuration."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            host="localhost",
            port=9999,
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )
        url = config.database_url.get_secret_value()
        assert "localhost:9999" in url

    def test_custom_host_configuration(self):
        """Test custom host configuration."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            host="custom.example.com",
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )
        url = config.database_url.get_secret_value()
        assert "custom.example.com" in url


class TestConfigErrorHandling:
    """Test configuration error handling."""

    def test_database_config_error_creation(self):
        """Test DatabaseConfigError creation."""
        error = DatabaseConfigError("Test error")
        assert str(error) == "Test error"
        assert isinstance(error, ConfigError)

    def test_pool_config_error_creation(self):
        """Test PoolConfigError creation."""
        error = PoolConfigError("Pool error")
        assert str(error) == "Pool error"
        assert isinstance(error, ConfigError)

    def test_environment_config_error_creation(self):
        """Test EnvironmentConfigError creation."""
        error = EnvironmentConfigError("Environment error")
        assert str(error) == "Environment error"
        assert isinstance(error, ConfigError)


class TestConfigStringRepresentation:
    """Test configuration string representations."""

    def test_database_config_repr(self):
        """Test DatabaseConfig repr."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        repr_str = repr(config)
        assert "DatabaseConfig" in repr_str
        assert "sqlite" in repr_str

    def test_database_config_str(self):
        """Test DatabaseConfig str."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        str_str = str(config)
        assert "DatabaseConfig" in str_str

    def test_pool_config_repr(self):
        """Test PoolConfig repr."""
        pool = PoolConfig(pool_size=10)
        repr_str = repr(pool)
        assert "PoolConfig" in repr_str
        assert "10" in repr_str


class TestConfigEquality:
    """Test configuration equality."""

    def test_database_config_equality(self):
        """Test DatabaseConfig equality."""
        config1 = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        config2 = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        assert config1 == config2

    def test_database_config_inequality(self):
        """Test DatabaseConfig inequality."""
        config1 = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        config2 = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="test",
            password="test",
            database="test",
            host="localhost",
            _env_file=None
        )
        assert config1 != config2

    def test_pool_config_equality(self):
        """Test PoolConfig equality."""
        pool1 = PoolConfig(pool_size=10)
        pool2 = PoolConfig(pool_size=10)
        assert pool1 == pool2

    def test_pool_config_inequality(self):
        """Test PoolConfig inequality."""
        pool1 = PoolConfig(pool_size=10)
        pool2 = PoolConfig(pool_size=20)
        assert pool1 != pool2