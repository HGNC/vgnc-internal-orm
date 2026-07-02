# VGNC Internal ORM

[![CI](https://github.com/HGNC/vgnc-internal-orm/actions/workflows/ci.yml/badge.svg)](https://github.com/HGNC/vgnc-internal-orm/actions/workflows/ci.yml) [![Coverage](https://codecov.io/gh/HGNC/vgnc-internal-orm/branch/main/graph/badge.svg)](https://codecov.io/gh/HGNC/vgnc-internal-orm) [Test Summary](test-summary.md)

Comprehensive SQLAlchemy 2.0 ORM toolkit for VGNC-style gene nomenclature data: typed models, robust configuration, optimized sessions, performance/index utilities, migration workflow & safety validation, and a flexible querying/export CLI.

**Version:** 0.5.6
**Python:** 3.11+
**License:** MIT

## Features

### Core ORM Capabilities

- **Typed declarative models** with rich CRUD helpers and async support
- **Sync & async session support** with tuned engine creation and connection pooling
- **Multi-database support**: MySQL (with UTF8MB4), PostgreSQL, SQLite
- **Full-text search** and specialized charset handling for international data

### Performance & Utilities

- **Index management**: Definition, mapping, schema analysis, and automated optimization
- **Query optimization**: N+1 detection, batch execution, performance profiling
- **MySQL-specific features**: Charset validation, connection pooling, query optimization
- **Schema analysis tools**: Performance monitoring and index recommendations

### Migration & Safety

- **Alembic integration** with comprehensive migration workflow
- **Migration safety validation**: Pre-deployment risk assessment and rollback checks
- **Incremental migrations**: Safe, validated database schema changes
- **Baseline management**: Initial schema setup and version tracking

### Developer Tools

- **CLI interface**: Query and export data in multiple formats (table/JSON/CSV/XML)
- **Comprehensive testing**: Unit, integration, and performance test suites
- **Code quality**: Black formatting, Ruff linting, MyPy type checking
- **Documentation**: Complete API reference and usage examples

## Quick Start

### Installation

```bash
# Install from PyPI (when available)
pip install vgnc-internal-orm

# Install from GitHub (latest development version)
pip install git+https://github.com/HGNC/vgnc-internal-orm.git

# Install with optional dependencies
pip install vgnc-internal-orm[mysql]      # MySQL support
pip install vgnc-internal-orm[dev]       # Development tools
pip install vgnc-internal-orm[test]      # Testing tools

# Using uv (modern Python package manager)
uv install vgnc-internal-orm
uv install vgnc-internal-orm[mysql]
uv install vgnc-internal-orm[dev]

# Install from GitHub with uv
uv install git+https://github.com/HGNC/vgnc-internal-orm.git
```

### Basic Usage

```python
from vgnc_internal_orm.config.settings import get_settings
from vgnc_internal_orm.sessions.factory import SessionFactory
from vgnc_internal_orm.models.species import Species

# Load configuration (from environment variables or .env file)
settings = get_settings()

# Create session factory
sf = SessionFactory(settings.database)

# Sync usage
with sf.get_session() as session:
    species = Species.find(session, limit=1)
    print(f"Found species: {species}")

# Async usage
async with sf.get_async_session() as session:
    species = await Species.async_find(session, limit=1)
    print(f"Found species: {species}")
```

### CLI Usage

```bash
# Query species data
vgnc-cli query-species --limit 5 --format table

# Export data to JSON
vgnc-cli export --entity species --format json --output species.json

# Run with custom configuration
VGNC_ENVIRONMENT=production vgnc-cli query-species --limit 10
```

## Documentation

### Core Documentation (in `docs/` directory)

**Getting Started:**

- **Architecture Overview**: `docs/architecture_overview.md` - High-level design and components
- **Getting Started**: `docs/getting_started.md` - Step-by-step installation and basic usage
- **Configuration**: `docs/configuration.md` - Environment variables and setup options

**Core API Reference:**

- **Models Reference**: `docs/models_reference.md` - Complete model documentation
- **Sessions & Engines**: `docs/sessions.md` - Session management and database connections
- **Utilities & Performance**: `docs/utilities.md` - Index management and optimization tools
- **CLI Reference**: `docs/cli.md` - Command-line interface documentation

**Migration & Database:**

- **Migration Workflow**: `docs/migration_workflow.md` - Alembic integration and migration process
- **Migration Safety**: `docs/migrations_safety.md` - Pre-deployment validation and safety checks
- **Alembic Baseline**: `docs/alembic_baseline.md` - Initial schema setup details
- **Incremental Migrations**: `docs/incremental_migrations.md` - Safe schema evolution

**Advanced Topics:**

- **Testing & Performance**: `docs/testing_and_performance.md` - Test strategies and performance optimization
- **Query Performance**: `docs/query_performance_optimization.md` - Advanced query optimization
- **API Reference**: `docs/api_reference.md` - Complete API catalog
- **Advanced Topics Index**: `docs/advanced_topics.md` - Advanced usage patterns

### Examples

- **Examples Overview**: `examples/README.md` - Code examples and tutorials
- **Run all examples**: `make examples`

### Development Documentation

- **CI/CD Pipeline**: `docs/ci_cd_pipeline.md` - Continuous integration and deployment
- **Code Coverage**: `docs/code_coverage.md` - Test coverage analysis
- **Load Testing**: `docs/load_testing.md` - Performance testing methodology

### Research & Analysis

- **Loading Strategy Analysis**: `docs/loading_strategy_analysis.md` - Data loading performance
- **Navigation and Loading Tests**: `docs/navigation_and_loading_tests.md` - Relationship optimization
- **Many-to-Many Relationships**: `docs/many_to_many_relationships_implementation.md` - Complex relationship patterns

## Migrations

Database schema changes are managed with Alembic. The `alembic/` directory contains migration scripts and configuration.

### Migration Resources

- **Quick Reference**: `alembic/README.md` for common commands and workflow
- **Detailed Guide**: `docs/migration_workflow.md` for step-by-step process
- **Safety Validation**: `docs/migrations_safety.md` for pre-deployment checks
- **Baseline Details**: `docs/alembic_baseline.md` for initial schema
- **Incremental Process**: `docs/incremental_migrations.md` for safe evolution

### Quick Runbook (Make Targets)

```bash
# Create a new revision (autogenerate/manual per script prompts)
make migrate-create MSG="add species index"

# Test the latest (or a specific) revision on a temp DB
make migrate-test               # latest
make migrate-test REV="<rev_id>"

# Validate a specific migration file with the safety checks
make migrate-validate FILE=alembic/versions/<revision_file>.py

# Show Alembic status
make migrate-status

# Test rollback steps (default 1). Optional REV to target a specific revision
make migrate-test-rollback STEPS=1
make migrate-test-rollback STEPS=1 REV="<rev_id>"
```

These targets call `.github/scripts/migration_workflow.py` under the hood using `uv run`.
To test against a non-SQLite DB, set `DATABASE_URL` before running, e.g.:

```bash
export DATABASE_URL="mysql+pymysql://user:pass@127.0.0.1:3306/vgnc_dev"
make migrate-test
```

### Common Operations

```bash
# View current database version
alembic current

# Generate new migration from model changes
alembic revision --autogenerate -m "Add new field"

# Apply all pending migrations
alembic upgrade head

# Rollback to previous version
alembic downgrade -1

# Validate migration safety before production
python .github/scripts/migration_workflow.py validate

# Test migration on development database
python .github/scripts/migration_workflow.py test

# Get migration status
python .github/scripts/migration_workflow.py status
```

### Migration Safety

⚠️ **Always review auto-generated migrations** before applying to production. Use the migration workflow script to:

- Validate migration safety
- Test on development environment
- Check for data loss risks
- Verify rollback capability

## Development

### Environment Setup

```bash
# Clone repository
git clone https://github.com/HGNC/vgnc-internal-orm.git
cd vgnc-internal-orm

# Option 1: Using pip (traditional)
pip install -e ".[dev]"

# Option 2: Using uv (modern, faster)
uv sync --dev
# or equivalently:
uv install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest
# or with uv:
uv run pytest

# Run linting
ruff check src/
black src/
# or with uv:
uv run ruff check src/
uv run black src/

# Run type checking
mypy src/
# or with uv:
uv run mypy src/
```

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=src/vgnc_internal_orm

# Run specific test categories
pytest tests/unit/          # Unit tests
pytest tests/integration/   # Integration tests
pytest tests/performance/   # Performance tests
pytest tests/load/          # Load tests

# Run benchmarks
pytest --benchmark-only
```

### Code Quality

The project uses a comprehensive code quality setup:

- **Formatting**: Black (line length: 88)
- **Linting**: Ruff (compatible with Black)
- **Type Checking**: MyPy (strict mode)
- **Security**: Bandit (security scanning)
- **Pre-commit**: Automated checks before commits

## Contributing

We welcome contributions! Please follow these steps:

### Contribution Process

1. **Open an Issue**: Describe the enhancement, bug fix, or feature you want to work on
2. **Create a Branch**: Use descriptive branch names (`feature/query-optimization`, `fix/migration-safety`)
3. **Make Changes**:
   - Follow existing code style and patterns
   - Add tests for new functionality
   - Update documentation as needed
4. **Quality Checks**: Ensure all checks pass:

   ```bash
   pytest -q                          # Tests
   ruff check src/                     # Linting
   black --check src/                  # Formatting
   mypy src/                          # Type checking
   bandit -r src/                     # Security
   ```

5. **Submit PR**: Provide a focused, well-documented pull request
6. **Migration Safety**: For schema changes, run migration safety checks:

   ```bash
   python .github/scripts/migration_workflow.py validate
   ```

### Development Guidelines

- **Code Style**: Follow Black formatting (88 character line length)
- **Type Hints**: Use comprehensive type annotations (MyPy strict mode)
- **Testing**: Maintain high test coverage with unit, integration, and performance tests
- **Documentation**: Update relevant docs for API changes
- **Migration Safety**: Always validate migration safety for schema changes

### Performance Testing

For performance-related changes, run benchmarks:

```bash
pytest tests/performance/ --benchmark-only
```

## License

MIT License - see LICENSE file for details.

## Project Links

- **Repository**: <https://github.com/HGNC/vgnc-internal-orm>
- **Issues**: <https://github.com/HGNC/vgnc-internal-orm/issues>
- **Documentation**: <https://github.com/HGNC/vgnc-internal-orm/docs>
- **PyPI**: <https://pypi.org/project/vgnc-internal-orm/> (when published)

## Support

For questions and support:

- 📖 **Documentation**: See the `docs/` directory
- 🐛 **Bug Reports**: Open an issue on GitHub
- 💬 **Discussions**: Use GitHub Discussions (when enabled)
- 📧 **Contact**: HGNC Development Team (<hgnc@genenames.org>)
