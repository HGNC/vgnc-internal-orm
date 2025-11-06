# Code Coverage Metrics and Reporting

This document describes the comprehensive code coverage framework for tracking how much of the VGNC ORM codebase is being tested.

## Overview

The code coverage framework provides:

- **Comprehensive coverage tracking** for all ORM modules
- **Multiple report formats** (terminal, HTML, JSON, XML)
- **Coverage thresholds** with failure enforcement
- **Branch coverage analysis** for complete testing validation
- **Integration with CI/CD pipelines** for automated reporting
- **Historical tracking** for coverage trends over time

## Setup

### Dependencies

```bash
# Coverage tools are already included with pytest-cov
pip install pytest-cov

# For standalone coverage usage
pip install coverage[toml]
```

### Configuration

The coverage configuration is defined in `.coveragerc`:

```ini
[run]
source = src/vgnc_internal_orm
omit =
    */tests/*
    */test_*.py
    */__pycache__/*
    */site-packages/*
branch = True
parallel = False
data_file = .coverage

[report]
exclude_lines =
    pragma: no cover
    if self.debug:
    if __name__ == "__main__":
    if TYPE_CHECKING:
    raise AssertionError
    raise NotImplementedError
    raise ImportError
    def __repr__
    def __str__
    @abstractmethod
    @abc.abstractmethod
    if False:
    if 0:
    if __debug__:
    >>>
    ...
    except ImportError:
    except ModuleNotFoundError:
    except ValueError:
    except TypeError:
    except KeyError:
    except AttributeError:
    class .*\(Protocol\):
    class .*\(ABC\):
    class .*Interface:
    @overload
    @.*\.setter
show_missing = True
precision = 2
sort = Name
skip_covered = False
skip_empty = True

[html]
directory = htmlcov
show_contexts = True

[xml]
output = coverage.xml

[json]
output = coverage.json
show_contexts = True
```

## Running Coverage Reports

### Basic Coverage Commands

```bash
# Run tests with coverage
python -m pytest --cov=src/vgnc_internal_orm --cov-report=term-missing

# Generate HTML report
python -m pytest --cov=src/vgnc_internal_orm --cov-report=html

# Generate JSON report for CI
python -m pytest --cov=src/vgnc_internal_orm --cov-report=json

# Generate XML report for tools
python -m pytest --cov=src/vgnc_internal_orm --cov-report=xml

# Generate all report formats
python -m pytest --cov=src/vgnc_internal_orm \
  --cov-report=term-missing \
  --cov-report=html \
  --cov-report=json \
  --cov-report=xml
```

### Coverage with Test Selection

```bash
# Coverage for unit tests only
python -m pytest tests/unit/ --cov=src/vgnc_internal_orm --cov-report=term-missing

# Coverage for integration tests only
python -m pytest tests/integration/ --cov=src/vgnc_internal_orm --cov-report=term-missing

# Coverage for performance tests only
python -m pytest tests/performance/ --cov=src/vgnc_internal_orm --cov-report=term-missing

# Coverage for load tests only
python -m pytest tests/load/ --cov=src/vgnc_internal_orm --cov-report=term-missing

# Coverage for specific test files
python -m pytest tests/unit/test_config.py --cov=src/vgnc_internal_orm --cov-report=term-missing
```

### Standalone Coverage Usage

```bash
# Run coverage on a specific script
python -m coverage run test_coverage_demo.py

# Generate report after running
python -m coverage report --show-missing

# Generate HTML report
python -m coverage html

# Clear previous coverage data
python -m coverage erase

# Combine coverage from multiple runs
python -m coverage combine
```

## Coverage Report Formats

### 1. Terminal Report

The terminal report provides a quick overview directly in your console:

```text
Name                                              Stmts   Miss  Cover   Missing
-----------------------------------------------------------------------------------------
src/vgnc_internal_orm/__init__.py                   15      0   100%
src/vgnc_internal_orm/config/__init__.py            45      5    89%   23-24, 45-48
src/vgnc_internal_orm/config/database.py            120     30    75%   67-89, 120-145
src/vgnc_internal_orm/models/__init__.py             10      0   100%
src/vgnc_internal_orm/models/base.py                 85     15    82%   45-67, 123-134
src/vgnc_internal_orm/models/species.py             156    23    85%   78-90, 156-178
src/vgnc_internal_orm/sessions/__init__.py           35      5    86%   12-15
-----------------------------------------------------------------------------------------
TOTAL                                             466     78    83%
```

