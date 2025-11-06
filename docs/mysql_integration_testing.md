# MySQL Integration Testing with Testcontainers

This document describes the MySQL integration testing framework that uses testcontainers to spin up real MySQL 8.0 instances for comprehensive testing.

## Overview

The MySQL integration testing framework provides:

- **Real MySQL 8.0 instances** using Docker testcontainers
- **Production-like testing environment** with proper MySQL configuration
- **Test isolation** with automatic transaction rollback
- **Connection pooling** and session management
- **Graceful fallback** when Docker is not available

## Setup

### Dependencies

```bash
# Install test dependencies with MySQL support
pip install -e ".[test,mysql]"

# Or install testcontainers separately
pip install 'testcontainers[mysql]'
```

### Docker Requirements

The integration tests require Docker to be running:

```bash
# Start Docker Desktop or Docker daemon
docker --version
docker ps  # Should list containers if Docker is running
```

## Available Fixtures

### Core Fixtures

- **`mysql_container`** - Starts a MySQL 8.0 container (session-scoped)
- **`mysql_engine`** - Creates SQLAlchemy engine connected to MySQL (function-scoped)
- **`mysql_session`** - Provides database session with automatic rollback (function-scoped)

### Data Fixtures

- **`sample_species_mysql`** - Creates a sample species record in MySQL
- **`mysql_populated_session`** - Session with pre-populated test data
- **`mysql_connection_info`** - Connection information for the MySQL container

### Utility Fixtures

- **`mock_mysql_container`** - Mock container for testing without Docker
- **`skip_if_no_docker`** - Automatically skips tests when Docker is unavailable

## Usage

### Basic MySQL Test

```python
import pytest
from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus

class TestMySQLBasic:
    def test_species_crud(self, mysql_session):
        """Test CRUD operations with MySQL."""
        # Create
        species = Species(
            taxon_id=10090,
            genefam_prefix="MMU",
            display_name="mouse (Mus musculus)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        )
        mysql_session.add(species)
        mysql_session.commit()
        mysql_session.refresh(species)

        # Read
        retrieved = mysql_session.get(Species, 10090)
        assert retrieved is not None
        assert retrieved.genefam_prefix == "MMU"

        # Update and Delete operations...
```

### Testing Without Docker

```python
def test_mysql_workflow_mock(mock_mysql_container):
    """Test MySQL workflow using mock container."""
    connection_url = mock_mysql_container.get_connection_url()

    # Use mock connection for testing logic
    assert "mysql+pymysql://" in connection_url
    # Test your application logic without requiring real MySQL
```

### Docker Availability Check

```python
def test_framework_availability():
    """Verify framework is properly configured."""
    try:
        from testcontainers.mysql import MySqlContainer
        testcontainers_available = True
    except ImportError:
        testcontainers_available = False

    print(f"Testcontainers available: {testcontainers_available}")
```

## MySQL Configuration

The MySQL container is configured with:

- **MySQL 8.0** with native password authentication
- **UTF8MB4** charset and unicode collation
- **InnoDB buffer pool**: 256MB
- **SQL Mode**: STRICT_TRANS_TABLES, NO_ZERO_DATE, NO_ZERO_IN_DATE, ERROR_FOR_DIVISION_BY_ZERO
- **Connection settings**: Optimized for testing with connection pooling

## Test Isolation

### Transaction Rollback

Each test function gets a fresh session with automatic transaction rollback:

```python
def test_transaction_isolation(mysql_session):
    # Data created here...
    species = Species(...)
    mysql_session.add(species)
    mysql_session.commit()

    # Transaction is automatically rolled back after test
    # Other tests won't see this data
```

### Table Management

Tables are created and dropped for each test:

```python
def test_table_isolation(mysql_session):
    # All tables are created fresh for this test
    # Tables are dropped after test completion
    pass
```

## Running Tests

### Run All MySQL Integration Tests

```bash
# Run only MySQL integration tests
pytest tests/integration/test_mysql_integration.py -v

# Run with verbose output
pytest tests/integration/test_mysql_integration.py -v -s
```

### Run Tests Without Docker

Tests that require Docker will be automatically skipped:

```bash
# Tests will skip gracefully if Docker is not running
pytest tests/integration/test_mysql_integration_simple.py -v
```

### Selective Test Execution

```bash
# Run only specific test classes
pytest tests/integration/test_mysql_integration.py::TestMySQLBasicCRUD -v

# Run specific test methods
pytest tests/integration/test_mysql_integration.py::TestMySQLBasicCRUD::test_species_crud_mysql -v
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: MySQL Integration Tests

on: [push, pull_request]

jobs:
  mysql-tests:
    runs-on: ubuntu-latest
    services:
      mysql:
        image: mysql:8.0
        env:
          MYSQL_ROOT_PASSWORD: rootpass
          MYSQL_DATABASE: vgnc_test
        options: >-
          --health-cmd="mysqladmin ping"
          --health-interval=10s
          --health-timeout=5s
          --health-retries=3

    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"

    - name: Install dependencies
      run: |
        pip install -e ".[test,mysql]"
        pip install testcontainers[mysql]

    - name: Run MySQL integration tests
      run: |
        pytest tests/integration/test_mysql_integration.py -v
```

## Best Practices

### 1. Use Appropriate Test Scopes

- **Session-scoped** for containers (expensive to start)
- **Function-scoped** for sessions and engines (ensure isolation)

### 2. Handle Docker Gracefully

- Use mock containers for development without Docker
- Implement skip markers for Docker-dependent tests
- Provide clear error messages when Docker is unavailable

### 3. Optimize Performance

- Reuse containers across tests (session scope)
- Use connection pooling
- Clean up resources properly in fixture teardown

### 4. Test Real-World Scenarios

- Test foreign key constraints
- Test transaction rollback behavior
- Test MySQL-specific features (charset, enums, auto-increment)
- Test performance characteristics

### 5. Data Management

- Use factories for complex test data
- Clean up test data automatically
- Use transactions for test isolation

## Troubleshooting

### Docker Issues

**Problem**: `docker.errors.DockerException: Error while fetching server API version`
**Solution**: Start Docker Desktop or Docker daemon

**Problem**: Tests are skipped due to Docker unavailability
**Solution**: Either start Docker or use mock fixtures for development

### Connection Issues

**Problem**: Connection timeout errors
**Solution**: Increase container startup wait time or check MySQL configuration

**Problem**: Foreign key constraint failures
**Solution**: Ensure tables are created in correct order with proper metadata

### Performance Issues

**Problem**: Tests are slow due to container startup
**Solution**: Use session-scoped containers and run tests in parallel where possible

**Problem**: Memory usage during bulk operations
**Solution**: Use smaller batch sizes and optimize MySQL configuration

## Examples

See the following test files for complete examples:

- `tests/integration/test_mysql_integration.py` - Comprehensive MySQL integration tests
- `tests/integration/test_mysql_integration_simple.py` - Basic framework validation tests

These examples demonstrate:

- CRUD operations with MySQL
- Transaction handling
- Relationship navigation
- MySQL-specific features
- Performance testing
- Data integrity validation
