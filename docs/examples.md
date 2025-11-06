# Examples

Runnable, minimal examples demonstrating common tasks. Run from repo root.

## Prerequisites

- Python environment with the project installed.

```bash
pip install -e ".[test,performance]"
```

- Database configuration via environment variables or `.env` for non-SQLite drivers. See `configuration.md`.

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

## Tips

- Use `make examples` to run them all (errors on MySQL-only demo are ignored).
- For performance deep dives, see `advanced_topics.md` and `query_performance_optimization.md`.
