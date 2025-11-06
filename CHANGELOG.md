# Changelog

All notable changes to this project will be documented in this file.

## Unreleased

_No changes yet._

## 0.2.0 - 2025-11-06

### Added

- Intersphinx integration (`docs/conf.py`) enabling cross-references to Python and SQLAlchemy documentation.
- Comprehensive documentation toctree now includes all previously orphaned markdown guides.

### Changed

- Refactored base model architecture: introduced `TimestampMixin`; updated `BaseModel` (id-based) and enhanced `BaseCustomModel` for composite/natural keys.
- Orthology-related models (`orthology.py`) migrated to `BaseCustomModel` and cleaned of redundant surrogate `id` columns; added explicit `__mapper_args__` for declarative clarity.
- Documentation code fences: replaced non-standard `ascii` lexer with `text` to eliminate Sphinx highlighting warnings.

### Fixed

- Resolved Sphinx autodoc import errors for orthology models (previous `AttributeError` on missing `__mapper_args__`).
- Eliminated all documentation build warnings (intersphinx + fence fixes + toctree completion).

### Removed

- Implicit/non-functional `id` fields from orthology composite-key models.

### Notes

- Incremental release focusing on internal architecture correctness and documentation quality; no database schema migration required.
