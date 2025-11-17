# Utilities & Performance Toolkit

**VGNC Internal ORM v0.4.3** - MIT License

## Index Ecosystem

- `index_definitions.py`: curated logical index sets (may include template columns not yet present).
- `index_mapper.py`: introspects models to propose indexes/constraints/full-text opportunities.
- `index_manager.py`: applies index objects, validates coverage, generates DDL assistance.
- `schema_analyzer.py`: produces schema report (missing/redundant indexes, recommendations).
- `specialized_indexes.py`: advanced / domain-specific index patterns.

## MySQL Features

`mysql_features.py`:

- UTF8MB4 detection & sanitization.
- Full-text index builder & query helpers.
- Query optimizer (EXPLAIN parsing, slow query hints).

## Query Optimization

`query_optimizer.py`:

- `RelationshipLoader` presets for eager loading.
- `NPlusOneDetector` for pattern surfacing.
- `OptimizedQueryBuilder` & `BatchQueryExecutor` for batched workloads.

## Typical Flow

1. Run schema analyzer → review missing/high-value indexes.
2. Use mapper recommendations → apply via manager.
3. Re-run analyzer → confirm improvements.
4. For MySQL heavy text queries → create FULLTEXT indexes then use search helpers.

## Example

```python
from vgnc_internal_orm.utils.schema_analyzer import SchemaAnalyzer
report = SchemaAnalyzer().analyze_current_schema()
print(report.summary())
```

### Applying Suggested Indexes

```python
from vgnc_internal_orm.utils.index_manager import IndexManager
manager = IndexManager()
manager.apply_indexes_to_models(models=[Species, Genefam])  # hypothetical usage pattern
```

### Full‑Text Search (MySQL)

```python
from vgnc_internal_orm.utils.mysql_features import FullTextSearch
match_clause = FullTextSearch.build_match_query(["assigned_name"], "kinase")
rows = session.execute(text(f"SELECT * FROM genefam WHERE {match_clause.text}"), {"search_query": "kinase"}).fetchall()
```

### Query Plan Analysis (MySQL)

```python
from vgnc_internal_orm.utils.mysql_features import MySQLQueryOptimizer
plan = MySQLQueryOptimizer.analyze_query_plan(session, "SELECT * FROM genefam WHERE assigned_symbol='ABC'", use_analyze=True)
print(plan.get("warnings"))
```

### Optimizing Join Query (Hint Injection)

```python
optimized = MySQLQueryOptimizer.optimize_join_query("SELECT * FROM a JOIN b ON a.id=b.a_id JOIN c ON b.id=c.b_id", {"a": ["idx_a_id"]})
```

### Detecting N+1 (Utility)

```python
from vgnc_internal_orm.utils.query_optimizer import NPlusOneDetector
detector = NPlusOneDetector(session)
analysis = detector.analyze_query_pattern(Species, ["genefams", "assemblies"])
print(analysis["suggestions"])  # actionable strategy changes
```
