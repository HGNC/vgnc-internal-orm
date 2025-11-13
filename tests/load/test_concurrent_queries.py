"""
Load testing for concurrent query handling.

This module tests the ORM's performance under concurrent access patterns,
simulating multiple users accessing the database simultaneously.
"""

import random

import pytest
from sqlalchemy import and_
from sqlalchemy.orm import Session

from tests.load.conftest import assert_load_test_performance, assert_load_test_stability
from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes
from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus


class TestConcurrentReadOperations:
    """Load testing for concurrent read operations."""

    @pytest.mark.load_test
    def test_concurrent_species_queries(
        self, load_test_runner, populated_load_test_db, load_test_config
    ):
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
            duration=load_test_config["test_duration"]["normal"],
        )

        # Assert performance
        assert_load_test_performance(
            result,
            load_test_config["performance_thresholds"],
            "concurrent species queries",
        )

        # Assert stability
        assert_load_test_stability(result, "concurrent species queries")

        # Basic result validation
        assert result.successful_requests > 0
        assert (
            result.error_rate < 0.015
        )  # Allow 1.5% error rate for concurrent operations
        print(f"Throughput: {result.throughput:.2f} ops/sec")
        print(f"P95 Response Time: {result.p95_response_time*1000:.2f}ms")

    @pytest.mark.load_test
    def test_concurrent_complex_queries(
        self, load_test_runner, populated_load_test_db, load_test_config
    ):
        """Test concurrent complex queries with joins and filters."""

        def complex_query(session: Session, worker_id: int):
            """Execute complex query with joins."""
            # Query species with assemblies and chromosomes
            query = (
                session.query(Species)
                .join(Assembly)
                .join(Chromosomes)
                .filter(
                    and_(
                        Species.is_live == SpeciesLiveStatus.YES,
                        Assembly.is_current,
                        Chromosomes.display_name.like("chr%"),
                    )
                )
                .limit(10)
            )

            results = query.all()
            return len(results)

        # Run load test
        result = load_test_runner.run_concurrent_test(
            complex_query,
            num_users=load_test_config["concurrent_users"]["medium"],
            duration=load_test_config["test_duration"]["normal"],
        )

        # Assert performance (allow more time for complex queries)
        complex_thresholds = load_test_config["performance_thresholds"].copy()
        complex_thresholds["response_time_p95"] = 0.2  # 200ms for complex queries
        complex_thresholds["throughput_min"] = (
            50  # Lower throughput for complex queries
        )

        assert_load_test_performance(
            result, complex_thresholds, "concurrent complex queries"
        )

        assert result.successful_requests > 0
        assert result.error_rate < 0.01

    @pytest.mark.load_test
    def test_concurrent_aggregate_queries(
        self, load_test_runner, populated_load_test_db, load_test_config
    ):
        """Test concurrent aggregate queries (COUNT, SUM, etc.)."""
        from sqlalchemy import func

        def aggregate_query(session: Session, worker_id: int):
            """Execute aggregate query."""
            # Count species by live status
            query = session.query(
                Species.is_live, func.count(Species.taxon_id).label("count")
            ).group_by(Species.is_live)

            results = query.all()
            return len(results)

        # Run load test
        result = load_test_runner.run_concurrent_test(
            aggregate_query,
            num_users=load_test_config["concurrent_users"]["light"],
            duration=load_test_config["test_duration"]["normal"],
        )

        # Assert performance
        assert_load_test_performance(
            result,
            load_test_config["performance_thresholds"],
            "concurrent aggregate queries",
        )

        assert result.successful_requests > 0

    @pytest.mark.load_test
    def test_concurrent_pagination_queries(
        self, load_test_runner, populated_load_test_db, load_test_config
    ):
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
            duration=load_test_config["test_duration"]["normal"],
        )

        # Assert performance
        assert_load_test_performance(
            result,
            load_test_config["performance_thresholds"],
            "concurrent pagination queries",
        )

        assert result.successful_requests > 0


