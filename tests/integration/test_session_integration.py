"""Integration tests for session factory with real database connections."""

import os
import tempfile

import pytest
from sqlalchemy import Integer, String, Text, text
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from vgnc_internal_orm.config.settings import (
    DatabaseConfig,
    DatabaseDriver,
)
from vgnc_internal_orm.models.base import BaseModel
from vgnc_internal_orm.sessions.factory import (
    SessionFactory,
    check_database_connection,
    get_session_context,
)


class TestSQLiteIntegration:
    """Integration tests with SQLite database."""

    def test_sqlite_session_creation_and_usage(self):
        """Test creating and using SQLite sessions."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            config = DatabaseConfig(driver=DatabaseDriver.SQLITE, database=db_path)
            SessionFactory(config)

            # Test session creation
            with get_session_context(config) as session:
                # Create tables for both BaseModel and IntegrationTestBase
                BaseModel.metadata.create_all(session.bind)
                IntegrationTestBase.metadata.create_all(session.bind)

                # Test basic query
                result = session.execute(text("SELECT 1 as test"))
                assert result.fetchone()[0] == 1

                # Test model operations
                test_model = IntegrationTestModel(
                    name="test", description="test description"
                )
                session.add(test_model)
                session.flush()  # Get ID without committing

                assert test_model.id is not None

            # Verify persistence
            with get_session_context(config) as session:
                retrieved = (
                    session.query(IntegrationTestModel)
                    .filter(IntegrationTestModel.name == "test")
                    .first()
                )
                assert retrieved is not None
                assert retrieved.name == "test"
                assert retrieved.description == "test description"

        finally:
            # Clean up
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_sqlite_health_check(self):
        """Test SQLite health check."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            config = DatabaseConfig(driver=DatabaseDriver.SQLITE, database=db_path)
            factory = SessionFactory(config)

            # Test health check
            result = factory.health_check()
            assert result is True

            # Test connection check function
            result = check_database_connection(config)
            assert result is True

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_sqlite_pool_status(self):
        """Test SQLite pool status reporting."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            config = DatabaseConfig(driver=DatabaseDriver.SQLITE, database=db_path)
            factory = SessionFactory(config)

            # Create engine to initialize pool
            engine = factory.engine
            assert engine is not None

            # Check pool status
            status = factory.get_pool_status()
            assert "StaticPool" in status["status"]

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_sqlite_engine_independent_of_environment(self):
        """db-common owns pooling now, so the session layer no longer consults
        the (soon-to-be-removed) ``environment`` field; an engine builds and a
        health check passes regardless of the value."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            config = DatabaseConfig(
                driver=DatabaseDriver.SQLITE, database=db_path, _env_file=None
            )
            factory = SessionFactory(config)

            # Engine builds via db_common.EngineFactory and is usable.
            engine = factory.engine
            assert engine is not None
            assert engine.url.drivername == "sqlite"

            # Health check delegated to db_common.health_check.
            assert factory.health_check() is True

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


class TestSessionFactoryLifecycle:
    """Test session factory lifecycle management."""

    def test_engine_disposal(self):
        """Test proper engine disposal."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            config = DatabaseConfig(driver=DatabaseDriver.SQLITE, database=db_path)
            factory = SessionFactory(config)

            # Create engine
            engine = factory.engine
            assert engine is not None
            assert factory._engine is not None

            # Dispose engine
            factory.dispose_engine()
            assert factory._engine is None

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_multiple_sessions_same_factory(self):
        """Test creating multiple sessions from the same factory."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            config = DatabaseConfig(driver=DatabaseDriver.SQLITE, database=db_path)
            SessionFactory(config)

            # Create multiple sessions
            with get_session_context(config) as session1:
                session1.execute(text("SELECT 1"))

            with get_session_context(config) as session2:
                session2.execute(text("SELECT 1"))

            # Both should work fine
            assert True  # If we get here, everything worked

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)

    def test_session_factory_with_different_configs(self):
        """Test session factory with different configurations."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file1:
            db_path1 = tmp_file1.name
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file2:
            db_path2 = tmp_file2.name

        try:
            # echo parameter was removed in db-common migration
            config1 = DatabaseConfig(
                driver=DatabaseDriver.SQLITE, database=db_path1
            )
            config2 = DatabaseConfig(
                driver=DatabaseDriver.SQLITE, database=db_path2
            )

            factory1 = SessionFactory(config1)
            factory2 = SessionFactory(config2)

            # Both should work independently
            info1 = factory1.get_engine_info()
            info2 = factory2.get_engine_info()

            # Verify different databases.
            # get_engine_info() truncates the URL for safety, so compare the
            # underlying engine URLs directly instead of the truncated info.
            url1 = str(factory1.engine.url)
            url2 = str(factory2.engine.url)
            assert db_path1 in url1
            assert db_path2 in url2
            assert url1 != url2

        finally:
            for db_path in [db_path1, db_path2]:
                if os.path.exists(db_path):
                    os.unlink(db_path)


class TestErrorHandling:
    """Test error handling in real scenarios."""

    def test_invalid_database_path(self):
        """Test handling of invalid database path."""
        # Use a path that doesn't exist and can't be created
        invalid_path = "/invalid/path/that/does/not/exist/test.db"

        config = DatabaseConfig(driver=DatabaseDriver.SQLITE, database=invalid_path)
        factory = SessionFactory(config)

        # Health check should fail
        result = factory.health_check()
        assert result is False

        # Connection check should fail
        result = check_database_connection(config)
        assert result is False

    def test_connection_cleanup_on_error(self):
        """Test that connections are properly cleaned up even on errors."""
        with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp_file:
            db_path = tmp_file.name

        try:
            config = DatabaseConfig(driver=DatabaseDriver.SQLITE, database=db_path)

            # Test that session cleanup works even when an error occurs
            with pytest.raises(ValueError):
                with get_session_context(config) as session:
                    session.execute(text("SELECT 1"))
                    raise ValueError("Test error")

            # After the error, we should still be able to create new sessions
            with get_session_context(config) as session:
                result = session.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1

        finally:
            if os.path.exists(db_path):
                os.unlink(db_path)


# Test model for integration tests
class IntegrationTestBase(DeclarativeBase):
    """Base class for integration test models."""

    pass


class IntegrationTestModel(IntegrationTestBase):
    """Simple test model for integration testing."""

    __tablename__ = "integration_test_models"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=True)
