# CI/CD Pipeline for Automated Test Execution

This document describes the comprehensive continuous integration and continuous deployment (CI/CD) pipeline for the VGNC ORM project.

## Overview

The CI/CD pipeline provides:

- **Automated testing** across multiple Python versions
- **Test suite execution** (unit, integration, performance, load tests)
- **Code quality checks** (formatting, linting, security)
- **Build validation** and package distribution
- **Coverage reporting** and performance tracking
- **Artifact management** and result aggregation
- **Notification system** for pipeline status updates

## Pipeline Architecture

### Workflow Triggers

The CI pipeline is triggered by:

```yaml
# Manual dispatch (with options)
workflow_dispatch:
  inputs:
    test_type:
      description: 'Type of tests to run'
      type: choice
      options: [all, unit, integration, performance, load, coverage]
    python_version:
      description: 'Python version to test'
      type: choice
      options: ['3.11', '3.12', '3.13']

# Automated triggers
on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main, develop ]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM UTC
```

### Job Dependencies

```text
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│  unit-tests     │    │integration-tests│    │performance-tests│
│ (3.11, 3.12,    │    │ (3.11, 3.12,    │    │     (3.13).     │
│ 3.13).          │    │ 3.13).          │    │                 │
└─────────┬───────┘    └─────────┬───────┘    └─────────┬───────┘
          │                      │                      │
          └──────────────────────┼──────────────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │    test-summary           │
                   └─────────────┬─────────────┘
                                 │
                   ┌─────────────▼─────────────┐
                   │    notifications          │
                   └───────────────────────────┘
```

## Test Execution Matrix

### Test Matrix Configuration

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
    include:
      - python-version: "3.11"
        test-type: "unit"
        cache-key: "unit"
      - python-version: "3.12"
        test-type: "integration"
        cache-key: "integration"
      - python-version: "3.13"
        test-type: "performance"
        cache-key: "performance"
```

### Test Types and Requirements

| Test Type        | Python Versions        | Est. Duration | Coverage Target |
|------------------|------------------------|---------------|-----------------|
| Unit Tests       | `3.11`, `3.12`, `3.13` | ≈ 5 min       | ≥ 70 %          |
| Integration Tests| `3.11`, `3.12`, `3.13` | ≈ 10 min      | ≥ 60 %          |
| Performance Tests| `3.13`                 | ≈ 3 min       | —               |
| Load Tests*      | `3.13`                 | ≈ 5–30 min    | —               |

## Job Definitions

### 1. Unit Tests

**Purpose**: Fast feedback on individual component functionality

```yaml
unit-tests:
  name: Unit Tests
  runs-on: ubuntu-latest
  strategy:
    matrix:
      python-version: ["3.11", "3.12", "3.13"]

  steps:
    - name: Checkout code
      uses: actions/checkout@v4

    - name: Set up Python ${{ matrix.python-version }}
      uses: actions/setup-python@v4

    - name: Install dependencies
      run: pip install -e ".[test]"

    - name: Run unit tests
      run: |
        python -m pytest tests/unit/ \
          --verbose \
          --tb=short \
          --durations=10 \
          --maxfail=5 \
          --junit-xml=test-results/unit.xml
```

**Features:**

- Fast execution (~5 minutes)
- Parallel testing across Python versions
- Early failure detection
- Detailed error reporting
- Duration analysis for slow tests

### 2. Integration Tests

**Purpose**: Test component interactions and database connectivity

```yaml
integration-tests:
  name: Integration Tests
  runs-on: ubuntu-latest
  needs: unit-tests
  strategy:
    matrix:
      python-version: ["3.11", "3.12", "3.13"]

  steps:
    - name: Install dependencies
      run: |
        pip install -e ".[test,mysql]"
        pip install testcontainers[mysql]

    - name: Run integration tests
      run: |
        python -m pytest tests/integration/ \
          --verbose \
          --tb=short \
          --durations=10 \
          --maxfail=5
