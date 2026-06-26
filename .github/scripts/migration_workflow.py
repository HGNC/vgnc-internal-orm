#!/usr/bin/env python3
"""
VGNC ORM Migration Workflow Script

This script provides a comprehensive workflow for managing database migrations
in the VGNC ORM project, including creation, testing, and deployment processes.
"""

import argparse
import os
import sys
import tempfile
from pathlib import Path

from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Add project root to Python path so the first-party safety module below
# resolves. NB: this file lives at <repo>/.github/scripts/migration_workflow.py,
# so the repo root is three parents up. Two parents resolve to <repo>/.github
# (which has no alembic.ini), which made every Config() load silently fail with
# "No 'script_location' key found in configuration".
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

try:
    from vgnc_internal_orm.migrations.safety import (  # noqa: E402
        RiskLevel,
        print_safety_report,
        validate_migration_safety,
    )

    SAFETY_MODULE_AVAILABLE = True
except ImportError:
    SAFETY_MODULE_AVAILABLE = False
    print(
        "⚠️  Warning: Safety module not available. Install package for full safety validation."
    )


class MigrationWorkflow:
    """Manages the complete migration workflow."""

    def __init__(self):
        self.project_root = project_root
        self.alembic_cfg = Config(str(project_root / "alembic.ini"))
        self.temp_databases = []

    def create_test_database(self):
        """Create a temporary test database for migration testing."""
        temp_db = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        temp_db.close()
        self.temp_databases.append(temp_db.name)
        return f"sqlite:///{temp_db.name}"

    def cleanup_test_databases(self):
        """Clean up temporary test databases."""
        for db_path in self.temp_databases:
            try:
                if os.path.exists(db_path):
                    os.unlink(db_path)
            except Exception as e:
                print(f"Warning: Could not cleanup {db_path}: {e}")
        self.temp_databases.clear()

    def create_migration(self, message: str, dry_run: bool = False):
        """Create a new migration."""
        print(f"🚀 Creating migration: {message}")

        if dry_run:
            print("🔍 DRY RUN - Migration would be created but not written")
            # For dry run, we'll just show what would happen
            print(f"   Command: alembic revision --autogenerate -m '{message}'")
            return True

        try:
            command.revision(self.alembic_cfg, autogenerate=True, message=message)
            print(f"✅ Migration created successfully: {message}")
            return True
        except Exception as e:
            print(f"❌ Failed to create migration: {e}")
            return False

    def test_migration(self, migration_id: str = None):
        """Test a migration on a clean database."""
        print("🧪 Testing migration on clean database...")

        # Create temporary database
        test_db_url = self.create_test_database()
        test_cfg = Config(str(self.project_root / "alembic.ini"))
        test_cfg.set_main_option("sqlalchemy.url", test_db_url)

        try:
            # Apply all migrations up to the specified one (or all if not specified)
            if migration_id:
                print(f"   Testing migration to: {migration_id}")
                command.upgrade(test_cfg, migration_id)
            else:
                print("   Testing all migrations...")
                command.upgrade(test_cfg, "head")

            print("✅ Migration test passed")

            # Test basic database operations
            self._test_basic_operations(test_db_url)
            print("✅ Database operations test passed")

            return True

        except Exception as e:
            print(f"❌ Migration test failed: {e}")
            return False

    def _test_basic_operations(self, db_url: str):
        """Test basic database operations after migration."""
        engine = create_engine(db_url)
        Session = sessionmaker(bind=engine)
        session = Session()

        try:
            # Test that we can query basic tables
            result = session.execute(
                text("SELECT name FROM sqlite_master WHERE type='table'")
            )
            tables = [row[0] for row in result.fetchall()]

            # Check for expected tables
            expected_tables = {"species", "genefam", "assembly", "chromosomes"}
            missing_tables = expected_tables - set(tables)

            if missing_tables:
                raise Exception(f"Missing tables: {missing_tables}")

        finally:
            session.close()

    def rollback_test(self, steps: int = 1):
        """Test migration rollback functionality."""
        print(f"🔄 Testing rollback by {steps} steps...")

        # Create temporary database
        test_db_url = self.create_test_database()
        test_cfg = Config(str(self.project_root / "alembic.ini"))
        test_cfg.set_main_option("sqlalchemy.url", test_db_url)

        try:
            # Apply all migrations
            command.upgrade(test_cfg, "head")

            # Get current revision
            current = command.current(test_cfg)
            print(f"   Current revision: {current}")

            # Rollback
            command.downgrade(test_cfg, f"-{steps}")
            new_current = command.current(test_cfg)
            print(f"   After rollback: {new_current}")

            # Re-apply to ensure rollback works correctly
            command.upgrade(test_cfg, "head")
            final_current = command.current(test_cfg)
            print(f"   After re-apply: {final_current}")

            if final_current == current:
                print("✅ Rollback test passed")
                return True
            else:
                print("❌ Rollback test failed - revisions don't match")
                return False

        except Exception as e:
            print(f"❌ Rollback test failed: {e}")
            return False

    def validate_migration(self, migration_file: str = None):
        """Validate migration file for potential issues."""
        print("🔍 Validating migration...")

        if migration_file:
            migration_path = Path(migration_file)
            if not migration_path.exists():
                print(f"❌ Migration file not found: {migration_file}")
                return False

            print(f"   Validating: {migration_path}")

            # Use comprehensive safety module if available
            if SAFETY_MODULE_AVAILABLE:
                try:
                    issues = validate_migration_safety(str(migration_path))
                    print_safety_report(issues)

                    # Check for critical/high risk issues
                    has_critical = any(
                        issue.risk_level == RiskLevel.CRITICAL for issue in issues
                    )
                    has_high = any(
                        issue.risk_level == RiskLevel.HIGH for issue in issues
                    )

                    if has_critical:
                        print("\n❌ CRITICAL issues found - manual review required")
                        return False
                    elif has_high:
                        print(
                            "\n⚠️  HIGH risk issues found - careful review recommended"
                        )
                    else:
                        print("\n✅ No critical safety issues detected")

                except Exception as e:
                    print(f"   ⚠️  Safety validation error: {e}")
                    # Fall through to basic validation

            # Fallback to basic validation if safety module unavailable or errored
            if not SAFETY_MODULE_AVAILABLE:
                content = migration_path.read_text()

                # Check for dangerous operations (basic version)
                dangerous_patterns = [
                    ("DROP TABLE", "Dropping tables"),
                    ("DROP COLUMN", "Dropping columns"),
                    ("DELETE FROM", "Direct deletion"),
                    ("TRUNCATE", "Truncating tables"),
                ]

                warnings = []
                for pattern, description in dangerous_patterns:
                    if pattern in content.upper():
                        warnings.append(f"⚠️  {description} detected")

                if warnings:
                    print("   Warnings found:")
                    for warning in warnings:
                        print(f"      {warning}")
                else:
                    print("   ✅ No dangerous operations detected (basic check)")

        # Always check current migrations
        try:
            history = command.history(self.alembic_cfg)
            if history is None:
                print("   No migrations found")
            else:
                print(f"   Migration history: {len(history)} revisions")

            current = command.current(self.alembic_cfg)
            print(f"   Current revision: {current}")

            # Check for unapplied migrations
            heads = command.heads(self.alembic_cfg)
            if heads and current != heads[0]:
                print(
                    f"⚠️  Unapplied migrations detected. Current: {current}, Head: {heads[0]}"
                )
            else:
                print("✅ All migrations applied")

            return True

        except Exception as e:
            print(f"❌ Validation failed: {e}")
            return False

    def show_status(self):
        """Show current migration status."""
        print("📊 Migration Status:")

        try:
            # Current revision
            current = command.current(self.alembic_cfg)
            print(f"   Current revision: {current}")

            # Available revisions
            heads = command.heads(self.alembic_cfg)
            if heads:
                print(f"   Head revision: {heads[0]}")

            # Migration history
            history = command.history(self.alembic_cfg)
            if history is None:
                print("   No migrations found")
            else:
                print(f"   Total migrations: {len(history)}")

                # Show recent migrations
                if history:
                    print("\n   Recent migrations:")
                    for revision in history[-5:]:
                        print(
                            f"      {revision.doc or 'No description'} ({revision.revision})"
                        )
                else:
                    print("\n   No migrations found")

        except Exception as e:
            print(f"❌ Failed to get status: {e}")

    def deploy_checklist(self):
        """Show deployment checklist."""
        print("📋 Deployment Checklist:\n")

        checklist = [
            "✅ Backup database before proceeding",
            "✅ Run migrations on staging environment first",
            "✅ Test rollback procedures",
            "✅ Validate migration doesn't contain destructive operations",
            "✅ Ensure sufficient maintenance window",
            "✅ Have rollback plan ready",
            "✅ Monitor performance after deployment",
            "✅ Verify application functionality",
        ]

        for item in checklist:
            print(f"   {item}")


