# API Reference Index

This page catalogs key modules, classes, and helpers with links to conceptual docs. For full details, consult source files under `src/vgnc_internal_orm/`.

**Version:** 0.5.3

## Configuration (`config`)

- `DatabaseConfig` (in `config/settings.py`): driver, credentials, pooling, SSL, charset; builds `database_url` and `async_database_url`.
- `Settings` / `get_settings()`: wrapper to access `DatabaseConfig` and other app settings.

Examples: see `configuration.md` and `getting_started.md`.

## Sessions (`sessions`)

- `SessionFactory` (in `sessions/factory.py`):
  - `get_engine()`, `get_session()`, `get_async_session()`
  - `health_check()`, `ahealth_check()`, `get_pool_info()`
- `SessionManager` (in `sessions/manager.py`): context-managed usage helpers.

Examples: see `sessions.md`.

## Models (`models`)

- Base classes:
  - `BaseModel`: id, timestamps, serialization; CRUD helpers (`create/find/update/delete`) and async variants.
  - `BaseCustomModel`: for tables with non-id primary keys.
- Domain:
  - `Species`, `Chromosomes`, `Assembly`, `Genefam`
- Relationships & composites:
  - `GeneOrthologyGroup`, `GeneFamilyGroupMember`, `SpeciesRelationship`
- Supporting:
  - `GeneStatus`, `Editor`, `AltName`, `AltSymbol`, `NomenclatureType`, `Comment`, `GeneFlag`, `FlagClass`, `FamilyNew`

Examples: see `models_reference.md` and `advanced_topics.md`.

## Utilities (`utils`)

- Query Optimization: `query_optimizer.py`
  - `QueryOptimizer`, `RelationshipLoader`, `OptimizedQueryBuilder`, `QueryProfiler`, `NPlusOneDetector`, `BatchQueryExecutor`
- MySQL features: `mysql_features.py`
  - `UTF8MB4Handler`, `CharsetValidator`, `FullTextSearch`, `MySQLConnectionPool`, `MySQLQueryOptimizer`
- Indexing & Schema: `index_definitions.py`, `index_mapper.py`, `index_manager.py`, `schema_analyzer.py`, `specialized_indexes.py`

Examples: see `utilities.md`, `query_performance_optimization.md`.

## CLI (`cli/main.py`)

- Commands: `query-species`, `query-genefams`, `query-genefam-species`, `export`, `export-query`
- Formats: table, json, csv, xml

Examples: see `cli.md`.

## Migrations & Safety

- `vgnc_internal_orm.migrations.safety`: `validate_migration_safety()`, `print_safety_report()`, `MigrationSafetyValidator`
- `.github/scripts/migration_workflow.py`: `MigrationWorkflow` (create/test/rollback/validate/status, integrates safety module)
- Alembic revision scripts: `alembic/versions/*`

Examples: see `migration_workflow.md`, `migrations_safety.md`.

## Short Examples

```python
# CRUD helper
sp = Species.create(session, taxon_id=9606, prefix="HGNC", common_name="Human")

# Optimized query
from sqlalchemy import select
from sqlalchemy.orm import selectinload
q = select(Species).options(selectinload(Species.genefams)).where(Species.is_live == True)
rows = session.execute(q).scalars().all()

# Async variant
created = await Species.acreate(async_session, taxon_id=10090, prefix="MGNC", common_name="Mouse")
```

See also: `advanced_topics.md` for deeper dives and performance notes.
