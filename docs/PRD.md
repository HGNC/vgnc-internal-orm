# Repository Planning Graph (RPG) Method - PRD Template

## Overview

### Problem Statement

The VGNC (Vertebrate Gene Nomenclature Committee) maintains a complex MySQL database (`genefam_production`) with 40+ interconnected tables managing gene families, species, chromosomes, orthologs, and extensive metadata. Currently, there is no Python ORM library to interact with this database, forcing developers to write raw SQL queries and manually handle complex relationships, charset issues, and database-specific optimizations.

### Target Users

1. **Bioinformatics Developers**: Need programmatic access to gene data for analysis pipelines
2. **Data Scientists**: Require efficient querying of gene relationships and orthologs
3. **VGNC Curators**: Need tools for data validation and integrity checks
4. **Internal Applications**: Require standardized database access patterns

### Success Metrics

- 90% reduction in raw SQL usage in internal projects
- Sub-100ms query performance for common gene lookups
- 100% UTF8MB4 support for international gene names
- Zero data corruption incidents with proper charset handling
- 50% faster development time for new database-dependent features

---

## Functional Decomposition

### Capability: Database Connection Management

**Brief description**: Handles connection lifecycle, environment switching, and pool management for MySQL databases

#### Feature: Environment Configuration

- **Description**: Load and validate database configurations for different environments
- **Inputs**: Environment name (dev/staging/prod), configuration files
- **Outputs**: Validated database connection settings
- **Behavior**: Read from environment variables or config files, validate connection parameters

#### Feature: Connection Pooling

- **Description**: Manage connection pools with environment-specific settings
- **Inputs**: Pool size, timeout settings, recycling interval
- **Outputs**: Active connection pool
- **Behavior**: Create and maintain connections based on environment requirements

#### Feature: Session Management

- **Description**: Provide database sessions with proper charset and isolation
- **Inputs**: Environment identifier, optional transaction settings
- **Outputs**: Configured SQLAlchemy session
- **Behavior**: Create session with UTF8MB4 charset and appropriate isolation level

### Capability: ORM Model Definitions

**Brief description**: Define SQLAlchemy models for all database tables with proper relationships and type hints

#### Feature: Core Entity Models

- **Description**: Models for central entities (Genefam, Species, Chromosomes, Assembly)
- **Inputs**: Database schema definitions
- **Outputs**: Complete SQLAlchemy model classes
- **Behavior**: Map tables with proper column types, primary keys, and relationships

#### Feature: Relationship Management

- **Description**: Define and configure all table relationships with optimal loading strategies
- **Inputs**: Foreign key definitions, cardinality information
- **Outputs**: Configured relationship attributes
- **Behavior**: Set lazy/selectin loading based on relationship type and usage patterns

#### Feature: Index and Constraint Mapping

- **Description**: Map database indexes, constraints, and full-text search capabilities
- **Inputs**: Index definitions, constraint specifications
- **Outputs**: SQLAlchemy index objects and constraints
- **Behavior**: Create proper index objects including full-text indexes

### Capability: MySQL-Specific Features

**Brief description**: Implement MySQL-specific optimizations and features

#### Feature: UTF8MB4 Charset Support

- **Description**: Ensure proper UTF8MB4 unicode support throughout the ORM
- **Inputs**: Connection parameters, table definitions
- **Outputs**: Properly configured connections and models
- **Behavior**: Set charset at connection and table level, handle encoding conversions

#### Feature: Full-Text Search

- **Description**: Provide full-text search capabilities for relevant text fields
- **Inputs**: Search terms, target columns, search mode
- **Outputs**: Query results with relevance scores
- **Behavior**: Generate MySQL full-text search queries with proper syntax

#### Feature: Query Optimization

- **Description**: Apply MySQL-specific query hints and optimizations
- **Inputs**: Query objects, optimization hints
- **Outputs**: Optimized SQL queries
- **Behavior**: Add STRAIGHT_JOIN, FORCE INDEX hints where beneficial

### Capability: Migration Management

**Brief description**: Handle database schema migrations using Alembic

#### Feature: Baseline Generation

- **Description**: Generate initial migration from existing schema without applying changes
- **Inputs**: Current database schema
- **Outputs**: Alembic migration file representing current state
- **Behavior**: Autogenerate migration that creates tables only if they don't exist

