"""Unit tests for MySQL-specific utilities that don't need a live database.

These exercise code paths that previously broke after the db_common migration
without requiring a Docker/testcontainer MySQL instance.
"""

from __future__ import annotations

from sqlalchemy import Engine

from vgnc_internal_orm.config import DatabaseConfig
from vgnc_internal_orm.utils.mysql_features import MySQLConnectionPool


class TestCreateEngineWithUtf8mb4:
    """Guard against stale references to fields dropped in the db_common migration."""

    def test_does_not_reference_dropped_echo_field(self):
        """``create_engine_with_utf8mb4`` must not read the dropped ``echo`` field.

        The db_common migration removed ``echo`` from ``DatabaseConfig``
        (pinned as a dropped field in test_config_dbcommon_migration). This
        MySQL utility previously passed ``echo=config.echo`` to ``create_engine``,
        which raised ``AttributeError`` at call time. SQLAlchemy engine creation
        is lazy (it does not connect), so the method is exercised here against an
        in-process config rather than a live MySQL server.
        """
        config = DatabaseConfig(
            driver="mysql+pymysql",
            username="user",
            password="pass",
            host="localhost",
            database="testdb",
            _env_file=None,
        )

        engine = MySQLConnectionPool.create_engine_with_utf8mb4(config)

        assert isinstance(engine, Engine)
        assert str(engine.url).startswith("mysql+pymysql")
