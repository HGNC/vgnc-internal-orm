# VGNC Internal ORM

Comprehensive SQLAlchemy 2.0 ORM toolkit for VGNC-style gene nomenclature data: typed models, robust configuration, optimized sessions, performance/index utilities, migration workflow & safety validation, and a flexible querying/export CLI.

## Features

- Typed declarative models with rich CRUD helpers
- Sync & async session support with tuned engine creation
- UTF8MB4 / full-text search support for MySQL
- Index definition, mapping, and schema analysis utilities
- Migration workflow script + safety validator
- CLI for querying & exporting (table / JSON / CSV / XML)

## Quick Start

```bash
pip install vgnc-internal-orm
```

```python
from vgnc_internal_orm.config.settings import get_settings
from vgnc_internal_orm.sessions.factory import SessionFactory
from vgnc_internal_orm.models.species import Species

settings = get_settings()
sf = SessionFactory(settings.database)
with sf.get_session() as session:
    first = Species.find(session, limit=1)
    print(first)
```

CLI:

```bash
python -m vgnc_internal_orm.cli query-species --limit 5 --format table
```

## Documentation

Core docs (in `docs/` directory):

- Architecture Overview: `docs/architecture_overview.md`
- Getting Started: `docs/getting_started.md`
- Configuration: `docs/configuration.md`
- Models Reference: `docs/models_reference.md`
- Sessions & Engines: `docs/sessions.md`
- Utilities & Performance: `docs/utilities.md`
- CLI Reference: `docs/cli.md`
- Migration Workflow: `docs/migration_workflow.md`
- Migration Safety: `docs/migrations_safety.md`
- Testing & Performance: `docs/testing_and_performance.md`
- Advanced Topics Index: `docs/advanced_topics.md`

Examples:

- Examples Overview: `examples/README.md`
- Run all: `make examples`

Additional domain/performance notes already exist (e.g. `docs/query_performance_optimization.md`, `docs/performance_testing.md`).

## Migrations

Database schema changes are managed with Alembic. The `alembic/` directory contains migration scripts and configuration.

- **Quick Reference**: See `alembic/README` for common commands and workflow
- **Detailed Guide**: `docs/migration_workflow.md` for step-by-step process
- **Safety Validation**: `docs/migrations_safety.md` for pre-deployment checks
- **Baseline Details**: `docs/alembic_baseline.md` for initial schema

Common operations:

```bash
# View current database version
alembic current

# Generate new migration from model changes
alembic revision --autogenerate -m "Add new field"

# Apply all pending migrations
alembic upgrade head

# Validate migration safety before production
python scripts/migration_workflow.py validate
```

Always review auto-generated migrations and validate before deploying to production.

## Contributing

1. Open an issue describing enhancement or fix.
2. Provide focused PR (limit scope).
3. Ensure tests pass (`pytest -q`).
4. Run safety checks for migration changes.

## License

Internal usage – adjust if public distribution is planned.
