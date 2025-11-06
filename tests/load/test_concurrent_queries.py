"""
Load testing for concurrent query handling.

This module tests the ORM's performance under concurrent access patterns,
simulating multiple users accessing the database simultaneously.
"""

import pytest
import time
import random
from typing import List
from sqlalchemy import select, and_, or_
from sqlalchemy.orm import Session

from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes

from tests.load.conftest import (
    LoadTestRunner, assert_load_test_performance, assert_load_test_stability
)


class TestConcurrentReadOperations:
    """Load testing for concurrent read operations."""

    @pytest.mark.load_test
    def test_concurrent_species_queries(self, load_test_runner, populated_load_test_db, load_test_config):
        """Test concurrent species lookup queries."""

        def query_species(session: Session, worker_id: int):
            """Query species by primary key."""
            # Random taxon_id from existing data
            taxon_id = random.choice([9000 + i for i in range(100)])
            species = session.get(Species, taxon_id)
            return species

        # Run load test
        result = load_test_runner.run_concurrent_test(
            query_species,
            num_users=load_test_config["concurrent_users"]["medium"],
            duration=load_test_config["test_duration"]["normal"]
        )

        # Assert performance
        assert_load_test_performance(
            result,
            load_test_config["performance_thresholds"],
            "concurrent species queries"
        )

        # Assert stability
        assert_load_test_stability(result, "concurrent species queries")

        # Basic result validation
        assert result.successful_requests > 0
        assert result.error_rate < 0.01
        print(f"Throughput: {result.throughput:.2f} ops/sec")
        print(f"P95 Response Time: {result.p95_response_time*1000:.2f}ms")

    @pytest.mark.load_test
    def test_concurrent_complex_queries(self, load_test_runner, populated_load_test_db, load_test_config):
        """Test concurrent complex queries with joins and filters."""

        def complex_query(session: Session, worker_id: int):
            """Execute complex query with joins."""
            # Query species with assemblies and chromosomes
            query = session.query(Species).join(Assembly).join(Chromosomes).filter(
                and_(
                    Species.is_live == SpeciesLiveStatus.YES,
                    Assembly.is_current == True,
                    Chromosomes.display_name.like("chr%")
                )
            ).limit(10)

            results = query.all()
            return len(results)

        # Run load test
        result = load_test_runner.run_concurrent_test(
            complex_query,
            num_users=load_test_config["concurrent_users"]["medium"],
            duration=load_test_config["test_duration"]["normal"]
        )

        # Assert performance (allow more time for complex queries)
        complex_thresholds = load_test_config["performance_thresholds"].copy()
        complex_thresholds["response_time_p95"] = 0.2  # 200ms for complex queries
        complex_thresholds["throughput_min"] = 50     # Lower throughput for complex queries

        assert_load_test_performance(
            result,
            complex_thresholds,
            "concurrent complex queries"
        )

        assert result.successful_requests > 0
        assert result.error_rate < 0.01

    @pytest.mark.load_test
    def test_concurrent_aggregate_queries(self, load_test_runner, populated_load_test_db, load_test_config):
        """Test concurrent aggregate queries (COUNT, SUM, etc.)."""
        from sqlalchemy import func

        def aggregate_query(session: Session, worker_id: int):
            """Execute aggregate query."""
            # Count species by live status
            query = session.query(
                Species.is_live,
                func.count(Species.taxon_id).label('count')
            ).group_by(Species.is_live)

            results = query.all()
            return len(results)

        # Run load test
        result = load_test_runner.run_concurrent_test(
            aggregate_query,
            num_users=load_test_config["concurrent_users"]["light"],
            duration=load_test_config["test_duration"]["normal"]
        )

        # Assert performance
        assert_load_test_performance(
            result,
            load_test_config["performance_thresholds"],
            "concurrent aggregate queries"
        )

        assert result.successful_requests > 0

    @pytest.mark.load_test
    def test_concurrent_pagination_queries(self, load_test_runner, populated_load_test_db, load_test_config):
        """Test concurrent pagination queries."""

        def pagination_query(session: Session, worker_id: int):
            """Execute paginated query."""
            # Random page number
            page = random.randint(1, 10)
            page_size = 20
            offset = (page - 1) * page_size

            query = session.query(Species).offset(offset).limit(page_size)
            results = query.all()
            return len(results)

        # Run load test
        result = load_test_runner.run_concurrent_test(
            pagination_query,
            num_users=load_test_config["concurrent_users"]["medium"],
            duration=load_test_config["test_duration"]["normal"]
        )

        # Assert performance
        assert_load_test_performance(
            result,
            load_test_config["performance_thresholds"],
            "concurrent pagination queries"
        )

        assert result.successful_requests > 0


