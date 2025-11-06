# VGNC Internal ORM Documentation

```{toctree}
:maxdepth: 2
:caption: Contents

getting_started
architecture_overview
configuration
models_reference
sessions
utilities
cli
migration_workflow
migrations_safety
testing_and_performance
advanced_topics
api_reference
api/index
examples
alembic_baseline
incremental_migrations
query_performance_optimization
performance_testing
many_to_many_relationships_implementation
navigation_and_loading_tests
loading_strategy_analysis
load_testing
mysql_integration_testing
code_coverage
ci_cd_pipeline
PRD
```

## Overview

This Sphinx site aggregates the Markdown guides already present in the repository. Use the sidebar or list above to navigate.

Examples live in `examples/`. See: `examples.md`.

API autodoc examples can be added later by creating `api/*.rst` with directives like:

```rst
.. automodule:: vgnc_internal_orm.models.species
   :members:
   :undoc-members:
```

## Contributing to Docs

- Edit existing markdown under `docs/`.
- Run `make docs-html` from project root to build.
- Add new pages and include them in the `toctree` above.

## Next Steps

Consider adding `api/` references if deeper symbol-level docs are needed for public distribution.