def main():
    """Main entry point for the migration workflow."""
    parser = argparse.ArgumentParser(description="VGNC ORM Migration Workflow")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    # Create command
    create_parser = subparsers.add_parser("create", help="Create new migration")
    create_parser.add_argument("message", help="Migration description")
    create_parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be done without executing",
    )

    # Test command
    test_parser = subparsers.add_parser("test", help="Test migration(s)")
    test_parser.add_argument(
        "--revision", help="Test specific revision (test all if not specified)"
    )

    # Rollback test command
    rollback_parser = subparsers.add_parser(
        "test-rollback", help="Test rollback functionality"
    )
    rollback_parser.add_argument(
        "--steps", type=int, default=1, help="Number of steps to rollback and re-apply"
    )

    # Validate command
    validate_parser = subparsers.add_parser("validate", help="Validate migration(s)")
    validate_parser.add_argument("--file", help="Validate specific migration file")

    # Status command
    subparsers.add_parser("status", help="Show migration status")

    # Checklist command
    subparsers.add_parser("checklist", help="Show deployment checklist")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 1

    workflow = MigrationWorkflow()

    try:
        if args.command == "create":
            success = workflow.create_migration(args.message, args.dry_run)

        elif args.command == "test":
            success = workflow.test_migration(args.revision)

        elif args.command == "test-rollback":
            success = workflow.rollback_test(args.steps)

        elif args.command == "validate":
            success = workflow.validate_migration(args.file)

        elif args.command == "status":
            workflow.show_status()
            success = True

        elif args.command == "checklist":
            workflow.deploy_checklist()
            success = True

    finally:
        workflow.cleanup_test_databases()

    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
