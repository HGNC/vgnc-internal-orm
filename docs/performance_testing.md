# Performance Testing Framework

This document describes the comprehensive performance testing framework built with pytest-benchmark for the VGNC Internal ORM project.

## Overview

The performance testing framework provides:

- **pytest-benchmark integration** for precise performance measurements
- **Comprehensive test coverage** for model operations, queries, and database interactions
- **Performance thresholds** with automatic validation
- **Regression detection** to catch performance degradation
- **Statistical analysis** with detailed benchmark reports
- **MySQL-specific performance testing** with testcontainers

## Setup

### Dependencies

```bash
# Install performance testing dependencies
pip install -e ".[test,performance]"

# Or install pytest-benchmark separately
pip install pytest-benchmark
```

### Benchmark Configuration

The framework is configured in `tests/performance/conftest.py` with:

- **Performance thresholds** for different operation types
- **Database fixtures** for SQLite and MySQL testing
- **Data factories** for generating realistic test data
- **Utility functions** for performance validation

## Available Benchmarks

### 1. Model Performance Tests (`test_model_performance.py`)

#### Model Creation Benchmarks

- `test_species_creation_performance` - Species model instantiation
- `test_genefam_creation_performance` - Genefam model instantiation
- `test_assembly_creation_performance` - Assembly model instantiation
- `test_chromosomes_creation_performance` - Chromosomes model instantiation
- `test_batch_model_creation` - Batch creation of 100 models

#### ORM Operation Benchmarks

- `test_add_single_object` - Database insertion of single object
- `test_add_multiple_objects` - Bulk insertion of 50 objects
- `test_update_single_object` - Single object update
- `test_update_multiple_objects` - Bulk update of 25 objects
- `test_delete_single_object` - Single object deletion
- `test_delete_multiple_objects` - Bulk deletion of 30 objects

#### Session Operation Benchmarks

- `test_session_commit_performance` - Transaction commit performance
- `test_session_rollback_performance` - Transaction rollback performance
- `test_session_flush_performance` - Session flush performance
- `test_session_refresh_performance` - Object refresh performance

#### Validation Performance Benchmarks

- `test_enum_validation_performance` - Enum field validation (100 iterations)
- `test_string_validation_performance` - String constraint validation (50 iterations)
- `test_datetime_validation_performance` - DateTime field validation (75 iterations)

#### Serialization Performance Benchmarks

- `test_model_dict_serialization` - Model to dictionary serialization

### 2. Query Performance Tests (`test_query_performance.py`)

#### Basic Query Benchmarks

- `test_simple_species_query` - Primary key lookup
- `test_species_list_query` - List all species
- `test_species_filter_query` - Filtered query
- `test_species_count_query` - Count query
- `test_assembly_by_species_query` - Related data query
- `test_chromosomes_by_species_query` - Large result set query

#### Complex Query Benchmarks

- `test_species_with_multiple_filters` - Multi-condition filtering
- `test_or_query_performance` - OR condition queries
- `test_join_query_performance` - JOIN operation performance
- `test_subquery_performance` - Subquery execution
- `test_order_by_performance` - Sorting operations
- `test_limit_offset_performance` - Pagination queries

#### Aggregate Query Benchmarks

- `test_count_by_group` - GROUP BY with COUNT
- `test_sum_aggregate` - SUM aggregate function
- `test_max_aggregate` - MAX aggregate function
- `test_having_clause` - HAVING clause filtering
- `test_multiple_aggregates` - Multiple aggregates in one query

#### Bulk Operation Benchmarks

- `test_bulk_insert_performance` - Bulk insert of 1000 records
- `test_bulk_delete_performance` - Bulk delete operations
- `test_bulk_update_performance` - Bulk update operations

#### Loading Strategy Benchmarks

- `test_lazy_loading_performance` - Lazy relationship loading
- `test_joined_loading_performance` - Eager JOIN loading
- `test_selectin_loading_performance` - SELECT IN loading

#### Index Performance Benchmarks