class TestConcurrentWriteOperations:
    """Load testing for concurrent write operations."""

    @pytest.mark.load_test
    def test_concurrent_insert_operations(
        self, load_test_runner, populated_load_test_db, load_test_config
    ):
        """Test concurrent insert operations (limited for SQLite compatibility)."""
        pytest.skip(
            "SQLite has limited concurrent write capability - skipping concurrent insert test"
        )

    @pytest.mark.load_test
    def test_concurrent_update_operations(
        self, load_test_runner, populated_load_test_db, load_test_config
    ):
        """Test concurrent update operations (limited for SQLite compatibility)."""
        pytest.skip(
            "SQLite has limited concurrent write capability - skipping concurrent update test"
        )

    @pytest.mark.load_test
    def test_concurrent_mixed_operations(
        self, load_test_runner, populated_load_test_db, load_test_config
    ):
        """Test concurrent mixed read operations (read-only for SQLite compatibility)."""

        def mixed_read_operation(session: Session, worker_id: int):
            """Perform various read operations."""
            operations = ["read_species", "read_assembly", "count_species"]
            operation = random.choice(operations)

            if operation == "read_species":
                # Read operation
                taxon_id = random.choice([9000 + i for i in range(100)])
                species = session.get(Species, taxon_id)
                return species is not None

            elif operation == "read_assembly":
                # Read assemblies
                assemblies = session.query(Assembly).limit(5).all()
                return len(assemblies)

            else:  # count_species
                # Count species
                from sqlalchemy import func

                count = session.query(func.count(Species.taxon_id)).scalar()
                return count

        # Run load test
        result = load_test_runner.run_concurrent_test(
            mixed_read_operation,
            num_users=load_test_config["concurrent_users"]["medium"],
            duration=load_test_config["test_duration"]["normal"],
        )

        # Assert performance
        assert_load_test_performance(
            result,
            load_test_config["performance_thresholds"],
            "concurrent mixed read operations",
        )

        assert result.successful_requests > 0


class TestConcurrentTransactionHandling:
    """Load testing for concurrent transaction handling."""

    @pytest.mark.load_test
    def test_concurrent_transaction_commit(
        self, load_test_runner, populated_load_test_db, load_test_config
    ):
        """Test concurrent transaction commits (limited for SQLite compatibility)."""
        pytest.skip(
            "SQLite has limited concurrent write capability - skipping concurrent transaction commit test"
        )

    @pytest.mark.load_test
    def test_concurrent_transaction_rollback(
        self, load_test_runner, populated_load_test_db, load_test_config
    ):
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
            duration=load_test_config["test_duration"]["normal"],
        )

        # Assert performance (rollbacks should be fast)
        rollback_thresholds = load_test_config["performance_thresholds"].copy()
        rollback_thresholds["response_time_p95"] = 0.1  # 100ms for rollbacks
        rollback_thresholds["throughput_min"] = 50

        assert_load_test_performance(
            result, rollback_thresholds, "concurrent transaction rollbacks"
        )

        assert result.successful_requests > 0


class TestConcurrentStressTesting:
    """Stress testing for high-concurrency scenarios."""

    @pytest.mark.slow_load_test
    def test_high_concurrency_stress(
        self, load_test_runner, populated_load_test_db, load_test_config
    ):
        """Stress test with high concurrency."""

        def stress_operation(session: Session, worker_id: int):
            """Mixed operation for stress testing."""

            operations = ["read_species", "read_assembly", "count_species"]
            operation = random.choice(operations)

            if operation == "read_species":
                taxon_id = random.choice([9000 + i for i in range(100)])
                return session.get(Species, taxon_id)

            elif operation == "read_assembly":
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
            duration=load_test_config["test_duration"][
                "quick"
            ],  # Shorter for stress test
        )

        # More lenient thresholds for stress testing
        stress_thresholds = load_test_config["performance_thresholds"].copy()
        stress_thresholds["response_time_p95"] = 0.5  # 500ms
        stress_thresholds["response_time_p99"] = 1.0  # 1000ms
        stress_thresholds["error_rate"] = 0.02  # 2% error rate
        stress_thresholds["throughput_min"] = 25

        assert_load_test_performance(
            result, stress_thresholds, "high concurrency stress test"
        )

        assert result.successful_requests > 0

    @pytest.mark.slow_load_test
    def test_sustained_load(
        self, load_test_runner, populated_load_test_db, load_test_config
    ):
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
            duration=load_test_config["test_duration"]["extended"],
        )

        # Assert performance (same as normal thresholds)
        assert_load_test_performance(
            result, load_test_config["performance_thresholds"], "sustained load test"
        )

        assert_load_test_stability(result, "sustained load test")

        # Should handle significant load
        assert result.total_requests > 1000
        assert result.successful_requests > 950