```

**Features:**

- MySQL testcontainers integration
- Docker-based database testing
- Database schema validation
- Relationship testing
- Transaction handling verification

### 3. Performance Tests

**Purpose**: Benchmark performance and detect regressions

```yaml
performance-tests:
  name: Performance Tests
  runs-on: ubuntu-latest
  needs: integration-tests

  steps:
    - name: Install dependencies
      run: |
        pip install -e ".[test,performance]"
        pip install pytest-benchmark

    - name: Run performance benchmarks
      run: |
        python -m pytest tests/performance/ \
          --benchmark-only \
          --benchmark-json=test-results/benchmark.json \
          --benchmark-html=test-results/benchmark.html

    - name: Performance regression checks
      run: |
        python -m pytest tests/performance/ \
          --benchmark-only \
          --benchmark-compare=baseline \
          --benchmark-compare-fail=20%
```

**Features:**

- pytest-benchmark integration
- Performance baseline tracking
- Regression detection (20% threshold)
- HTML benchmark reports
- Histogram generation for analysis

### 4. Load Tests

**Purpose**: Validate performance under concurrent load

```yaml
load-tests:
  name: Load Tests
  runs-on: ubuntu-latest
  needs: performance-tests
  if: github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'run-load-tests')

  strategy:
    matrix:
      test-scenario:
        - name: "light-load"
          users: 5
          duration: 30
        - name: "medium-load"
          users: 20
          duration: 60
        - name: "heavy-load"
          users: 50
          duration: 30

  steps:
    - name: Run load test
      run: |
        python simple_load_test.py \
          --test lookup \
          --users ${{ matrix.test-scenario.users }} \
          --duration ${{ matrix.test-scenario.duration }} \
          --output test-results/load-test.json
```

**Features:**

- Configurable user loads (5, 20, 50 concurrent users)
- Different test durations
- Performance metrics collection
- JSON output for analysis
- Manual trigger option for PRs

### 5. Quality Checks

**Purpose**: Code quality, formatting, and security validation

```yaml
quality-checks:
  name: Quality Checks
  runs-on: ubuntu-latest

  steps:
    - name: Install dependencies
      run: |
        pip install -e ".[dev]"

    - name: Run code quality checks
      run: |
        # Format check
        black --check --diff src/ tests/

        # Import sorting check
        isort --check-only --diff src/ tests/

        # Linting
        flake8 src/ tests/ --max-line-length=120

        # Type checking
        mypy src/ --ignore-missing-imports || true

    - name: Run security checks
      run: |
        # Security vulnerabilities
        bandit -r src/ -f json -o test-results/security-report.json

        # Dependency vulnerabilities
        pip-audit --output-format=json || true
```

**Features:**

- Code formatting validation (black)
- Import sorting (isort)
- Linting (flake8)
- Type checking (mypy)
- Security scanning (bandit)
- Dependency vulnerability checking (pip-audit)

### 6. Build Validation

**Purpose**: Package building and distribution validation

```yaml
build-validation:
  name: Build Validation
  strategy:
    matrix:
      python-version: ["3.11", "3.12", "3.13"]

  steps:
    - name: Build package
      run: |
        python -m pip install --upgrade pip build
        python -m build

    - name: Check package
      run: |
        twine check dist/*

    - name: Install package
      run: |
        python -m pip install dist/*.whl

    - name: Validate installation
      run: |
        python -c "import vgnc_internal_orm; print('Package installed successfully')"
```

**Features:**

- PEP 517/518 compliant building
- Package validation with twine
- Installation testing
- Multi-Python version compatibility

## Performance and Optimization

### Caching Strategy

```yaml
- name: Cache pip dependencies
  uses: actions/cache@v3
  with:
    path: ~/.cache/pip
    key: ${{ runner.os }}-pip-${{ cache-key }}-${{ hashFiles('**/pyproject.toml') }}
    restore-keys: |
      ${{ runner.os }}-pip-${{ cache-key }}-
      ${{ runner.os }}-pip-
