"""Configuration management settings for VGNC ORM."""

import os
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class DatabaseDriver(str, Enum):
    """Supported database drivers."""
    POSTGRES = "postgresql"
    POSTGRES_ASYNC = "postgresql+asyncpg"
    MYSQL = "mysql"
    MYSQL_ASYNC = "mysql+aiomysql"
    SQLITE = "sqlite"
    SQLITE_ASYNC = "sqlite+aiosqlite"


class Environment(str, Enum):
    """Supported environments."""
    DEVELOPMENT = "development"
    TESTING = "testing"
    STAGING = "staging"
    PRODUCTION = "production"


class ConnectionPoolSettings(BaseModel):
    """Database connection pool settings."""
    pool_size: int = Field(default=5, ge=1, le=100, description="Connection pool size")
    max_overflow: int = Field(default=10, ge=0, le=100, description="Maximum overflow connections")
    pool_timeout: int = Field(default=30, ge=1, description="Connection timeout in seconds")
    pool_recycle: int = Field(default=3600, ge=0, description="Connection recycle time in seconds")
    pool_pre_ping: bool = Field(default=True, description="Enable connection pre-ping")


class DatabaseConfig(BaseSettings):
    """Database configuration settings with support for multiple configuration sources."""

    model_config = SettingsConfigDict(
        env_prefix="DB_",
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Core database settings
    driver: DatabaseDriver = Field(default=DatabaseDriver.POSTGRES, description="Database driver")
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, ge=1, le=65535, description="Database port")
    username: Optional[str] = Field(default=None, description="Database username")
    password: Optional[SecretStr] = Field(default=None, description="Database password")
    database: str = Field(description="Database name")
    db_schema: Optional[str] = Field(default=None, description="Database schema (optional)")

    # Connection pool settings
    pool: ConnectionPoolSettings = Field(default_factory=ConnectionPoolSettings)

    # SSL settings
    ssl_mode: Optional[str] = Field(default=None, description="SSL mode")
    ssl_cert: Optional[Path] = Field(default=None, description="SSL certificate path")
    ssl_key: Optional[Path] = Field(default=None, description="SSL key path")
    ssl_ca: Optional[Path] = Field(default=None, description="SSL CA certificate path")

    # Additional connection parameters
    connect_timeout: int = Field(default=10, ge=1, description="Connection timeout in seconds")
    query_timeout: Optional[int] = Field(default=None, ge=1, description="Query timeout in seconds")
    isolation_level: Optional[str] = Field(default=None, description="Transaction isolation level")

    # Environment-specific settings
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Application environment")
    echo: bool = Field(default=False, description="Enable SQLAlchemy query logging")

    # MySQL-specific charset settings
    charset: str = Field(default="utf8mb4", description="Database character set")
    collation: Optional[str] = Field(default="utf8mb4_unicode_ci", description="Database collation")
    use_unicode: bool = Field(default=True, description="Enable Unicode support")
    autocommit: bool = Field(default=True, description="Enable autocommit mode")

    @field_validator("username", "password", mode="before")
    @classmethod
    def validate_auth_fields(cls, v, info):
        """Validate authentication fields for non-SQLite databases."""
        return v

    @field_validator("database", mode="before")
    @classmethod
    def validate_required_fields(cls, v, info):
        """Validate that required fields are not empty."""
        if v is None or (isinstance(v, str) and not v.strip()):
            raise ValueError(f"{info.field_name} is required and cannot be empty")
        return v

    @field_validator("username", "password", mode="after")
    @classmethod
    def validate_auth_required(cls, v, info):
        """Validate that auth fields are provided for non-SQLite databases."""
        # This will be checked in model_validator
        return v

    def model_post_init(self, __context):
        """Post-initialization validation for database-specific requirements."""
        if self.driver != DatabaseDriver.SQLITE:
            if not self.username:
                raise ValueError("username is required for non-SQLite databases")
            if not self.password:
                raise ValueError("password is required for non-SQLite databases")

    @field_validator("ssl_cert", "ssl_key", "ssl_ca", mode="before")
    @classmethod
    def validate_ssl_paths(cls, v):
        """Validate SSL certificate paths exist."""
        if v is not None:
            path = Path(v)
            if not path.exists():
                raise ValueError(f"SSL certificate path does not exist: {path}")
        return v

    @property
    def database_url(self) -> SecretStr:
        """Construct the database URL from configuration."""
        if self.driver == DatabaseDriver.SQLITE:
            url = f"{self.driver.value}:///{self.database}"
        else:
            if not self.username or not self.password:
                raise ValueError("username and password are required for non-SQLite databases")

            url = (
                f"{self.driver.value}://"
                f"{self.username}:{self.password.get_secret_value()}"
                f"@{self.host}:{self.port}/{self.database}"
            )

            # Build query parameters
            query_params = []

            # Add schema if specified (PostgreSQL)
            if self.db_schema and self.driver.value.startswith("postgresql"):
                query_params.append(f"options=-csearch_path={self.db_schema}")

            # Add SSL parameters for PostgreSQL
            if self.driver.value.startswith("postgresql") and self.ssl_mode:
                query_params.append(f"sslmode={self.ssl_mode}")

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
    def async_database_url(self) -> Optional[SecretStr]:
        """Get the async database URL if available for the driver."""
        async_drivers = {
            DatabaseDriver.POSTGRES: DatabaseDriver.POSTGRES_ASYNC,
            DatabaseDriver.MYSQL: DatabaseDriver.MYSQL_ASYNC,
            DatabaseDriver.SQLITE: DatabaseDriver.SQLITE_ASYNC,
        }

        # If already an async driver, return the current database_url
        if self.driver in [DatabaseDriver.POSTGRES_ASYNC, DatabaseDriver.MYSQL_ASYNC, DatabaseDriver.SQLITE_ASYNC]:
            return self.database_url

        if self.driver in async_drivers:
            # Create a temporary config with async driver
            temp_config_data = self.model_dump(exclude={"database_url", "async_database_url"})
            temp_config_data["driver"] = async_drivers[self.driver]
            temp_config = DatabaseConfig(**temp_config_data)
            return temp_config.database_url

        return None


