# Architecture Overview

This library implements a SQLAlchemy 2.0 ORM for VGNC domain data with strong typing, environment-aware configuration, optimized session handling, performance/index utilities, and migration safety tooling.

**Version:** 0.2.0
**License:** MIT

## High-Level Components

| Layer | Purpose |
|-------|---------|
| Configuration | Build validated DB URLs & global settings (`config/settings.py`) |
| Sessions | Create tuned (async/sync) engines & sessions (`sessions/factory.py`, `sessions/manager.py`) |
| Models | Domain entities + helpers (`models/*`, `BaseModel`) |
| Utilities | Index / performance / charset / schema analysis (`utils/*`) |
| CLI | Operational querying & export (`cli/main.py`) |
| Migrations | Workflow orchestration (`.github/scripts/migration_workflow.py`) & Alembic revisions (`alembic/versions/*`) |

## Module Map

- `config/settings.py`: `DatabaseConfig`, `Settings`, driver/env enums, secure URL builders (Postgres/MySQL/SQLite), charset + SSL.
- `sessions/factory.py`: `SessionFactory` engine creation, pool tuning, event listeners (SQLite pragmas, MySQL charset), health checks, contexts.
- `sessions/manager.py`: `SessionManager` convenience wrapper for scoped usage.
- `models/base.py`: `BaseModel` (id, timestamps, serialization, CRUD/query helpers, charset utilities) and `BaseCustomModel` for non-id PKs.
- Domain models: `species.py`, `chromosomes.py`, `assembly.py`, `genefam.py`.
- Relationship & composite structures: `orthology.py` (groups, membership, species relationships).
- Supporting & association tables: `supporting.py`, `associations.py`.
- Performance & indexing: `index_definitions.py`, `index_mapper.py`, `index_manager.py`, `schema_analyzer.py`, `specialized_indexes.py`.
- MySQL / query optimization: `mysql_features.py`, `query_optimizer.py`.
- Migration safety: `src/vgnc_internal_orm/migrations/safety.py` (risk scanning, downgrade checks) integrated into `.github/scripts/migration_workflow.py`.
- Workflow scripting: `.github/scripts/migration_workflow.py` (create/test/rollback/validate/status).
- CLI interface: `cli/main.py` (query/export commands; table/JSON/CSV/XML).

## Data & Control Flow

1. Load settings → build database URLs.
2. Initialize engines via `SessionFactory` (register events).
3. Acquire sessions through context managers or `SessionManager`.
4. Perform CRUD/query operations using `BaseModel` helpers & loading strategies.
5. Apply/analyze indexes & performance features via utilities.
6. Run migrations & validate safety before deployment.
7. Operate reporting/exports through CLI.

## Design Principles

- SQLAlchemy 2.0 declarative with `Mapped[...]` typing.
- Unified sync + async capability (parallel method sets).
- Encapsulated charset/UTF8MB4 handling (emoji & extended symbols).
- Rich reusable CRUD/query helpers reduce boilerplate.
- Separable performance/index tooling—non-invasive to core models.
- Migration safety integrated early (prevent risky operations).

## Cross References

See: `getting_started.md`, `configuration.md`, `models_reference.md`, `sessions.md`, `utilities.md`, `cli.md`, `migration_workflow.md`, `migrations_safety.md`, `advanced_topics.md`.

## Caveats

- Some relationships purposely commented to avoid circular metadata; documented in `models_reference.md`.
- Index definition modules may reference logical columns not present—treat as templates (see `utilities.md`).
