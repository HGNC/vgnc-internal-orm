#!/usr/bin/env python3
"""
Standalone load testing script for concurrent query handling.

This script can be run independently to test the ORM's performance
under concurrent load without requiring pytest.
"""

import argparse
import asyncio
import statistics
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, asdict
from typing import List, Dict, Any, Callable, Optional
from contextlib import contextmanager
import json
import sys
import os

# Add the project root to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool

from vgnc_internal_orm.models.base import BaseModel
from vgnc_internal_orm.models.species import BaseCustomModel, Species, SpeciesLiveStatus
from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes

# Import these after the main models to avoid relationship issues
try:
    from vgnc_internal_orm.models.genefam import Genefam
    from vgnc_internal_orm.models.supporting import GeneStatus, Editor
except ImportError:
    # For testing, we'll skip these models
    Genefam = None
    GeneStatus = None
    Editor = None


@dataclass
class LoadTestResult:
    """Results from a load test execution."""
    test_name: str
    total_requests: int
    successful_requests: int
    failed_requests: int
    total_duration: float
    response_times: List[float]
    errors: List[str]
    throughput: float
    avg_response_time: float
    p50_response_time: float
    p95_response_time: float
    p99_response_time: float
    error_rate: float

    @classmethod
    def from_metrics(cls, test_name: str, total_requests: int, successful_requests: int,
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
            test_name=test_name,
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

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return asdict(self)

    def print_summary(self):
        """Print a formatted summary of the results."""
        print(f"\n{'='*60}")
        print(f"Load Test Results: {self.test_name}")
        print(f"{'='*60}")
        print(f"Total Requests:     {self.total_requests:,}")
        print(f"Successful:         {self.successful_requests:,}")
        print(f"Failed:             {self.failed_requests:,}")
        print(f"Duration:           {self.total_duration:.2f}s")
        print(f"Throughput:         {self.throughput:.2f} req/s")
        print(f"Error Rate:         {self.error_rate:.2%}")
        print(f"\nResponse Times:")
        print(f"  Average:           {self.avg_response_time*1000:.2f}ms")
        print(f"  50th percentile:  {self.p50_response_time*1000:.2f}ms")
        print(f"  95th percentile:  {self.p95_response_time*1000:.2f}ms")
        print(f"  99th percentile:  {self.p99_response_time*1000:.2f}ms")

        if self.errors:
            print(f"\nTop Errors (first 5):")
            for error in self.errors[:5]:
                print(f"  - {error}")
        print(f"{'='*60}\n")


class LoadTestEnvironment:
    """Setup and manage the load testing environment."""

    def __init__(self):
        self.engine = None
        self.SessionLocal = None
        self._setup_database()

    def _setup_database(self):
        """Create in-memory database with test data."""
        print("Setting up load test database...")

        self.engine = create_engine(
            "sqlite:///:memory:",
            poolclass=StaticPool,
            connect_args={"check_same_thread": False},
            echo=False,
        )

        # Create unified metadata
        from sqlalchemy.schema import MetaData
        unified_metadata = MetaData()

        for table in BaseModel.metadata.tables.values():
            table.to_metadata(unified_metadata)

        for table in BaseCustomModel.metadata.tables.values():
            table.to_metadata(unified_metadata)

        # Create tables
        unified_metadata.create_all(self.engine)

        # Create session factory
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Populate with test data
        self._populate_database()

    def _populate_database(self):
        """Populate database with realistic test data."""
        print("Populating database with test data...")
        session = self.SessionLocal()

        try:
            # Supporting data (only if models are available)
            if GeneStatus and Editor:
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

            # Species data
            species_data = []
            for i in range(100):
                species = Species(
                    taxon_id=9000 + i,
                    genefam_prefix=f"TST{i:03d}",
                    display_name=f"Test Species {i}",
                    is_live=SpeciesLiveStatus.YES if i % 2 == 0 else SpeciesLiveStatus.NO,
                )
                species_data.append(species)
                session.add(species)

            session.commit()

            # Assembly data
            for species in species_data[:50]:
                for j in range(3):
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

            # Chromosome data
            for species in species_data:
                for j in range(25):
                    chromosome = Chromosomes(
                        display_name=f"chr{j+1}",
                        taxon_id=species.taxon_id,
                        coord_system=f"{species.genefam_prefix}_coord_system",
                    )
                    session.add(chromosome)

            session.commit()

            # Genefam data (only if model is available)
            if Genefam:
                for i in range(1000):
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
            print("Database setup complete.")

        finally:
            session.close()

    @contextmanager
    def get_session(self):
        """Get a database session."""
        session = self.SessionLocal()
        try:
            yield session
        finally:
            session.close()


class LoadTestRunner:
    """Main load testing runner."""

    def __init__(self, environment: LoadTestEnvironment):
        self.environment = environment
        self.results: List[LoadTestResult] = []

    def run_load_test(self, test_func: Callable, test_name: str, num_users: int,
                     duration: int, **kwargs) -> LoadTestResult:
        """Run a load test with the specified parameters."""
        print(f"Running load test: {test_name}")
        print(f"Concurrent users: {num_users}, Duration: {duration}s")

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
            with self.environment.get_session() as session:
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

                            session.rollback()

                        # Small delay to prevent overwhelming
                        time.sleep(0.001)

                finally:
                    return thread_results

        # Start timer
        overall_start = time.time()

        # Run concurrent workers
        with ThreadPoolExecutor(max_workers=num_users) as executor:
            futures = [executor.submit(worker_thread, i) for i in range(num_users)]

            # Progress indicator
            completed = 0
            for future in as_completed(futures):
                thread_results = future.result()

                results['total_requests'] += thread_results['requests']
                results['successful_requests'] += thread_results['successful']
                results['failed_requests'] += thread_results['failed']
                results['response_times'].extend(thread_results['response_times'])
                results['errors'].extend(thread_results['errors'])

                completed += 1
                if completed % 5 == 0 or completed == num_users:
                    print(f"  Completed: {completed}/{num_users} workers")

        # End timer
        overall_end = time.time()
        total_duration = overall_end - overall_start

        # Create LoadTestResult
        load_test_result = LoadTestResult.from_metrics(
            test_name=test_name,
            total_requests=results['total_requests'],
            successful_requests=results['successful_requests'],
            failed_requests=results['failed_requests'],
            total_duration=total_duration,
            response_times=results['response_times'],
            errors=results['errors']
        )

        self.results.append(load_test_result)
        return load_test_result


# Test functions
def test_concurrent_species_lookup(session: Session, worker_id: int):
    """Test concurrent species lookup."""
    import random
    taxon_id = random.choice([9000 + i for i in range(100)])
    species = session.get(Species, taxon_id)
    return species


def test_concurrent_complex_query(session: Session, worker_id: int):
    """Test concurrent complex queries."""
    from sqlalchemy import and_
    query = session.query(Species).join(Assembly).filter(
        and_(
            Species.is_live == SpeciesLiveStatus.YES,
            Assembly.is_current == True
        )
    ).limit(10)
    results = query.all()
    return len(results)


def test_concurrent_insert(session: Session, worker_id: int):
    """Test concurrent insert operations."""
    import time
    unique_id = int(time.time() * 1000) + worker_id
    taxon_id = 50000 + (unique_id % 10000)

    species = Species(
        taxon_id=taxon_id,
        genefam_prefix=f"LOAD{worker_id:03d}",
        display_name=f"Load Test Species {worker_id}",
        is_live=SpeciesLiveStatus.YES,
    )

    session.add(species)
    session.commit()
    session.refresh(species)

    return species.taxon_id


def test_concurrent_mixed_operations(session: Session, worker_id: int):
    """Test concurrent mixed read/write operations."""
    import random
    operation = random.choice(['read', 'read', 'write'])  # 2:1 read:write ratio

    if operation == 'read':
        taxon_id = random.choice([9000 + i for i in range(100)])
        species = session.get(Species, taxon_id)
        return species is not None

    else:
        taxon_id = random.choice([9000 + i for i in range(100)])
        species = session.get(Species, taxon_id)

        if species:
            species.display_name = f"Mixed update {worker_id}"
            session.commit()
            return True

        return False


def test_concurrent_transactions(session: Session, worker_id: int):
    """Test concurrent transaction handling."""
    try:
        species = session.query(Species).first()

        if species:
            # Create related assembly
            assembly = Assembly(
                name=f"TXN_TEST_{worker_id}",
                taxon_id=species.taxon_id,
                source="Test",
                genbank_assembly_accession=f"GCA_TEST_{worker_id}",
                is_current=False,
                is_vgnc_default=False,
            )
            session.add(assembly)

            # Update species
            species.display_name = f"Transaction test {worker_id}"

            session.commit()
            return True

        session.rollback()
        return False

    except Exception:
        session.rollback()
        raise


def main():
    """Main function to run load tests."""
    parser = argparse.ArgumentParser(description="Run load tests for VGNC ORM")
    parser.add_argument("--users", type=int, default=20, help="Number of concurrent users")
    parser.add_argument("--duration", type=int, default=30, help="Test duration in seconds")
    parser.add_argument("--output", type=str, help="Output JSON file for results")
    parser.add_argument("--test", type=str, choices=[
        "lookup", "complex", "insert", "mixed", "transactions", "all"
    ], default="all", help="Specific test to run")

    args = parser.parse_args()

    print("VGNC ORM Load Testing Framework")
    print("=" * 50)

    # Setup environment
    env = LoadTestEnvironment()
    runner = LoadTestRunner(env)

    # Define tests to run
    tests = [
        ("Concurrent Species Lookup", test_concurrent_species_lookup),
        ("Concurrent Complex Queries", test_concurrent_complex_query),
        ("Concurrent Insert Operations", test_concurrent_insert),
        ("Concurrent Mixed Operations", test_concurrent_mixed_operations),
        ("Concurrent Transactions", test_concurrent_transactions),
    ]

    if args.test != "all":
        test_map = {
            "lookup": 0,
            "complex": 1,
            "insert": 2,
            "mixed": 3,
            "transactions": 4
        }
        tests = [tests[test_map[args.test]]]

    # Run tests
    all_results = []
    for test_name, test_func in tests:
        print(f"\n{'-'*50}")
        result = runner.run_load_test(
            test_func, test_name, args.users, args.duration
        )
        result.print_summary()
        all_results.append(result)

    # Save results if requested
    if args.output:
        with open(args.output, 'w') as f:
            json.dump([r.to_dict() for r in all_results], f, indent=2)
        print(f"Results saved to: {args.output}")

    # Print overall summary
    print(f"\n{'='*50}")
    print("Overall Summary")
    print(f"{'='*50}")
    print(f"Tests run: {len(all_results)}")
    print(f"Total requests: {sum(r.total_requests for r in all_results):,}")
    print(f"Average throughput: {statistics.mean([r.throughput for r in all_results]):.2f} req/s")
    print(f"Average P95 response time: {statistics.mean([r.p95_response_time for r in all_results])*1000:.2f}ms")
    print(f"Overall error rate: {sum(r.failed_requests for r in all_results) / sum(r.total_requests for r in all_results):.2%}")


if __name__ == "__main__":
    main()