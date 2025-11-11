#!/usr/bin/env python3
"""
Example: Testing Migration Safety Module

Demonstrates how to use the migration safety validator to check
migrations before deployment.
"""

from vgnc_internal_orm.migrations.safety import (
    validate_migration_safety,
    print_safety_report,
    RiskLevel,
)


def main():
    """Run migration safety validation examples."""
    
    print("=" * 80)
    print("MIGRATION SAFETY VALIDATION EXAMPLES")
    print("=" * 80)
    print()
    
    # Example 1: Validate the baseline migration
    print("Example 1: Validating baseline migration")
    print("-" * 80)
    
    baseline_path = "alembic/versions/2025_11_05_2253-2299f7d46a8d_initial_baseline.py"
    issues = validate_migration_safety(baseline_path)
    
    # Show summary
    critical_count = sum(1 for i in issues if i.risk_level == RiskLevel.CRITICAL)
    high_count = sum(1 for i in issues if i.risk_level == RiskLevel.HIGH)
    medium_count = sum(1 for i in issues if i.risk_level == RiskLevel.MEDIUM)
    low_count = sum(1 for i in issues if i.risk_level == RiskLevel.LOW)
    
    print(f"\nSummary:")
    print(f"  CRITICAL: {critical_count}")
    print(f"  HIGH: {high_count}")
    print(f"  MEDIUM: {medium_count}")
    print(f"  LOW: {low_count}")
    print(f"  Total: {len(issues)}")
    print()
    
    # Example 2: Check for deployment readiness
    print("\nExample 2: Check deployment readiness")
    print("-" * 80)
    
    if critical_count > 0 or high_count > 0:
        print("⚠️  Migration contains high-risk operations")
        print("   Recommendations:")
        print("   - Review all flagged operations")
        print("   - Test on staging first")
        print("   - Prepare rollback plan")
        print("   - Schedule during maintenance window")
    else:
        print("✅ Migration appears safe for deployment")
        print("   Still recommended:")
        print("   - Backup database")
        print("   - Test on staging")
    print()
    
    # Example 3: Production mode validation
    print("\nExample 3: Production mode validation (stricter checks)")
    print("-" * 80)
    
    prod_issues = validate_migration_safety(baseline_path, production_mode=True)
    
    # Count production-specific issues
    prod_specific = len(prod_issues) - len(issues)
    if prod_specific > 0:
        print(f"⚠️  {prod_specific} additional production-specific issues found")
    else:
        print(f"ℹ️  No additional production-specific issues (baseline has {len(prod_issues)} total)")
    print()
    
    # Example 4: Show full report for one migration (optional)
    print("\nExample 4: Full safety report")
    print("-" * 80)
    print("Run the following to see full report:")
    print(f"  python -c \"from vgnc_internal_orm.migrations.safety import *; print_safety_report(validate_migration_safety('{baseline_path}'))\"")
    print()
    
    # Example 5: CI/CD integration pattern
    print("\nExample 5: CI/CD Integration Pattern")
    print("-" * 80)
    print("""
# In your CI/CD pipeline (e.g., GitHub Actions, GitLab CI):

- name: Validate Migration Safety
  run: |
    python -c "
    from vgnc_internal_orm.migrations.safety import validate_migration_safety, RiskLevel
    import sys
    
    issues = validate_migration_safety('alembic/versions/latest.py')
    has_critical = any(i.risk_level == RiskLevel.CRITICAL for i in issues)
    has_high = any(i.risk_level == RiskLevel.HIGH for i in issues)
    
    if has_critical:
        print('❌ CRITICAL risk operations detected - blocking deployment')
        sys.exit(1)
    elif has_high:
        print('⚠️  HIGH risk operations detected - manual approval required')
        sys.exit(1)
    else:
        print('✅ Migration safety checks passed')
    "
    """)
    print()


if __name__ == "__main__":
    main()
