"""Tests for migration safety validation system."""

import os
import tempfile
from pathlib import Path

from src.vgnc_internal_orm.migrations.safety import (
    MigrationSafetyValidator,
    ProductionSafetyValidator,
    RiskLevel,
    SafetyIssue,
    print_safety_report,
    validate_migration_safety,
)


class TestMigrationSafetyValidator:
    """Test migration safety validation functionality."""

    def test_detect_dangerous_operations(self):
        """Test detection of dangerous operations in migrations."""
        validator = MigrationSafetyValidator()

        # Create temporary migration with dangerous operations
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(
                """
def upgrade():
    op.drop_table('old_table')
    op.drop_column('users', 'password')
    DELETE FROM sessions WHERE created < '2020-01-01'
    TRUNCATE TABLE temp_data

def downgrade():
    pass
"""
            )
            tmp_path = tmp.name

        try:
            issues = validator.validate_migration_file(tmp_path)

            # Should detect multiple dangerous operations
            risk_levels = [issue.risk_level for issue in issues]
            assert (
                RiskLevel.CRITICAL in risk_levels
            ), "Should detect CRITICAL risk operations"
            assert RiskLevel.HIGH in risk_levels, "Should detect HIGH risk operations"

            # Check for specific issues
            messages = [issue.message for issue in issues]
            assert any(
                "Dropping entire table" in msg for msg in messages
            ), "Should detect table dropping"
            assert any(
                "Dropping column" in msg for msg in messages
            ), "Should detect column dropping"
            assert any(
                "Direct DELETE operation" in msg for msg in messages
            ), "Should detect DELETE operations"
            assert any(
                "Truncating table data" in msg for msg in messages
            ), "Should detect TRUNCATE operations"

        finally:
            os.unlink(tmp_path)

    def test_detect_missing_downgrade(self):
        """Test detection of missing downgrade function."""
        validator = MigrationSafetyValidator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(
                """
def upgrade():
    op.create_table('new_table', sa.Column('id', sa.Integer(), nullable=False))

# Missing downgrade function
"""
            )
            tmp_path = tmp.name

        try:
            issues = validator.validate_migration_file(tmp_path)

            # Should detect missing downgrade
            downgrade_issues = [
                issue
                for issue in issues
                if "Missing downgrade function" in issue.message
            ]
            assert len(downgrade_issues) > 0, "Should detect missing downgrade function"

            # Check risk level
            if downgrade_issues:
                assert (
                    downgrade_issues[0].risk_level == RiskLevel.HIGH
                ), "Missing downgrade should be HIGH risk"

        finally:
            os.unlink(tmp_path)

    def test_detect_empty_downgrade(self):
        """Test detection of empty downgrade function."""
        validator = MigrationSafetyValidator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(
                """
def upgrade():
    op.create_table('new_table', sa.Column('id', sa.Integer(), nullable=False))

def downgrade():
    pass
"""
            )
            tmp_path = tmp.name

        try:
            issues = validator.validate_migration_file(tmp_path)

            # Should detect empty downgrade
            downgrade_issues = [
                issue for issue in issues if "contains only 'pass'" in issue.message
            ]
            assert len(downgrade_issues) > 0, "Should detect empty downgrade function"

        finally:
            os.unlink(tmp_path)

    def test_detect_broad_data_operations(self):
        """Test detection of broad data operations."""
        validator = MigrationSafetyValidator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(
                """
def upgrade():
    # Broad UPDATE without LIMIT
    connection = op.get_bind()
    connection.execute(text("UPDATE users SET status = 'inactive' WHERE active = TRUE"))

    # Broad DELETE without LIMIT
    connection.execute(text("DELETE FROM temp_table WHERE created IS NOT NULL"))

def downgrade():
    pass
"""
            )
            tmp_path = tmp.name

        try:
            issues = validator.validate_migration_file(tmp_path)

            # Should detect broad data operations
            broad_issues = [
                issue
                for issue in issues
                if "Broad data operation detected" in issue.message
            ]
            assert len(broad_issues) > 0, "Should detect broad data operations"

        finally:
            os.unlink(tmp_path)

    def test_safe_migration_validation(self):
        """Test validation of safe migrations."""
        validator = MigrationSafetyValidator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(
                """
def upgrade():
    # Safe operations
    op.add_column('users', sa.Column('email', sa.String(255), nullable=True))
    op.create_index('idx_users_email', 'users', ['email'])

def downgrade():
    op.drop_index('idx_users_email', table_name='users')
    op.drop_column('users', 'email')
"""
            )
            tmp_path = tmp.name

        try:
            issues = validator.validate_migration_file(tmp_path)

            # Should have no critical issues
            critical_issues = [
                issue for issue in issues if issue.risk_level == RiskLevel.CRITICAL
            ]
            assert (
                len(critical_issues) == 0
            ), "Safe migration should have no critical issues"

            # May have low/medium risk issues (like recommendations)
            assert len(issues) <= 2, "Safe migration should have minimal issues"

        finally:
            os.unlink(tmp_path)

    def test_risk_level_adjustment(self):
        """Test risk level adjustment based on additional factors."""
        validator = MigrationSafetyValidator()

        # Test with production keywords
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(
                """
def upgrade():
    # Dangerous operation in production context
    op.drop_column('users', 'old_password', schema='PROD')
    op.drop_column('users', 'temp_field', schema='production')

def downgrade():
    pass
"""
            )
            tmp_path = tmp.name

        try:
            issues = validator.validate_migration_file(tmp_path)

            # Should have critical risk due to production keywords
            critical_issues = [
                issue for issue in issues if issue.risk_level == RiskLevel.CRITICAL
            ]
            assert (
                len(critical_issues) > 0
            ), "Production context should raise risk to CRITICAL"

        finally:
            os.unlink(tmp_path)

    def test_recommendation_generation(self):
        """Test generation of safety recommendations."""
        validator = MigrationSafetyValidator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(
                """
def upgrade():
    op.drop_table('legacy_data')

def downgrade():
    pass
"""
            )
            tmp_path = tmp.name

        try:
            issues = validator.validate_migration_file(tmp_path)

            # Should provide recommendations for dangerous operations
            issues_with_recommendations = [
                issue for issue in issues if issue.recommendation
            ]
            assert (
                len(issues_with_recommendations) > 0
            ), "Should provide recommendations for safety issues"

            # Check recommendation content
            recommendations = [
                issue.recommendation for issue in issues_with_recommendations
            ]
            assert any(
                "archive" in rec.lower() for rec in recommendations
            ), "Should suggest archiving for table drops"

        finally:
            os.unlink(tmp_path)

    def test_line_number_tracking(self):
        """Test that line numbers are correctly tracked."""
        validator = MigrationSafetyValidator()

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(
                """

def upgrade():
    # Line 5 - dangerous operation
    op.drop_table('users')

    # Safe operation
    op.add_column('users', sa.Column('email', sa.String(255)))

def downgrade():
    pass
"""
            )
            tmp_path = tmp.name

        try:
            issues = validator.validate_migration_file(tmp_path)

            # Should track line numbers
            issues_with_lines = [
                issue for issue in issues if issue.line_number is not None
            ]
            assert len(issues_with_lines) > 0, "Should track line numbers for issues"

            # Check specific line number
            drop_issues = [
                issue for issue in issues if "Dropping table" in issue.message
            ]
            if drop_issues:
                assert (
                    drop_issues[0].line_number == 5
                ), "Should correctly identify line 5"

        finally:
            os.unlink(tmp_path)