#### Feature: Incremental Migrations

- **Description**: Generate and apply migrations for schema changes
- **Inputs**: Model changes, new table definitions
- **Outputs**: Forward and rollback migration scripts
- **Behavior**: Compare models to database, generate delta migrations

#### Feature: Migration Safety

- **Description**: Validate migrations before applying to production
- **Inputs**: Migration scripts, environment settings
- **Outputs**: Validation report and approval workflow
- **Behavior**: Check for destructive operations, require confirmation

### Capability: CLI Tools

**Brief description**: Command-line interface for common database operations

#### Feature: Query Commands

- **Description**: CLI commands for querying genes, families, and related data
- **Inputs**: Search parameters, filters, output format
- **Outputs**: Formatted query results
- **Behavior**: Execute queries and format results for display

#### Feature: Data Export

- **Description**: Export table data to various formats (CSV, JSON, XML)
- **Inputs**: Table name, filters, output format, file path
- **Outputs**: Data files in specified format
- **Behavior**: Query data and convert to requested format with proper encoding

#### Feature: Database Health Checks

- **Description**: Validate database connectivity and integrity
- **Inputs**: Connection parameters, check types
- **Outputs**: Health status report
- **Behavior**: Test connection, check charset support, validate relationships

#### Feature: Interactive Shell

- **Description**: Drop into Python shell with pre-loaded models and session
- **Inputs**: Optional environment specification
- **Outputs**: Interactive Python session
- **Behavior**: Initialize session, import models, start REPL

### Capability: Testing Framework

**Brief description**: Comprehensive testing suite with performance benchmarks

#### Feature: Unit Testing

- **Description**: Fast unit tests using SQLite in-memory database
- **Inputs**: Test data, model definitions
- **Outputs**: Test results and coverage reports
- **Behavior**: Test model validation, relationships, business logic

#### Feature: Integration Testing

- **Description**: Full integration tests using MySQL containers
- **Inputs**: Test scenarios, container configuration
- **Outputs**: Integration test results
- **Behavior**: Test real database interactions, charset handling, full-text search

#### Feature: Performance Testing

- **Description**: Benchmark query performance and validate optimization
- **Inputs**: Query sets, performance thresholds
- **Outputs**: Performance reports and metrics
- **Behavior**: Execute queries, measure timing, compare against thresholds

#### Feature: Load Testing

- **Description**: Test performance under high load with large datasets
- **Inputs**: Load parameters, dataset size
- **Outputs**: Load test results and bottleneck analysis
- **Behavior**: Simulate concurrent access, measure throughput

---

## Structural Decomposition

### Repository Structure

The project follows a standard Python package structure with the following key directories:

