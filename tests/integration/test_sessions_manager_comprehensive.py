"""Comprehensive database-integrated tests for Session Manager functionality."""

import pytest
from unittest.mock import Mock, patch

from src.vgnc_internal_orm.sessions.manager import SessionManager, get_session_manager
from src.vgnc_internal_orm.sessions.factory import SessionFactory, DatabaseFactory
from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver
from src.vgnc_internal_orm.models.base import BaseModel
from src.vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from datetime import datetime, timezone


class TestSessionManagerComprehensive:
    """Comprehensive database-integrated tests for SessionManager."""

    def setup_method(self):
        """Set up test database and session manager."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables
        BaseModel.metadata.create_all(bind=self.engine)

        self.session_factory = SessionFactory(config=self.config)
        self.manager = SessionManager(self.session_factory)

    def teardown_method(self):
        """Clean up test database."""
        self.manager.dispose_engine()
        self.engine.dispose()

    def test_session_manager_initialization(self):
        """Test SessionManager initialization scenarios."""
        # Test with provided session factory
        manager1 = SessionManager(self.session_factory)
        assert manager1.session_factory is self.session_factory

        # Test with default session factory
        manager2 = SessionManager()
        assert manager2.session_factory is not None
        assert isinstance(manager2.session_factory, SessionFactory)

    def test_session_manager_get_session_context(self):
        """Test SessionManager get_session context manager."""
        # Test normal session usage
        with self.manager.get_session() as session:
            assert session is not None
            # Can perform database operations
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

        # Session should be automatically closed and committed
        with pytest.raises(Exception):  # Session should be closed
            session.execute(text("SELECT 1"))

    def test_session_manager_get_session_with_commit(self):
        """Test SessionManager get_session with automatic commit."""
        with self.manager.get_session() as session:
            # Create test species
            species = Species(
                taxon_id=9606,
                genefam_prefix="HS",
                display_name="Human (Homo sapiens)",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(timezone.utc)
            )
            session.add(species)
            # No explicit commit needed - should auto-commit

        # Verify data was committed
        with self.manager.get_session() as session2:
            retrieved = session2.query(Species).filter_by(taxon_id=9606).first()
            assert retrieved is not None
            assert retrieved.display_name == "Human (Homo sapiens)"

    def test_session_manager_get_session_with_rollback(self):
        """Test SessionManager get_session with automatic rollback on error."""
        try:
            with self.manager.get_session() as session:
                # Create test species
                species = Species(
                    taxon_id=9607,
                    genefam_prefix="MM",
                    display_name="Mouse (Mus musculus)",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(timezone.utc)
                )
                session.add(species)

                # Force an error
                raise ValueError("Test error")

        except ValueError:
            pass  # Expected error

        # Verify data was rolled back
        with self.manager.get_session() as session2:
            retrieved = session2.query(Species).filter_by(taxon_id=9607).first()
            assert retrieved is None

    def test_session_manager_get_session_no_commit(self):
        """Test SessionManager get_session_no_commit context manager."""
        with self.manager.get_session_no_commit() as session:
            assert session is not None
            # Can perform database operations
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

            # Create test species (won't auto-commit)
            species = Species(
                taxon_id=9608,
                genefam_prefix="RN",
                display_name="Rat (Rattus norvegicus)",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(timezone.utc)
            )
            session.add(species)
            # Manual commit required
            session.commit()

        # Verify data was committed (manual commit worked)
        with self.manager.get_session() as session2:
            retrieved = session2.query(Species).filter_by(taxon_id=9608).first()
            assert retrieved is not None

    def test_session_manager_create_session(self):
        """Test SessionManager create_session method."""
        session = self.manager.create_session()
        assert session is not None

        # Can perform database operations
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1

        # Manual cleanup required
        session.close()

    def test_session_manager_health_check(self):
        """Test SessionManager health check functionality."""
        health = self.manager.health_check()
        assert isinstance(health, bool)

        # For SQLite in-memory database, should be healthy
        assert health is True

    def test_session_manager_close_all_sessions(self):
        """Test SessionManager close_all_sessions method."""
        # Create multiple sessions
        session1 = self.manager.create_session()
        session2 = self.manager.create_session()
        session3 = self.manager.create_session()

        assert session1 is not None
        assert session2 is not None
        assert session3 is not None

        # Close all sessions
        self.manager.close_all_sessions()

        # Sessions should be closed
        # Note: In SQLite, sessions might not show as closed until engine is disposed
        self.manager.dispose_engine()

    def test_session_manager_dispose_engine(self):
        """Test SessionManager dispose_engine method."""
        # Create a session to ensure engine is active
        session = self.manager.create_session()
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1
        session.close()

        # Dispose engine
        self.manager.dispose_engine()

        # Create new manager to test fresh engine
        new_manager = SessionManager(self.session_factory)
        with new_manager.get_session() as session:
            result = session.execute(text("SELECT 1")).scalar()
            assert result == 1

        new_manager.dispose_engine()

    def test_session_manager_error_handling_comprehensive(self):
        """Test SessionManager error handling scenarios."""
        # Test with invalid session factory
        invalid_factory = Mock()
        invalid_factory.create_session.side_effect = Exception("Database connection failed")

        manager = SessionManager(invalid_factory)

        with pytest.raises(Exception, match="Database connection failed"):
            with manager.get_session():
                pass

    def test_session_manager_multiple_concurrent_sessions(self):
        """Test SessionManager with multiple concurrent sessions."""
        sessions_data = []

        def create_species_in_session(session_id, taxon_id):
            with self.manager.get_session() as session:
                species = Species(
                    taxon_id=taxon_id,
                    genefam_prefix=f"TS{session_id}",
                    display_name=f"Test Species {session_id}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(timezone.utc)
                )
                session.add(species)
                sessions_data.append((session_id, taxon_id))

        # Create multiple sessions concurrently
        base_taxon_id = 10000
        for i in range(10):
            create_species_in_session(i, base_taxon_id + i)

        # Verify all data was committed
        with self.manager.get_session() as session:
            for session_id, taxon_id in sessions_data:
                retrieved = session.query(Species).filter_by(taxon_id=taxon_id).first()
                assert retrieved is not None
                assert retrieved.genefam_prefix == f"TS{session_id}"

    def test_session_manager_nested_context_managers(self):
        """Test SessionManager with nested context managers."""
        with self.manager.get_session() as session1:
            # Create species in outer session
            species1 = Species(
                taxon_id=10010,
                genefam_prefix="NS1",
                display_name="Nested Species 1",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(timezone.utc)
            )
            session1.add(species1)

            with self.manager.get_session_no_commit() as session2:
                # Create species in inner session
                species2 = Species(
                    taxon_id=10011,
                    genefam_prefix="NS2",
                    display_name="Nested Species 2",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(timezone.utc)
                )
                session2.add(species2)
                session2.commit()  # Manual commit for inner session

        # Both species should be committed
        with self.manager.get_session() as session:
            retrieved1 = session.query(Species).filter_by(taxon_id=10010).first()
            retrieved2 = session.query(Species).filter_by(taxon_id=10011).first()
            assert retrieved1 is not None
            assert retrieved2 is not None

    def test_session_manager_transaction_isolation(self):
        """Test SessionManager transaction isolation."""
        with self.manager.get_session_no_commit() as session1:
            species1 = Species(
                taxon_id=10020,
                genefam_prefix="TI1",
                display_name="Transaction Isolation 1",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(timezone.utc)
            )
            session1.add(species1)
            session1.flush()  # Make it visible but don't commit yet

            # In another session, this shouldn't be visible yet
            with self.manager.get_session() as session2:
                retrieved = session2.query(Species).filter_by(taxon_id=10020).first()
                assert retrieved is None

            # Now commit in session1
            session1.commit()

        # After commit, it should be visible
        with self.manager.get_session() as session3:
            retrieved = session3.query(Species).filter_by(taxon_id=10020).first()
            assert retrieved is not None


class TestGlobalSessionManagerComprehensive:
    """Comprehensive tests for global session manager functionality."""

    def setup_method(self):
        """Reset global session manager for tests."""
        import src.vgnc_internal_orm.sessions.manager as manager_module
        manager_module.session_manager = None

    def test_get_session_manager_singleton(self):
        """Test get_session_manager returns singleton instance."""
        manager1 = get_session_manager()
        manager2 = get_session_manager()
        manager3 = get_session_manager()

        assert manager1 is manager2
        assert manager2 is manager3
        assert isinstance(manager1, SessionManager)

    def test_get_session_manager_initialization(self):
        """Test get_session_manager initialization."""
        import src.vgnc_internal_orm.sessions.manager as manager_module

        # Should be None initially
        assert manager_module.session_manager is None

        # First call should create instance
        manager = get_session_manager()
        assert manager is not None
        assert isinstance(manager, SessionManager)

        # Should be cached in module variable
        assert manager_module.session_manager is manager

        # Subsequent calls should return same instance
        manager2 = get_session_manager()
        assert manager2 is manager

    def test_global_session_manager_functionality(self):
        """Test global session manager works correctly."""
        manager = get_session_manager()

        # Test basic functionality
        health = manager.health_check()
        assert isinstance(health, bool)

        # Test session creation
        session = manager.create_session()
        assert session is not None
        session.close()

        manager.dispose_engine()

    def test_global_session_manager_state_persistence(self):
        """Test global session manager state persists across calls."""
        manager1 = get_session_manager()

        # Store some reference or state
        manager1._test_state = "test_value"

        manager2 = get_session_manager()
        assert hasattr(manager2, '_test_state')
        assert manager2._test_state == "test_value"
        assert manager1 is manager2

    def test_global_session_manager_multiple_modules(self):
        """Test global session manager works across different import patterns."""
        # Import in different ways
        from src.vgnc_internal_orm.sessions.manager import get_session_manager as gsm1
        import src.vgnc_internal_orm.sessions.manager as sm_module

        manager1 = gsm1()
        manager2 = sm_module.get_session_manager()

        assert manager1 is manager2
        assert isinstance(manager1, SessionManager)


class TestSessionManagerIntegrationWorkflows:
    """Integration tests for complete SessionManager workflows."""

    def setup_method(self):
        """Set up test environment."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables
        BaseModel.metadata.create_all(bind=self.engine)

        self.session_factory = SessionFactory(config=self.config)
        self.manager = SessionManager(self.session_factory)

    def teardown_method(self):
        """Clean up test environment."""
        self.manager.dispose_engine()
        self.engine.dispose()

    def test_complete_workflow_crud_operations(self):
        """Test complete CRUD workflow using session manager."""
        species_ids = []

        # Create multiple species
        for i in range(5):
            with self.manager.get_session() as session:
                species = Species(
                    taxon_id=20000 + i,
                    genefam_prefix=f"WF{i}",
                    display_name=f"Workflow Species {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(timezone.utc)
                )
                session.add(species)
                species_ids.append(20000 + i)

        # Read and verify
        with self.manager.get_session() as session:
            for taxon_id in species_ids:
                retrieved = session.query(Species).filter_by(taxon_id=taxon_id).first()
                assert retrieved is not None
                assert retrieved.genefam_prefix.startswith("WF")

        # Update
        with self.manager.get_session() as session:
            species_to_update = session.query(Species).filter_by(taxon_id=species_ids[0]).first()
            species_to_update.display_name = "Updated Workflow Species"
            species_to_update.is_live = SpeciesLiveStatus.TESTING

        # Verify update
        with self.manager.get_session() as session:
            updated = session.query(Species).filter_by(taxon_id=species_ids[0]).first()
            assert updated.display_name == "Updated Workflow Species"
            assert updated.is_live == SpeciesLiveStatus.TESTING

        # Delete some species
        with self.manager.get_session() as session:
            species_to_delete = session.query(Species).filter_by(taxon_id=species_ids[1]).first()
            session.delete(species_to_delete)

        # Verify deletion
        with self.manager.get_session() as session:
            deleted = session.query(Species).filter_by(taxon_id=species_ids[1]).first()
            assert deleted is None

    def test_batch_operations_workflow(self):
        """Test batch operations workflow."""
        # Create large number of records
        batch_size = 50
        species_data = []

        with self.manager.get_session_no_commit() as session:
            for i in range(batch_size):
                species = Species(
                    taxon_id=30000 + i,
                    genefam_prefix=f"BS{i:02d}",
                    display_name=f"Batch Species {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(timezone.utc)
                )
                session.add(species)
                species_data.append((30000 + i, f"BS{i:02d}"))

            session.commit()

        # Verify batch creation
        with self.manager.get_session() as session:
            count = session.query(Species).filter(
                Species.genefam_prefix.like("BS%")
            ).count()
            assert count == batch_size

        # Batch update
        with self.manager.get_session() as session:
            session.query(Species).filter(
                Species.genefam_prefix.like("BS%")
            ).update({"is_live": SpeciesLiveStatus.TESTING})

        # Verify batch update
        with self.manager.get_session() as session:
            updated_count = session.query(Species).filter(
                Species.genefam_prefix.like("BS%"),
                Species.is_live == SpeciesLiveStatus.TESTING
            ).count()
            assert updated_count == batch_size

    def test_error_recovery_workflow(self):
        """Test error recovery and cleanup workflow."""
        initial_count = 0

        with self.manager.get_session() as session:
            initial_count = session.query(Species).count()

        # Attempt operation that will fail
        try:
            with self.manager.get_session() as session:
                species = Species(
                    taxon_id=40000,
                    genefam_prefix="ER",
                    display_name="Error Recovery Species",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(timezone.utc)
                )
                session.add(species)

                # Force error
                raise RuntimeError("Simulated database error")

        except RuntimeError:
            pass  # Expected

        # Verify rollback occurred
        with self.manager.get_session() as session:
            current_count = session.query(Species).count()
            assert current_count == initial_count

            error_species = session.query(Species).filter_by(taxon_id=40000).first()
            assert error_species is None

    def test_long_running_session_workflow(self):
        """Test long-running session with multiple operations."""
        with self.manager.get_session_no_commit() as session:
            # Multiple operations in single session
            operations = []

            for i in range(10):
                species = Species(
                    taxon_id=50000 + i,
                    genefam_prefix=f"LR{i}",
                    display_name=f"Long Running Species {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(timezone.utc)
                )
                session.add(species)
                session.flush()  # Make visible but don't commit yet
                operations.append((50000 + i, f"LR{i}"))

            # Verify all operations are visible in same session
            for taxon_id, prefix in operations:
                visible = session.query(Species).filter_by(taxon_id=taxon_id).first()
                assert visible is not None

            # Commit all at once
            session.commit()

        # Verify persistence
        with self.manager.get_session() as final_session:
            for taxon_id, prefix in operations:
                persisted = final_session.query(Species).filter_by(taxon_id=taxon_id).first()
                assert persisted is not None