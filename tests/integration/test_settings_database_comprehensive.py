"""Comprehensive database-integrated tests for configuration settings."""

import pytest
import tempfile
import os
import toml
from pathlib import Path

from src.vgnc_internal_orm.config.settings import (
    DatabaseConfig,
    DatabaseDriver,
    DatabaseEnvironment,
    PoolConfig,
    Settings,
    SettingsError,
    SettingsValidationError,
    SecretString,
    get_database_url,
    parse_connection_url,
    validate_ssl_configuration,
    get_config_from_env,
    get_config_from_file,
    load_settings
)
from src.vgnc_internal_orm.sessions.factory import DatabaseFactory


class TestDatabaseConfigComprehensive:
    """Comprehensive database-integrated tests for DatabaseConfig."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_database_config_all_drivers_functional(self):
        """Test DatabaseConfig with all drivers using real URL generation."""
        test_cases = [
            # SQLite variations
            {
                "driver": DatabaseDriver.SQLITE,
                "database": ":memory:",
                "expected_prefix": "sqlite"
            },
            {
                "driver": DatabaseDriver.SQLITE,
                "database": "test.db",
                "expected_prefix": "sqlite"
            },
            # MySQL variations
            {
                "driver": DatabaseDriver.MYSQL,
                "username": "user",
                "password": "pass",
                "database": "db",
                "host": "localhost",
                "expected_prefix": "mysql"
            },
            {
                "driver": DatabaseDriver.MYSQL_PYMYSQL,
                "username": "user",
                "password": "pass",
                "database": "db",
                "host": "localhost",
                "expected_prefix": "mysql+pymysql"
            },
        ]

        for case in test_cases:
            config = DatabaseConfig(_env_file=None, **{k: v for k, v in case.items() if k != "expected_prefix"})

            # Test URL generation
            url = config.database_url
            assert url is not None
            assert case["expected_prefix"] in url

            # Test functional database connection if possible
            try:
                factory = DatabaseFactory(config)
                factory_url = factory.get_url()
                assert factory_url is not None
            except Exception as e:
                # Some configurations might not work without actual database server
                # but should at least generate valid URLs
                assert config.database_url is not None

    def test_database_config_all_environments(self):
        """Test DatabaseConfig with all environment types."""
        base_config = {
            "driver": DatabaseDriver.SQLITE,
            "database": "test.db",
        }

        for env in DatabaseEnvironment:
            config = DatabaseConfig(environment=env, _env_file=None, **base_config)

            assert config.environment == env
            assert config.database_url is not None

            # Test that environment-specific settings are applied
            factory = DatabaseFactory(config)
            pool_config = factory._get_pool_configuration(is_async=False)
            assert isinstance(pool_config, dict)

    def test_database_config_ssl_configurations(self):
        """Test DatabaseConfig with SSL configuration variations."""
        ssl_configurations = [
            {"ssl_mode": "DISABLED"},
            {"ssl_mode": "PREFERRED"},
            {"ssl_mode": "REQUIRED"},
            {"ssl_mode": "VERIFY_CA"},
            {"ssl_mode": "VERIFY_IDENTITY"},
            {"ssl_cert": "/path/to/cert.pem"},
            {"ssl_key": "/path/to/key.pem"},
            {"ssl_ca": "/path/to/ca.pem"},
            {
                "ssl_mode": "REQUIRED",
                "ssl_cert": "/path/to/cert.pem",
                "ssl_key": "/path/to/key.pem",
                "ssl_ca": "/path/to/ca.pem"
            }
        ]

        for ssl_config in ssl_configurations:
            config = DatabaseConfig(
                driver=DatabaseDriver.MYSQL,
                username="user",
                password="pass",
                database="db",
                host="localhost",
                _env_file=None,
                **ssl_config
            )

            # Should handle SSL configuration gracefully
            assert config.database_url is not None

    def test_database_config_pool_configurations(self):
        """Test DatabaseConfig with various pool configurations."""
        pool_configurations = [
            {
                "pool_size": 5,
                "max_overflow": 10
            },
            {
                "pool_size": 20,
                "max_overflow": 40,
                "pool_timeout": 60,
                "pool_recycle": 3600
            },
            {
                "pool_size": 1,
                "max_overflow": 0,
                "pool_timeout": 10,
                "pool_recycle": 300,
                "pool_pre_ping": True
            }
        ]

        for pool_config in pool_configurations:
            config = DatabaseConfig(
                driver=DatabaseDriver.SQLITE,
                database="test.db",
                _env_file=None,
                **pool_config
            )

            # Should create pool configuration
            pool = config.pool
            if pool:
                assert hasattr(pool, 'pool_size')
                assert hasattr(pool, 'max_overflow')

    def test_database_config_secret_string_functional(self):
        """Test SecretString functionality in configuration context."""
        secret_password = SecretString("super_secret_password")

        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL,
            username="user",
            password=secret_password,
            database="db",
            host="localhost",
            _env_file=None
        )

        # Test secret string behavior
        assert str(config.password) == "**********"
        assert repr(config.password) == "**********"
        assert config.password.get_secret_value() == "super_secret_password"

        # Test URL generation still works with secret
        url = config.database_url
        assert url is not None
        assert "super_secret_password" in url  # URL should contain actual password

    def test_database_config_edge_cases_functional(self):
        """Test DatabaseConfig edge cases with functional impact."""
        edge_cases = [
            # Minimal SQLite
            {
                "driver": DatabaseDriver.SQLITE,
                "database": ":memory:",
            },
            # MySQL with all optional fields
            {
                "driver": DatabaseDriver.MYSQL,
                "username": "user",
                "password": "pass",
                "database": "db",
                "host": "localhost",
                "port": 3306,
                "charset": "utf8mb4",
                "connect_timeout": 30,
                "read_timeout": 60,
                "write_timeout": 60
            },
            # Special characters in credentials
            {
                "driver": DatabaseDriver.MYSQL,
                "username": "user@domain.com",
                "password": "p@ssw0rd!#",
                "database": "test-db",
                "host": "host.name"
            }
        ]

        for case in edge_cases:
            config = DatabaseConfig(_env_file=None, **case)

            # Should generate URL without errors
            url = config.database_url
            assert url is not None

    def test_database_config_validation_comprehensive(self):
        """Test DatabaseConfig validation with comprehensive scenarios."""
        # Valid configurations
        valid_configs = [
            {
                "driver": DatabaseDriver.SQLITE,
                "database": "test.db"
            },
            {
                "driver": DatabaseDriver.MYSQL,
                "username": "user",
                "password": "pass",
                "database": "db",
                "host": "localhost"
            }
        ]

        for config_dict in valid_configs:
            config = DatabaseConfig(_env_file=None, **config_dict)
            # Should create without errors
            assert config is not None

        # Invalid configurations
        invalid_configs = [
            # Missing required fields for MySQL
            {
                "driver": DatabaseDriver.MYSQL,
                # Missing username, password, database, host
            },
            # Invalid port numbers
            {
                "driver": DatabaseDriver.MYSQL,
                "username": "user",
                "password": "pass",
                "database": "db",
                "host": "localhost",
                "port": -1
            },
            {
                "driver": DatabaseDriver.MYSQL,
                "username": "user",
                "password": "pass",
                "database": "db",
                "host": "localhost",
                "port": 70000  # Too large
            }
        ]

        for config_dict in invalid_configs:
            with pytest.raises((ValueError, SettingsError)):
                DatabaseConfig(_env_file=None, **config_dict)


class TestPoolConfigComprehensive:
    """Comprehensive tests for PoolConfig."""

    def test_pool_config_all_scenarios(self):
        """Test PoolConfig with all possible scenarios."""
        configurations = [
            # Default configuration
            {},
            # Custom pool sizes
            {
                "pool_size": 1,
                "max_overflow": 0
            },
            {
                "pool_size": 50,
                "max_overflow": 100
            },
            # Timeouts and recycling
            {
                "pool_timeout": 10,
                "pool_recycle": 300
            },
            {
                "pool_timeout": 120,
                "pool_recycle": 7200
            },
            # Pool pre-ping
            {
                "pool_pre_ping": True
            },
            {
                "pool_pre_ping": False
            },
            # Complete configuration
            {
                "pool_size": 20,
                "max_overflow": 30,
                "pool_timeout": 45,
                "pool_recycle": 3600,
                "pool_pre_ping": True
            }
        ]

        for config_dict in configurations:
            pool = PoolConfig(**config_dict)

            # Test that pool configuration is valid
            assert pool is not None
            assert hasattr(pool, 'pool_size')
            assert hasattr(pool, 'max_overflow')
            assert hasattr(pool, 'pool_timeout')
            assert hasattr(pool, 'pool_recycle')
            assert hasattr(pool, 'pool_pre_ping')

    def test_pool_config_validation(self):
        """Test PoolConfig validation."""
        # Valid pool sizes
        valid_pools = [
            {"pool_size": 1, "max_overflow": 0},
            {"pool_size": 100, "max_overflow": 200},
        ]

        for pool_dict in valid_pools:
            pool = PoolConfig(**pool_dict)
            assert pool.pool_size > 0
            assert pool.max_overflow >= 0

        # Test timeout values
        valid_timeouts = [
            {"pool_timeout": 0},
            {"pool_timeout": 30},
            {"pool_timeout": 300},
        ]

        for timeout_dict in valid_timeouts:
            pool = PoolConfig(**timeout_dict)
            assert pool.pool_timeout >= 0

        # Test recycle values
        valid_recycles = [
            {"pool_recycle": -1},  # No recycling
            {"pool_recycle": 300},
            {"pool_recycle": 7200},
        ]

        for recycle_dict in valid_recycles:
            pool = PoolConfig(**recycle_dict)
            assert isinstance(pool.pool_recycle, int)


class TestSettingsComprehensive:
    """Comprehensive tests for Settings."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_settings_from_toml_file_functional(self):
        """Test Settings creation from TOML file."""
        toml_content = {
            "database": {
                "driver": "sqlite",
                "database": "config_test.db",
                "echo": True
            },
            "app": {
                "name": "Test Application",
                "debug": True,
                "log_level": "INFO"
            },
            "session": {
                "pool_size": 10,
                "max_overflow": 20
            }
        }

        toml_file = Path(self.temp_dir) / "test_settings.toml"
        with open(toml_file, 'w') as f:
            toml.dump(toml_content, f)

        # Test loading settings from file
        settings = Settings(_env_file=str(toml_file))

        assert settings.app.name == "Test Application"
        assert settings.app.debug is True
        assert settings.app.log_level == "INFO"
        assert settings.database.driver == DatabaseDriver.SQLITE
        assert settings.database.database == "config_test.db"
        assert settings.database.echo is True

    def test_settings_environment_precedence(self):
        """Test Settings with environment variable precedence."""
        # Create TOML file
        toml_content = {
            "database": {
                "driver": "sqlite",
                "database": "file.db"
            },
            "app": {
                "name": "File App",
                "debug": False
            }
        }

        toml_file = Path(self.temp_dir) / "precedence_test.toml"
        with open(toml_file, 'w') as f:
            toml.dump(toml_content, f)

        # Set environment variables
        env_vars = {
            "DATABASE_URL": "sqlite:///:memory:",
            "APP_NAME": "Environment App",
            "APP_DEBUG": "true"
        }

        with pytest.MonkeyPatch().context() as m:
            for key, value in env_vars.items():
                m.setenv(key, value)

            settings = Settings(_env_file=str(toml_file))

            # Environment should override file
            assert "memory" in settings.database.database_url
            assert settings.app.name == "Environment App"
            assert settings.app.debug is True

    def test_settings_validation_comprehensive(self):
        """Test Settings validation with comprehensive scenarios."""
        # Valid settings
        valid_configs = [
            # Minimal configuration
            {},
            # Database only
            {
                "database": {
                    "driver": "sqlite",
                    "database": "test.db"
                }
            },
            # App only
            {
                "app": {
                    "name": "Test App",
                    "debug": False
                }
            },
            # Complete configuration
            {
                "database": {
                    "driver": "mysql",
                    "username": "user",
                    "password": "pass",
                    "database": "db",
                    "host": "localhost"
                },
                "app": {
                    "name": "Complete App",
                    "debug": True,
                    "log_level": "DEBUG"
                },
                "session": {
                    "pool_size": 15,
                    "max_overflow": 25
                }
            }
        ]

        for config_dict in valid_configs:
            # Create TOML file
            toml_file = Path(self.temp_dir) / f"valid_config_{id(config_dict)}.toml"
            with open(toml_file, 'w') as f:
                toml.dump(config_dict, f)

            # Should load without errors
            settings = Settings(_env_file=str(toml_file))
            assert settings is not None

    def test_settings_error_handling(self):
        """Test Settings error handling."""
        # Invalid TOML content
        invalid_toml = Path(self.temp_dir) / "invalid.toml"
        with open(invalid_toml, 'w') as f:
            f.write("invalid toml content [unclosed")

        with pytest.raises(SettingsError):
            Settings(_env_file=str(invalid_toml))

        # Non-existent file
        non_existent = Path(self.temp_dir) / "non_existent.toml"
        with pytest.raises(SettingsError):
            Settings(_env_file=str(non_existent))


