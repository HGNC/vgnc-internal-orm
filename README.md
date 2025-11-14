# VGNC Internal ORM

Comprehensive SQLAlchemy 2.0 ORM toolkit for VGNC-style gene nomenclature data: typed models, robust configuration, optimized sessions, performance/index utilities, migration workflow & safety validation, and a flexible querying/export CLI.

**Version:** 0.2.0
**Python:** 3.11+
**License:** CC0

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

# Install with optional dependencies
pip install vgnc-internal-orm[mysql]      # MySQL support
pip install vgnc-internal-orm[dev]       # Development tools
pip install vgnc-internal-orm[test]      # Testing tools
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
vgnc-cli export --table species --format json --output species.json

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
python scripts/migration_workflow.py validate

# Test migration on development database
python scripts/migration_workflow.py test

# Get migration status
python scripts/migration_workflow.py status
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
git clone https://github.com/vgnc/vgnc-internal-orm.git
cd vgnc-internal-orm

# Install in development mode
pip install -e ".[dev]"

# Install pre-commit hooks
pre-commit install

# Run tests
pytest

# Run linting
ruff check src/
black src/

# Run type checking
mypy src/
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
   python scripts/migration_workflow.py validate
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

CC0 License - see LICENSE file for details.

## Project Links

- **Repository**: <https://github.com/vgnc/vgnc-internal-orm>
- **Issues**: <https://github.com/vgnc/vgnc-internal-orm/issues>
- **Documentation**: <https://github.com/vgnc/vgnc-internal-orm/docs>
- **PyPI**: <https://pypi.org/project/vgnc-internal-orm/> (when published)

## Support

For questions and support:

- 📖 **Documentation**: See the `docs/` directory
- 🐛 **Bug Reports**: Open an issue on GitHub
- 💬 **Discussions**: Use GitHub Discussions (when enabled)
- 📧 **Contact**: VGNC Development Team (<dev@vgnc.com>)
