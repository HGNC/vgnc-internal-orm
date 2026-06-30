# Release v0.5.0

**Released:** 2026-06-30
**From:** v0.4.5

---

## New Features

### ci

- make coverage badge generation functional (22e88a7d)

### config

- migrate DatabaseConfig to db_common.DatabaseSettings subclass and drop async/env/SSL/charset fields (Task 4) (fe3d4960)

## Bug Fixes

### ci

- use default GITHUB_TOKEN + fix expression braces in release (4edb4671)
- strip stray backslashes from release & coverage workflows (01d3564f)
- carry --extra through uv run so pytest-cov stays installed (55d44088)
- use uv run for all commands to use correct venv (6615766b)
- use uv --extra instead of --group for optional dependencies (f15cf2d5)
- update workflows to use uv for Git dependency resolution (36a53dd3)

- resolve migration/CLI test failures (full tests/ tree now green) (e0304fee)
- resolve integration test failures (was: CI infra masked them) (5f33600e)

## Build System

- build(deps): add db-common git dep (v0.1.0) and bump requires-python to >=3.13 (Task T1) (3de67d4e)

## Code Refactoring

- refactor(workflows): simplify and fix GitHub Actions for Python 3.13 (7a575b80)
- refactor(alembic,deps,test): complete db-common migration, remove async dependencies (Task T5) (da3cec82)
- refactor(sessions): delegate session infra to db-common; drop async + MySQL/env pooling (Task T3) (e967249d)
- refactor(models): reparent UnifiedBase to db_common.DeclarativeBase; strip async BaseModel helpers (Task T2) (bbfc1b8b)
- refactor(tests): normalize imports to canonical vgnc_internal_orm (Task T1.5) (900d4a24)

## Style Changes

- style: clean lint/format across all .github/scripts (4d486d51)
- style: fix lint/format issues in migration_workflow.py (a230cbf6)
- style(models,config): modernize str-enums to enum.StrEnum (UP042) (30ec4870)

## Tests

- test: raise coverage to 70% (combined) + fix ci coverage gating (d5a7f336)

---

## 📊 Release Statistics

- **Total commits:** 288
- **Conventional commits:** 20
- **New features:** 2
- **Bug fixes:** 8

**Version bump:** v0.4.5 → v0.5.0
