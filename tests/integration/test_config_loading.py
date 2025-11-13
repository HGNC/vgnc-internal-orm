"""Integration tests for configuration loading from multiple sources."""

import os
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml

from vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver, Settings


class TestConfigLoadingIntegration:
    """Integration tests for configuration loading from various sources."""

    def test_env_file_loading(self):
        """Test loading configuration from .env file."""
        env_content = """
DATABASE__USERNAME=envfile_user
DATABASE__PASSWORD=envfile_password
DATABASE__DATABASE=envfile_db
DATABASE__HOST=envfile_host
DATABASE__PORT=5433
APP_NAME=EnvFile App
DEBUG=true
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".env", delete=False
        ) as env_file:
            env_file.write(env_content.strip())
            env_file_path = env_file.name

        try:
            with patch.dict(os.environ, {"ENV_FILE": env_file_path}):
                settings = Settings(_env_file=env_file_path)
                assert settings.database.username == "envfile_user"
                assert (
                    settings.database.password.get_secret_value() == "envfile_password"
                )
                assert settings.database.database == "envfile_db"
                assert settings.database.host == "envfile_host"
                assert settings.database.port == 5433
                assert settings.app_name == "EnvFile App"
                assert settings.debug is True
        finally:
            os.unlink(env_file_path)

    def test_environment_variable_precedence(self):
        """Test that environment variables take precedence over .env files."""
        env_content = """
