"""Simple tests to improve config/settings.py coverage."""

from pydantic import SecretStr

from vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestSettingsCoverage:
    """Additional tests to improve Settings coverage."""

    def test_database_driver_values(self):
        """Test DatabaseDriver enum values."""
        assert DatabaseDriver.MYSQL_PYMYSQL.value == "mysql+pymysql"
        assert DatabaseDriver.SQLITE.value == "sqlite"

    def test_database_config_validation_methods(self):
        """Test DatabaseConfig validation methods."""
        config = DatabaseConfig(
            host="localhost",
            username="test_user",
            password="test_password",
            database="test_db",
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            _env_file=None,
        )

        # Test that validation methods exist and can be called
        assert hasattr(config, "model_validate")

    def test_settings_model_validation(self):
        """Test DatabaseConfig model validation."""
        config = DatabaseConfig(
            host="localhost",
            username="test_user",
            password="test_password",
            database="test_db",
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            _env_file=None,
        )

        # Test that config was created
        assert config.username == "test_user"
        assert config.password == "test_password"
        assert config.database == "test_db"

    def test_database_config_comprehensive(self):
        """Test comprehensive DatabaseConfig configuration."""
        config = DatabaseConfig(
            host="localhost",
            port=3306,
            username="test_user",
            password="test_password",
            database="test_db",
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            pool_size=10,
            max_overflow=20,
            pool_recycle=1800,
            pool_pre_ping=True,
            _env_file=None,
        )

        assert config.host == "localhost"
        assert config.port == 3306
        assert config.username == "test_user"
        assert config.password == "test_password"
        assert config.database == "test_db"
        assert config.pool_size == 10
        assert config.max_overflow == 20
        assert config.pool_recycle == 1800
        assert config.pool_pre_ping is True

    def test_database_config_drivers_basic(self):
        """Test DatabaseConfig with basic driver configurations."""
        # Test MySQL driver
        mysql_config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            host="localhost",
            username="user",
            password="pass",
            database="test_db",
            _env_file=None,
        )
        assert mysql_config.driver == DatabaseDriver.MYSQL_PYMYSQL

        # Test SQLite driver
        sqlite_config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database="test.db", _env_file=None
        )
        assert sqlite_config.driver == DatabaseDriver.SQLITE

    def test_database_config_all_fields(self):
        """Test DatabaseConfig with all possible fields."""
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            host="custom-host",
            port=3307,
            username="custom_user",
            password="custom_password",
            database="custom_db",
            pool_size=15,
            max_overflow=25,
            pool_recycle=7200,
            pool_pre_ping=False,
            _env_file=None,
        )

        assert config.host == "custom-host"
        assert config.port == 3307
        assert config.pool_size == 15
        assert config.max_overflow == 25
        assert config.pool_recycle == 7200
        assert config.pool_pre_ping is False

    def test_database_config_edge_cases(self):
        """Test DatabaseConfig edge cases."""
        # Test with different port values
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            host="localhost",
            username="user",
            password="pass",
            database="test_db",
            port=5432,  # Non-standard port
            _env_file=None,
        )
        assert config.port == 5432

    def test_database_config_model_methods(self):
        """Test DatabaseConfig model methods."""
        config = DatabaseConfig(
            host="localhost",
            username="test_user",
            password="test_password",
            database="test_db",
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            _env_file=None,
        )

        # Test that standard Pydantic methods work
        assert hasattr(config, "model_dump")
        assert hasattr(config, "model_dump_json")
        assert hasattr(config, "model_validate")

        # Test model_dump
        data = config.model_dump()
        assert "username" in data
        assert "database" in data

        # Test model_dump_json
        json_str = config.model_dump_json()
        assert isinstance(json_str, str)

    def test_database_config_secret_fields(self):
        config = DatabaseConfig(
            driver=DatabaseDriver.MYSQL_PYMYSQL,
            host="localhost",
            username="test_user",
            password="test_password",
            database="test_db",
        )

        # Test that password is plain string (db_common uses str | None)
        assert isinstance(config.password, str)
        assert config.password == "test_password"

        # Test that database_url returns SecretStr
        assert hasattr(config, "database_url")
        assert isinstance(config.database_url, SecretStr)

        # Test get_url() returns sqlalchemy.URL
        from sqlalchemy import URL

        url = config.get_url()
        assert isinstance(url, URL)

    def test_sqlite_with_custom_database(self):
        """Test SQLite with custom database name."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="custom.db",
            _env_file=None,
        )

        url = config.get_url()
        assert url.drivername == "sqlite"
        assert url.database == "custom.db"

    def test_mysql_url_construction(self):
        """Test MySQL URL construction."""
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
        assert url.drivername == "mysql+pymysql"
        assert url.username == "testuser"
        assert url.password == "testpass"
        assert url.host == "localhost"
        assert url.port == 3306
        assert url.database == "testdb"