- **vgnc-internal-orm/**: Root project directory
  - **src/vgnc_internal_orm/**: Main package containing models and utilities
    - **models/**: Individual SQLAlchemy model files (one per table)
    - **config.py**: Database configuration management
    - **session.py**: Session and connection management
    - **mysql_features.py**: MySQL-specific optimizations
    - **cli.py**: Command-line interface
  - **tests/**: Test suite organized by type
    - **unit/**: Unit tests with SQLite
    - **integration/**: Integration tests with MySQL containers
    - **performance/**: Performance and load tests
  - **alembic/versions/**: Alembic migration revision scripts
  - **pyproject.toml**: UV project configuration
  - **README.md**: Project documentation

### Module Definitions

#### Module: vgnc_internal_orm

- **Maps to capability**: ORM Model Definitions
- **Responsibility**: Central package containing all models and utilities
- **Exports**:
  - `Genefam` - Main gene family model
  - `Species` - Species/taxonomy model
  - `get_session()` - Database session factory
  - `DatabaseConfig` - Configuration class
  - `cli` - Command-line interface group

#### Module: models

- **Maps to capability**: ORM Model Definitions
- **Responsibility**: Individual SQLAlchemy model definitions
- **Exports**:
  - `BaseModel` - Base class with common functionality
  - All individual model classes (40+)

#### Module: config

- **Maps to capability**: Database Connection Management
- **Responsibility**: Configuration loading and validation
- **Exports**:
  - `DatabaseConfig` - Pydantic settings class
  - `get_config()` - Configuration factory function

#### Module: session

- **Maps to capability**: Database Connection Management
- **Responsibility**: Session and connection management
- **Exports**:
  - `get_session()` - Session factory
  - `engine_from_config()` - Engine creation helper

#### Module: mysql_features

- **Maps to capability**: MySQL-Specific Features
- **Responsibility**: MySQL-specific optimizations and features
- **Exports**:
  - `FullTextSearch` - Full-text search query builder
  - `QueryOptimizer` - MySQL optimization hints
  - `CharsetHandler` - UTF8MB4 charset utilities

#### Module: cli

- **Maps to capability**: CLI Tools
- **Responsibility**: Command-line interface for database operations
- **Exports**:
  - `cli` - Click command group
  - `query()` - Query commands
  - `export()` - Data export commands
  - `health()` - Health check commands

#### Module: migrations

- **Maps to capability**: Migration Management
- **Responsibility**: Database schema migrations
- **Exports**:
  - Alembic migration commands
  - Migration validation utilities

#### Module: tests

- **Maps to capability**: Testing Framework
- **Responsibility**: Comprehensive testing suite
- **Exports**:
  - Test fixtures and utilities
  - Performance benchmarks
  - Integration test scenarios

### Dependency Graph

#### Foundation Layer (Phase 0)

No dependencies - these are built first.

- **config**: Provides configuration management with Pydantic settings
- **base**: Provides BaseModel class with common functionality

#### Core Layer (Phase 1)

- **models**: Depends on [config, base]
  - Requires configuration for database settings
  - Inherits from BaseModel for common functionality
- **session**: Depends on [config]
  - Needs configuration to create database connections
- **mysql_features**: Depends on [config]
  - Requires database configuration for charset and optimization settings

#### Service Layer (Phase 2)

- **cli**: Depends on [models, session, mysql_features]
  - Needs models for querying data
  - Requires session management for database operations
  - Uses MySQL features for optimized queries

#### Support Layer (Phase 3)

- **migrations**: Depends on [models, config]
  - Requires model definitions for autogeneration
  - Needs configuration for database connections
- **tests**: Depends on [models, session, config, mysql_features]
  - Requires all components for comprehensive testing

---

## Implementation Roadmap

### Phase 0: Foundation

**Goal**: Establish core configuration and base model infrastructure

**Entry Criteria**: Clean repository with UV initialized

**Tasks**:

- [ ] Create project structure with UV (depends on: none)
  - Acceptance criteria: pyproject.toml configured with all dependencies
  - Test strategy: Verify UV can install package in development mode
- [ ] Implement configuration management (depends on: none)
  - Acceptance criteria: DatabaseConfig loads settings from environment
  - Test strategy: Unit tests for configuration validation
- [ ] Create BaseModel class (depends on: none)
  - Acceptance criteria: BaseModel provides timestamps, serialization, query helpers
  - Test strategy: Unit tests for all BaseModel methods

**Exit Criteria**: All tests pass, configuration loads correctly, BaseModel functional

**Delivers**: Configurable project foundation with base model functionality

### Phase 1: Core Models

**Goal**: Implement all SQLAlchemy models with proper relationships

**Entry Criteria**: Phase 0 complete

**Tasks**:

- [ ] Generate core entity models (depends on: [base, config])
  - Acceptance criteria: Genefam, Species, Chromosomes models complete
  - Test strategy: Unit tests for model validation and relationships
- [ ] Implement relationship configurations (depends on: [core models])
  - Acceptance criteria: All relationships defined with optimal loading
  - Test strategy: Integration tests for relationship loading strategies
- [ ] Add index and constraint mappings (depends on: [all models])
  - Acceptance criteria: All indexes and constraints properly mapped
  - Test strategy: Schema validation against existing database

**Exit Criteria**: All models created, relationships functional, indexes mapped

**Delivers**: Complete ORM model layer ready for database operations

### Phase 2: MySQL Features & Session Management

**Goal**: Implement MySQL-specific features and session handling

**Entry Criteria**: Phase 1 complete

**Tasks**:

- [ ] Implement UTF8MB4 charset support (depends on: [config, session])
  - Acceptance criteria: All connections use UTF8MB4 charset
  - Test strategy: Integration tests with emoji and international characters
- [ ] Add full-text search capabilities (depends on: [models])
  - Acceptance criteria: Full-text search functional on relevant fields
  - Test strategy: Integration tests for search accuracy and performance
- [ ] Implement query optimization hints (depends on: [mysql_features])
  - Acceptance criteria: Query hints properly applied to complex queries
  - Test strategy: Performance benchmarks with and without hints
- [ ] Create session management (depends on: [config])
  - Acceptance criteria: Environment-specific session creation working
  - Test strategy: Unit tests for session factory and configuration

**Exit Criteria**: MySQL features working, sessions manageable across environments

**Delivers**: Production-ready database layer with MySQL optimizations

### Phase 3: CLI Tools

**Goal**: Build command-line interface for database operations

**Entry Criteria**: Phase 2 complete

**Tasks**:

- [ ] Implement query commands (depends on: [models, session])
  - Acceptance criteria: Query genes, families, species from CLI
  - Test strategy: Integration tests for all query commands
- [ ] Add data export functionality (depends on: [query commands])
  - Acceptance criteria: Export data to CSV, JSON, XML formats
  - Test strategy: Verify exported data integrity and encoding
- [ ] Create health check commands (depends on: [session, mysql_features])
  - Acceptance criteria: Health checks validate connection and charset
  - Test strategy: Test against various database states
- [ ] Implement interactive shell (depends on: [models, session])
  - Acceptance criteria: Shell starts with pre-loaded models and session
  - Test strategy: Manual testing of shell functionality

**Exit Criteria**: All CLI commands functional and documented

**Delivers**: Complete CLI toolkit for database operations

### Phase 4: Migration Management

**Goal**: Set up Alembic for safe database migrations

**Entry Criteria**: Phase 3 complete

**Tasks**:

- [ ] Generate baseline migration (depends on: [models])
  - Acceptance criteria: Migration represents current schema without breaking
  - Test strategy: Apply migration to empty database, verify schema match
- [ ] Implement incremental migration workflow (depends on: [baseline])
  - Acceptance criteria: New migrations autogenerate correctly
  - Test strategy: Create table, generate migration, apply and verify
- [ ] Add migration safety checks (depends on: [incremental migrations])
  - Acceptance criteria: Destructive migrations require confirmation
  - Test strategy: Attempt dangerous migration, verify safety checks work

**Exit Criteria**: Migration system ready for production use

**Delivers**: Safe migration workflow for future schema changes

### Phase 5: Testing Framework

**Goal**: Comprehensive testing suite with performance benchmarks

**Entry Criteria**: Phase 4 complete

**Tasks**:

- [ ] Implement unit tests (depends on: [models, config])
  - Acceptance criteria: 90% code coverage for models and utilities
  - Test strategy: Unit tests with SQLite in-memory database
- [ ] Create integration tests (depends on: [all components])
  - Acceptance criteria: All major workflows tested with real MySQL
  - Test strategy: Testcontainers with MySQL 8.0
- [ ] Build performance benchmarks (depends on: [models, mysql_features])
  - Acceptance criteria: Performance thresholds defined and met
  - Test strategy: pytest-benchmark with query timing validation
- [ ] Implement load testing (depends on: [performance benchmarks])
  - Acceptance criteria: System handles 100 concurrent queries
  - Test strategy: Simulate load with test data

**Exit Criteria**: All tests pass, performance criteria met

**Delivers**: Production-ready package with comprehensive test coverage

---

## Test Strategy

### Test Pyramid

| Test Level            | Percentage | Description                              | Test Tools/Approach                                |
| --------------------- | ---------- | ---------------------------------------- | -------------------------------------------------- |
| **Unit Tests**        | 40%        | SQLite, fast logic tests                 | pytest, SQLite in-memory, mocked dependencies      |
| **Integration Tests** | 30%        | MySQL container tests                    | testcontainers, real MySQL 8.0, full workflows     |
| **Performance Tests** | 20%        | Benchmarks, load testing                 | pytest-benchmark, load testing with large datasets |
| **E2E Tests**         | 10%        | End-to-end workflows                     | Complete application workflows, migration testing  |

### Coverage Requirements

- Line coverage: 90% minimum
- Branch coverage: 85% minimum
- Function coverage: 95% minimum
- Statement coverage: 90% minimum

### Critical Test Scenarios

#### Database Connection Management

**Happy path**:

- Connect to all environments (dev/staging/prod) successfully
- Expected: Valid session with UTF8MB4 charset

**Edge cases**:

- Invalid credentials
- Network timeouts
- Expected: Graceful error handling with clear messages

**Error cases**:

- Wrong charset support
- Connection pool exhaustion
- Expected: Proper exception handling and recovery

**Integration points**:

- Session creation with different environments
- Expected: Correct pool settings per environment

#### ORM Models

**Happy path**:

- Create, read, update, delete operations on all models
- Expected: Data integrity maintained

**Edge cases**:

- NULL values in optional fields
- Maximum string lengths
- Expected: Proper validation and handling

**Error cases**:

- Foreign key constraint violations
- Duplicate primary keys
- Expected: SQLAlchemy exceptions properly raised

**Integration points**:

- Relationship loading with different strategies
- Expected: Optimal query patterns

#### MySQL Features

**Happy path**:

- Full-text search on gene names and descriptions
- Expected: Relevant results with proper ranking

**Edge cases**:

- Search with special characters and emoji
- Expected: UTF8MB4 handles all characters correctly

**Error cases**:

- Full-text search on non-indexed columns
- Expected: Graceful fallback or clear error

**Integration points**:

- Query optimization hints with complex joins
- Expected: Improved query performance

#### CLI Tools

**Happy path**:

- Query genes by symbol, species, family
- Expected: Correct results in tabular format

**Edge cases**:

- Large result sets (>10,000 records)
- Expected: Pagination or streaming output

**Error cases**:

- Invalid query parameters
- Expected: Clear error messages and usage help

**Integration points**:

- Export to different formats
- Expected: Proper encoding and formatting

---

## Architecture

### System Components

- **ORM Layer**: SQLAlchemy models with relationships and indexes
- **Configuration Layer**: Pydantic-based settings management
- **Session Layer**: Connection pooling and environment management
- **MySQL Feature Layer**: Charset support, full-text search, optimization
- **CLI Layer**: Command-line interface for common operations
- **Migration Layer**: Alembic-based schema migration system
- **Testing Layer**: Comprehensive test suite with performance benchmarks

### Data Models

Core entities include:

- Genefam: Central gene family entity with relationships to species, chromosomes, orthologs
- Species: Taxonomy information with genome assemblies
- Chromosomes: Chromosome data with coordinate systems
- Family: Gene family hierarchies and relationships
- Orthologs: Cross-species orthology relationships
- Supporting tables for names, symbols, references, and editorial data

### Technology Stack

- **Language**: Python 3.11+
- **ORM**: SQLAlchemy 2.0 with declarative models
- **Database**: MySQL 8.0+ with UTF8MB4 support
- **Type Validation**: Pydantic v2 for configuration
- **Migrations**: Alembic for schema management
- **CLI**: Click for command-line interface
- **Testing**: pytest with testcontainers
- **Code Quality**: Ruff, MyPy, pre-commit hooks
- **Packaging**: UV for dependency management

#### Decision: SQLAlchemy 2.0 with declarative models

- **Rationale**: Modern, type-hint friendly, excellent relationship management
- **Trade-offs**: Learning curve for team members unfamiliar with SQLAlchemy 2.0
- **Alternatives considered**: Django ORM, Tortoise ORM, SQLModel

#### Decision: UTF8MB4 charset throughout

- **Rationale**: Full Unicode support for international gene names and symbols
- **Trade-offs**: Slightly larger storage requirements
- **Alternatives considered**: Latin1 (existing), UTF8 (incomplete)

#### Decision: One file per model organization

- **Rationale**: Maximum clarity for 40+ tables, easier version control
- **Trade-offs**: More files to manage
- **Alternatives considered**: Grouped by domain, single large file

---

## Risks

### Technical Risks

**Risk**: Complex relationship queries causing performance issues

- **Impact**: High - affects all application performance
- **Likelihood**: Medium - given the many-to-many relationships
- **Mitigation**: Smart loading strategies, query optimization, performance testing
- **Fallback**: Materialized views for complex queries

**Risk**: Charset conversion issues with existing latin1 data

- **Impact**: Medium - data corruption possible
- **Likelihood**: Medium - mixed collations in existing schema
- **Mitigation**: Careful migration planning, validation scripts
- **Fallback**: Maintain latin1 for legacy tables

**Risk**: Full-text search performance with large datasets

- **Impact**: Medium - search functionality degradation
- **Likelihood**: Low - MySQL full-text is generally performant
- **Mitigation**: Proper indexing, query optimization
- **Fallback**: External search service (Elasticsearch)

### Dependency Risks

**Risk**: MySQL connector compatibility issues

- **Impact**: High - blocks all database operations
- **Likelihood**: Low - mature ecosystem
- **Mitigation**: Pin versions, test with multiple MySQL versions
- **Fallback**: Alternative connector (PyMySQL)

**Risk**: Alembic autogenerate issues with complex schema

- **Impact**: Medium - migration problems
- **Likelihood**: Medium - complex relationships can confuse autogenerate
- **Mitigation**: Manual migration review, custom migration scripts
- **Fallback**: Manual SQL migrations only

### Scope Risks

**Risk**: Scope creep with additional features

- **Impact**: Medium - delayed delivery
- **Likelihood**: High - common in ORM projects
- **Mitigation**: Clear PRD, phase-based delivery, stakeholder alignment
- **Fallback**: Defer features to future releases

**Risk**: Underestimating relationship complexity

- **Impact**: High - significant rework required
- **Likelihood**: Medium - 40+ tables with complex relationships
- **Mitigation**: Incremental development, continuous testing
- **Fallback**: Simplify initial relationships, add complexity later

---

## Appendix

### References

- SQLAlchemy 2.0 Documentation: <https://docs.sqlalchemy.org/en/20/>
- MySQL 8.0 Reference Manual: <https://dev.mysql.com/doc/refman/8.0/en/>
- Pydantic v2 Documentation: <https://docs.pydantic.dev/latest/>
- Alembic Documentation: <https://alembic.sqlalchemy.org/>
- UV Documentation: <https://docs.astral.sh/uv/>

### Glossary

- **VGNC**: Vertebrate Gene Nomenclature Committee
- **Ortholog**: Genes in different species that evolved from a common ancestral gene
- **HCOP**: HGNC Comparison of Orthology Predictions
- **Locus Type**: Type of gene location (e.g., protein coding, RNA, pseudogene)
- **Taxon ID**: Unique identifier for species in NCBI taxonomy

### Open Questions

- Should we include read replica support for query distribution?
- Do we need to support MySQL versions older than 8.0?
- Should we implement caching for frequently accessed reference data?
- Do we need to handle database sharding for very large datasets?

---

## Task Master Integration

### How Task Master Uses This PRD

When you run `task-master parse-prd prd.txt`, the parser:

1. **Extracts capabilities** → Main tasks
   - Each `### Capability:` becomes a top-level task
   - Database Connection Management, ORM Model Definitions, MySQL-Specific Features, Migration Management, CLI Tools, Testing Framework
2. **Extracts features** → Subtasks
   - Each `#### Feature:` becomes a subtask under its capability
   - Environment Configuration, Connection Pooling, Session Management, etc.
3. **Parses dependencies** → Task dependencies
   - `Depends on: [X, Y]` sets task.dependencies = ["X", "Y"]
   - Models depend on config and base, CLI depends on models and session
4. **Orders by phases** → Task priorities
   - Phase 0 tasks = highest priority (Foundation)
   - Phase 1 tasks = next priority (Core Models)
   - Phase N tasks = lower priority, properly sequenced
5. **Uses test strategy** → Test generation context
   - Feeds test scenarios to Surgical Test Generator during implementation
   - Performance thresholds, coverage requirements, critical scenarios

**Result**: A dependency-aware task graph that can be executed in topological order, ensuring foundation components are built before dependent features.

### Why RPG Structure Matters

Traditional flat PRDs lead to:

- ❌ Unclear task dependencies
- ❌ Arbitrary task ordering
- ❌ Circular dependencies discovered late
- ❌ Poorly scoped tasks

RPG-structured PRDs provide:

- ✅ Explicit dependency chains
- ✅ Topological execution order
- ✅ Clear module boundaries
- ✅ Validated task graph before implementation

### Tips for Best Results

1. **Spend time on dependency graph** - This is the most valuable section for Task Master
2. **Keep features atomic** - Each feature should be independently testable
3. **Progressive refinement** - Start broad, use `task-master expand` to break down complex tasks
4. **Use research mode** - `task-master parse-prd --research` leverages AI for better task generation
