"""
Pytest configuration and fixtures for VGNC ORM testing.

This module provides shared fixtures and configuration for unit tests,
integration tests, performance benchmarks, and load testing.
"""

import os
import tempfile
from datetime import datetime
from typing import Generator, AsyncGenerator
from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from src.vgnc_internal_orm.models.base import BaseModel, BaseCustomModel
from src.vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from src.vgnc_internal_orm.models.genefam import Genefam
from src.vgnc_internal_orm.models.assembly import Assembly
from src.vgnc_internal_orm.models.chromosomes import Chromosomes
from src.vgnc_internal_orm.models.supporting import GeneStatus, Editor
from src.vgnc_internal_orm.models import supporting  # Import supporting models


@pytest.fixture(scope="session")
def test_database_url() -> str:
    """Get SQLite in-memory database URL for testing."""
    return "sqlite:///:memory:"


@pytest.fixture(scope="session")
def test_engine(test_database_url: str) -> sa.Engine:
    """Create SQLAlchemy engine for testing with SQLite in-memory database."""
    engine = create_engine(
        test_database_url,
        connect_args={
            "check_same_thread": False,
            "timeout": 20,
        },
        poolclass=StaticPool,
        echo=False,  # Set to True for SQL debugging
    )

    # Enable foreign key constraints for SQLite
    @sa.event.listens_for(engine, "connect")
    def enable_foreign_keys(dbapi_connection, connection_record):
        cursor = dbapi_connection.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()

    return engine


@pytest.fixture(scope="function")
def test_db_session(test_engine: sa.Engine) -> Generator[Session, None, None]:
    """Create a fresh database session for each test function."""
    # Create only core tables needed for testing
    # This avoids foreign key dependency issues
    from src.vgnc_internal_orm.models.species import Species
    from src.vgnc_internal_orm.models.assembly import Assembly
    from src.vgnc_internal_orm.models.chromosomes import Chromosomes
    from src.vgnc_internal_orm.models.supporting import GeneStatus, Editor

    # Create tables manually to avoid dependency issues
    # Create supporting tables first due to foreign key dependencies
    GeneStatus.__table__.create(test_engine, checkfirst=True)
    Editor.__table__.create(test_engine, checkfirst=True)
    Species.__table__.create(test_engine, checkfirst=True)
    Assembly.__table__.create(test_engine, checkfirst=True)
    Chromosomes.__table__.create(test_engine, checkfirst=True)

    # Create session
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()

    try:
        yield session
    finally:
        session.close()
        # Drop tables for clean state (reverse order of creation)
        Chromosomes.__table__.drop(test_engine, checkfirst=True)
        Assembly.__table__.drop(test_engine, checkfirst=True)
        Species.__table__.drop(test_engine, checkfirst=True)
        GeneStatus.__table__.drop(test_engine, checkfirst=True)
        Editor.__table__.drop(test_engine, checkfirst=True)


@pytest.fixture(scope="function")
def sample_gene_status(test_db_session: Session) -> GeneStatus:
    """Create a sample gene status for testing."""
    gene_status = GeneStatus(
        status="Approved",
        display="Approved Status"
    )
    test_db_session.add(gene_status)
    test_db_session.commit()
    return gene_status


@pytest.fixture(scope="function")
def sample_editor(test_db_session: Session) -> Editor:
    """Create a sample editor for testing."""
    editor = Editor(
        display_name="Test Editor",
        first_name="Test",
        last_name="Editor"
    )
    test_db_session.add(editor)
    test_db_session.commit()
    return editor


@pytest.fixture(scope="function")
def test_transaction_session(test_engine: sa.Engine) -> Generator[Session, None, None]:
    """Create a session within a transaction that's rolled back after each test."""
    # Create only core tables needed for testing
    from src.vgnc_internal_orm.models.species import Species
    from src.vgnc_internal_orm.models.assembly import Assembly
    from src.vgnc_internal_orm.models.chromosomes import Chromosomes

    # Create tables manually to avoid dependency issues
    Species.__table__.create(test_engine, checkfirst=True)
    Assembly.__table__.create(test_engine, checkfirst=True)
    Chromosomes.__table__.create(test_engine, checkfirst=True)

    # Create session with transaction
    SessionLocal = sessionmaker(bind=test_engine)
    session = SessionLocal()

    # Begin transaction
    transaction = session.begin()

    try:
        yield session
    finally:
        # Rollback transaction to ensure test isolation
        transaction.rollback()
        session.close()
        # Drop tables for clean state
        Chromosomes.__table__.drop(test_engine, checkfirst=True)
        Assembly.__table__.drop(test_engine, checkfirst=True)
        Species.__table__.drop(test_engine, checkfirst=True)


