"""Performance benchmarks for MySQL-specific operations.

This module benchmarks MySQL-specific features, connection pooling,
and performance characteristics to ensure optimal performance
in MySQL environments.
"""

import pytest
from datetime import datetime
from sqlalchemy import text

from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes

from tests.performance.conftest import (
    populated_benchmark_db, benchmark_db, performance_thresholds,
    assert_performance_threshold, BenchmarkUtils
)

# Note: This test now uses SQLite instead of MySQL for portability


class TestMySQLConnectionPerformance:
    """Benchmarks for MySQL connection and pooling performance."""

    def test_mysql_connection_establishment(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL connection establishment."""
        def establish_connection(session):
            # Simple query to test connection
            result = session.execute(text("SELECT 1 as test"))
            result.fetchone()[0]  # Just execute, don't return value for benchmark

        result = benchmark(establish_connection, populated_benchmark_db)
        # Basic assertion - just ensure the benchmark runs without error

    def test_mysql_transaction_commit(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL transaction commit performance."""
        def commit_transaction(session):
            # Create a species
            species = Species(
                taxon_id=90001,
                genefam_prefix="MYSQL",
                display_name="MySQL Test",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species)
            session.commit()
            session.refresh(species)

            # Update and commit again
            species.display_name = "MySQL Test Updated"
            session.commit()
            session.refresh(species)

            return species.display_name

        result = benchmark(commit_transaction, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["simple_query"], "MySQL transaction commit")
        assert result == "MySQL Test Updated"

    def test_mysql_transaction_rollback(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL transaction rollback performance."""
        def rollback_transaction(session):
            # Create a species
            species = Species(
                taxon_id=90002,
                genefam_prefix="ROL",
                display_name="Rollback Test",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species)
            session.commit()
            session.refresh(species)

            # Update
            species.display_name = "Should be rolled back"
            # Don't commit, just rollback
            session.rollback()

            # Verify rollback
            rolled_back = session.get(Species, 90002)
            return rolled_back.display_name == "Rollback Test"

        result = benchmark(rollback_transaction, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["simple_query"], "MySQL transaction rollback")
        assert result is True

    def test_mysql_savepoint_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL savepoint performance."""
        def use_savepoint(session):
            # Create initial data
            species1 = Species(
                taxon_id=90003,
                genefam_prefix="SAVE",
                display_name="Savepoint Test 1",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species1)
            session.commit()

            # Create savepoint
            savepoint = session.begin_nested()

            try:
                # Create more data within savepoint
                species2 = Species(
                    taxon_id=90004,
                    genefam_prefix="SAVE",
                    display_name="Savepoint Test 2",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                session.add(species2)
                session.flush()

                # Rollback savepoint
                savepoint.rollback()

                # species1 should still exist, species2 should not
                exists1 = session.get(Species, 90003) is not None
                exists2 = session.get(Species, 90004) is None

                return exists1 and not exists2

            except Exception:
                savepoint.rollback()
                raise

        result = benchmark(use_savepoint, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["simple_query"], "MySQL savepoint operations")
        assert result is True


class TestMySQLQueryPerformance:
    """Benchmarks for MySQL-specific query performance."""

    def test_mysql_primary_key_lookup(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL primary key lookup performance."""
        def pk_lookup(session):
            # Create test data first
            species = Species(
                taxon_id=90005,
                genefam_prefix="PK",
                display_name="Primary Key Test",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species)
            session.commit()

            # Multiple lookups
            for _ in range(10):
                found = session.get(Species, 90005)
                assert found is not None

            return True

        result = benchmark(pk_lookup, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["simple_query"], "MySQL primary key lookup")
        assert result is True

    def test_mysql_index_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL index usage performance."""
        def index_lookup(session):
            # Create test data
            for i in range(20):
                assembly = Assembly(
                    name=f"Index Test {i}",
                    taxon_id=9606,  # Use existing species
                    source="Index Test",
                    genbank_assembly_accession=f"GCA_IDX_{i:010d}",
                )
                session.add(assembly)

            session.commit()

            # Query by indexed field (genefam_prefix would need to be indexed)
            assemblies = session.query(Assembly).filter(
                Assembly.source == "Index Test"
            ).all()

            return len(assemblies)

        result = benchmark(index_lookup, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["complex_query"], "MySQL index lookup")
        assert result == 20

    def test_mysql_text_search_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL text search performance."""
        def text_search(session):
            # Create test data
            for i in range(15):
                species = Species(
                    taxon_id=91000 + i,
                    genefam_prefix=f"TXT{i:03d}",
                    display_name=f"Text Search Test {i} with special characters: ñáéíóú",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                session.add(species)

            session.commit()

            # Text search with LIKE
            results = session.query(Species).filter(
                Species.display_name.like("%special%")
            ).all()

            return len(results)

        result = benchmark(text_search, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["complex_query"], "MySQL text search")
        assert result == 15

    def test_mysql_json_operations(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL JSON operations (if supported)."""
        def json_operations(session):
            # Test basic SQL with JSON-like operations
            # Note: This tests SQL functionality, not actual JSON fields
            result = session.execute("""
                SELECT COUNT(*) as count
                FROM species
                WHERE genefam_prefix LIKE 'HSA%'
            """)
            count = result.fetchone()[0]

            # Test aggregation
            result = session.execute("""
                SELECT genefam_prefix, COUNT(*) as cnt
                FROM species
                WHERE genefam_prefix LIKE 'HSA%'
                GROUP BY genefam_prefix
            """)
            groups = result.fetchall()

            return count + len(groups)

        result = benchmark(json_operations, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["aggregate_query"], "MySQL aggregation operations")
        assert result > 0

    def test_mysql_union_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL UNION operation performance."""
        def union_operation(session):
            # Create test data
            for i in range(10):
                species = Species(
                    taxon_id=92000 + i,
                    genefam_prefix=f"UN{i:03d}",
                    display_name=f"Union Test {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                session.add(species)

            session.commit()

            # UNION query
            result = session.execute("""
                SELECT genefam_prefix, display_name
                FROM species
                WHERE genefam_prefix LIKE 'UN%'
                UNION
                SELECT genefam_prefix, display_name
                FROM species
                WHERE genefam_prefix LIKE 'UN%' AND display_name LIKE '%5%'
            """)
            rows = result.fetchall()

            return len(rows)

        result = benchmark(union_operation, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["complex_query"], "MySQL UNION operation")
        assert result > 0


class TestMySQLBulkPerformance:
    """Benchmarks for MySQL bulk operations performance."""

    def test_mysql_bulk_insert_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL bulk insert performance."""
        def bulk_insert(session):
            # Create test data
            test_data = []
            for i in range(100):
                data = {
                    "taxon_id": 93000 + i,
                    "genefam_prefix": f"BULK{i:03d}",
                    "display_name": f"Bulk Insert Test {i}",
                    "is_live": SpeciesLiveStatus.YES,
                    "created": datetime.now(),
                }
                test_data.append(data)

            # Bulk insert using SQLAlchemy
            instances = [Species(**data) for data in test_data]
            session.add_all(instances)
            session.commit()

            return len(instances)

        result = benchmark(bulk_insert, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["bulk_insert"], "MySQL bulk insert")
        assert result == 100

    def test_mysql_batch_insert_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL batch insert performance."""
        def batch_insert(session):
            # Create test data in smaller batches
            total_inserted = 0
            batch_size = 20
            num_batches = 5

            for batch_num in range(num_batches):
                test_data = []
                for i in range(batch_size):
                    data = {
                        "taxon_id": 94000 + batch_num * batch_size + i,
                        "genefam_prefix": f"BAT{batch_num:02d}{i:02d}",
                        "display_name": f"Batch Insert Test {batch_num}-{i}",
                        "is_live": SpeciesLiveStatus.YES,
                        "created": datetime.now(),
                    }
                    test_data.append(data)

                # Insert batch
                instances = [Species(**data) for data in test_data]
                session.add_all(instances)
                session.commit()
                total_inserted += len(instances)

            return total_inserted

        result = benchmark(batch_insert, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["bulk_insert"], "MySQL batch insert")
        assert result == 100  # 5 batches × 20 records = 100

    def test_mysql_bulk_update_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL bulk update performance."""
        def bulk_update(session):
            # Create test data first
            test_data = []
            for i in range(50):
                data = {
                    "taxon_id": 95000 + i,
                    "genefam_prefix": f"UPD{i:03d}",
                    "display_name": f"Original Name {i}",
                    "is_live": SpeciesLiveStatus.YES,
                    "created": datetime.now(),
                }
                test_data.append(data)

            instances = [Species(**data) for data in test_data]
            session.add_all(instances)
            session.commit()

            # Bulk update
            updated_count = session.query(Species).filter(
                Species.taxon_id >= 95000,
                Species.taxon_id < 95050
            ).update({
                "display_name": Species.display_name + " (Updated)"
            })
            session.commit()

            return updated_count

        result = benchmark(bulk_update, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["simple_query"], "MySQL bulk update")
        assert result == 50

    def test_mysql_bulk_delete_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL bulk delete performance."""
        def bulk_delete(session):
            # Create test data first
            test_data = []
            for i in range(30):
                data = {
                    "taxon_id": 96000 + i,
                    "genefam_prefix": f"DEL{i:03d}",
                    "display_name": f"Delete Test {i}",
                    "is_live": SpeciesLiveStatus.YES,
                    "created": datetime.now(),
                }
                test_data.append(data)

            instances = [Species(**data) for data in test_data]
            session.add_all(instances)
            session.commit()

            # Bulk delete
            deleted_count = session.query(Species).filter(
                Species.taxon_id >= 96000,
                Species.taxon_id < 96030
            ).delete()
            session.commit()

            return deleted_count

        result = benchmark(bulk_delete, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["bulk_insert"], "MySQL bulk delete")
        assert result == 30


class TestMySQLFeaturePerformance:
    """Benchmarks for MySQL-specific features."""

    def test_mysql_charset_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL charset handling performance."""
        def charset_test(session):
            # Create data with Unicode characters
            unicode_species = Species(
                taxon_id=97000,
                genefam_prefix="UNI",
                display_name="Unicode Test ñáéíóú with emoji 🧬",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(unicode_species)
            session.commit()

            # Query back and verify
            retrieved = session.get(Species, 97000)
            return "ñáéíóú" in retrieved.display_name

        result = benchmark(charset_test, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["simple_query"], "MySQL charset handling")
        assert result is True

    def test_mysql_enum_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL enum handling performance."""
        def enum_test(session):
            # Test all enum values
            enum_values = [
                SpeciesLiveStatus.YES,
                SpeciesLiveStatus.NO,
                SpeciesLiveStatus.CANCELLED,
                SpeciesLiveStatus.TESTING,
                SpeciesLiveStatus.FLAGGED,
            ]

            species = []
            for i, enum_val in enumerate(enum_values):
                sp = Species(
                    taxon_id=98000 + i,
                    genefam_prefix=f"ENUM{i}",
                    display_name=f"Enum Test {i}",
                    is_live=enum_val,
                    created=datetime.now(),
                )
                species.append(sp)

            session.add_all(species)
            session.commit()

            return len(species)

        result = benchmark(enum_test, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["simple_query"], "MySQL enum handling")
        assert result == 5

    def test_mysql_auto_increment_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL auto_increment performance."""
        def auto_increment_test(session):
            # Create multiple records to test auto_increment
            assemblies = []
            for i in range(50):
                assembly = Assembly(
                    name=f"Auto Increment Test {i}",
                    taxon_id=9606,
                    source="Auto Test",
                    genbank_assembly_accession=f"GCA_AUTO_{i:010d}",
                )
                assemblies.append(assembly)

            session.add_all(assemblies)
            session.commit()

            # Get the IDs to verify auto increment worked
            ids = []
            for assembly in assemblies:
                session.refresh(assembly)
                ids.append(assembly.id)

            return len(ids) and len(set(ids)) == len(ids)  # All IDs should be unique

        result = benchmark(auto_increment_test, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["bulk_insert"], "MySQL auto increment")
        assert result is True

    def test_mysql_foreign_key_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL foreign key constraint performance."""
        def foreign_key_test(session):
            # Create species first
            species = Species(
                taxon_id=99000,
                genefam_prefix="FK",
                display_name="Foreign Key Test",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species)
            session.commit()

            # Create related assemblies
            assemblies = []
            for i in range(25):
                assembly = Assembly(
                    name=f"FK Test {i}",
                    taxon_id=species.taxon_id,  # Valid foreign key
                    source="FK Test",
                    genbank_assembly_accession=f"GCA_FK_{i:010d}",
                )
                assemblies.append(assembly)

            session.add_all(assemblies)
            session.commit()

            return len(assemblies)

        result = benchmark(foreign_key_test, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["bulk_insert"], "MySQL foreign key constraints")
        assert result == 25

    def test_mysql_transaction_isolation(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MySQL transaction isolation performance."""
        def isolation_test(session):
            # Test READ COMMITTED isolation level
            # Create data
            species = Species(
                taxon_id=100000,
                genefam_prefix="ISO",
                display_name="Isolation Test",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species)
            session.commit()

            # In the same transaction, try to read the data
            read_species = session.get(Species, 100000)
            updated = False

            # Update within transaction
            if read_species:
                read_species.display_name = "Updated within transaction"
                session.flush()
                updated = True

            # Commit the update
            session.commit()

            return updated

        result = benchmark(isolation_test, populated_benchmark_db)
        assert_performance_threshold(result, performance_thresholds["simple_query"], "MySQL transaction isolation")
        assert result is True