- `test_primary_key_lookup_performance` - Primary key index usage
- `test_foreign_key_lookup_performance` - Foreign key index usage
- `test_indexed_filter_performance` - Index filter optimization

### 3. MySQL Performance Tests (`test_mysql_performance.py`)

#### MySQL Connection Benchmarks

- `test_mysql_connection_performance` - Connection establishment
- `test_mysql_session_operations` - Session management
- `test_mysql_transaction_isolation` - Transaction isolation levels

#### MySQL Query Performance

- `test_mysql_primary_key_lookup` - MySQL PK lookup performance
- `test_mysql_index_usage` - MySQL index optimization
- `test_mysql_bulk_operations` - MySQL bulk insert/update/delete

#### MySQL Feature Benchmarks

- `test_mysql_charset_performance` - UTF8MB4 charset performance
- `test_mysql_enum_performance` - MySQL ENUM handling
- `test_mysql_auto_increment_performance` - Auto-increment fields
- `test_mysql_foreign_key_performance` - Foreign key constraint performance

## Performance Thresholds

The framework defines performance thresholds for different operation types:

```python
"thresholds": {
    "simple_query": 0.001,      # 1ms for simple queries
    "complex_query": 0.010,      # 10ms for complex queries
    "bulk_insert": 0.100,        # 100ms for bulk insert of 1000 records
    "relationship_loading": 0.050, # 50ms for relationship loading
    "aggregate_query": 0.020,    # 20ms for aggregate queries
}
```

## Running Benchmarks

### Run All Performance Tests

```bash
# Run all performance benchmarks
pytest tests/performance/ -v

# Run with verbose output
pytest tests/performance/ -v -s

# Run specific test file
pytest tests/performance/test_model_performance.py -v

# Run specific test class
pytest tests/performance/test_model_performance.py::TestModelCreationPerformance -v

# Run specific test
pytest tests/performance/test_model_performance.py::TestModelCreationPerformance::test_species_creation_performance -v
```

### Generate Benchmark Reports

```bash
# Generate HTML benchmark report
pytest tests/performance/ --benchmark-only --benchmark-html=benchmark_report.html

# Generate JSON report for CI integration
pytest tests/performance/ --benchmark-only --benchmark-json=benchmark_results.json

# Compare with previous results
pytest tests/performance/ --benchmark-only --benchmark-compare=benchmark_results.json

# Save baseline for future comparison
pytest tests/performance/ --benchmark-only --benchmark-save=baseline
```

### Performance Regression Detection

```bash
# Detect performance regressions (fail if 20% slower than baseline)
pytest tests/performance/ --benchmark-only --benchmark-compare=baseline --benchmark-warmup=on

# Generate regression report
pytest tests/performance/ --benchmark-only --benchmark-compare=baseline --benchmark-histogram
```

## Benchmark Output Analysis

### Understanding Benchmark Results

```text

------------------------------------------------------------------------------------------ benchmark: 2 tests ------------------------------------------------------------------------------------------
Name (time in us)                    Min                   Max               Mean            StdDev             Median               IQR            Outliers  OPS (Kops/s)            Rounds  Iterations
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
test_simple_species_creation      2.9170 (1.0)         14.8330 (1.0)       3.5431 (1.0)      1.3277 (1.0)       3.3340 (1.0)      0.1260 (1.0)          7;84      282.2384 (1.0)         330           1
test_batch_creation              30.1670 (10.34)    1,180.4170 (79.58)    34.5469 (9.75)     9.8939 (7.45)     34.3330 (10.30)    1.0420 (8.27)     162;3837       28.9462 (0.10)      16238           1
--------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------
```

**Key Metrics:**

- **Min/Max**: Fastest/slowest execution times
- **Mean**: Average execution time (primary metric)
- **StdDev**: Standard deviation (consistency measure)
- **Median**: Middle value (robust to outliers)
- **OPS**: Operations per second
- **Rounds**: Number of test rounds executed
- **Outliers**: Statistical outliers detected

### Performance Analysis Guidelines

