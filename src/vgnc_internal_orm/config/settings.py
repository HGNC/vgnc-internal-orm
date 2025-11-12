"""Configuration management settings for VGNC ORM."""

from enum import Enum
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field, SecretStr, ValidationInfo, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseDriver(str, Enum):
    """Enumeration for supported database drivers and connection types.

    This enum specifies the database drivers that the ORM can connect to.
    Each driver has different connection parameters, SQL dialects, and
    capabilities that are handled by the configuration layer.

    Attributes:
        MYSQL: MySQL synchronous database driver using PyMySQL.
        MYSQL_ASYNC: MySQL asynchronous database driver using aiomysql.
        SQLITE: SQLite synchronous database driver for file-based databases.
        SQLITE_ASYNC: SQLite asynchronous database driver using aiosqlite.

    Note:
        The driver value is used to construct the SQLAlchemy connection
        string in the format: {driver}://{user}:{password}@{host}:{port}/{database}
        For async operations, use the ASYNC variants or the async_database_url property.

    Example:
        >>> driver = DatabaseDriver.MYSQL
        >>> print(driver.value)
        'mysql+pymysql'
    """

    MYSQL = "mysql+pymysql"
    MYSQL_ASYNC = "mysql+aiomysql"
    SQLITE = "sqlite"
    SQLITE_ASYNC = "sqlite+aiosqlite"


