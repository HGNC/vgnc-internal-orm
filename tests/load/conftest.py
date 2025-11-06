"""
Load testing configuration and fixtures for concurrent query handling tests.

This module provides the foundation for load testing the VGNC ORM with
concurrent access patterns, simulating real-world usage scenarios.
"""

import pytest
import asyncio
import threading
import time
import statistics
from typing import List, Dict, Any, Callable, Optional
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass
from datetime import datetime
from contextlib import contextmanager

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from vgnc_internal_orm.models.base import BaseModel
from vgnc_internal_orm.models.species import BaseCustomModel, Species, SpeciesLiveStatus
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes
from vgnc_internal_orm.models.supporting import GeneStatus, Editor


# Load testing configuration
LOAD_TEST_CONFIG = {
    # Concurrent user simulation
    "concurrent_users": {
        "light": 5,      # Light load: 5 concurrent users
        "medium": 20,    # Medium load: 20 concurrent users
        "heavy": 50,     # Heavy load: 50 concurrent users
        "stress": 100,   # Stress test: 100 concurrent users
    },

    # Test duration (seconds)
    "test_duration": {
        "quick": 10,     # Quick test: 10 seconds
        "normal": 30,    # Normal test: 30 seconds
        "extended": 60,  # Extended test: 60 seconds
        "stress": 120,   # Stress test: 2 minutes
    },

    # Performance thresholds
    "performance_thresholds": {
        "response_time_p95": 0.1,      # 95th percentile: 100ms
        "response_time_p99": 0.5,      # 99th percentile: 500ms
        "error_rate": 0.01,            # Max 1% error rate
        "throughput_min": 100,         # Min 100 ops/sec
        "connection_pool_max": 0.8,    # Max 80% connection pool usage
    },

    # Database settings for load testing
    "database": {
        "pool_size": 20,
        "max_overflow": 30,
        "pool_timeout": 30,
        "pool_recycle": 3600,
    }
}


@dataclass
class LoadTestResult:
    """Results from a load test execution."""
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration: float
    response_times: List[float]
    errors: List[str]
    throughput: float  # requests per second
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    error_rate: float

    @classmethod
    def from_metrics(cls, total_requests: int, successful_requests: int,
                    failed_requests: int, total_duration: float,
                    response_times: List[float], errors: List[str]) -> 'LoadTestResult':
        """Create LoadTestResult from raw metrics."""
        response_times.sort()

        throughput = total_requests / total_duration if total_duration > 0 else 0
        avg_response_time = statistics.mean(response_times) if response_times else 0
        p50_response_time = statistics.median(response_times) if response_times else 0
        p95_response_time = response_times[int(len(response_times) * 0.95)] if response_times else 0
        p99_response_time = response_times[int(len(response_times) * 0.99)] if response_times else 0
        error_rate = failed_requests / total_requests if total_requests > 0 else 0

        return cls(
            total_requests=total_requests,
            successful_requests=successful_requests,
            failed_requests=failed_requests,
            total_duration=total_duration,
            response_times=response_times,
            errors=errors,
            throughput=throughput,
            avg_response_time=avg_response_time,
            p50_response_time=p50_response_time,
            p95_response_time=p95_response_time,
            p99_response_time=p99_response_time,
            error_rate=error_rate,
        )


