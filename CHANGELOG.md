# CHANGELOG

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Security

- Resolved all 24 open Dependabot alerts by upgrading transitive and direct dependencies (`uv lock --upgrade`): `cryptography` 46→49, `starlette` 0.50→1.3.1, `urllib3` 2.5→2.7, `black` 25.9→26.5.1, `pytest` 8.4→9.1.1, and `mako`/`idna`/`pygments`/`requests`/`virtualenv`/`filelock`/`python-dotenv` to their fixed-in versions.

# Release v0.5.3

**Released:** 2026-07-01
**From:** v0.5.2

---

## Bug Fixes

### deps

- adopt psycopg 3 as the PostgreSQL driver (9476ba5c)

## Documentation

- docs(readme): fix broken coverage badge with hosted CI + Codecov badges (a512daf2)

---

## 📊 Release Statistics

- **Total commits:** 15
- **Conventional commits:** 2
- **Bug fixes:** 1

**Version bump:** v0.5.2 → v0.5.3

# Release v0.5.4

**Released:** 2026-07-01
**From:** v0.5.3

---

## Bug Fixes

### mysql

- stop referencing dropped DatabaseConfig.echo (d3d9c9eb)

## Chores

- chore: sync uv.lock with 0.5.3 (d8e03fb9)

## Style Changes

- style(test): reformat test_postgres_driver for black/ruff (c2203615)

---

## 📊 Release Statistics

- **Total commits:** 10
- **Conventional commits:** 3
- **Bug fixes:** 1

**Version bump:** v0.5.3 → v0.5.4

# Release v0.3.0

**Released:** 2025-11-14
**From:** v0.2.0

---

## New Features

- add version reference updater script and integrate into release workflow fix: update .gitignore to exclude temporary GitHub Actions files fix: enhance type hints in commit info class and constructor (bc7b0af2)
- add intelligent commit analysis for automatic version detection (13344682)

## Bug Fixes

- validate new version before release and ensure proper version handling (34e8195c)
- enhance version calculation logic to handle no bumps and validate new version (180e5497)
- improve intelligent analysis accuracy and reduce false positives (2fd49848)
- properly handle dry-run mode in semantic release workflow (516057dd)
- resolve string comparison issues in release notes generation (d5d2bdef)
- resolve workflow issues with version analysis and release notes (ce66aabe)
- resolve GitHub Actions output format issue in version bump script (a4f31960)

## Chores

- chore: update file permissions for script files to executable (d2e2922f)
- chore: add automated semantic versioning and release system (d83460d1)

---

## 📊 Release Statistics

- **Total commits:** 69
- **Conventional commits:** 11
- **New features:** 2
- **Bug fixes:** 7

**Version bump:** v0.2.0 → v0.3.0

# Release v0.4.0

**Released:** 2025-11-17
**From:** v0.3.0

---

## New Features

- add version reference updater script and integrate into release workflow fix: update .gitignore to exclude temporary GitHub Actions files fix: enhance type hints in commit info class and constructor (bc7b0af2)
- add intelligent commit analysis for automatic version detection (13344682)

## Bug Fixes

- include release-notes.md in version update process and commit changes (11677d7b)
- validate new version before release and ensure proper version handling (34e8195c)
- enhance version calculation logic to handle no bumps and validate new version (180e5497)
- improve intelligent analysis accuracy and reduce false positives (2fd49848)
- properly handle dry-run mode in semantic release workflow (516057dd)
- resolve string comparison issues in release notes generation (d5d2bdef)
- resolve workflow issues with version analysis and release notes (ce66aabe)
- resolve GitHub Actions output format issue in version bump script (a4f31960)

## Chores