class TestConcurrentWriteOperations:
    """Load testing for concurrent write operations."""

    @pytest.mark.load_test
    def test_concurrent_insert_operations(self, load_test_runner, populated_load_test_db, load_test_config):
        """Test concurrent insert operations."""

        def insert_species(session: Session, worker_id: int):
            """Insert new species with unique IDs."""
            import time

            # Generate unique ID using timestamp and worker ID
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

        # Run load test
        result = load_test_runner.run_concurrent_test(
            insert_species,
            num_users=load_test_config["concurrent_users"]["light"],
            duration=load_test_config["test_duration"]["normal"]
        )

        # Assert performance (allow more time for write operations)
        write_thresholds = load_test_config["performance_thresholds"].copy()
        write_thresholds["response_time_p95"] = 0.2  # 200ms for writes
        write_thresholds["throughput_min"] = 20     # Lower throughput for writes

        assert_load_test_performance(
            result,
            write_thresholds,
            "concurrent insert operations"
        )

        assert result.successful_requests > 0
        assert result.error_rate < 0.05  # Allow higher error rate for concurrent writes

    @pytest.mark.load_test
    def test_concurrent_update_operations(self, load_test_runner, populated_load_test_db, load_test_config):
        """Test concurrent update operations."""

        def update_species(session: Session, worker_id: int):
            """Update existing species."""
            # Select random species
            taxon_id = random.choice([9000 + i for i in range(100)])
            species = session.get(Species, taxon_id)

            if species:
                species.display_name = f"Updated by worker {worker_id}"
                session.commit()
                session.refresh(species)
                return True

            return False

        # Run load test
        result = load_test_runner.run_concurrent_test(
            update_species,
            num_users=load_test_config["concurrent_users"]["light"],
            duration=load_test_config["test_duration"]["normal"]
        )

        # Assert performance
        write_thresholds = load_test_config["performance_thresholds"].copy()
        write_thresholds["response_time_p95"] = 0.15  # 150ms for updates
        write_thresholds["throughput_min"] = 30

        assert_load_test_performance(
            result,
            write_thresholds,
            "concurrent update operations"
        )

        assert result.successful_requests > 0

    @pytest.mark.load_test
    def test_concurrent_mixed_operations(self, load_test_runner, populated_load_test_db, load_test_config):
        """Test concurrent mixed read/write operations."""

        def mixed_operation(session: Session, worker_id: int):
            """Perform mixed read/write operations."""
            operation = random.choice(['read', 'read', 'write'])  # 2:1 read:write ratio

            if operation == 'read':
                # Read operation
                taxon_id = random.choice([9000 + i for i in range(100)])
                species = session.get(Species, taxon_id)
                return species is not None

            else:
                # Write operation (update display_name)
                taxon_id = random.choice([9000 + i for i in range(100)])
                species = session.get(Species, taxon_id)

                if species:
                    species.display_name = f"Mixed update {worker_id}"
                    session.commit()
                    return True

                return False

        # Run load test
        result = load_test_runner.run_concurrent_test(
            mixed_operation,
            num_users=load_test_config["concurrent_users"]["medium"],
            duration=load_test_config["test_duration"]["normal"]
        )

        # Assert performance
        assert_load_test_performance(
            result,
            load_test_config["performance_thresholds"],
            "concurrent mixed operations"
        )

        assert result.successful_requests > 0


