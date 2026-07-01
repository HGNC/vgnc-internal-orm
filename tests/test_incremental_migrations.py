"""Tests for incremental migration workflow and validation."""

import os
import sys
import tempfile
from datetime import datetime
from pathlib import Path

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Set up path for migration workflow import before importing it
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root / ".github" / "scripts"))
sys.path.insert(0, str(project_root / "scripts"))  # Fallback location

# ruff: noqa: E402, I001 - Import must come after path setup for module resolution
import migration_workflow

MigrationWorkflow = migration_workflow.MigrationWorkflow


@pytest.fixture
def test_database():
    """Create a temporary database for migration testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    engine = create_engine(f"sqlite:///{db_path}")

    yield db_path, engine

    # Cleanup
    engine.dispose()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def migration_workflow():
    """Create migration workflow instance."""
    workflow = MigrationWorkflow()
    yield workflow
    workflow.cleanup_test_databases()


class TestIncrementalMigrations:
    """Test incremental migration functionality."""

    def test_create_sample_migration(self, migration_workflow):
        """Test creating a sample migration."""
        # Create a simple model change to generate a migration
        original_cwd = os.getcwd()

        try:
            # Create a temporary migration message
            test_message = (
                f"test_add_sample_field_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            )

            # Test dry run
            success = migration_workflow.create_migration(test_message, dry_run=True)
            assert success, "Migration creation dry run should succeed"

            # We can't actually test real migration creation without modifying the project
            # but we can test the workflow logic

        finally:
            os.chdir(original_cwd)

    def test_migration_workflow_status(self, migration_workflow):
        """Test migration workflow status reporting."""
        # This should not raise an exception
        migration_workflow.show_status()

    def test_migration_workflow_validation(self, migration_workflow):
        """Test migration workflow validation."""
        # Test validation without specific file (validates current state)
        success = migration_workflow.validate_migration()
        assert success, "Migration validation should succeed"

    def test_migration_workflow_checklist(self, migration_workflow):
        """Test deployment checklist generation."""
        # This should not raise an exception
        migration_workflow.deploy_checklist()

    def test_detect_dangerous_operations(self, migration_workflow):
        """Test detection of dangerous operations in migrations."""
        # Create a temporary migration file with dangerous operations
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write('''
"""Test migration with dangerous operations."""
from alembic import op
import sqlalchemy as sa

def upgrade():
    op.drop_table('old_table')
    op.drop_column('species', 'unused_column')
    # DELETE FROM species WHERE id > 1000
    op.execute("TRUNCATE TABLE temp_table")

def downgrade():
    pass
''')
            tmp_path = tmp.name

        try:
            # Test validation - should detect dangerous operations and fail
            success = migration_workflow.validate_migration(tmp_path)
            assert not success, "Validation should fail for dangerous operations"
        finally:
            os.unlink(tmp_path)

    def test_rollback_functionality(self, migration_workflow):
        """Test migration rollback functionality."""
        # Test rollback with 1 step
        success = migration_workflow.rollback_test(steps=1)
        assert success, "Rollback test should succeed"

    def test_database_operations_after_migration(self, migration_workflow):
        """Test basic database operations after migration."""
        success = migration_workflow.test_migration()
        assert success, "Migration test should succeed"


class TestMigrationNaming:
    """Test migration naming conventions."""

    def test_migration_naming_pattern(self):
        """Test that migration files follow naming conventions."""
        alembic_cfg = Config("alembic.ini")

        # Get migration history
        history = command.history(alembic_cfg)

        if history:
            for revision in history:
                # Check that revision follows expected format (should be 12-char hash)
                assert (
                    len(revision.revision) == 12
                ), f"Revision {revision.revision} should be 12 characters"
                assert (
                    revision.revision.isalnum()
                ), f"Revision {revision.revision} should be alphanumeric"

    def test_migration_file_format(self):
        """Test that migration files are properly formatted."""
        versions_dir = Path("alembic/versions")

        if versions_dir.exists():
            for migration_file in versions_dir.glob("*.py"):
                content = migration_file.read_text()

                # Check for required elements
                assert (
                    "revision:" in content
                ), f"Migration {migration_file.name} missing revision identifier"
                assert (
                    "down_revision:" in content
                ), f"Migration {migration_file.name} missing down_revision"
                assert (
                    "def upgrade(" in content
                ), f"Migration {migration_file.name} missing upgrade function"
                assert (
                    "def downgrade(" in content
                ), f"Migration {migration_file.name} missing downgrade function"

                # Check for proper imports
                assert (
                    "import sqlalchemy as sa" in content
                ), f"Migration {migration_file.name} missing SQLAlchemy import"
                assert (
                    "from alembic import op" in content
                ), f"Migration {migration_file.name} missing Alembic op import"


class TestMigrationIntegration:
    """Test migration integration with models."""

    def test_models_work_after_migration(self, test_database):
        """Test that models work correctly after applying migrations."""
        db_path, engine = test_database

        # Apply migrations
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
        command.upgrade(alembic_cfg, "head")

        # Test models work with migrated database
        from datetime import datetime

        from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus

        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            # Create test data
            species = Species(
                taxon_id=9606,
                genefam_prefix="HSA",
                display_name="human (Homo sapiens)",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species)
            session.commit()

            # Query data
            saved = session.query(Species).filter(Species.taxon_id == 9606).first()
            assert saved is not None
            assert saved.display_name == "human (Homo sapiens)"

        finally:
            session.close()

    def test_migration_history_consistency(self, test_database):
        """Test that migration history is consistent."""
        db_path, engine = test_database

        # Apply migrations
        alembic_cfg = Config("alembic.ini")
        alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")
        command.upgrade(alembic_cfg, "head")

        # Check alembic version table
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()

        # Check that current command returns same version
        current = command.current(alembic_cfg)
        # Note: command.current() may return None in some configurations,
        # but the database should still have the correct version
        if current is not None:
            assert (
                current == version
            ), f"Current version {current} doesn't match alembic_version table {version}"

            # Check that heads command matches
            heads = command.heads(alembic_cfg)
            assert (
                current == heads[0]
            ), f"Current version {current} doesn't match head {heads[0]}"
        else:
            # If current returns None, verify that the database has a version
            assert (
                version is not None
            ), "Database should have a version in alembic_version table"

            # Check that heads command returns the same version as in database
            heads = command.heads(alembic_cfg)
            if heads:
                assert (
                    version == heads[0]
                ), f"Database version {version} doesn't match head {heads[0]}"


class TestMigrationCommands:
    """Test command-line migration functionality."""

    def test_alembic_commands_available(self):
        """Test that basic Alembic commands are available."""
        alembic_cfg = Config("alembic.ini")

        # These should not raise exceptions
        command.current(alembic_cfg)
        command.history(alembic_cfg)
        command.heads(alembic_cfg)

    def test_migration_help_output(self):
        """Test that migration script provides help."""
        import sys
        from io import StringIO

        # `migration_workflow` is already importable as a top-level module
        # (.github/scripts is on sys.path from the module-level setup above).
        # Use an explicit import (not the bare name) because this test module
        # also defines a *fixture* named `migration_workflow` that shadows the
        # module-level import within method scope.
        from migration_workflow import main

        # Capture help output
        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            # Run with --help to check it doesn't crash
            sys.argv = ["migration_workflow.py", "--help"]
            with pytest.raises(SystemExit) as exc_info:
                main()
            assert exc_info.value.code == 0, "Help should exit with code 0"
        finally:
            sys.stdout = old_stdout

    def test_migration_workflow_commands(self):
        """Test migration workflow command structure."""
        workflow = MigrationWorkflow()

        # These should not raise exceptions
        workflow.show_status()
        workflow.deploy_checklist()

        # Cleanup
        workflow.cleanup_test_databases()
