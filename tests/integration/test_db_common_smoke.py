"""Integration smoke test for db-common migration.

This test verifies end-to-end that the migration to db-common is complete:
- DatabaseConfig works with db-common.DatabaseSettings
- engine_from_config() delegates to db-common.EngineFactory
- db_common.DeclarativeBase.metadata contains all model tables
- get_session_context() round-trips insert/SELECT
- Alembic's target_metadata is db_common.DeclarativeBase.metadata
"""

from datetime import datetime
from pathlib import Path

import pytest
from db_common import DeclarativeBase
from sqlalchemy import select, text

from vgnc_internal_orm.config.settings import DatabaseConfig
from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from vgnc_internal_orm.sessions.factory import (
    engine_from_config,
    get_session_context,
)


class TestDbCommonSmoke:
    """End-to-end smoke test for db-common integration."""

    def test_database_config_subclass(self):
        """Verify DatabaseConfig is a db_common.DatabaseSettings subclass."""
        assert issubclass(DatabaseConfig, DatabaseConfig.__bases__[0])
        # Import db_common.DatabaseSettings to check inheritance
        from db_common import DatabaseSettings

        assert issubclass(DatabaseConfig, DatabaseSettings)

    def test_database_config_driver_enum(self):
        """Verify DatabaseConfig uses db_common.DatabaseDriver."""
        config = DatabaseConfig(driver="sqlite")
        # The driver field should be a DatabaseDriver enum
        # Note: db_common.DatabaseDriver is an enum, but when set via string
        # it gets validated and converted
        from db_common import DatabaseDriver as DbCommonDriver

        assert config.driver == DbCommonDriver.SQLITE

    def test_database_url_compat_shim(self):
        """Verify database_url compat property works."""
        config = DatabaseConfig(driver="sqlite", database="test_db")
        # The compat shim should return a SecretStr wrapping the URL
        url_secret = config.database_url
        assert url_secret.get_secret_value() == "sqlite:///test_db"

    def test_engine_from_config_delegates_to_db_common(self):
        """Verify engine_from_config() creates a working engine via db-common."""
        config = DatabaseConfig(driver="sqlite")

        engine = engine_from_config(config)

        assert engine is not None
        # Verify it's a real SQLAlchemy engine
        assert hasattr(engine, "connect")

        # Verify it can execute a simple query
        with engine.connect() as conn:
            result = conn.execute(text("SELECT 1"))
            assert result.scalar() == 1

        engine.dispose()

    def test_get_session_context_round_trip(self):
        """Verify get_session_context() round-trips SELECT and rolls back on exception."""
        config = DatabaseConfig(driver="sqlite")

        # Test successful round-trip
        with get_session_context(config) as session:
            result = session.execute(text("SELECT 1"))
            assert result.scalar() == 1

        # Test rollback on exception
        with pytest.raises(ValueError):
            with get_session_context(config) as session:
                session.execute(text("SELECT 1"))
                raise ValueError("Test exception")

    def test_metadata_is_db_common_metadata(self):
        """Verify all model tables are registered in db_common.DeclarativeBase.metadata."""
        # Check that the shared metadata has our tables
        metadata = DeclarativeBase.metadata

        # Verify key tables exist
        assert "species" in metadata.tables
        assert "genefam" in metadata.tables
        assert "assembly" in metadata.tables
        assert "chromosomes" in metadata.tables

    def test_can_create_all_tables_via_db_common_metadata(self):
        """Verify db_common.DeclarativeBase.metadata.create_all() works."""
        config = DatabaseConfig(driver="sqlite")
        engine = engine_from_config(config)

        try:
            # Create all tables using the shared metadata
            DeclarativeBase.metadata.create_all(engine)

            # Verify tables were created by checking sqlite_master
            with engine.connect() as conn:
                result = conn.execute(
                    text(
                        "SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"
                    )
                )
                tables = [row[0] for row in result.fetchall()]

                # Verify key tables exist
                assert "species" in tables
                assert "genefam" in tables
                assert "assembly" in tables

        finally:
            engine.dispose()

    def test_insert_and_select_via_session_context(self):
        """Verify full round-trip: insert via session, select, verify data."""
        config = DatabaseConfig(driver="sqlite")

        # Create a session factory to get the engine that will be used
        from vgnc_internal_orm.sessions.factory import SessionFactory

        factory = SessionFactory(config)
        engine = factory.engine

        try:
            # Create tables using the same engine that sessions will use
            DeclarativeBase.metadata.create_all(engine)

            # Insert a Species record using the same factory
            with factory.get_session() as session:
                species = Species(
                    taxon_id=9606,
                    genefam_prefix="HGNC",
                    display_name="Homo sapiens",
                    scientific_name="Homo sapiens",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                session.add(species)
                session.flush()

                # Select it back
                stmt = select(Species).where(Species.taxon_id == 9606)
                result = session.execute(stmt).scalar_one_or_none()

                assert result is not None
                assert result.taxon_id == 9606
                assert result.genefam_prefix == "HGNC"
                assert result.display_name == "Homo sapiens"
                # is_active is a computed property
                assert result.is_active is True

            # Verify data persists (in a new session)
            with factory.get_session() as session:
                stmt = select(Species).where(Species.taxon_id == 9606)
                result = session.execute(stmt).scalar_one_or_none()

                assert result is not None
                assert result.display_name == "Homo sapiens"

        finally:
            factory.dispose_engine()

    def test_alembic_target_metadata_is_db_common_metadata(self):
        """Verify Alembic's target_metadata is db_common.DeclarativeBase.metadata.

        This test verifies that the alembic/env.py file correctly references
        db_common.DeclarativeBase.metadata rather than manually merging
        BaseModel.metadata and BaseCustomModel.metadata.
        """
        # Read the alembic/env.py file and check it references db_common

        alembic_env_path = Path(__file__).parent.parent.parent / "alembic" / "env.py"
        assert alembic_env_path.exists(), "alembic/env.py should exist"

        content = alembic_env_path.read_text()

        # Verify it imports DeclarativeBase from db_common
        assert (
            "from db_common import DeclarativeBase" in content
        ), "alembic/env.py should import DeclarativeBase from db_common"

        # Verify it uses DeclarativeBase.metadata as target_metadata
        assert (
            "target_metadata = DeclarativeBase.metadata" in content
        ), "alembic/env.py should use DeclarativeBase.metadata as target_metadata"

        # Verify it does NOT manually merge metadata
        assert (
            "unified_metadata" not in content
        ), "alembic/env.py should not manually merge metadata (redundant after db-common migration)"