```

**Cache Keys:**

- Unit tests: `unit`
- Integration tests: `integration`
- Performance tests: `performance`
- Load tests: `load`
- Quality checks: `quality`

### Parallel Execution

```yaml
strategy:
  matrix:
    python-version: ["3.11", "3.12", "3.13"]
  fail-fast: false  # Continue testing other versions if one fails
```

### Fast Feedback

- **Unit tests**: Run immediately on all Python versions
- **Integration tests**: Depend on unit tests success
- **Performance tests**: Depend on integration tests success
- **Load tests**: Manual trigger for PRs, automatic for main branch

## Artifact Management

### Test Results

```yaml
- name: Upload test results
  uses: actions/upload-artifact@v3
  if: always()
  with:
    name: test-results-${{ matrix.python-version }}-${{ matrix.test-type }}
    path: |
      test-results/
    retention-days: 7
```

**Artifacts Generated:**

- JUnit XML reports
- Coverage reports (XML, HTML)
- Performance benchmark reports
- Load test JSON results
- Security scan reports
- Build artifacts (wheels, source distributions)

### Coverage Reports

```yaml
# Unit test coverage
--cov-report=xml:test-results/coverage-unit-${{ matrix.python-version }}.xml
--cov-report=html:test-results/coverage-html-unit-${{ matrix.python-version }}

# Combined coverage
python -m coverage combine
python -m coverage xml -o coverage-combined.xml
python -m coverage html -o htmlcov-combined
```

## Error Handling and Failures

### Failure Strategies

```yaml
# Fast failure for critical jobs
strategy:
  fail-fast: true

# Continue on non-critical failures
strategy:
  fail-fast: false

# Conditional execution
if: github.event_name != 'pull_request' || contains(github.event.pull_request.labels.*.name, 'run-load-tests')
```

### Error Reporting

```yaml
- name: Run tests with failure handling
  run: |
    python -m pytest tests/unit/ \
      --maxfail=5 \
      --tb=short \
      || echo "Tests failed but continuing..."
```

## Notifications and Reporting

### Test Summary Generation

```python
def generate_test_summary():
    total_tests = 0
    total_failures = 0
    total_errors = 0

    # Aggregate results from all test files
    for result_file in glob.glob('all-test-results/**/*.xml'):
        tests, failures, errors = parse_junit_xml(result_file)
        total_tests += tests
        total_failures += failures
        total_errors += errors

    # Generate markdown summary
    print(f"## 🧪 Test Results Summary")
    print(f"- **Total Tests:** {total_tests}")
    print(f"- **Passed:** {total_tests - total_failures - total_errors}")
    print(f"- **Failed:** {total_failures}")
    print(f"- **Errors:** {total_errors}")
    print(f"- **Success Rate:** {success_rate:.1f}%")
```

### PR Comments

```yaml
- name: Comment test summary on PR
  if: github.event_name == 'pull_request'
  uses: actions/github-script@v7
  with:
    script: |
      const summary = fs.readFileSync('test-summary.md', 'utf8');
      github.rest.issues.createComment({
        issue_number: context.issue.number,
        owner: context.repo.owner,
        repo: context.repo.repo,
        body: summary
      });
```

### Notifications

**Success Notification:**

- Pipeline completed successfully
- All tests passed
- Coverage thresholds met
- Performance benchmarks within limits

**Failure Notification:**

- Specific test failures identified
- Coverage below threshold
- Performance regressions detected
- Build validation errors

## Security Considerations

### Dependency Scanning

```yaml
- name: Security checks
  run: |
    # Check for security vulnerabilities in code
    bandit -r src/ -f json -o test-results/security-report.json

    # Check dependencies for vulnerabilities
    pip-audit --output-format=json --output-file=test-results/dependency-audit.json
```

### Secret Management

```yaml
env:
  PYTHONUNBUFFERED: 1
  PYTHONDONTWRITEBYTECODE: 1
  # No secrets exposed in workflow
