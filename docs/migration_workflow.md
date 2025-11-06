# Migration Workflow

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
3. Execute safety validator (`migrations/safety.py`).
4. Inspect generated objects / indexes.
5. Promote migration to target environment.

## Example

```bash
python scripts/migration_workflow.py create --message "add species index"
python scripts/migration_workflow.py test --revision <rev_id>
python scripts/migration_workflow.py status
```

### Programmatic Invocation

```python
from scripts.migration_workflow import MigrationWorkflow
mw = MigrationWorkflow(alembic_ini_path="alembic.ini")
rev = mw.create_revision(message="add activity flag")
mw.test_revision(rev)
mw.validate_revision(rev)
```