@pytest.fixture
def sample_species_data() -> dict:
    """Sample species data for testing."""
    return {
        "taxon_id": 9606,
        "genefam_prefix": "HSA",
        "display_name": "human (Homo sapiens)",
        "is_live": SpeciesLiveStatus.YES,
        "created": datetime.now(),
    }


@pytest.fixture
def sample_genefam_data() -> dict:
    """Sample genefam data for testing."""
    return {
        "genefam_id": "HSA000001",
        "description": "Test gene family",
        "version": "1.0",
        "created": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_assembly_data() -> dict:
    """Sample assembly data for testing."""
    return {
        "assembly_name": "GRCh38",
        "accession": "GCA_000001405.28",
        "version": "p13",
        "created": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_chromosome_data() -> dict:
    """Sample chromosome data for testing."""
    return {
        "chromosome_name": "chr1",
        "length": 248956422,
        "created": "2024-01-01T00:00:00Z",
    }


@pytest.fixture
def sample_species(test_db_session: Session, sample_species_data: dict) -> Species:
    """Create a sample Species instance in the database."""
    species = Species(**sample_species_data)
    test_db_session.add(species)
    test_db_session.commit()
    test_db_session.refresh(species)
    return species


# Skip genefam fixture for now due to complex foreign key dependencies
# @pytest.fixture
# def sample_genefam(test_db_session: Session, sample_genefam_data: dict) -> Genefam:
#     """Create a sample Genefam instance in the database."""
#     genefam = Genefam(**sample_genefam_data)
#     test_db_session.add(genefam)
#     test_db_session.commit()
#     test_db_session.refresh(genefam)
#     return genefam


@pytest.fixture
def sample_assembly(test_db_session: Session, sample_assembly_data: dict, sample_species: Species) -> Assembly:
    """Create a sample Assembly instance in the database."""
    assembly = Assembly(
        **sample_assembly_data,
        species_id=sample_species.id
    )
    test_db_session.add(assembly)
    test_db_session.commit()
    test_db_session.refresh(assembly)
    return assembly


@pytest.fixture
def sample_chromosome(
    test_db_session: Session,
    sample_chromosome_data: dict,
    sample_species: Species
) -> Chromosomes:
    """Create a sample Chromosomes instance in the database."""
    chromosome = Chromosomes(
        **sample_chromosome_data,
        species_id=sample_species.id
    )
    test_db_session.add(chromosome)
    test_db_session.commit()
    test_db_session.refresh(chromosome)
    return chromosome


@pytest.fixture
def populated_database(
    test_db_session: Session,
    sample_species: Species,
    sample_assembly: Assembly,
    sample_chromosome: Chromosomes,
) -> Session:
    """Provide a session with pre-populated test data."""
    return test_db_session


# Mock fixtures for testing with dependencies
@pytest.fixture
def mock_config():
    """Mock configuration for testing."""
    return Mock(
        database_url="sqlite:///:memory:",
        username="test_user",
        password="test_pass",
        host="localhost",
        port=5432,
        database="test_db",
    )


@pytest.fixture
def temp_file():
    """Create a temporary file for testing."""
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        yield tmp
    # Cleanup happens automatically when context exits


@pytest.fixture
def temp_directory():
    """Create a temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield tmp_dir


# Environment fixtures
@pytest.fixture
def clean_env():
    """Provide clean environment variables for testing."""
    original_env = os.environ.copy()
    try:
        yield os.environ
    finally:
        os.environ.clear()
        os.environ.update(original_env)


# Performance testing fixtures
@pytest.fixture
def performance_data():
    """Generate performance test data."""
    return {
        "small_dataset": list(range(100)),
        "medium_dataset": list(range(1000)),
        "large_dataset": list(range(10000)),
    }


# Benchmark configuration
@pytest.fixture
def benchmark_min_rounds():
    """Configure minimum rounds for benchmark tests."""
    return 5


@pytest.fixture
def benchmark_max_time():
    """Configure maximum time for benchmark tests (in seconds)."""
    return 1.0


# Async fixtures for async testing
@pytest.fixture(scope="session")
async def async_test_engine():
    """Create async SQLAlchemy engine for testing."""
    # Note: This would require aiosqlite dependency
    # For now, return None - can be implemented when async testing is needed
    return None


@pytest.fixture
async def async_test_session(async_test_engine):
    """Create async database session for testing."""
    # Note: This would require aiosqlite dependency
    # For now, return None - can be implemented when async testing is needed
    return None