class TestProductionSafetyValidator:
    """Test production-specific safety validation."""

    def test_production_approval_requirements(self):
        """Test production approval requirements."""
        # Set up environment for testing
        old_approvals = os.environ.get("MIGRATION_APPROVALS")
        os.environ["MIGRATION_APPROVALS"] = "dba,lead,architect"

        try:
            validator = ProductionSafetyValidator()
            is_ready, issues = validator.validate_production_readiness("dummy_file.py")

            # Should require approvals
            assert not is_ready, "Should not be ready without approvals"
            assert any(
                "dba" in issue for issue in issues
            ), "Should require DBA approval"
            assert any(
                "lead" in issue for issue in issues
            ), "Should require lead approval"
            assert any(
                "architect" in issue for issue in issues
            ), "Should require architect approval"

        finally:
            # Restore environment
            if old_approvals:
                os.environ["MIGRATION_APPROVALS"] = old_approvals
            else:
                os.environ.pop("MIGRATION_APPROVALS", None)

    def test_backup_requirement(self):
        """Test backup requirement validation."""
        # Set up environment
        old_backup = os.environ.get("MIGRATION_BACKUP_REQUIRED")
        os.environ["MIGRATION_BACKUP_REQUIRED"] = "true"

        try:
            validator = ProductionSafetyValidator()
            is_ready, issues = validator.validate_production_readiness("dummy_file.py")

            # Should require backup
            assert not is_ready, "Should not be ready without backup confirmation"
            assert any(
                "backup" in issue.lower() for issue in issues
            ), "Should require backup"

        finally:
            # Restore environment
            if old_backup:
                os.environ["MIGRATION_BACKUP_REQUIRED"] = old_backup
            else:
                os.environ.pop("MIGRATION_BACKUP_REQUIRED", None)

    def test_environment_variable_validation(self):
        """Test environment variable validation."""
        # Remove required environment variables
        old_db_url = os.environ.get("DATABASE_URL")
        old_maintenance = os.environ.get("MAINTENANCE_WINDOW")

        if "DATABASE_URL" in os.environ:
            del os.environ["DATABASE_URL"]
        if "MAINTENANCE_WINDOW" in os.environ:
            del os.environ["MAINTENANCE_WINDOW"]

        try:
            validator = ProductionSafetyValidator()
            is_ready, issues = validator.validate_production_readiness("dummy_file.py")

            # Should fail without environment variables
            assert not is_ready, "Should not be ready without environment setup"
            assert (
                len(issues) >= 2
            ), "Should detect multiple missing environment variables"

        finally:
            # Restore environment
            if old_db_url:
                os.environ["DATABASE_URL"] = old_db_url
            if old_maintenance:
                os.environ["MAINTENANCE_WINDOW"] = old_maintenance

    def test_production_mode_validation(self):
        """Test production mode validation integration."""
        # Create a temporary migration with dangerous operations
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp.write(
                """
def upgrade():
    op.drop_table('users')

def downgrade():
    pass
"""
            )
            tmp_path = tmp.name

        try:
            # Set up production environment
            old_approvals = os.environ.get("MIGRATION_APPROVALS")
            os.environ["MIGRATION_APPROVALS"] = "dba"

            # Test production mode validation
            issues = validate_migration_safety(tmp_path, production_mode=True)

            # Should have both safety and production issues
            safety_issues = [
                issue for issue in issues if "Production safety" not in issue.message
            ]
            prod_issues = [
                issue for issue in issues if "Production safety" in issue.message
            ]

            assert len(safety_issues) > 0, "Should detect safety issues"
            assert len(prod_issues) > 0, "Should detect production issues"

        finally:
            # Restore environment
            if old_approvals:
                os.environ["MIGRATION_APPROVALS"] = old_approvals
            else:
                os.environ.pop("MIGRATION_APPROVALS", None)

            os.unlink(tmp_path)