- chore: improve version bump commit message formatting (b3680179)
- chore: enhance version calculation debugging in release workflow (0f655950)
- chore: enhance version validation and debugging in release workflow (32f71474)
- chore: add release-notes.md to repository and update .gitignore (93bf90de)
- chore: update version to 0.3.0 and reflect changes in documentation and configuration files (eee47be3)
- chore: update file permissions for script files to executable (d2e2922f)
- chore: add automated semantic versioning and release system (d83460d1)

## Documentation

- docs: test workflow debug output (88f2eb6d)

---

## 📊 Release Statistics

- **Total commits:** 81
- **Conventional commits:** 18
- **New features:** 2
- **Bug fixes:** 8

**Version bump:** v0.3.0 → v0.4.0

# Release v0.4.1

**Released:** 2025-11-17
**From:** v0.4.0

---

---

## 📊 Release Statistics

- **Total commits:** 0
- **Conventional commits:** 0

**Version bump:** v0.4.0 → v0.4.1

# Release v0.4.2

**Released:** 2025-11-17
**From:** v0.4.1

---

---

## 📊 Release Statistics

- **Total commits:** 0
- **Conventional commits:** 0

**Version bump:** v0.4.1 → v0.4.2

# Release v0.4.3

**Released:** 2025-11-17
**From:** v0.4.2

---

---

## 📊 Release Statistics

- **Total commits:** 0
- **Conventional commits:** 0

**Version bump:** v0.4.2 → v0.4.3

# Release v0.4.4

**Released:** 2025-11-17
**From:** v0.4.3

---

---

## 📊 Release Statistics

- **Total commits:** 0
- **Conventional commits:** 0

**Version bump:** v0.4.3 → v0.4.4

# Release v0.4.5

**Released:** 2025-11-17
**From:** v0.4.4

---

## Bug Fixes

- add missing newline in FullTextSearch docstring (797751b2)

## Chores

- chore: update version to 0.4.4 in __init__.py (6609d3b6)
- chore: update version to 0.4.4 and enhance docstrings across multiple modules (cc592163)
- chore: enhance Git tag and release creation process with improved variable handling (2688f5cb)
- chore: enhance version calculation and debugging for Git tag and release creation (d06ff20a)

## Documentation

- docs: final debug test for VERSION variable (d8e5adad)
- docs: test file-based version passing approach (d5780b77)
- docs: final test change for version validation (a5d6dab1)
- docs: another test change for release validation (29b59672)
- docs: test change for release validation (e9070579)

---

## 📊 Release Statistics

- **Total commits:** 13
- **Conventional commits:** 10
- **Bug fixes:** 1

**Version bump:** v0.4.4 → v0.4.5

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

# Release v0.5.1

**Released:** 2026-06-30
**From:** v0.5.0

---

## Bug Fixes

### ci

- repair docs build and coverage summary failures (c85b5091)

---

## 📊 Release Statistics

- **Total commits:** 19
- **Conventional commits:** 1
- **Bug fixes:** 1

**Version bump:** v0.5.0 → v0.5.1

# Release v0.5.2

**Released:** 2026-06-30
**From:** v0.5.1

---

## Bug Fixes

### ci

- drop stale reference to deleted test_config_loading.py (6271cb5e)

---

## 📊 Release Statistics

- **Total commits:** 11
- **Conventional commits:** 1
- **Bug fixes:** 1

**Version bump:** v0.5.1 → v0.5.2
## [0.2.0] - 2024-11-14

### 🚀 Initial Release Setup
- Set up semantic versioning workflow
- Configured automated changelog generation
- Added conventional commit analysis
- Integrated with GitHub Actions for automated releases

### 📦 Package Configuration
- Updated to MIT license
- Comprehensive test suite setup
- Performance testing infrastructure
- Code quality and security checks

### 🏗️ Development Infrastructure
- GitHub Actions CI/CD pipeline
- Documentation deployment to GitHub Pages
- Code coverage reporting with Codecov
- Automated dependency management

---

**Note:** This changelog is now automatically maintained by the semantic release workflow.
All future changes will be documented here automatically based on conventional commits.
