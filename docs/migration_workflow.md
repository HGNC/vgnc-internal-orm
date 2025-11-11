# Migration Workflow

**VGNC Internal ORM v0.2.0** - MIT License

`scripts/migration_workflow.py` orchestrates Alembic tasks for a safer and repeatable migration lifecycle.

## Capabilities

- Create revision (autogenerate or manual).
- Apply upgrade to ephemeral test DB (often SQLite temp file).
- Rollback (downgrade) validation.
- Status reporting of heads & branches.
- Validation checklist output.

## Typical Sequence

1. Author or autogenerate revision.
2. Run workflow script → applies migration on temp DB.
3. Execute safety validator (automatically invoked by workflow script using `vgnc_internal_orm.migrations.safety`).
4. Inspect generated objects / indexes.
5. Promote migration to target environment.

## Example

```bash
# Using the script directly
python scripts/migration_workflow.py create --message "add species index"
python scripts/migration_workflow.py test --revision <rev_id>
python scripts/migration_workflow.py status

# Using the CLI (alternative interface)
vgnc-cli migration create --message "add species index"
vgnc-cli migration test --revision <rev_id>
vgnc-cli migration status

# Or via Python module
python -m vgnc_internal_orm.cli migration create --message "add species index"
python -m vgnc_internal_orm.cli migration test --revision <rev_id>
python -m vgnc_internal_orm.cli migration status
```

### Programmatic Invocation

```python
from scripts.migration_workflow import MigrationWorkflow
mw = MigrationWorkflow(alembic_ini_path="alembic.ini")
rev = mw.create_revision(message="add activity flag")
mw.test_revision(rev)
mw.validate_revision(rev)
```