class TestSafetyReporting:
    """Test safety reporting functionality."""

    def test_safety_report_formatting(self):
        """Test safety report formatting and output."""
        # Create test issues
        issues = [
            SafetyIssue(
                risk_level=RiskLevel.CRITICAL,
                message="Dropping table: 'users'",
                line_number=15,
                code_snippet="op.drop_table('users')",
                recommendation="Archive table data before dropping",
            ),
            SafetyIssue(
                risk_level=RiskLevel.MEDIUM, message="No error handling detected"
            ),
            SafetyIssue(
                risk_level=RiskLevel.LOW,
                message="Minor formatting issue",
                recommendation="Consider adding comments",
            ),
        ]

        # Capture output
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            print_safety_report(issues)
            output = sys.stdout.getvalue()

            # Check that report contains expected elements
            assert "🔍 Migration Safety Report" in output
            assert "🚨 CRITICAL RISK ISSUES" in output
            assert "⚠️ HIGH RISK ISSUES" not in output  # No high risk issues in test
            assert "⚡ MEDIUM RISK ISSUES" in output
            assert "ℹ️ LOW RISK ISSUES" in output
            assert "Line 15: Dropping table: 'users'" in output
            assert "💡 Recommendation: Archive table data before dropping" in output

        finally:
            sys.stdout = old_stdout

    def test_no_issues_report(self):
        """Test report when no safety issues are found."""
        # Capture output
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            print_safety_report([])
            output = sys.stdout.getvalue()

            # Should show success message
            assert "✅ No safety issues found" in output

        finally:
            sys.stdout = old_stdout


class TestSafetyIntegration:
    """Test integration of safety validation with migration workflow."""

    def test_integration_with_alembic_migrations(self):
        """Test safety validation with actual Alembic migration files."""
        versions_dir = Path("alembic/versions")

        if versions_dir.exists():
            validator = MigrationSafetyValidator()

            # Test validation of existing migration files
            migration_files = list(versions_dir.glob("*.py"))

            if migration_files:
                # Test the first migration file
                migration_file = str(migration_files[0])
                issues = validator.validate_migration_file(migration_file)

                # Should not crash and should return some result
                assert isinstance(issues, list), "Should return list of issues"

                # Check that issues have proper structure
                for issue in issues:
                    assert isinstance(
                        issue, SafetyIssue
                    ), "All issues should be SafetyIssue objects"
                    assert hasattr(issue, "risk_level"), "Issues should have risk level"
                    assert hasattr(issue, "message"), "Issues should have message"

    def test_validation_error_handling(self):
        """Test error handling in validation."""
        validator = MigrationSafetyValidator()

        # Test with non-existent file
        issues = validator.validate_migration_file("non_existent_file.py")
        assert len(issues) == 1, "Should return one issue for non-existent file"
        assert (
            issues[0].risk_level == RiskLevel.CRITICAL
        ), "Non-existent file should be critical risk"
        assert "not found" in issues[0].message, "Should mention file not found"

        # Test with unreadable file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as tmp:
            tmp_path = tmp.name

        # Make file unreadable (if possible on the system)
        try:
            os.chmod(tmp_path, 0o000)
            issues = validator.validate_migration_file(tmp_path)
            assert len(issues) >= 1, "Should handle unreadable file gracefully"
        finally:
            # Restore permissions and cleanup
            os.chmod(tmp_path, 0o644)
            os.unlink(tmp_path)
