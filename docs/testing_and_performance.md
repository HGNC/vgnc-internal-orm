# Testing & Performance

**VGNC Internal ORM v0.4.4** - MIT License

## Existing Test Suites

Located in `tests/` split by:

- `unit/`: model/base utilities
- `integration/`: cross-table behavior, loading strategies
- `performance/`: timing & query performance comparisons
- `load/`: concurrency / stress checks

## Coverage

Coverage reports in `coverage.xml` & HTML under `htmlcov/`. Aim to keep high coverage for core models & session factories.

## Performance Strategy

- Employ eager loading presets to mitigate N+1.
- Apply recommended indexes from analyzer output.
- Use MySQL full-text indexes for text-heavy queries.
- Profile with `QueryProfiler` & detect N+1 via `NPlusOneDetector`.

## Load Testing Runner

Standalone concurrency tool: `load_test_runner.py`.

```bash
python load_test_runner.py --users 50 --duration 20 --test mixed --output mixed_results.json
```

## Benchmark + Coverage Integration

```bash
pytest --cov=vgnc_internal_orm --cov-report=term-missing
pytest tests/performance/ --benchmark-only --benchmark-save=baseline
pytest tests/performance/ --benchmark-only --benchmark-compare=baseline
```

## Advanced Topics Reference

See `advanced_topics.md` for index of deeper guides (loading strategy analysis, query optimization, full benchmark details).

## Example Profiling

```python
from vgnc_internal_orm.utils.query_optimizer import QueryProfiler
with QueryProfiler(session) as profiler:
    _ = session.query(Species).limit(100).all()
print(profiler.summary())
```
