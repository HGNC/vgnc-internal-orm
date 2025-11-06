.PHONY: help install install-dev test test-unit test-integration test-performance test-load ci clean coverage quality build dev docs-html docs-live examples

# Default target
help:
	@echo "VGNC ORM - Available Commands:"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  install      Install project in development mode"
	@echo "  install-dev  Install development dependencies"
	@echo ""
	@echo "Testing:"
	@echo "  test         Run all tests (quick)"
	@echo "  test-unit    Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-performance Run performance tests only"
	@echo "  test-load    Run load tests only"
	@echo ""
	@echo "CI/CD:"
	@echo "  ci           Run local CI pipeline"
	@echo "  coverage     Run tests with coverage"
	@echo "  quality      Run code quality checks"
	@echo "  build        Build and validate package"
	@echo ""
	@echo "Development:"
	@echo "  dev          Quick development setup"
	@echo "  clean        Clean build artifacts"
	@echo "  format       Format code with black and isort"
	@echo "  lint         Run linting checks"
	@echo "  docs-html    Build Sphinx HTML documentation (docs/_build/html)"
	@echo "  docs-live    Auto-rebuild docs with sphinx-autobuild (if installed)"
	@echo "  examples     Run all example scripts for smoke verification"

# Installation
install:
	pip install -e ".[test,performance]"

install-dev:
	pip install -e ".[test,performance,dev]"
	pip install black isort flake8 mypy bandit twine build

# Testing
test:
	python -m pytest tests/unit/ tests/integration/ --tb=short --maxfail=5

test-unit:
	python -m pytest tests/unit/ --tb=short --maxfail=5

test-integration:
	python -m pytest tests/integration/ --tb=short --maxfail=5

test-performance:
	python -m pytest tests/performance/ --benchmark-only

test-load:
	python simple_load_test.py --test lookup --users 10 --duration 30

# CI/CD
ci:
	python scripts/run_ci_locally.py

coverage:
	python -m pytest tests/ --cov=src/vgnc_internal_orm --cov-report=html --cov-report=term-missing

quality:
	black --check src/ tests/
	isort --check-only src/ tests/
	flake8 src/ tests/ --max-line-length=120
	bandit -r src/

build:
	python -m build
	twine check dist/*

# Development
dev:
	pip install -e ".[test,performance,dev]"
	@echo "Development environment setup complete!"

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf htmlcov/
	rm -rf .coverage
	rm -rf test-results/
	rm -rf .pytest_cache/
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

# Code formatting
format:
	black src/ tests/
	isort src/ tests/

# Linting
lint:
	flake8 src/ tests/ --max-line-length=120
	mypy src/ --ignore-missing-imports || true

# Quick development check
dev-check: format lint test-unit

# Full development check
dev-full: install-dev format lint test coverage quality

# Docker development
docker-build:
	docker build -t vgnc-orm-dev .

docker-test:
	docker run --rm vgnc-orm-dev make test

# Performance profiling
profile:
	python -m cProfile -o profile.stats -m pytest tests/unit/ --tb=short
	python -c "import pstats; p=pstats.Stats('profile.stats'); p.sort_stats('cumulative'); p.print_stats(10)"

# Security audit
security:
	pip-audit
	bandit -r src/ -f json -o security-report.json

# Generate documentation
docs:
	pip install sphinx
	cd docs && make html

# Build Sphinx HTML from root (Markdown via MyST)
docs-html:
	pip install sphinx myst-parser
	cd docs && sphinx-build -b html . _build/html
	@echo "Open docs/_build/html/index.html in your browser."

docs-live:
	@command -v sphinx-autobuild >/dev/null 2>&1 || pip install sphinx-autobuild myst-parser
	cd docs && sphinx-autobuild -b html . _build/html

# Run example scripts
examples:
	python examples/basic_sync.py
	python examples/basic_async.py
	python examples/full_text_search_demo.py || true
	python examples/query_optimization_demo.py

# Release preparation
release-check:
	@echo "Preparing for release..."
	$(MAKE) clean
	$(MAKE) install-dev
	$(MAKE) format
	$(MAKE) lint
	$(MAKE) test
	$(MAKE) coverage
	$(MAKE) quality
	$(MAKE) build
	@echo "Release preparation complete!"

# Database testing with Docker
test-mysql:
	docker-compose up -d mysql
	sleep 10
	$(MAKE) test-integration
	docker-compose down

test-postgres:
	docker-compose up -d postgres
	sleep 10
	$(MAKE) test-integration
	docker-compose down

# Performance profiling with memory analysis
memory-profile:
	python -m memory_profiler -o profile.mprof -m pytest tests/unit/ --tb=short
	mprof2pdf profile.mprof

# Load testing with different scenarios
load-test-light:
	python simple_load_test.py --test lookup --users 5 --duration 30

load-test-medium:
	python simple_load_test.py --test lookup --users 20 --duration 60

load-test-heavy:
	python simple_load_test.py --test lookup --users 50 --duration 30

# Generate test reports
reports:
	mkdir -p reports
	$(MAKE) coverage 2>&1 | tee reports/coverage.txt
	$(MAKE) test 2>&1 | tee reports/test-results.txt
	$(MAKE) quality 2>&1 | tee reports/quality-checks.txt

# Pre-commit setup
pre-commit-install:
	pip install pre-commit
	pre-commit install

# Run pre-commit hooks
pre-commit:
	pre-commit run --all-files

# Benchmark comparison
benchmark-compare:
	python -m pytest tests/performance/ --benchmark-only --benchmark-compare=baseline

# Save performance baseline
benchmark-save:
	python -m pytest tests/performance/ --benchmark-only --benchmark-save=baseline

# Check for memory leaks
memory-leak-check:
	python -m pytest tests/unit/ --tb=short --cov=src/vgnc_internal_orm
	# This would need additional memory profiling setup