```

### Access Control

- **Read-only access** to repository for testing
- **Isolated environments** for test execution
- **No production credentials** in CI/CD
- **Artifact retention limits** (7 days for test results)

## Local Development

### Running CI Tests Locally

```bash
# Install CI dependencies
pip install -e ".[test,performance,dev]"

# Run unit tests (CI style)
python -m pytest tests/unit/ \
  --verbose \
  --tb=short \
  --durations=10 \
  --maxfail=5

# Run integration tests
python -m pytest tests/integration/ \
  --verbose \
  --tb=short \
  --durations=10

# Run performance tests
python -m pytest tests/performance/ \
  --benchmark-only \
  --benchmark-json=local-benchmark.json

# Run quality checks
black --check --diff src/ tests/
isort --check-only --diff src/ tests/
flake8 src/ tests/
bandit -r src/
```

### Pre-commit Hook Simulation

```bash
# Simulate CI quality checks locally
pre-commit run --all-files

# Or run individual checks
black src/ tests/
isort src/ tests/
flake8 src/ tests/
mypy src/
```

## Monitoring and Maintenance

### Pipeline Performance

- **Execution Time**: Monitor total pipeline duration
- **Success Rate**: Track pass/fail rates over time
- **Resource Usage**: Monitor GitHub Actions runner usage
- **Artifact Storage**: Monitor artifact storage consumption

### Maintenance Tasks

1. **Monthly**:
   - Review and update Python versions
   - Update dependency versions
   - Check for deprecated GitHub Actions
   - Review coverage thresholds

2. **Quarterly**:
   - Optimize caching strategies
   - Review test execution times
   - Update quality check rules
   - Audit security scanning tools

3. **As Needed**:
   - Add new test types
   - Update notification settings
   - Modify failure handling
   - Add new quality checks

## Troubleshooting

### Common Issues

**Cache Misses:**

- Check cache key formatting
- Verify dependency file changes
- Review cache retention policies

**Test Failures:**

- Review test logs for specific errors
- Check Python version compatibility
- Verify environment setup

**Build Failures:**

- Check pyproject.toml configuration
- Verify build dependencies
- Review package metadata

**Performance Issues:**

- Monitor job execution times
- Optimize caching strategies
- Consider test parallelization

### Debug Mode

```yaml
# Enable debug logging
env:
  ACTIONS_STEP_DEBUG: true
  ACTIONS_RUNNER_DEBUG: true

# Add verbose output
- name: Debug test execution
  run: |
    python -m pytest tests/unit/ \
      --verbose \
      --debug
```

### Manual Pipeline Triggers

```bash
# Using GitHub CLI
gh workflow run ci.yml \
  --field test_type=performance \
  --field python_version=3.13

# Using GitHub API
curl -X POST \
  -H "Authorization: token $GITHUB_TOKEN" \
  -H "Accept: application/vnd.github.v3+json" \
  https://api.github.com/repos/$OWNER/$REPO/actions/workflows/ci.yml/dispatches \
  -d '{"ref":"main","inputs":{"test_type":"integration"}}'
```

## Best Practices

### Pipeline Design

1. **Fast Feedback**: Unit tests run first and fastest
2. **Dependency Management**: Clear job dependencies
3. **Fail Fast**: Critical jobs fail fast to save resources
4. **Parallel Execution**: Matrix strategy for parallel testing
5. **Artifact Management**: Proper retention and organization

### Test Organization

1. **Test Isolation**: Each test type independent
2. **Data Management**: Test data created and cleaned properly
3. **Environment Consistency**: Same environment across local and CI
4. **Error Handling**: Proper error reporting and cleanup
5. **Performance Monitoring**: Track test execution times

### Quality Assurance

1. **Automated Quality Gates**: Enforce standards automatically
2. **Coverage Requirements**: Minimum coverage thresholds
3. **Security Scanning**: Regular vulnerability assessments
4. **Performance Monitoring**: Track performance regressions
5. **Documentation**: Keep pipeline documentation current

---

This comprehensive CI/CD pipeline ensures that the VGNC ORM maintains high quality through automated testing, quality checks, and continuous monitoring across all development stages.
