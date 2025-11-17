"""
Migration Safety Validation Module

Provides comprehensive safety checks for database migrations to prevent
accidental data loss and ensure safe deployment practices.
"""

import os
import re
from dataclasses import dataclass
from enum import Enum
from typing import Any


class RiskLevel(Enum):
    """Risk levels for migration operations."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class SafetyIssue:
    """Represents a safety issue found in a migration."""

    risk_level: RiskLevel
    message: str
    line_number: int | None = None
    code_snippet: str | None = None
    recommendation: str | None = None


class MigrationSafetyValidator:
    """Validates migrations for safety issues and destructive operations."""

    def __init__(self) -> None:
        """Initialize MigrationSafetyValidator with safety patterns.

        Sets up dangerous operation patterns and risk assessment rules
        for comprehensive migration safety validation.
        """
        self.dangerous_patterns = self._initialize_dangerous_patterns()
        self.risk_assessments = self._initialize_risk_assessments()

    def _initialize_dangerous_patterns(self) -> list[tuple[str, str, RiskLevel]]:
        """Initialize patterns for detecting dangerous operations."""
        return [
            # Index operations (most specific, must come first)
            (r"\bdrop_index\b", "Dropping index", RiskLevel.MEDIUM),
            # Table operations (more specific to avoid matching index operations)
            (r"\bdrop_table\b", "Dropping entire table", RiskLevel.CRITICAL),
            (r"\btruncate_table\b", "Truncating table data", RiskLevel.CRITICAL),
            (
                r"\bTRUNCATE\s+TABLE\b",
                "Truncating table data",
                RiskLevel.CRITICAL,
            ),  # Raw SQL
            (r"\bdelete\s+from\b", "Direct DELETE operation", RiskLevel.HIGH),
            (
                r"\bDELETE\s+FROM\b",
                "Direct DELETE operation",
                RiskLevel.HIGH,
            ),  # Raw SQL
            # Column operations
            (r"\bdrop_column\b", "Dropping column", RiskLevel.HIGH),
            (r"\balter_table.*drop_column\b", "Dropping column", RiskLevel.HIGH),
            # Constraint operations
            (r"\bdrop_constraint\b", "Dropping constraint", RiskLevel.MEDIUM),
            (r"\bdrop_primary_key\b", "Dropping primary key", RiskLevel.HIGH),
            (r"\bdrop_foreign_key\b", "Dropping foreign key", RiskLevel.MEDIUM),
            # Type changes that might lose data
            (
                r"\balter_table.*change.*varchar.*to.*varchar\b",
                "VARCHAR length reduction",
                RiskLevel.MEDIUM,
            ),
            (
                r"\balter_table.*modify.*varchar.*to.*varchar\b",
                "VARCHAR length reduction",
                RiskLevel.MEDIUM,
            ),
            # Direct data manipulation
            (
                r"\bupdate.*set.*where.*1\s*=\s*1\b",
                "UPDATE without WHERE clause",
                RiskLevel.CRITICAL,
            ),
            (
                r"\bdelete.*where.*1\s*=\s*1\b",
                "DELETE without WHERE clause",
                RiskLevel.CRITICAL,
            ),
        ]

    def _initialize_risk_assessments(self) -> dict[str, dict[str, Any]]:
        """Initialize risk assessment rules."""
        return {
            "DROP TABLE": {
                "risk": RiskLevel.CRITICAL,
                "description": "Dropping a table permanently deletes all data",
                "recommendation": "Consider archiving data before dropping table",
            },
            "DROP COLUMN": {
                "risk": RiskLevel.HIGH,
                "description": "Dropping a column permanently deletes all data in that column",
                "recommendation": "Archive column data or mark as deprecated instead",
            },
            "DELETE FROM": {
                "risk": RiskLevel.HIGH,
                "description": "Direct DELETE operations can cause data loss",
                "recommendation": "Use soft deletes or mark records as inactive",
            },
            "TRUNCATE TABLE": {
                "risk": RiskLevel.CRITICAL,
                "description": "Truncating deletes all table data permanently",
                "recommendation": "Archive data before truncating",
            },
            "ALTER TABLE ... DROP PRIMARY KEY": {
                "risk": RiskLevel.HIGH,
                "description": "Dropping primary key can break relationships",
                "recommendation": "Ensure no dependent tables or create new primary key first",
            },
        }

    def validate_migration_file(self, file_path: str) -> list[SafetyIssue]:
        """Validate a migration file for safety issues."""
        issues = []

        if not os.path.exists(file_path):
            return [
                SafetyIssue(
                    risk_level=RiskLevel.CRITICAL,
                    message=f"Migration file not found: {file_path}",
                )
            ]

        try:
            with open(file_path, encoding="utf-8") as f:
                content = f.read()
                lines = content.splitlines()

            # Check for dangerous patterns
            for line_num, line in enumerate(lines, 1):
                issues.extend(self._check_line_for_patterns(line, line_num))

            # Check for missing downgrade function
            issues.extend(self._check_downgrade_function(content))

            # Check for missing error handling
            issues.extend(self._check_error_handling(content))

            # Check for data migration safety
            issues.extend(self._check_data_migration_safety(content, lines))

            # Check for transaction safety
            issues.extend(self._check_transaction_safety(content, lines))

        except Exception as e:
            issues.append(
                SafetyIssue(
                    risk_level=RiskLevel.MEDIUM,
                    message=f"Error reading migration file: {e}",
                )
            )

        return issues

    def _check_line_for_patterns(self, line: str, line_num: int) -> list[SafetyIssue]:
        """Check a single line for dangerous patterns."""
        issues = []
        line_upper = line.upper()

        for pattern, description, risk_level in self.dangerous_patterns:
            if re.search(pattern, line_upper, re.IGNORECASE):
                # Get more specific operation type
                operation = self._extract_operation_type(line)

                # Check for additional risk factors
                additional_risks = self._assess_additional_risks(line, line_upper)
                final_risk = self._adjust_risk_level(risk_level, additional_risks)

                # Get recommendation
                recommendation = self._get_recommendation(description, final_risk)

                issues.append(
                    SafetyIssue(
                        risk_level=final_risk,
                        message=f"{description}: {operation}",
                        line_number=line_num,
                        code_snippet=line.strip(),
                        recommendation=recommendation,
                    )
                )

        return issues

    def _extract_operation_type(self, line: str) -> str:
        """Extract the specific operation type from a line."""
        # Try to identify the specific table/object being affected
        if "TABLE" in line.upper():
            # Extract table name
            match = re.search(
                r"\b(\w+)\b", line.split("TABLE")[-1] if "TABLE" in line else ""
            )
            if match:
                return f"Table '{match.group(1)}'"

        elif "COLUMN" in line.upper():
            # Extract column name
            parts = line.upper().split("COLUMN")
            if len(parts) > 1:
                match = re.search(r"\b(\w+)\b", parts[1])
                if match:
                    return f"Column '{match.group(1)}'"

        # Fallback to generic description
        return line.strip()

    def _assess_additional_risks(self, line: str, line_upper: str) -> list[str]:
        """Assess additional risk factors in a line."""
        risks = []

        # Check for production keywords (case-insensitive)
        if any(
            keyword in line_upper for keyword in ["PROD", "PRODUCTION", "LIVE"]
        ) or any(keyword in line for keyword in ["prod", "production", "live"]):
            risks.append("production_environment")

        # Check for force operations
        if any(keyword in line_upper for keyword in ["FORCE", "CASCADE"]):
            risks.append("force_operation")

        # Check for lack of transaction control
        if not any(
            keyword in line_upper for keyword in ["BEGIN", "COMMIT", "ROLLBACK"]
        ):
            risks.append("no_transaction")

        # Check for missing WHERE clause in DELETE/UPDATE
        if any(op in line_upper for op in ["DELETE FROM", "UPDATE"]):
            if "WHERE" not in line_upper:
                risks.append("no_where_clause")

        return risks

    def _adjust_risk_level(
        self, base_risk: RiskLevel, additional_risks: list[str]
    ) -> RiskLevel:
        """Adjust risk level based on additional factors."""
        if "production_environment" in additional_risks:
            return RiskLevel.CRITICAL

        if "force_operation" in additional_risks:
            if base_risk == RiskLevel.LOW:
                return RiskLevel.MEDIUM
            elif base_risk == RiskLevel.MEDIUM:
                return RiskLevel.HIGH
            elif base_risk == RiskLevel.HIGH:
                return RiskLevel.CRITICAL

        if "no_where_clause" in additional_risks:
            return RiskLevel.CRITICAL

        return base_risk

    def _get_recommendation(self, operation: str, risk_level: RiskLevel) -> str:
        """Get safety recommendation for an operation."""
        # Check if the description (first part of message) contains 'table'
        if "Dropping entire table" in operation or "table" in operation.lower():
            if risk_level == RiskLevel.CRITICAL:
                return "Archive table data before dropping. Consider marking table as deprecated instead."

        elif "Column" in operation or "column" in operation.lower():
            if risk_level == RiskLevel.HIGH:
                return "Archive column data or mark as deprecated instead of dropping."

        elif "DELETE" in operation.upper():
            if risk_level == RiskLevel.HIGH:
                return "Consider using soft deletes or marking records as inactive."
            elif risk_level == RiskLevel.CRITICAL:
                return "Never use DELETE without WHERE clause in production!"

        return "Review this operation carefully and ensure proper backups exist."

    def _check_downgrade_function(self, content: str) -> list[SafetyIssue]:
        """Check for proper downgrade function implementation."""
        issues = []

        if "def downgrade()" not in content:
            issues.append(
                SafetyIssue(
                    risk_level=RiskLevel.HIGH,
                    message="Missing downgrade function",
                    recommendation="Always implement downgrade function for safe rollbacks",
                )
            )

        if "def downgrade()" in content and "pass" in content:
            # Check if downgrade just contains 'pass'
            lines = content.splitlines()
            downgrade_found = False
            downgrade_line = -1

            for i, line in enumerate(lines):
                if "def downgrade()" in line:
                    downgrade_found = True
                    downgrade_line = i
                elif (
                    downgrade_found
                    and line.strip()
                    and not line.strip().startswith("#")
                ):
                    if line.strip() == "pass":
                        issues.append(
                            SafetyIssue(
                                risk_level=RiskLevel.HIGH,
                                message="Downgrade function contains only 'pass'",
                                line_number=downgrade_line + 1,
                                recommendation="Implement proper rollback logic",
                            )
                        )
                    break

        return issues

    def _check_error_handling(self, content: str) -> list[SafetyIssue]:
        """Check for proper error handling in migrations."""
        issues = []

        # Check for basic error handling patterns
        if "try:" not in content and any(
            op in content.upper() for op in ["UPDATE", "DELETE", "INSERT"]
        ):
            issues.append(
                SafetyIssue(
                    risk_level=RiskLevel.MEDIUM,
                    message="No error handling detected for data operations",
                    recommendation="Wrap data operations in try-except blocks",
                )
            )

        return issues

    def _check_data_migration_safety(
        self, content: str, lines: list[str]
    ) -> list[SafetyIssue]:
        """Check for safety issues in data migration operations."""
        issues = []

        # Check for large data operations without batching
        for line_num, line in enumerate(lines, 1):
            if "UPDATE" in line.upper() or "DELETE" in line.upper():
                if "LIMIT" not in line.upper() and "WHERE" in line.upper():
                    # Check if the WHERE clause might affect many rows
                    if any(
                        broad_condition in line.upper()
                        for broad_condition in ["1=1", "TRUE", "IS NOT NULL"]
                    ):
                        issues.append(
                            SafetyIssue(
                                risk_level=RiskLevel.HIGH,
                                message="Broad data operation detected",
                                line_number=line_num,
                                code_snippet=line.strip(),
                                recommendation="Consider batching large data operations or adding LIMIT",
                            )
                        )

        return issues

    def _check_transaction_safety(
        self, content: str, lines: list[str]
    ) -> list[SafetyIssue]:
        """Check for proper transaction handling."""
        issues = []

        # Check if migration is properly wrapped in transaction
        has_begin = any("BEGIN" in line.upper() for line in lines)
        has_commit = any("COMMIT" in line.upper() for line in lines)

        if (
            not has_begin
            and not has_commit
            and any(op in content.upper() for op in ["UPDATE", "DELETE", "INSERT"])
        ):
            issues.append(
                SafetyIssue(
                    risk_level=RiskLevel.MEDIUM,
                    message="No explicit transaction control detected",
                    recommendation="Consider wrapping data operations in explicit transactions",
                )
            )

        return issues

    def validate_migration_plan(self, migrations: list[str]) -> list[SafetyIssue]:
        """Validate a migration plan (list of migrations to apply)."""
        issues = []

        # Check for too many migrations in one deployment
        if len(migrations) > 5:
            issues.append(
                SafetyIssue(
                    risk_level=RiskLevel.MEDIUM,
                    message=f"Large migration plan: {len(migrations)} migrations",
                    recommendation="Consider breaking into smaller deployment batches",
                )
            )

        # Check for risky migration combinations
        risky_combinations = self._check_migration_combinations(migrations)
        issues.extend(risky_combinations)

        return issues

    def _check_migration_combinations(self, migrations: list[str]) -> list[SafetyIssue]:
        """Check for risky combinations of migrations."""
        issues = []

        # Look for patterns that might be risky when combined
        has_destructive = any("drop" in mig.lower() for mig in migrations)
        has_data_changes = any(
            "update" in mig.lower()
            or "insert" in mig.lower()
            or "delete" in mig.lower()
            for mig in migrations
        )

        if has_destructive and has_data_changes:
            issues.append(
                SafetyIssue(
                    risk_level=RiskLevel.HIGH,
                    message="Mixing destructive and data-changing migrations",
                    recommendation="Separate destructive changes from data changes",
                )
            )

        return issues


class ProductionSafetyValidator:
    """Additional safety checks specifically for production environments."""

    def __init__(self) -> None:
        """Initialize ProductionSafetyValidator with environment-specific rules.

        Loads production safety requirements from environment variables including
        approval requirements and backup policies.
        """
        self.required_approvals = os.environ.get("MIGRATION_APPROVALS", "").split(",")
        self.backup_required = (
            os.environ.get("MIGRATION_BACKUP_REQUIRED", "true").lower() == "true"
        )

    def validate_production_readiness(
        self, migration_file: str
    ) -> tuple[bool, list[str]]:
        """Validate if migration is ready for production deployment."""
        issues = []

        # Check backup requirement
        if self.backup_required:
            issues.append("Database backup required before production deployment")

        # Check approval requirements
        if self.required_approvals:
            pending_approvals = [
                approval for approval in self.required_approvals if approval.strip()
            ]
            if pending_approvals:
                issues.append(f"Pending approvals: {', '.join(pending_approvals)}")

        # Check environment variables
        if not os.environ.get("DATABASE_URL"):
            issues.append("DATABASE_URL environment variable not set")

        # Check maintenance window
        if not os.environ.get("MAINTENANCE_WINDOW"):
            issues.append("MAINTENANCE_WINDOW not specified")

        # Run basic safety validation
        safety_validator = MigrationSafetyValidator()
        safety_issues = safety_validator.validate_migration_file(migration_file)

        # Filter for high and critical risk issues
        high_risk_issues = [
            issue
            for issue in safety_issues
            if issue.risk_level in [RiskLevel.HIGH, RiskLevel.CRITICAL]
        ]

        if high_risk_issues:
            issues.extend(
                [f"High risk operation: {issue.message}" for issue in high_risk_issues]
            )

        return len(issues) == 0, issues


def validate_migration_safety(
    migration_file: str, production_mode: bool = False
) -> list[SafetyIssue]:
    """
    Main function to validate migration safety.

    Args:
        migration_file: Path to migration file
        production_mode: Whether to apply production-specific checks

    Returns:
        List of safety issues found
    """
    validator = MigrationSafetyValidator()
    issues = validator.validate_migration_file(migration_file)

    if production_mode:
        prod_validator = ProductionSafetyValidator()
        is_ready, prod_issues = prod_validator.validate_production_readiness(
            migration_file
        )

        if not is_ready:
            for issue in prod_issues:
                issues.append(
                    SafetyIssue(
                        risk_level=RiskLevel.CRITICAL,
                        message=f"Production safety: {issue}",
                        recommendation="Address production deployment requirements",
                    )
                )

    return issues


def print_safety_report(issues: list[SafetyIssue]) -> None:
    """Print a formatted safety report."""
    if not issues:
        print("✅ No safety issues found in migration")
        return

    # Group issues by risk level
    risk_groups: dict[RiskLevel, list[SafetyIssue]] = {}
    for issue in issues:
        if issue.risk_level not in risk_groups:
            risk_groups[issue.risk_level] = []
        risk_groups[issue.risk_level].append(issue)

    # Print issues by risk level (critical first)
    risk_order = [RiskLevel.CRITICAL, RiskLevel.HIGH, RiskLevel.MEDIUM, RiskLevel.LOW]

    print("\n🔍 Migration Safety Report")
    print("=" * 50)

    for risk_level in risk_order:
        if risk_level in risk_groups:
            emoji = {"CRITICAL": "🚨", "HIGH": "⚠️", "MEDIUM": "⚡", "LOW": "ℹ️"}[
                risk_level.name
            ]
            print(
                f"\n{emoji} {risk_level.value.upper()} RISK ISSUES ({len(risk_groups[risk_level])})"
            )

            for issue in risk_groups[risk_level]:
                if issue.line_number:
                    print(f"   Line {issue.line_number}: {issue.message}")
                else:
                    print(f"   {issue.message}")

                if issue.code_snippet:
                    print(f"      Code: {issue.code_snippet}")

                if issue.recommendation:
                    print(f"      💡 Recommendation: {issue.recommendation}")

    print(f"\n📊 Summary: {len(issues)} safety issues found")
    print("   Review these issues before proceeding with migration")