class Settings(BaseSettings):
    """Application settings with environment-specific configuration."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        env_nested_delimiter="__",
        extra="ignore",
        case_sensitive=False,
    )

    # Application settings
    app_name: str = Field(default="VGNC ORM", description="Application name")
    version: str = Field(default="0.1.0", description="Application version")
    debug: bool = Field(default=False, description="Enable debug mode")
    environment: Environment = Field(default=Environment.DEVELOPMENT, description="Application environment")

    # Database configuration
    database: DatabaseConfig = Field(default_factory=DatabaseConfig, description="Database configuration")

    # Logging settings
    log_level: str = Field(default="INFO", description="Logging level")
    log_format: str = Field(default="%(asctime)s - %(name)s - %(levelname)s - %(message)s", description="Log format")

    # API settings (if applicable)
    api_host: str = Field(default="0.0.0.0", description="API host")
    api_port: int = Field(default=8000, ge=1, le=65535, description="API port")

    # Cache settings
    redis_url: Optional[str] = Field(default=None, description="Redis connection URL")
    cache_ttl: int = Field(default=3600, ge=1, description="Cache TTL in seconds")

    @field_validator("log_level", mode="before")
    @classmethod
    def normalize_log_level(cls, v):
        """Normalize log level to uppercase."""
        if isinstance(v, str):
            return v.upper()
        return v

    def get_database_url(self, use_async: bool = False) -> SecretStr:
        """Get the appropriate database URL."""
        if use_async:
            async_url = self.database.async_database_url
            return async_url if async_url else self.database.database_url
        return self.database.database_url

    def is_development(self) -> bool:
        """Check if running in development environment."""
        return self.environment == Environment.DEVELOPMENT

    def is_testing(self) -> bool:
        """Check if running in testing environment."""
        return self.environment == Environment.TESTING

    def is_production(self) -> bool:
        """Check if running in production environment."""
        return self.environment == Environment.PRODUCTION


# Global settings instance will be initialized lazily
settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Get or create global settings instance."""
    global settings
    if settings is None:
        settings = Settings()
    return settings