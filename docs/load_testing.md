# Load Testing Framework for Concurrent Query Handling

This document describes the comprehensive load testing framework for validating the VGNC ORM's performance under concurrent access patterns.

## Overview

The load testing framework provides:

- **Concurrent user simulation** with configurable thread pools
- **Realistic database workloads** including reads, writes, and mixed operations
- **Performance metrics collection** with detailed statistics
- **Stress testing capabilities** for high-load scenarios
- **Regression detection** for performance monitoring
- **JSON output support** for CI/CD integration

## Setup

### Dependencies

Load testing uses standard Python libraries plus SQLAlchemy:

```bash
# Core dependencies (already installed with the ORM)
pip install sqlalchemy

# Optional: For advanced load testing
pip install locust  # Alternative load testing framework
```

### Test Environment

The load testing framework creates an isolated in-memory SQLite database populated with realistic test data:

- **100 species records** with varying taxon IDs
- **150 assembly records** (3 assemblies per species for 50 species)
- **2500 chromosome records** (25 chromosomes per species)
- **Proper foreign key relationships** for realistic query patterns

## Available Load Tests

### 1. Concurrent Read Operations

#### Species Lookup Tests

- **Test**: `test_concurrent_species_queries`
- **Pattern**: Primary key lookups on species table
- **Use Case**: Simulates users looking up specific species information
- **Expected Performance**: High throughput, low latency (<10ms P95)

#### Complex Query Tests

- **Test**: `test_concurrent_complex_queries`
- **Pattern**: JOIN queries with filtering (species → assemblies → chromosomes)
- **Use Case**: Complex data retrieval with relationships
- **Expected Performance**: Moderate throughput, medium latency (<200ms P95)

#### Aggregate Query Tests

- **Test**: `test_concurrent_aggregate_queries`
- **Pattern**: GROUP BY and COUNT operations
- **Use Case**: Dashboard queries and analytics
- **Expected Performance**: Lower throughput, higher latency (<100ms P95)

#### Pagination Tests

- **Test**: `test_concurrent_pagination_queries`
- **Pattern**: LIMIT/OFFSET queries for paginated results
- **Use Case**: List views with pagination
- **Expected Performance**: High throughput, low latency (<50ms P95)

### 2. Concurrent Write Operations

#### Insert Operations

- **Test**: `test_concurrent_insert_operations`
- **Pattern**: New species record creation with unique IDs
- **Use Case**: User registration or data entry
- **Expected Performance**: Moderate throughput, medium latency (<200ms P95)

#### Update Operations

- **Test**: `test_concurrent_update_operations`
- **Pattern**: In-place updates to existing records
- **Use Case**: Profile updates or data modifications
- **Expected Performance**: High throughput, low latency (<150ms P95)

#### Mixed Operations

- **Test**: `test_concurrent_mixed_operations`
- **Pattern**: 2:1 read-to-write ratio simulating real usage
- **Use Case**: General application usage patterns
- **Expected Performance**: Balanced throughput and latency

### 3. Transaction Handling

#### Transaction Commit Tests

- **Test**: `test_concurrent_transaction_commit`
- **Pattern**: Multi-operation transactions with commits
- **Use Case**: Complex business operations requiring ACID properties
- **Expected Performance**: Lower throughput due to transaction overhead (<300ms P95)

#### Transaction Rollback Tests

- **Test**: `test_concurrent_transaction_rollback`
- **Pattern**: Transactions that are deliberately rolled back
- **Use Case**: Error handling and data consistency validation
- **Expected Performance**: Fast rollback operations (<100ms P95)

### 4. Stress Testing

#### High Concurrency Tests

- **Test**: `test_high_concurrency_stress`
- **Pattern**: 50+ concurrent users with mixed operations
- **Use Case**: Peak load scenarios and capacity planning
- **Expected Performance**: Degraded but acceptable performance (<500ms P95)

#### Sustained Load Tests

- **Test**: `test_sustained_load`
- **Pattern**: Extended duration tests (60+ seconds)
- **Use Case**: Memory leak detection and performance stability
- **Expected Performance**: Stable performance over time

## Running Load Tests

### Through Pytest