class TestConcurrentTransactionHandling:
    """Load testing for concurrent transaction handling."""

    @pytest.mark.load_test
    def test_concurrent_transaction_commit(self, load_test_runner, populated_load_test_db, load_test_config):
        """Test concurrent transaction commits."""

        def transaction_commit(session: Session, worker_id: int):
            """Execute transaction with multiple operations."""
            try:
                # Start transaction
                # Read operation
                species = session.query(Species).first()

                # Write operation
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

                    # Commit transaction
                    session.commit()
                    return True

                session.rollback()
                return False

            except Exception:
                session.rollback()
                raise

        # Run load test
        result = load_test_runner.run_concurrent_test(
            transaction_commit,
            num_users=load_test_config["concurrent_users"]["light"],
            duration=load_test_config["test_duration"]["normal"]
        )

        # Assert performance
        transaction_thresholds = load_test_config["performance_thresholds"].copy()
        transaction_thresholds["response_time_p95"] = 0.3  # 300ms for transactions
        transaction_thresholds["throughput_min"] = 15

        assert_load_test_performance(
            result,
            transaction_thresholds,
            "concurrent transaction commits"
        )

        assert result.successful_requests > 0

    @pytest.mark.load_test
    def test_concurrent_transaction_rollback(self, load_test_runner, populated_load_test_db, load_test_config):
        """Test concurrent transaction rollbacks."""

        def transaction_rollback(session: Session, worker_id: int):
            """Execute transaction that deliberately rolls back."""
            try:
                # Start transaction
                species = session.query(Species).first()

                if species:
                    # Modify species (will be rolled back)
                    species.display_name = f"Rollback test {worker_id}"

                    # Create assembly (will be rolled back)
                    assembly = Assembly(
                        name=f"ROLLBACK_{worker_id}",
                        taxon_id=species.taxon_id,
                        source="Test",
                        genbank_assembly_accession=f"GCA_ROLLBACK_{worker_id}",
                        is_current=False,
                        is_vgnc_default=False,
                    )
                    session.add(assembly)

                    # Deliberately rollback
                    session.rollback()
                    return True

                return False

            except Exception:
                session.rollback()
                raise

        # Run load test
        result = load_test_runner.run_concurrent_test(
            transaction_rollback,
            num_users=load_test_config["concurrent_users"]["light"],
            duration=load_test_config["test_duration"]["normal"]
        )

        # Assert performance (rollbacks should be fast)
        rollback_thresholds = load_test_config["performance_thresholds"].copy()
        rollback_thresholds["response_time_p95"] = 0.1  # 100ms for rollbacks
        rollback_thresholds["throughput_min"] = 50

        assert_load_test_performance(
            result,
            rollback_thresholds,
            "concurrent transaction rollbacks"
        )

        assert result.successful_requests > 0


class TestConcurrentStressTesting:
    """Stress testing for high-concurrency scenarios."""

    @pytest.mark.slow_load_test
    def test_high_concurrency_stress(self, load_test_runner, populated_load_test_db, load_test_config):
        """Stress test with high concurrency."""

        def stress_operation(session: Session, worker_id: int):
            """Mixed operation for stress testing."""
            import time
            operations = ['read_species', 'read_assembly', 'count_species']
            operation = random.choice(operations)

            if operation == 'read_species':
                taxon_id = random.choice([9000 + i for i in range(100)])
                return session.get(Species, taxon_id)

            elif operation == 'read_assembly':
                assemblies = session.query(Assembly).limit(5).all()
                return len(assemblies)

            else:  # count_species
                from sqlalchemy import func
                count = session.query(func.count(Species.taxon_id)).scalar()
                return count

        # Run stress test
        result = load_test_runner.run_concurrent_test(
            stress_operation,
            num_users=load_test_config["concurrent_users"]["heavy"],
            duration=load_test_config["test_duration"]["quick"]  # Shorter for stress test
        )

        # More lenient thresholds for stress testing
        stress_thresholds = load_test_config["performance_thresholds"].copy()
        stress_thresholds["response_time_p95"] = 0.5  # 500ms
        stress_thresholds["response_time_p99"] = 1.0  # 1000ms
        stress_thresholds["error_rate"] = 0.02       # 2% error rate
        stress_thresholds["throughput_min"] = 25

        assert_load_test_performance(
            result,
            stress_thresholds,
            "high concurrency stress test"
        )

        assert result.successful_requests > 0

    @pytest.mark.slow_load_test
    def test_sustained_load(self, load_test_runner, populated_load_test_db, load_test_config):
        """Test sustained load over extended period."""

        def sustained_operation(session: Session, worker_id: int):
            """Simple operation for sustained load testing."""
            taxon_id = random.choice([9000 + i for i in range(100)])
            species = session.get(Species, taxon_id)
            return species is not None

        # Run sustained load test
        result = load_test_runner.run_concurrent_test(
            sustained_operation,
            num_users=load_test_config["concurrent_users"]["medium"],
            duration=load_test_config["test_duration"]["extended"]
        )

        # Assert performance (same as normal thresholds)
        assert_load_test_performance(
            result,
            load_test_config["performance_thresholds"],
            "sustained load test"
        )

        assert_load_test_stability(result, "sustained load test")

        # Should handle significant load
        assert result.total_requests > 1000
        assert result.successful_requests > 950