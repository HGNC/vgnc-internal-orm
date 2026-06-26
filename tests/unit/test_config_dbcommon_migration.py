"""Unit tests for db-common-based DatabaseConfig (T4).

These tests verify that DatabaseConfig is correctly refactored as a
db_common.DatabaseSettings subclass with the new structure.

RED phase: Tests FAIL before the migration because:
- DatabaseConfig is not a db_common.DatabaseSettings subclass
- ConnectionPoolSettings is still nested, not flat fields
- DatabaseDriver still has MYSQL_ASYNC/SQLITE_ASYNC
- async_database_url property still exists
- Settings class still exists
- get_url() doesn't return sqlalchemy.URL

GREEN phase: Tests PASS after the migration is complete.
"""

# Import what we expect to exist AFTER migration
from db_common import DatabaseSettings as DbCommonDatabaseSettings
from pydantic import SecretStr
from sqlalchemy import URL

from vgnc_internal_orm.config.settings import (
    DatabaseConfig,
    DatabaseDriver,
)


class TestDatabaseConfigDbCommonMigration:
    """Test DatabaseConfig refactored as db_common.DatabaseSettings subclass."""

    def test_database_config_is_subclass_of_db_common(self):
        """Verify DatabaseConfig subclasses db_common.DatabaseSettings."""
        assert issubclass(
            DatabaseConfig, DbCommonDatabaseSettings
        ), "DatabaseConfig should be a subclass of db_common.DatabaseSettings"

    def test_database_driver_uses_db_common_enum(self):
        """Verify DatabaseDriver re-exports db_common.DatabaseDriver."""
        # The new DatabaseDriver should have SQLITE but not MYSQL_ASYNC/SQLITE_ASYNC
        assert hasattr(DatabaseDriver, "SQLITE")
        assert DatabaseDriver.SQLITE.value == "sqlite"

        # Should have MYSQL_PYMYSQL but not MYSQL_ASYNC
        assert hasattr(DatabaseDriver, "MYSQL_PYMYSQL")
        assert DatabaseDriver.MYSQL_PYMYSQL.value == "mysql+pymysql"

        # Should NOT have async variants
        assert not hasattr(DatabaseDriver, "MYSQL_ASYNC")
        assert not hasattr(DatabaseDriver, "SQLITE_ASYNC")

    def test_pool_fields_are_flat_not_nested(self):
        """Verify pool fields are flat, not in a nested ConnectionPoolSettings."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None,
        )

        # Pool fields should be directly accessible, not via config.pool.*
        assert hasattr(config, "pool_size")
        assert hasattr(config, "max_overflow")
        assert hasattr(config, "pool_recycle")
        assert hasattr(config, "pool_pre_ping")

        # Should NOT have a nested pool object
        assert not hasattr(config, "pool") or not isinstance(
            config.pool, object
        ), "pool field should not exist or should not be a nested object"

    def test_async_database_url_property_does_not_exist(self):
        """Verify async_database_url property is removed."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None,
        )

        assert not hasattr(
            config, "async_database_url"
        ), "async_database_url property should be removed"

    def test_get_url_returns_sqlalchemy_url(self):
        """Verify get_url() returns a sqlalchemy.URL object."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None,
        )

        url = config.get_url()
        assert isinstance(
            url, URL
        ), f"get_url() should return sqlalchemy.URL, got {type(url)}"

    def test_database_url_compat_shim_works(self):
        """Verify database_url property returns SecretStr compat shim."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None,
        )

        url = config.database_url
        assert isinstance(
            url, SecretStr
        ), "database_url should return SecretStr for compatibility"

        # Should be gettable as a string
        url_str = url.get_secret_value()
        assert isinstance(url_str, str)
        assert "test.db" in url_str

    def test_environment_enum_removed(self):
        """Verify Environment enum is removed from settings."""
        from vgnc_internal_orm.config import settings

        # Environment should not be imported from settings
        assert not hasattr(
            settings, "Environment"
        ), "Environment enum should be removed"

    def test_settings_class_removed(self):
        """Verify Settings class is removed."""
        from vgnc_internal_orm.config import settings

        # Settings should not be imported from settings
        assert not hasattr(settings, "Settings"), "Settings class should be removed"

    def test_no_dropped_fields_exist(self):
        """Verify dropped fields don't exist in DatabaseConfig."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None,
        )

        # These fields should be removed
        dropped_fields = [
            "ssl_mode",
            "ssl_cert",
            "ssl_key",
            "ssl_ca",
            "connect_timeout",
            "query_timeout",
            "isolation_level",
            "echo",
            "charset",  # This is in db_common but on a different path
            "collation",
            "use_unicode",
            "autocommit",
            "db_schema",
        ]

        for field in dropped_fields:
            # Some fields like charset might be in db_common but not on the subclass
            # The key is they should not be on our DatabaseConfig
            # For now, just verify we don't have these specific vgnc-added fields
            if field in [
                "ssl_mode",
                "ssl_cert",
                "ssl_key",
                "ssl_ca",
                "query_timeout",
                "use_unicode",
                "autocommit",
                "db_schema",
            ]:
                assert not hasattr(
                    config, field
                ), f"Field '{field}' should be removed from DatabaseConfig"

    def test_mysql_url_construction(self):
        """Verify MySQL URL construction with db_common structure."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            username="testuser",
            password="testpass",
            host="localhost",
            port=3306,
            database="testdb",
            _env_file=None,
        )

        url = config.get_url()
        assert isinstance(url, URL)
        assert url.drivername == "mysql+pymysql"
        assert url.username == "testuser"
        assert url.password == "testpass"
        assert url.host == "localhost"
        assert url.port == 3306
        assert url.database == "testdb"

        # database_url compat shim should also work
        compat_url = config.database_url.get_secret_value()
        assert "mysql+pymysql" in compat_url
        assert "testuser" in compat_url
        assert "testdb" in compat_url