### 2. HTML Report

The HTML report provides an interactive, detailed view:

```bash
# Generate HTML report
python -m coverage html

# View in browser
open htmlcov/index.html
```

**Features:**

- Interactive source code viewing
- Color-coded coverage visualization
- Branch coverage indicators
- Missing line highlighting
- Search and navigation capabilities

### 3. JSON Report

The JSON report provides programmatic access to coverage data:

```bash
# Generate JSON report
python -m coverage json

# Use in scripts
python -c "
import json
with open('coverage.json') as f:
    data = json.load(f)
    print(f'Total coverage: {data[\"totals\"][\"percent_covered\"]:.1f}%')
    print(f'covered lines: {data[\"totals\"][\"covered_lines\"]}')
    print(f'missing lines: {data[\"totals\"][\"missing_lines\"]}')
"
```

### 4. XML Report

The XML report is compatible with CI/CD tools and coverage services:

```bash
# Generate XML report
python -m coverage xml

# Use with CI tools (example for GitHub Actions)
- name: Upload coverage to Codecov
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage.xml
    flags: unittests
    name: codecov-umbrella
```

## Coverage Thresholds

### Setting Minimum Coverage

```bash
# Fail if coverage is below 80%
python -m pytest --cov=src/vgnc_internal_orm --cov-fail-under=80

# Fail if coverage is below 90% for production
python -m pytest --cov=src/vgnc_internal_orm --cov-fail-under=90
```

### Per-Module Coverage Requirements

```bash
# Check coverage for specific modules
python -m pytest --cov=src/vgnc_internal_orm.models \
  --cov-fail-under=85 \
  --cov-report=term-missing

python -m pytest --cov=src/vgnc_internal_orm.config \
  --cov-fail-under=90 \
  --cov-report=term-missing
```

## Branch Coverage

### Enabling Branch Coverage

Branch coverage measures both if statements and their branches:

```ini
# In .coveragerc
[run]
branch = True
```

### Running Branch Coverage

```bash
# Run tests with branch coverage
python -m pytest --cov=src/vgnc_internal_orm --cov-branch --cov-report=term-missing

# Check branch coverage specifically
python -m coverage report --show-missing --show-contexts
```

### Branch Coverage Report Example

```text
Name                                              Stmts   Miss Branch BrPart  Cover   Missing
-----------------------------------------------------------------------------------------
src/vgnc_internal_orm/config/database.py            120     30     12      3    73%   67-89, 2->exit, 45->46
src/vgnc_internal_orm/models/species.py             156    23      8      2    81%   78-90, 123->124, 156->exit
-----------------------------------------------------------------------------------------
TOTAL                                             466     78     25      5    79%
```

## Coverage Patterns and Exclusions

### Common Exclusions

The configuration automatically excludes common patterns:

```python
# Debug code
if self.debug:
    expensive_debug_operation()

# Script entry points
if __name__ == "__main__":
    main()

# Type checking blocks
if TYPE_CHECKING:
    from typing import Optional

# Abstract methods
@abstractmethod
def abstract_method(self):
    pass

# Error handling that's hard to test
try:
    risky_operation()
except ImportError:
    handle_import_error()

# Defensive programming
if False:
    unreachable_code()
```

### Custom Exclusions

Add custom patterns to `.coveragerc`:

```ini
[report]
exclude_lines =
    # Standard exclusions (from above)
    pragma: no cover
    # ... other patterns

    # Custom exclusions
    # Development utilities
    if DEVELOPMENT_MODE:

    # Testing utilities
    @pytest.fixture
    def test_.*:

    # Performance monitoring
    if MONITOR_PERFORMANCE:
```

## CI/CD Integration

### GitHub Actions Example

```yaml
name: Code Coverage

on: [push, pull_request]

jobs:
  coverage:
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

    - name: Run tests with coverage
      run: |
        python -m pytest \
          --cov=src/vgnc_internal_orm \
          --cov-report=xml \
          --cov-report=html \
          --cov-report=term-missing \
          --cov-fail-under=80

    - name: Upload coverage to Codecov
      uses: codecov/codecov-action@v3
      with:
        file: ./coverage.xml
        flags: unittests
        name: codecov-umbrella
        fail_ci_if_error: false

    - name: Upload coverage artifacts
      uses: actions/upload-artifact@v3
      with:
        name: coverage-report
        path: htmlcov/
```

### Coverage Badge Generation

```bash
# Generate coverage badge (requires coverage-badge package)
pip install coverage-badge

# After running coverage tests
coverage-badge -o coverage.svg -f coverage.json
```