@pytest.fixture(scope="function")
def load_test_db():
    """Create a database optimized for load testing."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create unified metadata for testing
    from sqlalchemy.schema import MetaData
    unified_metadata = MetaData()

    # Add all tables from both metadata registries
    for table in BaseModel.metadata.tables.values():
        table.to_metadata(unified_metadata)

    for table in BaseCustomModel.metadata.tables.values():
        table.to_metadata(unified_metadata)

    # Create all tables
    unified_metadata.create_all(engine)

    # Create session factory
    SessionLocal = sessionmaker(bind=engine)

    try:
        yield SessionLocal
    finally:
        # Drop tables for clean state
        unified_metadata.drop_all(engine)


@pytest.fixture(scope="function")
def populated_load_test_db(load_test_db):
    """Create a load test database with realistic data for testing."""
    SessionLocal = load_test_db
    session = SessionLocal()

    try:
        # Create supporting data
        gene_statuses = [
            GeneStatus(id=1, status="Approved"),
            GeneStatus(id=2, status="Pending"),
            GeneStatus(id=3, status="Rejected"),
        ]
        for status in gene_statuses:
            session.add(status)

        editors = [
            Editor(id=1, display_name="Test Editor", email="test@example.com", current=True, connected=True),
            Editor(id=2, display_name="Senior Editor", email="senior@example.com", current=True, connected=True),
        ]
        for editor in editors:
            session.add(editor)

        session.commit()

        # Create species data (more records for load testing)
        species_data = []
        for i in range(100):  # 100 species
            species = Species(
                taxon_id=9000 + i,
                genefam_prefix=f"TST{i:03d}",
                display_name=f"Test Species {i}",
                is_live=SpeciesLiveStatus.YES if i % 2 == 0 else SpeciesLiveStatus.NO,
                created=datetime.now(),
            )
            species_data.append(species)
            session.add(species)

        session.commit()

        # Create assembly data
        for species in species_data[:50]:  # 50 species with assemblies
            for j in range(3):  # 3 assemblies per species
                assembly = Assembly(
                    name=f"{species.genefam_prefix}_assembly_{j+1}",
                    taxon_id=species.taxon_id,
                    source="Ensembl" if j == 0 else "NCBI",
                    genbank_assembly_accession=f"GCA_{species.taxon_id:08d}_{j+1:010d}",
                    refseq_assembly_accession=f"GCF_{species.taxon_id:08d}_{j+1:010d}" if j == 0 else None,
                    is_current=True if j == 0 else False,
                    is_vgnc_default=True if j == 0 else False,
                )
                session.add(assembly)

        session.commit()

        # Create chromosome data
        chromosomes_per_species = 25
        for species in species_data:
            for j in range(chromosomes_per_species):
                chromosome = Chromosomes(
                    display_name=f"chr{j+1}",
                    taxon_id=species.taxon_id,
                    coord_system=f"{species.genefam_prefix}_coord_system",
                )
                session.add(chromosome)

        session.commit()

        # Create genefam data
        for i in range(1000):  # 1000 gene families
            genefam = Genefam(
                taxon_id=species_data[i % len(species_data)].taxon_id,
                assigned_id=f"TST{i:06d}",
                assigned_symbol=f"TST{i:04d}",
                assigned_name=f"Test Gene Family {i}",
                status_id=1,
                editor_id=1,
                hcop_support_level=i % 5 + 1,
            )
            session.add(genefam)

        session.commit()

        yield session

    finally:
        session.close()


@pytest.fixture
def load_test_config():
    """Provide load testing configuration."""
    return LOAD_TEST_CONFIG


class LoadTestRunner:
    """Utility class for running load tests."""

    def __init__(self, session_factory: Callable[[], Session], config: Dict[str, Any]):
        self.session_factory = session_factory
        self.config = config
        self.results: List[LoadTestResult] = []

    def run_concurrent_test(self, test_func: Callable, num_users: int,
                           duration: int, **kwargs) -> LoadTestResult:
        """Run a test function concurrently with multiple users."""

        results = {
            'total_requests': 0,
            'successful_requests': 0,
            'failed_requests': 0,
            'response_times': [],
            'errors': [],
            'start_time': None,
            'end_time': None
        }

        def worker_thread(worker_id: int):
            """Worker thread function."""
            session = self.session_factory()
            thread_results = {
                'requests': 0,
                'successful': 0,
                'failed': 0,
                'response_times': [],
                'errors': []
            }

            try:
                end_time = time.time() + duration

                while time.time() < end_time:
                    start_time = time.time()
                    try:
                        result = test_func(session, worker_id, **kwargs)
                        end_time_req = time.time()

                        response_time = end_time_req - start_time
                        thread_results['requests'] += 1
                        thread_results['successful'] += 1
                        thread_results['response_times'].append(response_time)

                    except Exception as e:
                        end_time_req = time.time()
                        response_time = end_time_req - start_time

                        thread_results['requests'] += 1
                        thread_results['failed'] += 1
                        thread_results['response_times'].append(response_time)
                        thread_results['errors'].append(str(e))

                        # Rollback on error
                        session.rollback()

                    # Small delay to prevent overwhelming
                    time.sleep(0.001)

            finally:
                session.close()
                return thread_results

        # Start timer
        overall_start = time.time()

        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(num_users)]

            for future in as_completed(futures):
                thread_results = future.result()

                results['total_requests'] += thread_results['requests']
                results['successful_requests'] += thread_results['successful']
                results['failed_requests'] += thread_results['failed']
                results['response_times'].extend(thread_results['response_times'])
                results['errors'].extend(thread_results['errors'])

        # End timer
        overall_end = time.time()
        total_duration = overall_end - overall_start

        # Create LoadTestResult
        load_test_result = LoadTestResult.from_metrics(
            total_requests=results['total_requests'],
            successful_requests=results['successful_requests'],
            failed_requests=results['failed_requests'],
            total_duration=total_duration,
            response_times=results['response_times'],
            errors=results['errors']
        )

        self.results.append(load_test_result)
        return load_test_result

    def run_async_test(self, test_func: Callable, num_users: int,
                      duration: int, **kwargs) -> LoadTestResult:
        """Run a test function asynchronously with multiple users."""

        async def async_worker(worker_id: int):
            """Async worker function."""
            session = self.session_factory()
            worker_results = {
                'requests': 0,
                'successful': 0,
                'failed': 0,
                'response_times': [],
                'errors': []
            }

            try:
                end_time = time.time() + duration

                while time.time() < end_time:
                    start_time = time.time()
                    try:
                        # Run sync function in thread pool for async compatibility
                        loop = asyncio.get_event_loop()
                        result = await loop.run_in_executor(None, test_func, session, worker_id, **kwargs)
                        end_time_req = time.time()

                        response_time = end_time_req - start_time
                        worker_results['requests'] += 1
                        worker_results['successful'] += 1
                        worker_results['response_times'].append(response_time)

                    except Exception as e:
                        end_time_req = time.time()
                        response_time = end_time_req - start_time

                        worker_results['requests'] += 1
                        worker_results['failed'] += 1
                        worker_results['response_times'].append(response_time)
                        worker_results['errors'].append(str(e))

                        session.rollback()

                    await asyncio.sleep(0.001)  # Small async delay

            finally:
                session.close()
                return worker_results

        async def run_async_workers():
            """Run all async workers."""
            tasks = [async_worker(i) for i in range(num_users)]
            results = await asyncio.gather(*tasks, return_exceptions=True)

            # Aggregate results
            total_results = {
                'total_requests': 0,
                'successful_requests': 0,
                'failed_requests': 0,
                'response_times': [],
                'errors': []
            }

            for result in results:
                if isinstance(result, Exception):
                    total_results['errors'].append(str(result))
                    continue

                total_results['total_requests'] += result['requests']
                total_results['successful_requests'] += result['successful']
                total_results['failed_requests'] += result['failed']
                total_results['response_times'].extend(result['response_times'])
                total_results['errors'].extend(result['errors'])

            return total_results

        # Run async test
        start_time = time.time()
        aggregated_results = asyncio.run(run_async_workers())
        end_time = time.time()

        total_duration = end_time - start_time

        # Create LoadTestResult
        load_test_result = LoadTestResult.from_metrics(
            total_requests=aggregated_results['total_requests'],
            successful_requests=aggregated_results['successful_requests'],
            failed_requests=aggregated_results['failed_requests'],
            total_duration=total_duration,
            response_times=aggregated_results['response_times'],
            errors=aggregated_results['errors']
        )

        self.results.append(load_test_result)
        return load_test_result


@pytest.fixture
def load_test_runner(load_test_db, load_test_config):
    """Provide a load test runner instance."""
    return LoadTestRunner(load_test_db, load_test_config)


# Load testing assertions
def assert_load_test_performance(result: LoadTestResult, thresholds: Dict[str, float],
                                test_name: str = "load test"):
    """Assert that load test results meet performance thresholds."""

    # Check response time percentiles
    if result.p95_response_time > thresholds.get("response_time_p95", 0.1):
        pytest.fail(
            f"P95 response time exceeded for {test_name}: "
            f"{result.p95_response_time:.4f}s > {thresholds['response_time_p95']:.4f}s"
        )

    if result.p99_response_time > thresholds.get("response_time_p99", 0.5):
        pytest.fail(
            f"P99 response time exceeded for {test_name}: "
            f"{result.p99_response_time:.4f}s > {thresholds['response_time_p99']:.4f}s"
        )

    # Check error rate
    if result.error_rate > thresholds.get("error_rate", 0.01):
        pytest.fail(
            f"Error rate exceeded for {test_name}: "
            f"{result.error_rate:.2%} > {thresholds['error_rate']:.2%}"
        )

    # Check throughput
    if result.throughput < thresholds.get("throughput_min", 100):
        pytest.fail(
            f"Throughput too low for {test_name}: "
            f"{result.throughput:.2f} ops/sec < {thresholds['throughput_min']} ops/sec"
        )


def assert_load_test_stability(result: LoadTestResult, test_name: str = "load test"):
    """Assert that load test results are stable (low variance)."""

    if len(result.response_times) < 10:
        return  # Skip stability check for small sample sizes

    # Calculate coefficient of variation
    mean_time = statistics.mean(result.response_times)
    std_dev = statistics.stdev(result.response_times)
    cv = std_dev / mean_time if mean_time > 0 else float('inf')

    # Coefficient of variation should be less than 50%
    if cv > 0.5:
        pytest.fail(
            f"Load test results unstable for {test_name}: "
            f"CV = {cv:.2f} (should be < 0.5)"
        )


# Configure pytest for load testing
def pytest_configure(config):
    """Configure pytest settings for load testing."""
    config.addinivalue_line(
        "markers",
        "load_test: mark test as a load test"
    )
    config.addinivalue_line(
        "markers",
        "slow_load_test: mark test as a slow load test (extended duration)"
    )