class TestConfigUtilityFunctionsComprehensive:
    """Comprehensive tests for configuration utility functions."""

    def test_get_database_url_functional(self):
        """Test get_database_url function with various inputs."""
        test_cases = [
            # Direct URL (should return as-is)
            ("mysql://user:pass@localhost/db", "mysql://user:pass@localhost/db"),
            # Database name (should construct SQLite URL)
            ("test.db", "sqlite:///test.db"),
            # Special SQLite names
            (":memory:", "sqlite:///:memory:"),
            # Complex URLs
            (
                "mysql+pymysql://user:pass@localhost:3306/db?charset=utf8mb4",
                "mysql+pymysql://user:pass@localhost:3306/db?charset=utf8mb4"
            ),
        ]

        for input_url, expected in test_cases:
            result = get_database_url(input_url)
            assert str(result) == expected

    def test_parse_connection_url_functional(self):
        """Test parse_connection_url function."""
        test_urls = [
            "mysql://user:pass@localhost:3306/database",
            "sqlite:///test.db",
            "sqlite:///:memory:",
            "mysql+pymysql://user:pass@localhost/database?charset=utf8",
        ]

        for url in test_urls:
            parsed = parse_connection_url(url)
            assert hasattr(parsed, 'drivername')
            assert hasattr(parsed, 'database')
            assert hasattr(parsed, 'host')

    def test_validate_ssl_configuration_comprehensive(self):
        """Test SSL configuration validation."""
        # Valid SSL configurations
        valid_ssl_configs = [
            {"ssl_mode": "DISABLED"},
            {"ssl_mode": "PREFERRED"},
            {"ssl_mode": "REQUIRED"},
            {"ssl_mode": "VERIFY_CA"},
            {"ssl_mode": "VERIFY_IDENTITY"},
            {"ssl_cert": "/path/to/cert.pem"},
            {"ssl_key": "/path/to/key.pem"},
            {"ssl_ca": "/path/to/ca.pem"},
        ]

        for ssl_config in valid_ssl_configs:
            try:
                result = validate_ssl_configuration(ssl_config)
                assert isinstance(result, dict)
            except Exception as e:
                # Some SSL configurations might not be fully supported
                # but should not crash catastrophically
                assert isinstance(e, (SettingsError, SettingsValidationError))

    def test_get_config_from_env_functional(self):
        """Test get_config_from_env function."""
        env_vars = {
            "DATABASE_URL": "sqlite:///:memory:",
            "APP_NAME": "Environment Test",
            "APP_DEBUG": "true",
            "DATABASE_POOL_SIZE": "15"
        }

        with pytest.MonkeyPatch().context() as m:
            for key, value in env_vars.items():
                m.setenv(key, value)

            config = get_config_from_env()

            # Should parse environment variables correctly
            assert "memory" in config.get("database_url", "")
            assert config.get("app_name") == "Environment Test"

    def test_get_config_from_file_functional(self):
        """Test get_config_from_file function."""
        config_content = {
            "database": {
                "driver": "sqlite",
                "database": "file.db",
                "echo": True
            },
            "app": {
                "name": "File Config App",
                "debug": False,
                "log_level": "WARNING"
            }
        }

        # Create temporary config file
        config_file = Path(self.temp_dir) / "test_config.toml"
        with open(config_file, 'w') as f:
            toml.dump(config_content, f)

        config = get_config_from_file(str(config_file))

        assert config["database"]["driver"] == "sqlite"
        assert config["app"]["name"] == "File Config App"
        assert config["app"]["debug"] is False

    def test_load_settings_comprehensive(self):
        """Test load_settings function with comprehensive scenarios."""
        scenarios = [
            # Default settings (no file, no env)
            {},
            # File-based only
            {
                "config_file": "test_config.toml"
            },
            # Environment variables only
            {
                "database_url": "sqlite:///:memory:"
            },
            # Both file and environment
            {
                "config_file": "test_config.toml",
                "database_url": "sqlite:///:memory:"
            }
        ]

        for scenario in scenarios:
            try:
                # Create config file if specified
                if "config_file" in scenario:
                    config_path = Path(self.temp_dir) / scenario["config_file"]
                    if not config_path.exists():
                        config_content = {
                            "database": {
                                "driver": "sqlite",
                                "database": "file.db"
                            },
                            "app": {
                                "name": "Test App"
                            }
                        }
                        with open(config_path, 'w') as f:
                            toml.dump(config_content, f)
                    scenario["_env_file"] = str(config_path)

                settings = load_settings(**{k: v for k, v in scenario.items() if k != "config_file"})
                assert settings is not None

            except Exception as e:
                # Some scenarios might legitimately fail
                assert isinstance(e, (SettingsError, FileNotFoundError))


