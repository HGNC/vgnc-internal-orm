"""Configuration management settings for VGNC ORM."""

from db_common import DatabaseDriver, DatabaseSettings
from pydantic import SecretStr
from sqlalchemy import URL

__all__ = ["DatabaseConfig", "DatabaseDriver"]


class DatabaseConfig(DatabaseSettings):
    """Main configuration class for database connection settings.

    This class extends db_common.DatabaseSettings to provide the VGNC ORM
    configuration interface. It keeps the environment variable loading behavior
    with the ``DB_`` prefix and adds a compatibility shim for ``database_url``.

    Attributes:
        driver: Database driver (from db_common.DatabaseDriver).
        host: Database host.
        port: Database port.
        username: Database username.
        password: Database password.
        database: Database name.
        pool_size: Connection pool size.
        max_overflow: Maximum overflow connections.
        pool_recycle: Connection recycle time in seconds.
        pool_pre_ping: Enable connection pre-ping.
        charset: Connection charset (MySQL only).
        collation: Optional connection collation (MySQL only).

    Note:
        Configuration can be loaded from environment variables with the ``DB_`` prefix,
        from .env files, or programmatically. This class is a thin wrapper around
        db_common.DatabaseSettings to maintain compatibility.

    Example:
        >>> config = DatabaseConfig(
        ...     driver="mysql+pymysql",
        ...     host='localhost',
        ...     port=3306,
        ...     database='myapp',
        ...     username='app_user',
        ...     password='pass123'
        ... )
        >>> url = config.get_url()
    """

    # Keep the same env_prefix behavior as before
    model_config = DatabaseSettings.model_config.copy()
    model_config.update(
        {
            "env_file": ".env",
            "env_file_encoding": "utf-8",
            "extra": "ignore",
            "case_sensitive": False,
        }
    )

    def get_url(self) -> URL:
        """Build a SQLAlchemy URL from the settings.

        Overrides db_common's get_url() to preserve VGNC's SQLite behavior
        where the database file name is used instead of :memory:.

        For non-SQLite drivers, delegates to the parent db_common implementation.

        Returns:
            URL: The SQLAlchemy connection URL.

        Example:
            >>> config = DatabaseConfig(
            ...     driver="sqlite",
            ...     database='myapp.db'
            ... )
            >>> url = config.get_url()
            >>> str(url)
            'sqlite:///myapp.db'
        """
        # For SQLite, use the provided database name (not :memory: like db-common does)
        if self.driver == "sqlite":
            return URL.create(drivername="sqlite", database=self.database or ":memory:")

        # For other drivers, delegate to parent db_common implementation
        return super().get_url()

    @property
    def database_url(self) -> SecretStr:
        """Get the database URL as SecretStr for backward compatibility.

        This property provides a compatibility shim for code that expects
        database_url to return a SecretStr. It wraps the get_url() method
        which returns a sqlalchemy.URL object.

        Returns:
            SecretStr: The database URL wrapped in SecretStr for backward compatibility.

        Example:
            >>> config = DatabaseConfig(
            ...     driver="mysql+pymysql",
            ...     host='localhost',
            ...     database='myapp',
            ...     username='user',
            ...     password='pass'
            ... )
            >>> url = config.database_url
            >>> str_value = url.get_secret_value()
        """
        return SecretStr(str(self.get_url()))