```bash
# Run all load tests
pytest tests/load/ -v -s

# Run specific test class
pytest tests/load/test_concurrent_queries.py::TestConcurrentReadOperations -v

# Run specific test
pytest tests/load/test_concurrent_queries.py::TestConcurrentReadOperations::test_concurrent_species_queries -v

# Run with custom markers
pytest -m "load_test" tests/load/ -v
pytest -m "slow_load_test" tests/load/ -v
```

### Standalone Script

```bash
# Run simple load test (works independently)
python simple_load_test.py --test lookup --users 10 --duration 30

# Run all tests
python simple_load_test.py --test all --users 20 --duration 60

# Save results to JSON
python simple_load_test.py --test all --users 20 --duration 30 --output load_results.json

# Available tests: lookup, complex, insert, mixed, transactions, aggregate
```

## Load Test Configuration

### Default Parameters

```python
LOAD_TEST_CONFIG = {
    "concurrent_users": {
        "light": 5,      # Light load testing
        "medium": 20,    # Medium load testing
        "heavy": 50,     # Heavy load testing
        "stress": 100,   # Stress testing
    },
    "test_duration": {
        "quick": 10,     # Quick validation
        "normal": 30,    # Normal testing
        "extended": 60,  # Extended testing
        "stress": 120,   # Stress duration
    },
    "performance_thresholds": {
        "response_time_p95": 0.1,      # 100ms P95 threshold
        "response_time_p99": 0.5,      # 500ms P99 threshold
        "error_rate": 0.01,            # 1% max error rate
        "throughput_min": 100,         # 100 ops/sec minimum
    }
}
```

### Custom Configuration

You can customize load test parameters by modifying the fixtures:

```python
@pytest.fixture
def custom_load_test_config():
    """Custom load test configuration."""
    return {
        "concurrent_users": {"custom": 30},
        "test_duration": {"custom": 45},
        "performance_thresholds": {
            "response_time_p95": 0.05,  # Stricter: 50ms
            "throughput_min": 200,       # Higher: 200 ops/sec
        }
    }
```

## Performance Metrics

### Collected Metrics

Each load test collects comprehensive performance data:

1. **Request Metrics**

   - Total requests executed
   - Successful requests
   - Failed requests
   - Error rate percentage

2. **Response Time Metrics**

   - Average response time
   - 50th percentile (median)
   - 95th percentile (P95)
   - 99th percentile (P99)
   - Minimum and maximum times

3. **Throughput Metrics**

   - Requests per second
   - Operations per minute
   - Concurrency efficiency

4. **Error Tracking**

   - Error messages and types
   - Error frequency analysis
   - Failure pattern identification

### Example Output

```text
============================================================Load Test Results: Concurrent Species Lookup
============================================================
Total Requests:     2,847
Successful:         2,847
Failed:             0
Duration:           10.00s
Throughput:         284.70 req/s
Error Rate:         0.00%

Response Times:
  Average:           3.51ms
  50th percentile:  3.20ms
  95th percentile:  6.80ms
  99th percentile:  12.40ms
============================================================
```

## Performance Thresholds

### Default Thresholds

- **P95 Response Time**: ≤ 100ms for simple operations
- **P99 Response Time**: ≤ 500ms for complex operations
- **Error Rate**: ≤ 1% for all tests
- **Minimum Throughput**: ≥ 100 ops/sec

### Threshold Adjustment by Test Type

- **Write Operations**: 2x more lenient response time thresholds
- **Complex Queries**: 2x more lenient response time thresholds
- **Stress Tests**: 5x more lenient response time thresholds
- **Transaction Tests**: 3x more lenient response time thresholds

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Load Testing

on: [push, pull_request]

jobs:
  load-tests:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v3

    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: "3.11"

    - name: Install dependencies
      run: |
        pip install -e ".[test]"

    - name: Run load tests
      run: |
        pytest tests/load/test_concurrent_queries.py::TestConcurrentReadOperations::test_concurrent_species_queries -v

    - name: Run stress tests
      run: |
        python simple_load_test.py --test lookup --users 50 --duration 30 --output stress_results.json

    - name: Upload load test results
      uses: actions/upload-artifact@v3
      with:
        name: load-test-results
        path: stress_results.json
