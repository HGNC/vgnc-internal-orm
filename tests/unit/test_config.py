"""Unit tests for configuration management."""

import pytest
from pydantic import SecretStr, ValidationError

from vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestDatabaseConfig:
    """Test cases for DatabaseConfig."""

    def test_minimal_config(self):
        """Test minimal configuration requirements."""
        config = DatabaseConfig(
            host="localhost",
            username="test_user",
            password="test_password",
            database="test_db",
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            _env_file=None,  # Disable environment file loading for tests
        )
        assert config.username == "test_user"
        assert config.password == "test_password"
        assert config.database == "test_db"
        assert config.host == "localhost"
        assert config.port is None
        assert config.driver == DatabaseDriver.MYSQL_PYMYSQL

    def test_complete_config(self):
        """Test complete configuration with all settings."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            host="custom-host",
            port=3307,
            username="custom_user",
            password="custom_password",
            database="custom_db",
            pool_size=20,
            pool_recycle=1800,
            _env_file=None,
        )
        assert config.driver == DatabaseDriver.MYSQL_PYMYSQL
        assert config.host == "custom-host"
        assert config.port == 3307
        assert config.pool_size == 20
        assert config.pool_recycle == 1800

    def test_database_url_sqlite(self):
        """Test SQLite database URL construction."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database="test.db", _env_file=None
        )
        url = config.database_url.get_secret_value()
        assert url == "sqlite:///test.db"

    def test_required_fields_validation(self):
        """Test validation of required fields for non-SQLite."""
        with pytest.raises(ValidationError) as exc_info:
            DatabaseConfig(
                driver=DatabaseDriver.MYSQL_PYMYSQL,
                host=None,  # Host is required for non-SQLite
                username="user",
                database="db",
                _env_file=None,
            )
        assert "host" in str(exc_info.value)

    def test_database_url_compat_shim(self):
        """Test database_url compat shim returns SecretStr."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database="test.db", _env_file=None
        )
        url = config.database_url
        assert isinstance(url, SecretStr)
        assert "test.db" in url.get_secret_value()

    def test_get_url_returns_sqlalchemy_url(self):
        """Test get_url() returns sqlalchemy.URL."""
        from sqlalchemy import URL

        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database="test.db", _env_file=None
        )
        url = config.get_url()
        assert isinstance(url, URL)
        assert url.database == "test.db"

    def test_pool_fields_are_flat(self):
        """Test that pool fields are flat (not nested)."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            host="localhost",
            username="user",
            password="pass",
            database="db",
            _env_file=None,
        )
        # Pool fields should be directly accessible
        assert hasattr(config, "pool_size")
        assert hasattr(config, "max_overflow")
        assert hasattr(config, "pool_recycle")
        assert hasattr(config, "pool_pre_ping")

        # Should NOT have a nested pool object
        assert not hasattr(config, "pool")

    def test_database_driver_values(self):
        """Test DatabaseDriver enum values."""
        assert DatabaseDriver.SQLITE.value == "sqlite"
        assert DatabaseDriver.MYSQL_PYMYSQL.value == "mysql+pymysql"

    def test_no_async_driver_variants(self):
        """Test that async driver variants don't exist."""
        assert not hasattr(DatabaseDriver, "MYSQL_ASYNC")
        assert not hasattr(DatabaseDriver, "SQLITE_ASYNC")

    def test_no_async_database_url_property(self):
        """Test that async_database_url property is removed."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database="test.db", _env_file=None
        )
        assert not hasattr(config, "async_database_url")