class Environment(str, Enum):
    """Enumeration for different runtime environments.

    This enum defines the various runtime environments where the application
    can be deployed. Each environment may have different configuration settings,
    database connections, and resource allocations.

    Attributes:
        DEVELOPMENT: Local development environment with debug mode enabled.
        TESTING: Testing environment for automated test execution.
        STAGING: Pre-production environment for testing before release.
        PRODUCTION: Production environment serving real users.

    Note:
        Environment-specific configuration can be set through the VGNC_ENVIRONMENT
        environment variable or in the Settings class.

    Example:
        >>> env = Environment.PRODUCTION
        >>> print(env.value)
        'production'
    """

    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConnectionPoolSettings(BaseModel):
    """Configuration for database connection pooling settings.

    This class manages the connection pool parameters that control how
    database connections are created, reused, and managed. Connection pooling
    improves performance by reusing connections rather than creating new ones
    for each database operation.

    Attributes:
        pool_size (int): The number of connections to keep in the pool.
            Default is 5. Higher values increase memory usage but allow
            more concurrent operations. Range: 1-100.
        max_overflow (int): The maximum number of connections that can be
            created beyond pool_size when the pool is exhausted.
            Default is 10. Range: 0-100.
        pool_timeout (int): Time in seconds to wait for a connection from
            the pool before raising an error. Default is 30 seconds.
        pool_recycle (int): Time in seconds after which connections are
            recycled. Useful for databases that close idle connections.
            Default is 3600 seconds (1 hour).
        pool_pre_ping (bool): If True, validates connections before use.
            Default is True. Helps detect stale connections early.

    Note:
        Pool settings are especially important for production environments
        with high database traffic. For development, smaller pool sizes
        are typically sufficient.

    Example:
        >>> config = ConnectionPoolSettings(
        ...     pool_size=20,
        ...     max_overflow=40,
        ...     pool_timeout=60.0
        ... )
        >>> print(config.pool_size)
        20
    """

    pool_size: int = Field(default=5, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(
        default=10, ge=0, le=100, description="Maximum overflow connections"
    )
    pool_timeout: int = Field(
        default=30, ge=1, description="Connection timeout in seconds"
    )
    pool_recycle: int = Field(
        default=3600, ge=0, description="Connection recycle time in seconds"
    )
    pool_pre_ping: bool = Field(default=True, description="Enable connection pre-ping")


class DatabaseConfig(BaseSettings):
    """Main configuration class for database connection settings.

    This class aggregates all database connection parameters and provides
    a unified interface for accessing database configuration. It handles
    connection string construction, secret management, and environment-specific
    settings with validation and type safety.

    Attributes:
        driver (DatabaseDriver): The database driver to use (MySQL, SQLite, etc.).
        host (str): The hostname or IP address of the database server.
        port (int): The port number for the database connection.
        database (str): The name of the database to connect to.
        username (str | None): The username for authentication.
        password (SecretStr | None): The password for authentication (handled securely).
        db_schema (str | None): Database schema (optional, for PostgreSQL).
        pool (ConnectionPoolSettings): Connection pooling configuration.
        ssl_mode (str | None): SSL mode for encrypted connections.
        ssl_cert (Path | None): Path to SSL certificate file.
        ssl_key (Path | None): Path to SSL private key file.
        ssl_ca (Path | None): Path to SSL CA certificate file.
        connect_timeout (int): Connection timeout in seconds.
        query_timeout (int | None): Query timeout in seconds.
        isolation_level (str | None): Transaction isolation level.
        environment (Environment): Runtime environment for configuration.
        echo (bool): Whether to log all SQL statements.
        charset (str): Database character set (MySQL-specific).
        collation (str | None): Database collation (MySQL-specific).
        use_unicode (bool): Enable Unicode support (MySQL-specific).
        autocommit (bool): Enable autocommit mode (MySQL-specific).

    Note:
        Configuration can be loaded from environment variables with the ``DB_`` prefix,
        from .env files, or programmatically. Secrets are handled securely using
        Pydantic's SecretStr type.

    Example:
        >>> config = DatabaseConfig(
        ...     driver=DatabaseDriver.MYSQL,
        ...     host='localhost',
        ...     port=3306,
        ...     database='myapp',
        ...     username='app_user',
        ...     password='secure_password'
        ... )
        >>> url = config.database_url.get_secret_value()
    """

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Core database settings
    driver: DatabaseDriver = Field(
        default=DatabaseDriver.MYSQL, description="Database driver"
    )
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=3306, ge=1, le=65535, description="Database port")
    username: str | None = Field(default=None, description="Database username")
    password: SecretStr | None = Field(default=None, description="Database password")
    database: str = Field(description="Database name")
    db_schema: str | None = Field(
        default=None, description="Database schema (optional)"
    )

    # Connection pool settings
    pool: ConnectionPoolSettings = Field(default_factory=ConnectionPoolSettings)

    # SSL settings
    ssl_mode: str | None = Field(default=None, description="SSL mode")
    ssl_cert: Path | None = Field(default=None, description="SSL certificate path")
    ssl_key: Path | None = Field(default=None, description="SSL key path")
    ssl_ca: Path | None = Field(default=None, description="SSL CA certificate path")

    # Additional connection parameters
    connect_timeout: int = Field(
        default=10, ge=1, description="Connection timeout in seconds"
    )
    query_timeout: int | None = Field(
        default=None, ge=1, description="Query timeout in seconds"
    )
    isolation_level: str | None = Field(
        default=None, description="Transaction isolation level"
    )

    # Environment-specific settings
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Application environment"
    )
    echo: bool = Field(default=False, description="Enable SQLAlchemy query logging")

    # MySQL-specific charset settings
    charset: str = Field(default="utf8mb4", description="Database character set")
    collation: str | None = Field(
        default="utf8mb4_unicode_ci", description="Database collation"
    )
    use_unicode: bool = Field(default=True, description="Enable Unicode support")
    autocommit: bool = Field(default=True, description="Enable autocommit mode")

    @field_validator("username", "password", mode="before")
    @classmethod
    def validate_auth_fields(cls, v: Any, info: ValidationInfo) -> Any:
        """Validate authentication fields for non-SQLite databases."""
        return v

    @field_validator("database", mode="before")
    @classmethod
    def validate_required_fields(cls, v: Any, info: ValidationInfo) -> Any:
        """Validate that required fields are not empty."""
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError(f"{info.field_name} is required and cannot be empty")
        return v

    @field_validator("username", "password", mode="after")
    @classmethod
    def validate_auth_required(cls, v: Any, info: ValidationInfo) -> Any:
        """Validate that auth fields are provided for non-SQLite databases."""
        # This will be checked in model_validator
        return v

    def model_post_init(self, __context: Any) -> None:
        """Post-initialization validation for database-specific requirements."""
        if self.driver != DatabaseDriver.SQLITE:
            if not self.username:
                raise ValueError("username is required for non-SQLite databases")
            if not self.password:
                raise ValueError("password is required for non-SQLite databases")

    @field_validator("ssl_cert", "ssl_key", "ssl_ca", mode="before")
    @classmethod
    def validate_ssl_paths(cls, v: Any) -> Any:
        """Validate SSL certificate paths exist."""
        if v is not None:
            path = Path(v)
            if not path.exists():
                raise ValueError(f"SSL certificate path does not exist: {path}")
        return v

    @property
    def database_url(self) -> SecretStr:
        """Get the database URL with proper secret handling.

        Constructs and returns the synchronous database connection URL in the
        format expected by SQLAlchemy. The password is handled securely using
        SecretStr and not exposed in debug output or logs. This property
        reconstructs the URL each time it's called to ensure secrets are not cached.

        The URL format is: {driver}://{user}:{password}@{host}:{port}/{database}?{params}

        Returns:
            SecretStr: The complete database connection URL suitable for SQLAlchemy
                engine creation. Passwords are properly URL-encoded and wrapped
                in SecretStr for security.

        Raises:
            ValueError: If username or password are missing for non-SQLite databases.
            ValueError: If required configuration parameters are invalid.

        Example:
            >>> config = DatabaseConfig(
            ...     driver=DatabaseDriver.MYSQL,
            ...     host='localhost',
            ...     port=3306,
            ...     database='myapp',
            ...     username='user',
            ...     password='pass123'
            ... )
            >>> url = config.database_url
            >>> print(url.get_secret_value())
            'mysql+pymysql://user:pass123@localhost:3306/myapp?charset=utf8mb4&collation=utf8mb4_unicode_ci&use_unicode=1&autocommit=true'

        Note:
            The returned URL contains the actual password. Use .get_secret_value() only
            in trusted contexts. The URL includes driver-specific parameters like
            charset and collation for MySQL connections.
        """
        if self.driver == DatabaseDriver.SQLITE:
            url = f"{self.driver.value}:///{self.database}"
        else:
            if not self.username or not self.password:
                raise ValueError(
                    "username and password are required for non-SQLite databases"
                )

            url = (
                f"{self.driver.value}://"
                f"{self.username}:{self.password.get_secret_value()}"
                f"@{self.host}:{self.port}/{self.database}"
            )

            # Build query parameters
            query_params = []

            # Add charset parameters for MySQL
            if self.driver.value.startswith("mysql"):
                query_params.append(f"charset={self.charset}")
                if self.collation:
                    query_params.append(f"collation={self.collation}")
                if self.use_unicode:
                    query_params.append("use_unicode=1")
                if self.autocommit:
                    query_params.append("autocommit=true")

            # Add query parameters to URL
            if query_params:
                separator = "?" if "?" not in url else "&"
                url += f"{separator}{'&'.join(query_params)}"

        return SecretStr(url)

    @property
    def async_database_url(self) -> SecretStr | None:
        """Get async-compatible database URL for asynchronous connections.

        Constructs and returns the asynchronous database connection URL if the
        current driver supports async operations. The async URL uses an async
        driver plugin (e.g., 'mysql+aiomysql' instead of 'mysql+pymysql').

        The async URL format is: {driver}+{async_driver}://{user}:{password}@{host}:{port}/{database}

        Returns:
            SecretStr | None: The complete async database connection URL suitable
                for async SQLAlchemy engine creation, or None if async is not
                supported by the current driver.

        Raises:
            ValueError: If any required configuration parameter is missing or invalid.

        Example:
            >>> config = DatabaseConfig(
            ...     driver=DatabaseDriver.MYSQL,
            ...     host='localhost',
            ...     port=3306,
            ...     database='myapp',
            ...     username='user',
            ...     password='pass123'
            ... )
            >>> async_url = config.async_database_url
            >>> print(async_url.get_secret_value())
            'mysql+aiomysql://user:pass123@localhost:3306/myapp?charset=utf8mb4&collation=utf8mb4_unicode_ci&use_unicode=1&autocommit=true'

        Note:
            Only MYSQL and SQLITE support async drivers in this configuration.
            If already using an async driver (MYSQL_ASYNC or SQLITE_ASYNC),
            returns the current database_url. The async driver plugin must be
            installed (e.g., 'aiomysql' for MySQL, 'aiosqlite' for SQLite).
        """
        async_drivers = {
            DatabaseDriver.MYSQL: DatabaseDriver.MYSQL_ASYNC,
            DatabaseDriver.SQLITE: DatabaseDriver.SQLITE_ASYNC,
        }

        # If already an async driver, return the current database_url
        if self.driver in [DatabaseDriver.MYSQL_ASYNC, DatabaseDriver.SQLITE_ASYNC]:
            return self.database_url

        if self.driver in async_drivers:
            # Create a temporary config with async driver
            temp_config_data = self.model_dump(
                exclude={"database_url", "async_database_url"}
            )
            temp_config_data["driver"] = async_drivers[self.driver]
            temp_config = DatabaseConfig(**temp_config_data)
            return temp_config.database_url

        return None


