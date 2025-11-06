"""Unit tests for configuration management."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
from pydantic import ValidationError

from vgnc_internal_orm.config.settings import DatabaseConfig, Settings, DatabaseDriver, Environment


class TestDatabaseConfig:
    """Test cases for DatabaseConfig."""

    def test_minimal_config(self):
        """Test minimal configuration requirements."""
        config = DatabaseConfig(
            username="test_user",
            password="test_password",
            database="test_db"
        )
        assert config.username == "test_user"
        assert config.password.get_secret_value() == "test_password"
        assert config.database == "test_db"
        assert config.host == "localhost"
        assert config.port == 5432
        assert config.driver == DatabaseDriver.POSTGRES

    def test_complete_config(self):
        """Test complete configuration with all settings."""
        config = DatabaseConfig(
            driver=DatabaseDriver.POSTGRES_ASYNC,
            host="custom-host",
            port=5433,
            username="custom_user",
            password="custom_password",
            database="custom_db",
            db_schema="custom_schema",
            ssl_mode="require",
            connect_timeout=20,
            echo=True
        )
        assert config.driver == DatabaseDriver.POSTGRES_ASYNC
        assert config.host == "custom-host"
        assert config.port == 5433
        assert config.db_schema == "custom_schema"
        assert config.ssl_mode == "require"
        assert config.connect_timeout == 20
        assert config.echo is True

    def test_database_url_postgres(self):
        """Test PostgreSQL database URL construction."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            host="localhost",
            port=5432
        )
        url = config.database_url.get_secret_value()
        assert url == "postgresql://user:pass@localhost:5432/db"

    def test_database_url_sqlite(self):
        """Test SQLite database URL construction."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None
        )
        url = config.database_url.get_secret_value()
        assert url == "sqlite:///test.db"

    def test_database_url_with_schema(self):
        """Test database URL construction with schema."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            db_schema="public"
        )
        url = config.database_url.get_secret_value()
        assert "options=-csearch_path=public" in url

    def test_async_database_url(self):
        """Test async database URL generation."""
        config = DatabaseConfig(
            driver=DatabaseDriver.POSTGRES,
            username="user",
            password="pass",
            database="db"
        )
        async_url = config.async_database_url.get_secret_value()
        assert async_url.startswith("postgresql+asyncpg://")

    def test_required_fields_validation(self):
        """Test validation of required fields."""
        with pytest.raises(ValidationError) as exc_info:
            DatabaseConfig(
                username="",  # Empty username should fail
                password="pass",
                database="db"
            )
        assert "username" in str(exc_info.value)

    def test_ssl_paths_validation(self):
        """Test SSL certificate path validation."""
        with tempfile.NamedTemporaryFile(delete=False) as temp_file:
            temp_path = temp_file.name

        try:
            # Valid path should work
            config = DatabaseConfig(
                username="user",
                password="pass",
                database="db",
                ssl_cert=Path(temp_path)
            )
            assert config.ssl_cert == Path(temp_path)

            # Invalid path should fail
            with pytest.raises(ValidationError) as exc_info:
                DatabaseConfig(
                    username="user",
                    password="pass",
                    database="db",
                    ssl_cert=Path("/nonexistent/path.crt")
                )
            assert "SSL certificate path does not exist" in str(exc_info.value)
        finally:
            os.unlink(temp_path)


class TestSettings:
    """Test cases for Settings."""

    def test_default_settings(self):
        """Test default settings values."""
        settings = Settings(
            database={
                "username": "test_user",
                "password": "test_password",
                "database": "test_db"
            },
            _env_file=None
        )
        assert settings.app_name == "VGNC ORM"
        assert settings.version == "0.1.0"
        assert settings.debug is False
        assert settings.environment == Environment.DEVELOPMENT
        assert settings.log_level == "INFO"

    def test_environment_variable_loading(self):
        """Test loading settings from environment variables."""
        with patch.dict(os.environ, {
            "APP_NAME": "Test App",
            "DEBUG": "true",
            "ENVIRONMENT": "production",
            "LOG_LEVEL": "DEBUG",
            "DATABASE__USERNAME": "test_user",
            "DATABASE__PASSWORD": "test_password",
            "DATABASE__DATABASE": "test_db"
        }):
            settings = Settings()
            assert settings.app_name == "Test App"
            assert settings.debug is True
            assert settings.environment == Environment.PRODUCTION
            assert settings.log_level == "DEBUG"

    def test_nested_database_config(self):
        """Test nested database configuration loading."""
        with patch.dict(os.environ, {
            "DATABASE__USERNAME": "env_user",
            "DATABASE__PASSWORD": "env_pass",
            "DATABASE__DATABASE": "env_db",
            "DATABASE__HOST": "env_host",
            "DATABASE__PORT": "5433"
        }):
            settings = Settings()
            assert settings.database.username == "env_user"
            assert settings.database.password.get_secret_value() == "env_pass"
            assert settings.database.database == "env_db"
            assert settings.database.host == "env_host"
            assert settings.database.port == 5433

    def test_environment_helpers(self):
        """Test environment helper methods."""
        # Development
        dev_settings = Settings(
            environment=Environment.DEVELOPMENT,
            database={
                "username": "test_user",
                "password": "test_password",
                "database": "test_db"
            },
            _env_file=None
        )
        assert dev_settings.is_development()
        assert not dev_settings.is_production()
        assert not dev_settings.is_testing()

        # Production
        prod_settings = Settings(
            environment=Environment.PRODUCTION,
            database={
                "username": "test_user",
                "password": "test_password",
                "database": "test_db"
            },
            _env_file=None
        )
        assert prod_settings.is_production()
        assert not prod_settings.is_development()
        assert not prod_settings.is_testing()

        # Testing
        test_settings = Settings(
            environment=Environment.TESTING,
            database={
                "username": "test_user",
                "password": "test_password",
                "database": "test_db"
            },
            _env_file=None
        )
        assert test_settings.is_testing()
        assert not test_settings.is_development()
        assert not test_settings.is_production()

    def test_log_level_normalization(self):
        """Test log level normalization."""
        settings = Settings(
            log_level="debug",
            database={
                "username": "test_user",
                "password": "test_password",
                "database": "test_db"
            },
            _env_file=None
        )
        assert settings.log_level == "DEBUG"

        settings = Settings(
            log_level="INFO",
            database={
                "username": "test_user",
                "password": "test_password",
                "database": "test_db"
            },
            _env_file=None
        )
        assert settings.log_level == "INFO"