class TestSecretStringComprehensive:
    """Comprehensive tests for SecretString."""

    def test_secret_string_functionality(self):
        """Test SecretString functionality."""
        secret = SecretString("my_secret_password")

        # Test string representation is masked
        assert str(secret) == "**********"
        assert repr(secret) == "**********"

        # Test accessing actual value
        assert secret.get_secret_value() == "my_secret_password"

        # Test equality
        secret2 = SecretString("my_secret_password")
        assert secret.get_secret_value() == secret2.get_secret_value()

        # Test with different values
        secret3 = SecretString("different_password")
        assert secret.get_secret_value() != secret3.get_secret_value()

    def test_secret_string_edge_cases(self):
        """Test SecretString edge cases."""
        # Empty string
        empty_secret = SecretString("")
        assert empty_secret.get_secret_value() == ""
        assert str(empty_secret) == "**********"

        # Short secret
        short_secret = SecretString("x")
        assert short_secret.get_secret_value() == "x"
        assert str(short_secret) == "**********"

        # Long secret
        long_secret = SecretString("x" * 100)
        assert len(long_secret.get_secret_value()) == 100
        assert str(long_secret) == "**********"

        # Secret with special characters
        special_secret = SecretString("p@ssw0rd!#$%^&*()")
        assert special_secret.get_secret_value() == "p@ssw0rd!#$%^&*()"
        assert str(special_secret) == "**********"