1. **Focus on Mean time**: Primary performance indicator
2. **Check StdDev**: High values indicate inconsistent performance
3. **Monitor Outliers**: Too many outliers suggest measurement issues
4. **Compare OPS**: Higher operations per second = better performance

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Performance Tests

on: [push, pull_request]

jobs:
  performance:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"

    - name: Install dependencies
      run: |
        pip install -e ".[test,performance]"

    - name: Run performance benchmarks
      run: |
        pytest tests/performance/ --benchmark-only --benchmark-json=benchmark_results.json

    - name: Upload benchmark results
      uses: actions/upload-artifact@v3
      with:
        name: benchmark-results
        path: benchmark_results.json

    - name: Performance regression check
      run: |
        # Compare with baseline if available
        if [ -f baseline.json ]; then
          pytest tests/performance/ --benchmark-only --benchmark-compare=baseline.json --benchmark-fail=20
        fi
```

### Performance Threshold Validation

```bash
# Validate that all benchmarks meet performance thresholds
pytest tests/performance/ --benchmark-only --benchmark-max-time=1.0

# Fail tests if performance exceeds thresholds
pytest tests/performance/ --benchmark-only --benchmark-performance-regression=20
```

## Best Practices

### 1. Test Environment Setup

- Use consistent hardware for benchmark comparisons
- Disable unnecessary services during benchmarking
- Use the same Python and dependency versions
- Run benchmarks multiple times to establish baseline

### 2. Benchmark Design

- Keep benchmark operations focused and representative
- Use realistic data sizes and patterns
- Include both simple and complex operations
- Test edge cases and worst-case scenarios

### 3. Result Interpretation

- Focus on trends rather than absolute values
- Consider hardware and environmental factors
- Use statistical analysis for significant changes
- Document baseline expectations

### 4. Performance Monitoring

- Run benchmarks regularly (daily/weekly)
- Track performance trends over time
- Set up alerts for significant regressions
- Maintain historical performance data

## Troubleshooting

### Common Issues

#### High Standard Deviation

- Check for system load during benchmarks
- Ensure consistent test data
- Verify database state consistency
- Consider increasing warmup iterations

#### Inconsistent Results

- Disable system services that may interfere
- Use performance-optimized system settings
- Ensure consistent database schema
- Check for memory or disk I/O bottlenecks

#### Benchmark Failures

- Verify test dependencies are installed
- Check database connection configuration
- Ensure test data fixtures are working
- Review test isolation and cleanup

### Debug Mode

```bash
# Enable verbose benchmark debugging
pytest tests/performance/ -v -s --benchmark-warmup=on --benchmark-sort=mean

# Run single benchmark for detailed analysis
pytest tests/performance/test_model_performance.py::TestModelCreationPerformance::test_species_creation_performance -v -s --benchmark-min-rounds=20
```

## Extending the Framework

### Adding New Benchmarks

1. **Create new test class** in appropriate test file
2. **Define benchmark function** with proper fixtures
3. **Include performance assertions** if needed
4. **Add documentation** for new benchmarks

Example:

```python
class TestNewFeaturePerformance:
    def test_new_operation_performance(self, benchmark, benchmark_session):
        """Benchmark new operation performance."""
        def new_operation():
            # Your operation here
            return result

        result = benchmark(new_operation)
        assert result.is_valid
```

### Custom Performance Thresholds

```python
@pytest.fixture
def custom_performance_thresholds():
    """Custom thresholds for specific operations."""
    return {
        "fast_operation": 0.0001,  # 0.1ms
        "slow_operation": 0.1,     # 100ms
    }
```

## References

- [pytest-benchmark documentation](https://pytest-benchmark.readthedocs.io/)
- [SQLAlchemy performance guide](https://docs.sqlalchemy.org/en/20/performance.html)
- [Python profiling guide](https://docs.python.org/3/library/profile.html)

---

This performance testing framework provides comprehensive coverage of ORM operations and ensures consistent performance monitoring throughout the development lifecycle.
