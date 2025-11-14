# Examples

Runnable, minimal examples demonstrating common tasks. Run from repo root.

## Prerequisites

- Python environment with the project installed:

```bash
# Using pip
pip install -e ".[test,performance]"

# Using uv (modern Python package manager)
uv install -e ".[test,performance]"
# or equivalently:
uv sync --extra test --extra performance
```

- Database configuration via environment variables or `.env` for non-SQLite drivers. See `docs/configuration.md`.

## Scripts

### 1) basic_sync.py

- Purpose: Connect, open a session, fetch a few `Species`, and use `BaseModel` helpers.
- Run:

```bash
python examples/basic_sync.py
```

### 2) basic_async.py

- Purpose: Async session usage to fetch rows and use async helpers.
- Run:

```bash
python examples/basic_async.py
```

### 3) full_text_search_demo.py (MySQL only)

- Purpose: Demonstrates building a MySQL FULLTEXT search with `FullTextSearch`.
- Notes: Skips automatically if `driver` != `mysql`.
- Run:

```bash
python examples/full_text_search_demo.py
```

### 4) query_optimization_demo.py

- Purpose: Use `QueryOptimizer` + `QueryProfiler` to build and evaluate an optimized query.
- Run:

```bash
python examples/query_optimization_demo.py
```

### 5) test_migration_safety.py

- Purpose: Demonstrate migration safety validation using `vgnc_internal_orm.migrations.safety`.
- Features:
  - Validate migrations for destructive operations
  - Risk level detection (CRITICAL, HIGH, MEDIUM, LOW)
  - Production mode validation
  - CI/CD integration patterns
- Run:

```bash
python examples/test_migration_safety.py
```

## Tips

- Use `make examples` to run them all (errors on MySQL-only demo are ignored).
- For performance deep dives, see `docs/advanced_topics.md` and `docs/query_performance_optimization.md`.