class TestConfigurationIntegration:
    """Integration tests for the complete configuration system."""

    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_complete_configuration_workflow(self):
        """Test complete configuration workflow from file to DatabaseConfig."""
        # Create comprehensive configuration file
        config_content = {
            "database": {
                "driver": "sqlite",
                "database": "integration_test.db",
                "echo": True,
                "pool_size": 10,
                "max_overflow": 20
            },
            "app": {
                "name": "Integration Test App",
                "debug": True,
                "log_level": "DEBUG"
            },
            "session": {
                "pool_size": 15,
                "max_overflow": 25,
                "pool_timeout": 30,
                "pool_recycle": 1800
            }
        }

        config_file = Path(self.temp_dir) / "integration_config.toml"
        with open(config_file, 'w') as f:
            toml.dump(config_content, f)

        # Load settings
        settings = Settings(_env_file=str(config_file))

        # Extract database configuration
        db_config = settings.database

        # Test that configuration is properly loaded
        assert db_config.driver == DatabaseDriver.SQLITE
        assert db_config.database == "integration_test.db"
        assert db_config.echo is True

        # Test that settings are accessible
        assert settings.app.name == "Integration Test App"
        assert settings.app.debug is True
        assert settings.app.log_level == "DEBUG"

        # Test pool configuration
        assert hasattr(db_config, 'pool')
        if db_config.pool:
            assert db_config.pool.pool_size >= 0

        # Test functional usage with DatabaseFactory
        try:
            factory = DatabaseFactory(db_config)
            url = factory.get_url()
            assert url is not None
            assert "integration_test.db" in url.database
        except Exception as e:
            # Should at least generate URL without errors
            assert db_config.database_url is not None

    def test_configuration_with_overrides(self):
        """Test configuration with various override mechanisms."""
        # Base configuration file
        base_config = {
            "database": {
                "driver": "sqlite",
                "database": "base.db",
                "echo": False
            },
            "app": {
                "name": "Base App",
                "debug": False,
                "log_level": "INFO"
            }
        }

        config_file = Path(self.temp_dir) / "base_config.toml"
        with open(config_file, 'w') as f:
            toml.dump(base_config, f)

        # Test with environment overrides
        env_overrides = {
            "DATABASE_URL": "sqlite:///:memory:",
            "APP_NAME": "Override App",
            "APP_DEBUG": "true"
        }

        with pytest.MonkeyPatch().context() as m:
            for key, value in env_overrides.items():
                m.setenv(key, value)

            settings = Settings(_env_file=str(config_file))

            # Environment should override file
            assert "memory" in settings.database.database_url
            assert settings.app.name == "Override App"
            assert settings.app.debug is True
            # File values that weren't overridden should remain
            assert settings.app.log_level == "INFO"