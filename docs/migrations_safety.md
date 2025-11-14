# Migration Safety

**VGNC Internal ORM v0.2.0** - MIT License

`vgnc_internal_orm.migrations.safety` provides comprehensive validators to detect high-risk operations (dropping columns, destructive data changes, missing transaction wrappers) before deployment.

## Validator Functions

- `validate_migration_safety(migration_file, production_mode=False)` → List of `SafetyIssue` objects with risk classifications.
- `print_safety_report(issues)` → Human-readable formatted report.
- `MigrationSafetyValidator` → Core validation class with customizable patterns.
- `ProductionSafetyValidator` → Additional production-specific checks.

## Checks Performed

- **Destructive Operations**: DROP TABLE, DROP COLUMN, TRUNCATE, DELETE FROM
- **Data Modifications**: UPDATE, ALTER COLUMN TYPE, MODIFY COLUMN  
- **Constraint Changes**: DROP INDEX, DROP CONSTRAINT, ADD UNIQUE constraints
- **Performance Concerns**: ADD NOT NULL COLUMN, CREATE INDEX on large tables
- **Downgrade Logic**: Presence and implementation of rollback functions
- **Transaction Safety**: Explicit transaction boundaries for data operations
- **Error Handling**: Try-except blocks around risky operations

## Risk Levels

- **CRITICAL**: Irreversible data loss (DROP TABLE, TRUNCATE)
- **HIGH**: Significant risk (DROP COLUMN, DELETE without WHERE)
- **MEDIUM**: Requires review (ALTER COLUMN TYPE, constraint changes)
- **LOW**: Minor concerns (CREATE INDEX, informational)

## Usage

### Standalone Validation

```python
from vgnc_internal_orm.migrations.safety import validate_migration_safety, print_safety_report

# Validate a single migration file
issues = validate_migration_safety('alembic/versions/001_initial.py')
print_safety_report(issues)

# Production mode validation (stricter checks)
issues = validate_migration_safety('alembic/versions/001_initial.py', production_mode=True)
```

### Integrated with Workflow

The safety module is automatically invoked by `.github/scripts/migration_workflow.py`:

```bash
# Validates migration using safety module (script)
python .github/scripts/migration_workflow.py validate --file alembic/versions/001_initial.py

# Test migration (includes safety validation) (script)
python .github/scripts/migration_workflow.py test --revision <rev_id>

# Using CLI (alternative interface)
vgnc-cli migration validate --file alembic/versions/001_initial.py
vgnc-cli migration test --revision <rev_id>

# Using Python module (alternative interface)
python -m vgnc_internal_orm.cli migration validate --file alembic/versions/001_initial.py
python -m vgnc_internal_orm.cli migration test --revision <rev_id>
```

### CI Integration

```bash
# In CI pipeline, fail on critical/high risk issues
python -c "
from vgnc_internal_orm.migrations.safety import validate_migration_safety, RiskLevel
import sys

issues = validate_migration_safety('alembic/versions/latest.py')
has_critical = any(i.risk_level == RiskLevel.CRITICAL for i in issues)
has_high = any(i.risk_level == RiskLevel.HIGH for i in issues)

if has_critical or has_high:
    print('❌ Migration contains high-risk operations')
    sys.exit(1)
"
```

## Sample Report Output

```text
🔍 Migration Safety Report
==================================================

🚨 CRITICAL RISK ISSUES (1)
   Line 23: Dropping entire table: Table 'old_data'
      Code: op.drop_table('old_data')
      💡 Recommendation: Archive table data before dropping. Consider marking table as deprecated instead.

⚠️ HIGH RISK ISSUES (2)
   Line 45: Dropping column: Column 'legacy_field'
      Code: op.drop_column('users', 'legacy_field')
      💡 Recommendation: Archive column data or mark as deprecated instead of dropping.

   Missing downgrade function
      💡 Recommendation: Always implement downgrade function for safe rollbacks

📊 Summary: 3 safety issues found
   Review these issues before proceeding with migration
```

## Safety Checklist

1. ✅ Review all flagged risk items
2. ✅ Ensure downgrade function is implemented and tested
3. ✅ Verify transaction boundaries for data operations
4. ✅ Archive data before destructive operations
5. ✅ Test migration on staging environment
6. ✅ Have rollback plan prepared
7. ✅ Schedule during maintenance window for high-risk changes
8. ✅ Monitor application after deployment
