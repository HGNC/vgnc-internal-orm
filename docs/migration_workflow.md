# Migration Workflow

**VGNC Internal ORM v0.3.0** - MIT License

`.github/scripts/migration_workflow.py` orchestrates Alembic tasks for a safer and repeatable migration lifecycle.

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
python .github/scripts/migration_workflow.py create --message "add species index"
python .github/scripts/migration_workflow.py test --revision <rev_id>
python .github/scripts/migration_workflow.py status
```

Note: The workflow is provided as a standalone script. Importing it as a Python
module is not supported; invoke it via subprocess if you need to call it from code.

## Runbook (Make Targets)

Convenient wrappers are available in the `Makefile`:

```bash
# Create a new revision (autogenerate/manual per script prompts)
make migrate-create MSG="add species index"

# Test the latest (or a specific) revision on a temp DB
make migrate-test               # latest
make migrate-test REV="<rev_id>"

# Validate a specific migration file with the safety checks
make migrate-validate FILE=alembic/versions/2025_11_11_1648-39a9..._add_scientific_common_name_columns.py

# Show Alembic status
make migrate-status

# Test rollback steps (default 1). Optional REV to target a specific revision
make migrate-test-rollback STEPS=1
make migrate-test-rollback STEPS=1 REV="<rev_id>"
```

These targets call `.github/scripts/migration_workflow.py` under the hood using `uv run`.
If you prefer direct script usage, the equivalent commands are:

```bash
uv run python .github/scripts/migration_workflow.py create --message "..."
uv run python .github/scripts/migration_workflow.py test [--revision <rev_id>]
uv run python .github/scripts/migration_workflow.py validate --file <path-to-revision>
uv run python .github/scripts/migration_workflow.py status
uv run python .github/scripts/migration_workflow.py test-rollback --steps 1 [--revision <rev_id>]
```

### Database URL

The workflow script uses an ephemeral SQLite DB by default for safety. To point
at a different database for testing (e.g., local MySQL), export `DATABASE_URL`:

```bash
export DATABASE_URL="mysql+pymysql://user:pass@127.0.0.1:3306/vgnc_dev"
make migrate-test
```