```

### Performance Regression Detection

```bash
# Run load tests and save baseline
python simple_load_test.py --test all --users 20 --duration 30 --output baseline.json

# Compare against baseline in CI
if [ -f baseline.json ]; then
  python simple_load_test.py --test all --users 20 --duration 30 --output current.json

  # Compare results (custom script needed)
  python compare_load_results.py baseline.json current.json
fi
```

## Best Practices

### 1. Test Environment Setup

- Use dedicated hardware for consistent results
- Disable unnecessary services during testing
- Ensure consistent database state between runs
- Monitor system resources (CPU, memory, I/O)

### 2. Test Design Principles

- Simulate realistic user behavior patterns
- Include appropriate think times between operations
- Test both average and peak load scenarios
- Validate data consistency under load

### 3. Result Analysis

- Focus on percentiles rather than averages
- Monitor error rates and failure patterns
- Track performance trends over time
- Correlate performance with system metrics

### 4. Continuous Monitoring

- Run load tests regularly (daily/weekly)
- Establish performance baselines
- Set up alerts for performance regressions
- Maintain historical performance data

## Troubleshooting

### Common Issues

#### High Error Rates

- Check database connection limits
- Verify foreign key constraints
- Monitor memory usage
- Review concurrent access patterns

#### Slow Response Times

- Analyze query execution plans
- Check for missing indexes
- Monitor database locks
- Review transaction isolation levels

#### Inconsistent Results

- Ensure proper test isolation
- Check for resource contention
- Verify database cleanup between tests
- Monitor system load variations

### Debug Mode

```bash
# Run with verbose output
pytest tests/load/ -v -s --tb=long

# Run single test for detailed analysis
pytest tests/load/test_concurrent_queries.py::TestConcurrentReadOperations::test_concurrent_species_queries -v -s

# Enable SQLAlchemy debugging
SQLALCHEMY_ECHO=1 python simple_load_test.py --test lookup --users 5 --duration 10
```

## Performance Optimization

### Database Optimization

1. **Indexing**: Ensure proper indexes on foreign keys and query columns
2. **Connection Pooling**: Optimize pool size for expected load
3. **Query Optimization**: Use EXPLAIN QUERY PLAN for slow queries
4. **Batch Operations**: Use bulk inserts/updates for large datasets

### Application Optimization

1. **Connection Management**: Reuse connections efficiently
2. **Transaction Scope**: Keep transactions short and focused
3. **Caching**: Implement appropriate caching strategies
4. **Async Operations**: Consider async patterns for I/O-bound operations

### System Optimization

1. **Memory Allocation**: Ensure adequate memory for database cache
2. **I/O Configuration**: Use appropriate storage subsystems
3. **Network Configuration**: Optimize for database connection latency
4. **Resource Limits**: Configure appropriate system limits

## Extending the Framework

### Adding New Tests

```python
@pytest.mark.load_test
def test_custom_load_scenario(self, load_test_runner, populated_load_test_db, load_test_config):
    """Custom load test scenario."""

    def custom_operation(session: Session, worker_id: int):
        # Your custom operation here
        return result

    result = load_test_runner.run_concurrent_test(
        custom_operation,
        num_users=load_test_config["concurrent_users"]["medium"],
        duration=load_test_config["test_duration"]["normal"]
    )

    # Assert performance meets requirements
    assert_load_test_performance(result, load_test_config["performance_thresholds"], "custom scenario")
```

### Custom Metrics Collection

```python
class CustomLoadTestRunner(LoadTestRunner):
    """Extended load test runner with custom metrics."""

    def run_load_test_with_metrics(self, test_func, test_name, num_users, duration):
        # Run standard test
        result = super().run_load_test(test_func, test_name, num_users, duration)

        # Add custom metrics
        result.custom_metric = self.calculate_custom_metric()

        return result
```

## References

- [SQLAlchemy Performance Guide](https://docs.sqlalchemy.org/en/20/performance.html)
- [Python Concurrency Documentation](https://docs.python.org/3/library/concurrency.html)
- [Load Testing Best Practices](https://github.com/topics/load-testing)

---

This load testing framework provides comprehensive validation of the ORM's concurrent query handling capabilities and ensures reliable performance under realistic load conditions.
