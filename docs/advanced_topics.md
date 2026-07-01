# Advanced Topics & Guides

**VGNC Internal ORM v0.5.4** - MIT License

This consolidated guide indexes the deeper documents in `docs/` and provides a navigation overview. Detailed original files remain for full reference; this page surfaces what each covers and when to consult them.

## Performance & Querying

- `query_performance_optimization.md` – Comprehensive loading strategies (selectin vs joined vs subquery), QueryOptimizer usage, N+1 avoidance patterns.
- `loading_strategy_analysis.md` – Static analysis of current relationship configuration and rationale.
- `performance_testing.md` – pytest-benchmark driven suite: thresholds, running, interpreting results.
- `load_testing.md` + `load_test_runner.py` – Concurrency & throughput testing outside pytest.
- `navigation_and_loading_tests.md` – Tests validating multi-hop navigation and eager loading correctness.

### Quick Examples

```python
# Optimized species query with relationships
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from vgnc_internal_orm.models.species import Species
from vgnc_internal_orm.models.genefam import Genefam

q = (
    select(Species)
    .options(
        selectinload(Species.genefams).selectinload(Genefam.enhanced_species_associations),
        selectinload(Species.chromosomes)
    )
    .where(Species.is_live == True)
)
species = session.execute(q).scalars().all()
```

## Indexes & Schema

- `loading_strategy_analysis.md` (indirectly via relationship ordering)
- `utilities.md` & `schema_analyzer.py` – Index discovery and application flow.
- `many_to_many_relationships_implementation.md` – Association design trade-offs (constraints vs flexibility).

## Migrations & Lifecycle

- `alembic_baseline.md` – Creating and reasoning about an initial baseline revision.
- `incremental_migrations.md` – Strategy for layering frequent schema changes safely.
- `migration_workflow.md` – Scripted operational flow (create/test/rollback/status).
- `migrations_safety.md` – Risk detection (drops, missing downgrade, large table changes).

### Programmatic Safety Check

```python
from vgnc_internal_orm.migrations.safety import validate_migration_safety, print_safety_report
report = validate_migration_safety("alembic/versions")
print_safety_report(report)
```

## MySQL & Charset

- `mysql_integration_testing.md` – Connection, charset, and feature tests.
- `utilities.md` (UTF8MB4 & full-text search).
- `query_performance_optimization.md` – MySQL loading patterns interplay.

### Full‑Text Search Example

```python
from sqlalchemy import text
from vgnc_internal_orm.utils.mysql_features import FullTextSearch

match = FullTextSearch.build_match_query(["assigned_name", "assigned_symbol"], "kinase", mode=FullTextSearch.SearchMode.NATURAL_LANGUAGE)
rows = session.execute(text(f"SELECT * FROM genefam WHERE {match.text}"), {"search_query": "kinase"}).fetchall()
```

## CI/CD & Quality

- `ci_cd_pipeline.md` – Suggested pipeline stages (lint, type check, tests, safety, perf benchmarks).
- `code_coverage.md` – Maintaining coverage levels & interpreting `htmlcov/` output.
- `performance_testing.md` – Integrating regression checks in pipeline.

## Coverage & Benchmarking Commands

```bash
pytest --maxfail=1 -q
pytest tests/performance/ --benchmark-only --benchmark-save=baseline
pytest tests/performance/ --benchmark-only --benchmark-compare=baseline
```

## When To Use Which Document

| Scenario | Consult |
|----------|--------|
| Unexpected slow joins | `query_performance_optimization.md`, `utilities.md` |
| Planning new many-to-many | `many_to_many_relationships_implementation.md` |
| Adding baseline schema | `alembic_baseline.md` |
| Frequent small schema changes | `incremental_migrations.md` |
| Dropping columns safely | `migrations_safety.md` |
| Charset issues / emojis failing | `mysql_integration_testing.md`, `utilities.md` |
| Benchmark regression | `performance_testing.md` |
| High concurrency stress | `load_testing.md`, `load_test_runner.py` |

## Consolidation Notes

This page centralizes navigation; original files remain unmodified to preserve detailed guidance. Future refactors may merge overlapping performance docs into a single `performance_deep_dive.md` if duplication increases.
