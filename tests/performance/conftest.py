"""Pytest-benchmark configuration and fixtures for performance testing.

This module provides the foundation for performance benchmarking of the VGNC ORM,
including database setup, test data generation, and benchmark configuration.
"""

import time
from datetime import datetime
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.base import BaseModel
from vgnc_internal_orm.models.chromosomes import Chromosomes
from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus


# Benchmark configuration
BENCHMARK_CONFIG = {
    # Minimum and maximum time for benchmarks (in seconds)
    "min_rounds": 5,
    "max_time": 1.0,
    "min_time": 0.000005,
    "calibration_precision": 10,
    "warmup": False,
    "warmup_iterations": 100000,
    # Performance thresholds (in seconds)
    "thresholds": {
        "simple_query": 0.005,  # 5ms for simple queries (adjusted for system variability)
        "complex_query": 0.015,  # 15ms for complex queries (adjusted for system variability)
        "bulk_insert": 0.150,  # 150ms for bulk insert of 1000 records (adjusted for system variability)
        "relationship_loading": 0.075,  # 75ms for relationship loading (adjusted for system variability)
        "aggregate_query": 0.030,  # 30ms for aggregate queries (adjusted for system variability)
    },
    # Data sizes for different benchmark scenarios
    "data_sizes": {
        "small": 100,  # 100 records
        "medium": 1000,  # 1,000 records
        "large": 10000,  # 10,000 records
    },
}


@pytest.fixture(scope="session")
def benchmark_config():
    """Provide benchmark configuration."""
    return BENCHMARK_CONFIG