class Settings(BaseSettings):
    """Application settings with environment-specific configuration.

    This class aggregates all application-level settings including database
    configuration, logging, API settings, and cache configuration. It supports
    loading from environment variables, .env files, and programmatic configuration.

    Attributes:
        app_name (str): Application name for logging and identification.
        version (str): Application version for tracking and compatibility.
        debug (bool): Enable debug mode with detailed error messages.
        environment (Environment): Runtime environment (development, testing, staging, production).
        database (DatabaseConfig): Database connection and pool configuration.
        log_level (str): Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_format (str): Log message format string.
        api_host (str): API server host address for HTTP services.
        api_port (int): API server port number. Range: 1-65535.
        redis_url (str | None): Redis connection URL for caching (optional).
        cache_ttl (int): Cache time-to-live in seconds for cached data.

    Note:
        Settings can be configured through environment variables (VGNC prefix),
        .env files in the project root, or programmatically. The Settings class
        provides convenience methods for environment detection.

    Example:
        >>> settings = Settings()
        >>> print(settings.app_name)
        'VGNC ORM'
        >>> print(settings.is_production())
        False
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = Field(default="VGNC ORM", description="Application name")
    version: str = Field(default="0.2.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: Environment = Field(
        default=Environment.DEVELOPMENT, description="Application environment"
    )

    # Database configuration
    database: DatabaseConfig = Field(
        default_factory=lambda: DatabaseConfig(
            driver=DatabaseDriver.MYSQL, host="localhost", port=3306, database="vgnc"
        ),
        description="Database configuration",
    )

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(
        default="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        description="Log format",
    )

    # API settings (if applicable)
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API port")

    # Cache settings
    redis_url: str | None = Field(default=None, description="Redis connection URL")
    cache_ttl: int = Field(default=3600, ge=1, description="Cache TTL in seconds")

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v: Any) -> Any:
        """Normalize log level to uppercase."""
        if isinstance(v, str):
            return v.upper()
        return v

    def get_database_url(self, use_async: bool = False) -> SecretStr:
        """Get the appropriate database URL based on async requirement.

        Returns either the synchronous or asynchronous database URL based on the
        use_async parameter. This method automatically falls back to sync URL if
        async is not supported by the current database driver.

        Args:
            use_async (bool): If True, returns async database URL. If False,
                returns synchronous database URL. Default is False.

        Returns:
            SecretStr: The database URL suitable for creating either sync or async
                SQLAlchemy engines. The URL is wrapped in SecretStr for security.

        Example:
            >>> settings = Settings()
            >>> sync_url = settings.get_database_url(use_async=False)
            >>> async_url = settings.get_database_url(use_async=True)
            >>> print(async_url or sync_url)
            SecretStr('mysql+pymysql://...')
        """
        if use_async:
            async_url = self.database.async_database_url
            return async_url if async_url else self.database.database_url
        return self.database.database_url

    def is_development(self) -> bool:
        """Check if running in development environment.

        Returns:
            bool: True if the current environment is DEVELOPMENT, False otherwise.

        Example:
            >>> settings = Settings()
            >>> settings.environment = Environment.DEVELOPMENT
            >>> print(settings.is_development())
            True
        """
        return self.environment == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        """Check if running in testing environment.

        Returns:
            bool: True if the current environment is TESTING, False otherwise.

        Example:
            >>> settings = Settings()
            >>> settings.environment = Environment.TESTING
            >>> print(settings.is_testing())
            True
        """
        return self.environment == Environment.TESTING

    def is_production(self) -> bool:
        """Check if running in production environment.

        Returns:
            bool: True if the current environment is PRODUCTION, False otherwise.

        Example:
            >>> settings = Settings()
            >>> settings.environment = Environment.PRODUCTION
            >>> print(settings.is_production())
            True
        """
        return self.environment == Environment.PRODUCTION


# Global settings instance will be initialized lazily
settings: Settings | None = None


def get_settings() -> Settings:
    """Get or create global settings instance.

    This function implements the singleton pattern for application settings,
    ensuring that only one Settings instance exists throughout the application
    lifecycle. The instance is created lazily on first access.

    Returns:
        Settings: The global application settings instance. Creates the instance
            on first call if it doesn't exist, otherwise returns the existing instance.

    Example:
        >>> settings1 = get_settings()
        >>> settings2 = get_settings()
        >>> print(settings1 is settings2)  # Same instance
        True
        >>> print(settings1.app_name)
        'VGNC ORM'

    Note:
        This function should be used instead of directly instantiating Settings()
        to ensure consistent configuration throughout the application.
        The global settings instance is created with default configuration
        unless environment variables or .env files are present.
    """
    global settings
    if settings is None:
        settings = Settings()
    return settings