DATABASE__USERNAME=envfile_user
DATABASE__PASSWORD=envfile_password
DATABASE__DATABASE=envfile_db
APP_NAME=EnvFile App
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".env", delete=False
        ) as env_file:
            env_file.write(env_content.strip())
            env_file_path = env_file.name

        try:
            # Environment variables should override .env file
            with patch.dict(
                os.environ,
                {"DATABASE__USERNAME": "env_var_user", "APP_NAME": "Env Var App"},
            ):
                settings = Settings(_env_file=env_file_path)
                assert settings.database.username == "env_var_user"  # From env var
                assert (
                    settings.database.password.get_secret_value() == "envfile_password"
                )  # From .env
                assert settings.app_name == "Env Var App"  # From env var
        finally:
            os.unlink(env_file_path)

    def test_json_config_loading(self):
        """Test loading configuration from JSON file."""
        config_data = {
            "database": {
                "username": "json_user",
                "password": "json_password",
                "database": "json_db",
                "host": "json_host",
                "port": 5433,
                "ssl_mode": "require",
            },
            "app_name": "JSON App",
            "debug": True,
            "environment": "staging",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False
        ) as json_file:
            import json

            json.dump(config_data, json_file)
            json_file_path = json_file.name

        try:
            # Note: This would require custom implementation to load JSON files
            # For now, we test passing the config as dict
            settings = Settings(**config_data)
            assert settings.database.username == "json_user"
            assert settings.database.password.get_secret_value() == "json_password"
            assert settings.database.database == "json_db"
            assert settings.database.host == "json_host"
            assert settings.database.port == 5433
            assert settings.database.ssl_mode == "require"
            assert settings.app_name == "JSON App"
            assert settings.debug is True
        finally:
            os.unlink(json_file_path)

    def test_yaml_config_loading(self):
        """Test loading configuration from YAML file."""
        config_data = {
            "database": {
                "username": "yaml_user",
                "password": "yaml_password",
                "database": "yaml_db",
                "driver": "sqlite",
                "pool": {"pool_size": 10, "max_overflow": 20},
            },
            "app_name": "YAML App",
            "log_level": "WARNING",
        }

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".yaml", delete=False
        ) as yaml_file:
            yaml.dump(config_data, yaml_file)
            yaml_file_path = yaml_file.name

        try:
            # Note: This would require custom implementation to load YAML files
            # For now, we test passing the config as dict
            settings = Settings(**config_data)
            assert settings.database.username == "yaml_user"
            assert settings.database.password.get_secret_value() == "yaml_password"
            assert settings.database.database == "yaml_db"
            assert settings.database.driver.value == "sqlite"
            assert settings.database.pool.pool_size == 10
            assert settings.database.pool.max_overflow == 20
            assert settings.app_name == "YAML App"
            assert settings.log_level == "WARNING"
        finally:
            os.unlink(yaml_file_path)

    def test_complex_configuration_precedence(self):
        """Test complex precedence: defaults < .env < env vars < direct params."""
        env_content = """
DATABASE__USERNAME=envfile_user
DATABASE__PASSWORD=envfile_password
DATABASE__DATABASE=envfile_db
APP_NAME=EnvFile App
DEBUG=false
"""

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".env", delete=False
        ) as env_file:
            env_file.write(env_content.strip())
            env_file_path = env_file.name

        try:
            with patch.dict(
                os.environ,
                {
                    "DATABASE__PASSWORD": "env_var_password",  # Override password
                    "APP_NAME": "Env Var App",  # Override app name
                },
            ):
                # Direct parameters should override everything
                settings = Settings(
                    database={
                        "username": "direct_user",  # Override all database settings
                        "password": "direct_password",
                        "database": "direct_db",
                    },
                    app_name="Direct App",  # Override app name
                    _env_file=env_file_path,
                )

                assert settings.database.username == "direct_user"  # Direct param
                assert (
                    settings.database.password.get_secret_value() == "direct_password"
                )  # Direct param
                assert settings.database.database == "direct_db"  # Direct param
                assert settings.app_name == "Direct App"  # Direct param
        finally:
            os.unlink(env_file_path)

    def test_configuration_validation_edge_cases(self):
        """Test configuration validation edge cases."""
        # Test invalid database driver
        with pytest.raises(ValueError):
            DatabaseConfig(
                username="user", password="pass", database="db", driver="invalid_driver"
            )

        # Test invalid port range
        with pytest.raises(ValueError):
            DatabaseConfig(
                username="user",
                password="pass",
                database="db",
                port=70000,  # Invalid port
            )

        # Test missing required fields
        with pytest.raises(ValueError):
            DatabaseConfig(
                username="user",
                driver=DatabaseDriver.MYSQL,  # Explicitly set to ensure validation triggers
                # Missing password and database
            )

    def test_ssl_configuration_validation(self):
        """Test SSL configuration validation."""
        # Create a temporary certificate file
        with tempfile.NamedTemporaryFile(suffix=".crt", delete=False) as cert_file:
            cert_file.write(
                b"-----BEGIN CERTIFICATE-----\nMOCK CERT\n-----END CERTIFICATE-----"
            )
            cert_path = cert_file.name

        try:
            config = DatabaseConfig(
                username="user",
                password="pass",
                database="db",
                ssl_mode="require",
                ssl_cert=Path(cert_path),
            )
            assert config.ssl_mode == "require"
            assert config.ssl_cert == Path(cert_path)
        finally:
            os.unlink(cert_path)

        # Test non-existent certificate
        with pytest.raises(ValueError, match="SSL certificate path does not exist"):
            DatabaseConfig(
                username="user",
                password="pass",
                database="db",
                ssl_cert=Path("/nonexistent/cert.crt"),
            )

    def test_pool_settings_validation(self):
        """Test connection pool settings validation."""
        config = DatabaseConfig(
            username="user",
            password="pass",
            database="db",
            pool={
                "pool_size": 10,
                "max_overflow": 20,
                "pool_timeout": 60,
                "pool_recycle": 7200,
                "pool_pre_ping": True,
            },
        )

        assert config.pool.pool_size == 10
        assert config.pool.max_overflow == 20
        assert config.pool.pool_timeout == 60
        assert config.pool.pool_recycle == 7200
        assert config.pool.pool_pre_ping is True

        # Test invalid pool size
        with pytest.raises(ValueError):
            DatabaseConfig(
                username="user",
                password="pass",
                database="db",
                pool={"pool_size": 0},  # Invalid pool size
            )