@pytest.fixture(scope="function")
def benchmark_db():
    """Create a performance test database with sample data."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "timeout": 20,
        },
        echo=False,  # Set to True for SQL debugging in benchmarks
        # Disable deprecated datetime adapter warnings
        native_datetime=True,
    )

    # Create all tables using the unified metadata registry
    from sqlalchemy.schema import MetaData

    unified_metadata = MetaData()

    # Add all tables from the shared metadata registry
    for table in BaseModel.metadata.tables.values():
        table.to_metadata(unified_metadata)

    # Create all tables
    unified_metadata.create_all(engine)

    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    try:
        yield session, engine
    finally:
        try:
            session.close()
        except Exception:
            pass  # Session might already be closed
        try:
            # Drop tables for clean state
            unified_metadata.drop_all(engine)
        except Exception:
            pass  # Engine might have issues
        finally:
            # Always dispose engine to close all connections
            try:
                engine.dispose()
            except Exception:
                pass  # Engine might already be disposed


@pytest.fixture(scope="function")
def benchmark_session(benchmark_db):
    """Provide a transactional session for benchmark testing.

    This session starts a transaction and automatically rolls back
    after each test to ensure data isolation between benchmark runs.
    """
    session, engine = benchmark_db

    # Start a transaction for test isolation
    transaction = session.begin()

    try:
        yield session
    finally:
        # Always rollback to ensure test isolation and prevent constraint violations
        try:
            transaction.rollback()
        except Exception:
            pass  # Transaction might already be rolled back
        # Ensure proper session cleanup to prevent ResourceWarnings
        # Note: Don't close session or dispose engine here - benchmark_db fixture handles that
        # Just make sure any pending operations are cleaned up
        try:
            session.expire_all()
        except Exception:
            pass  # Session might already be closed


@pytest.fixture(scope="function")
def populated_benchmark_db(benchmark_db):
    """Create a benchmark database with realistic test data."""
    session, engine = benchmark_db

    # Create species data
    species_data = [
        Species(
            taxon_id=9606,
            genefam_prefix="HSA",
            display_name="human (Homo sapiens)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        ),
        Species(
            taxon_id=10090,
            genefam_prefix="MMU",
            display_name="mouse (Mus musculus)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        ),
        Species(
            taxon_id=10116,
            genefam_prefix="RNO",
            display_name="rat (Rattus norvegicus)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        ),
        Species(
            taxon_id=7227,
            genefam_prefix="DME",
            display_name="fruit fly (Drosophila melanogaster)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        ),
        Species(
            taxon_id=6239,
            genefam_prefix="CEL",
            display_name="nematode (Caenorhabditis elegans)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        ),
    ]

    for species in species_data:
        session.add(species)

    session.commit()

    # Create assembly data
    for species in species_data:
        for i in range(2):  # 2 assemblies per species
            assembly = Assembly(
                name=f"{species.genefam_prefix}_assembly_{i+1}",
                taxon_id=species.taxon_id,
                source="Ensembl" if i == 0 else "NCBI",
                genbank_assembly_accession=f"GCA_{species.taxon_id:08d}_{i+1:010d}",
                refseq_assembly_accession=f"GCF_{species.taxon_id:08d}_{i+1:010d}",
                is_current=True if i == 0 else False,
                is_vgnc_default=True if i == 0 else False,
            )
            session.add(assembly)

    session.commit()

    # Create chromosome data
    for species in species_data:
        chromosome_configs = {
            "HSA": [
                "chr1",
                "chr2",
                "chr3",
                "chr4",
                "chr5",
                "chr6",
                "chr7",
                "chr8",
                "chr9",
                "chr10",
                "chr11",
                "chr12",
                "chr13",
                "chr14",
                "chr15",
                "chr16",
                "chr17",
                "chr18",
                "chr19",
                "chr20",
                "chr21",
                "chr22",
                "chrX",
                "chrY",
            ],
            "MMU": [
                "chr1",
                "chr2",
                "chr3",
                "chr4",
                "chr5",
                "chr6",
                "chr7",
                "chr8",
                "chr9",
                "chr10",
                "chr11",
                "chr12",
                "chr13",
                "chr14",
                "chr15",
                "chr16",
                "chr17",
                "chr18",
                "chr19",
                "chrX",
                "chrY",
            ],
            "RNO": [
                "chr1",
                "chr2",
                "chr3",
                "chr4",
                "chr5",
                "chr6",
                "chr7",
                "chr8",
                "chr9",
                "chr10",
                "chr11",
                "chr12",
                "chr13",
                "chr14",
                "chr15",
                "chr16",
                "chr17",
                "chr18",
                "chr19",
                "chr20",
                "chrX",
                "chrY",
            ],
            "DME": ["chr2L", "chr2R", "chr3L", "chr3R", "chr4", "chrX", "chrY"],
            "CEL": ["chrI", "chrII", "chrIII", "chrIV", "chrV", "chrX", "chrY"],
        }

        chromosomes = chromosome_configs.get(species.genefam_prefix, ["chr1"])

        for chr_name in chromosomes:
            chromosome = Chromosomes(
                display_name=chr_name,
                taxon_id=species.taxon_id,
                coord_system=f"{species.genefam_prefix}_coord_system",
            )
            session.add(chromosome)

    session.commit()

    return session


@pytest.fixture
def benchmark_data_factory():
    """Factory for creating benchmark test data."""

    def create_species_data(count: int = 100) -> list[dict[str, Any]]:
        """Create species data for benchmarking."""
        data = []
        for i in range(count):
            data.append(
                {
                    "taxon_id": 90000 + i,
                    "genefam_prefix": f"TEST{i:03d}",
                    "display_name": f"Test species {i}",
                    "is_live": SpeciesLiveStatus.YES,
                    "created": datetime.now(),
                }
            )
        return data

    def create_genefam_data(
        count: int = 100, species_ids: list[int] = None
    ) -> list[dict[str, Any]]:
        """Create genefam data for benchmarking."""
        if species_ids is None:
            species_ids = [9606, 10090, 10116]

        data = []
        for i in range(count):
            data.append(
                {
                    "taxon_id": species_ids[i % len(species_ids)],
                    "assigned_id": f"TEST{i:06d}",
                    "assigned_symbol": f"TEST{i:04d}",
                    "assigned_name": f"Test gene family {i}",
                    "status_id": 1,
                    "editor_id": 1,
                    "hcop_support_level": i % 5 + 1,
                }
            )
        return data

    def create_chromosome_data(
        count: int = 100, species_ids: list[int] = None
    ) -> list[dict[str, Any]]:
        """Create chromosome data for benchmarking."""
        if species_ids is None:
            species_ids = [9606, 10090, 10116]

        data = []
        for i in range(count):
            data.append(
                {
                    "display_name": f"chr_test_{i}",
                    "taxon_id": species_ids[i % len(species_ids)],
                    "coord_system": f"TEST_COORD_SYS_{i % 3}",
                }
            )
        return data

    return {
        "species": create_species_data,
        "genefam": create_genefam_data,
        "chromosomes": create_chromosome_data,
    }


@pytest.fixture
def performance_thresholds(benchmark_config):
    """Provide performance thresholds for benchmark validation."""
    return benchmark_config["thresholds"]


# Custom benchmark assertions
def assert_performance_threshold(
    benchmark_fixture, threshold: float, operation_name: str
):
    """Assert that benchmark result meets performance threshold."""
    mean_time = benchmark_fixture.stats["mean"]
    if mean_time > threshold:
        pytest.fail(
            f"Performance threshold exceeded for {operation_name}: "
            f"Mean time {mean_time:.6f}s > threshold {threshold:.6f}s"
        )


def assert_performance_regression(
    benchmark_result,
    baseline: float,
    max_regression_percent: float = 20.0,
    operation_name: str = "",
):
    """Assert that benchmark result hasn't regressed significantly from baseline."""
    mean_time = benchmark_result.mean
    regression_threshold = baseline * (1 + max_regression_percent / 100)

    if mean_time > regression_threshold:
        regression_percent = ((mean_time - baseline) / baseline) * 100
        pytest.fail(
            f"Performance regression detected for {operation_name}: "
            f"Mean time {mean_time:.6f}s is {regression_percent:.1f}% worse than baseline {baseline:.6f}s"
        )


# Benchmark utilities
class BenchmarkUtils:
    """Utility class for benchmark operations."""

    @staticmethod
    def measure_query_time(session: Session, query_func, *args, **kwargs):
        """Measure execution time of a query function."""
        start_time = time.perf_counter()
        result = query_func(session, *args, **kwargs)
        end_time = time.perf_counter()
        return result, end_time - start_time

    @staticmethod
    def create_large_dataset(
        session: Session, model_class, data: list[dict], batch_size: int = 1000
    ):
        """Create a large dataset efficiently using batch inserts."""
        total_time = 0
        for i in range(0, len(data), batch_size):
            batch = data[i : i + batch_size]
            start_time = time.perf_counter()

            instances = [model_class(**item) for item in batch]
            session.add_all(instances)
            session.commit()

            end_time = time.perf_counter()
            total_time += end_time - start_time

        return total_time, len(data)

    @staticmethod
    def warmup_database(session: Session, query_count: int = 10):
        """Warm up the database with some basic queries."""
        for _ in range(query_count):
            session.execute(text("SELECT 1"))
            session.execute(text("SELECT COUNT(*) FROM species"))


# Configure pytest-benchmark
def pytest_configure(config):
    """Configure pytest-benchmark settings."""
    config.addinivalue_line("markers", "benchmark: mark test as a benchmark")
    config.addinivalue_line(
        "markers", "benchmark_min_time: set minimum time for benchmark"
    )
    config.addinivalue_line(
        "markers", "benchmark_max_time: set maximum time for benchmark"
    )
