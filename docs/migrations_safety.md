# Migration Safety

`migrations/safety.py` supplies validators to detect high-risk operations (dropping columns, destructive data changes, missing transaction wrappers) before deployment.

## Validator Functions

- `validate_migration_safety(path)` → structured risk report.
- `print_safety_report(report)` for human-readable output.

## Checks Performed (Illustrative)

- Presence of downgrade logic.
- Transaction boundaries.
- Destructive DDL (DROP/ALTER) severity classification.
- Potential blocking operations on large tables.

## Usage

Integrate into CI prior to applying migrations:

```bash
python -c "from vgnc_internal_orm.migrations.safety import validate_migration_safety, print_safety_report; r=validate_migration_safety('alembic/versions'); print_safety_report(r)"
```

### Sample Report Snippet

```text
Revision: 2025_11_05_add_column_x
Risks:
 - HIGH: DROP COLUMN old_field (irreversible)
 - MEDIUM: ALTER TABLE species MODIFY display_name (length reduction)
Downgrade: PRESENT
Recommendations:
 - Provide data migration script for old_field archival
 - Verify length constraints in staging
```