## Coverage Analysis

### Identifying Uncovered Code

1. **Run comprehensive coverage report**

   ```bash
   python -m pytest --cov=src/vgnc_internal_orm --cov-report=term-missing
   ```

2. **Review missing lines** in the terminal output

3. **Open HTML report** for detailed analysis:

   ```bash
   open htmlcov/index.html
   ```

4. **Prioritize uncovered code**:
   - Critical business logic (high priority)
   - Error handling paths (medium priority)
   - Utility functions (low priority)

### Coverage Trends

Track coverage over time:

```bash
# Save coverage data
python -m coverage json > coverage_$(date +%Y%m%d).json

# Compare with previous runs
python -c "
import json
import sys

current = json.load(open('coverage_20241105.json'))
previous = json.load(open('coverage_20241104.json'))

current_pct = current['totals']['percent_covered']
previous_pct = previous['totals']['percent_covered']

change = current_pct - previous_pct
print(f'Coverage change: {change:+.1f}% ({current_pct:.1f}% total)')
"
```

## Best Practices

### 1. Coverage Targets

- **Minimum Coverage**: 80% for production code
- **Critical Modules**: 90%+ coverage
- **Utility Modules**: 70%+ coverage
- **Test Files**: Not included in coverage calculations

### 2. Coverage Quality

- **Focus on meaningful coverage** rather than percentage
- **Test error conditions and edge cases**
- **Cover both positive and negative paths**
- **Include integration and end-to-end scenarios**

### 3. Continuous Monitoring

- **Set up coverage gates** in CI/CD pipelines
- **Monitor coverage trends** over time
- **Investigate sudden coverage drops**
- **Celebrate coverage improvements**

### 4. Coverage Maintenance

- **Regular coverage reviews** (weekly/monthly)
- **Address coverage regressions** immediately
- **Refactor tests** for better coverage
- **Update exclusions** as code evolves

## Advanced Coverage Features

### Coverage Context

```bash
# Run coverage with test context
python -m pytest --cov=src/vgnc_internal_orm --cov-context=test

# View which tests cover which lines
python -m coverage html --show-contexts
```

### Coverage Combining

```bash
# Run different test suites separately
python -m coverage run -m pytest tests/unit/
python -m coverage run -a -m pytest tests/integration/
python -m coverage run -a -m pytest tests/performance/

# Combine results
python -m coverage combine

# Generate combined report
python -m coverage report --show-missing
```

### Coverage Filtering

```bash
# Generate coverage for specific modules only
python -m coverage report --include=src/vgnc_internal_orm/models/*

# Exclude specific modules from coverage
python -m coverage report --omit=src/vgnc_internal_orm/migrations/*
```

## Troubleshooting

### Common Issues

#### Coverage shows 0% or no data

- Check source path configuration in `.coveragerc`
- Ensure PYTHONPATH includes source directory
- Verify tests are actually importing the modules

#### Missing coverage data for imports

- Use `--cov-context=test` to see which tests import modules
- Check if modules are imported before coverage starts
- Consider using `python -m coverage run` instead of pytest-cov

#### Coverage too slow

- Use `parallel = True` in `.coveragerc` for parallel execution
- Exclude non-critical files from coverage
- Run coverage on specific test suites

#### False positives in coverage

- Review exclude patterns in `.coveragerc`
- Add appropriate `# pragma: no cover` comments
- Use conditional imports for test-only code

### Debug Mode

```bash
# Enable verbose coverage output
python -m coverage run --trace=coverage your_script.py

# Check what files are being measured
python -m coverage debug sys

# View coverage configuration
python -m coverage debug config
```

## Integration with Other Tools

### Pre-commit Hooks

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: pytest-cov
        name: pytest with coverage
        entry: python -m pytest
        args: [--cov=src/vgnc_internal_orm, --cov-fail-under=80, --cov-report=term-missing]
        language: system
        pass_filenames: false
        always_run: true
```

### IDE Integration

**VS Code with Python extension:**

```json
{
    "python.testing.pytestArgs": [
        "--cov=src/vgnc_internal_orm",
        "--cov-report=term-missing"
    ]
}
```

**PyCharm:**

- Run/Debug Configurations → Pytest → Additional Arguments
- Add: `--cov=src/vgnc_internal_orm --cov-report=html`

---

This comprehensive coverage framework ensures that the VGNC ORM maintains high code quality through systematic testing and coverage monitoring.
