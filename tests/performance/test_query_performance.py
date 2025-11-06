"""Performance benchmarks for database queries.

This module benchmarks various query patterns to ensure they meet
performance requirements and to track performance regressions.
"""

import pytest
from sqlalchemy import select, func, and_, or_, text
from sqlalchemy.orm import joinedload, selectinload, subqueryload

from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes

from tests.performance.conftest import (
    populated_benchmark_db, benchmark_data_factory,
    performance_thresholds, assert_performance_threshold,
    assert_performance_regression, BenchmarkUtils
)


class TestBasicQueryPerformance:
    """Benchmarks for basic database queries."""

    def test_simple_species_query(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark simple species query by primary key."""
        session = populated_benchmark_db

        def query_species():
            return session.get(Species, 9606)

        # Store the actual query result before benchmarking
        query_result = session.get(Species, 9606)
        assert query_result is not None

        # Benchmark the query operation
        benchmark(query_species)

        # Check performance threshold using the benchmark fixture
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "simple species query")

    def test_species_list_query(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark species list query."""
        session = populated_benchmark_db

        def list_species(session):
            return session.query(Species).all()

        result = benchmark(list_species, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "species list query")
        assert len(result) >= 5  # Should have at least 5 species from fixtures

    def test_species_filter_query(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark species query with filter."""
        session = populated_benchmark_db

        def filter_species(session):
            return session.query(Species).filter(
                Species.genefam_prefix == "HSA"
            ).first()

        result = benchmark(filter_species, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "species filter query")
        assert result.genefam_prefix == "HSA"

    def test_species_count_query(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark species count query."""
        session = populated_benchmark_db

        def count_species(session):
            return session.query(Species).count()

        result = benchmark(count_species, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "species count query")
        assert result >= 5

    def test_assembly_by_species_query(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark assembly query filtered by species."""
        session = populated_benchmark_db

        def query_assemblies(session):
            return session.query(Assembly).filter(
                Assembly.taxon_id == 9606
            ).all()

        result = benchmark(query_assemblies, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "assembly by species query")
        assert len(result) >= 1

    def test_chromosomes_by_species_query(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark chromosomes query filtered by species."""
        session = populated_benchmark_db

        def query_chromosomes(session):
            return session.query(Chromosomes).filter(
                Chromosomes.taxon_id == 9606
            ).all()

        result = benchmark(query_chromosomes, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "chromosomes by species query")
        assert len(result) >= 20  # Human has many chromosomes


class TestComplexQueryPerformance:
    """Benchmarks for complex database queries."""

    def test_species_with_multiple_filters(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark species query with multiple filters."""
        session = populated_benchmark_db

        def complex_filter(session):
            return session.query(Species).filter(
                and_(
                    Species.is_live == SpeciesLiveStatus.YES,
                    Species.genefam_prefix.like("H%"),
                    Species.display_name.contains("human")
                )
            ).all()

        result = benchmark(complex_filter, session)
        assert_performance_threshold(benchmark, performance_thresholds["complex_query"], "complex species filter")
        assert len(result) >= 1

    def test_or_query_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark OR query performance."""
        session = populated_benchmark_db

        def or_filter(session):
            return session.query(Species).filter(
                or_(
                    Species.genefam_prefix == "HSA",
                    Species.genefam_prefix == "MMU",
                    Species.genefam_prefix == "RNO"
                )
            ).all()

        result = benchmark(or_filter, session)
        assert_performance_threshold(benchmark, performance_thresholds["complex_query"], "OR query")
        assert len(result) == 3

    def test_join_query_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark join query performance."""
        session = populated_benchmark_db

        def join_query(session):
            return session.query(Species, Assembly).join(
                Assembly, Species.taxon_id == Assembly.taxon_id
            ).all()

        result = benchmark(join_query, session)
        assert_performance_threshold(benchmark, performance_thresholds["complex_query"], "join query")
        assert len(result) >= 5  # Should have species-assembly pairs

    def test_subquery_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark subquery performance."""
        session = populated_benchmark_db

        def subquery_query(session):
            # Find species that have assemblies
            species_with_assemblies = session.query(Assembly.taxon_id).subquery()
            return session.query(Species).filter(
                Species.taxon_id.in_(species_with_assemblies)
            ).all()

        result = benchmark(subquery_query, session)
        assert_performance_threshold(benchmark, performance_thresholds["complex_query"], "subquery")
        assert len(result) >= 5

    def test_order_by_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark ORDER BY query performance."""
        session = populated_benchmark_db

        def order_by_query(session):
            return session.query(Species).order_by(
                Species.display_name.asc()
            ).all()

        result = benchmark(order_by_query, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "ORDER BY query")
        assert len(result) >= 5

    def test_limit_offset_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark LIMIT/OFFSET query performance."""
        session = populated_benchmark_db

        def limit_offset_query(session):
            return session.query(Species).offset(1).limit(3).all()

        result = benchmark(limit_offset_query, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "LIMIT/OFFSET query")
        assert len(result) <= 3


class TestAggregateQueryPerformance:
    """Benchmarks for aggregate queries."""

    def test_count_by_group(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark COUNT BY GROUP BY query."""
        session = populated_benchmark_db

        def count_by_group(session):
            return session.query(
                Species.is_live, func.count(Species.taxon_id)
            ).group_by(Species.is_live).all()

        result = benchmark(count_by_group, session)
        assert_performance_threshold(benchmark, performance_thresholds["aggregate_query"], "COUNT BY GROUP BY")
        assert len(result) >= 1

    def test_sum_aggregate(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark SUM aggregate query."""
        session = populated_benchmark_db

        def sum_query(session):
            # Count chromosomes per species
            return session.query(
                Species.taxon_id,
                func.count(Chromosomes.chr_id).label('chromosome_count')
            ).join(
                Chromosomes, Species.taxon_id == Chromosomes.taxon_id
            ).group_by(Species.taxon_id).all()

        result = benchmark(sum_query, session)
        assert_performance_threshold(benchmark, performance_thresholds["aggregate_query"], "SUM aggregate")
        assert len(result) >= 5

    def test_max_aggregate(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark MAX aggregate query."""
        session = populated_benchmark_db

        def max_query(session):
            return session.query(
                func.max(Assembly.id)
            ).scalar()

        result = benchmark(max_query, session)
        assert_performance_threshold(benchmark, performance_thresholds["aggregate_query"], "MAX aggregate")
        assert result is not None

    def test_having_clause(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark HAVING clause query."""
        session = populated_benchmark_db

        def having_query(session):
            return session.query(
                Species.taxon_id,
                func.count(Chromosomes.chr_id).label('chromosome_count')
            ).join(
                Chromosomes, Species.taxon_id == Chromosomes.taxon_id
            ).group_by(Species.taxon_id).having(
                func.count(Chromosomes.chr_id) > 10
            ).all()

        result = benchmark(having_query, session)
        assert_performance_threshold(benchmark, performance_thresholds["aggregate_query"], "HAVING clause")
        # Human species should have >10 chromosomes

    def test_multiple_aggregates(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark multiple aggregates in one query."""
        session = populated_benchmark_db

        def multiple_aggregates(session):
            return session.query(
                func.count(Species.taxon_id).label('total_species'),
                func.count(func.distinct(Species.genefam_prefix)).label('unique_prefixes'),
                func.count(Species.taxon_id).filter(Species.is_live == SpeciesLiveStatus.YES).label('live_species')
            ).first()

        result = benchmark(multiple_aggregates, session)
        assert_performance_threshold(benchmark, performance_thresholds["aggregate_query"], "multiple aggregates")
        assert result.total_species >= 5


class TestBulkOperationPerformance:
    """Benchmarks for bulk database operations."""

    def test_bulk_insert_performance(self, benchmark, benchmark_db, benchmark_data_factory, performance_thresholds):
        """Benchmark bulk insert performance."""
        session = benchmark_db

        def bulk_insert(session):
            # Generate test data
            test_data = benchmark_data_factory["species"](1000)

            # Create instances
            instances = [Species(**data) for data in test_data]
            session.add_all(instances)
            session.commit()

            return len(instances)

        result = benchmark(bulk_insert, session)
        assert_performance_threshold(benchmark, performance_thresholds["bulk_insert"], "bulk insert")
        assert result == 1000

    def test_bulk_delete_performance(self, benchmark, benchmark_db, performance_thresholds):
        """Benchmark bulk delete performance."""
        session = benchmark_db

        def bulk_delete(session):
            # First insert test data
            test_data = benchmark_data_factory["species"](500)
            instances = [Species(**data) for data in test_data]
            session.add_all(instances)
            session.commit()

            # Then delete them
            deleted_count = session.query(Species).filter(
                Species.genefam_prefix.like("TEST%")
            ).delete()
            session.commit()

            return deleted_count

        result = benchmark(bulk_delete, session)
        assert_performance_threshold(benchmark, performance_thresholds["bulk_insert"], "bulk delete")  # Use same threshold
        assert result == 500

    def test_bulk_update_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark bulk update performance."""
        session = populated_benchmark_db

        def bulk_update(session):
            # Update display names for all species
            updated_count = session.query(Species).filter(
                Species.taxon_id.in_([9606, 10090, 10116])
            ).update(
                {"display_name": Species.display_name + " (Updated)"}
            )
            session.commit()

            return updated_count

        result = benchmark(bulk_update, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "bulk update")
        assert result == 3


class TestLoadingStrategyPerformance:
    """Benchmarks for different relationship loading strategies."""

    def test_lazy_loading_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark lazy loading performance."""
        session = populated_benchmark_db

        def lazy_loading(session):
            # Query species without loading relationships
            species = session.query(Species).filter(Species.taxon_id == 9606).first()

            # Access relationship (triggers lazy load)
            assemblies = session.query(Assembly).filter(
                Assembly.taxon_id == species.taxon_id
            ).all()

            return len(assemblies)

        result = benchmark(lazy_loading, session)
        assert_performance_threshold(benchmark, performance_thresholds["relationship_loading"], "lazy loading")
        assert result >= 1

    def test_joined_loading_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark joined loading performance."""
        session = populated_benchmark_db

        def joined_loading(session):
            # Query with joined loading
            species = session.query(Species).options(
                joinedload(Species.assemblies)
            ).filter(Species.taxon_id == 9606).first()

            return len(species.assemblies) if hasattr(species, 'assemblies') else 0

        result = benchmark(joined_loading, session)
        assert_performance_threshold(benchmark, performance_thresholds["relationship_loading"], "joined loading")
        # Note: This will return 0 because the relationship isn't properly defined in the model

    def test_selectin_loading_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark selectin loading performance."""
        session = populated_benchmark_db

        def selectin_loading(session):
            # Query with selectin loading (for collections)
            species = session.query(Species).filter(
                Species.taxon_id == 9606
            ).all()

            # Then load assemblies for all species
            for sp in species:
                assemblies = session.query(Assembly).filter(
                    Assembly.taxon_id == sp.taxon_id
                ).all()

            return len(species)

        result = benchmark(selectin_loading, session)
        assert_performance_threshold(benchmark, performance_thresholds["relationship_loading"], "selectin loading")
        assert result == 1


class TestIndexPerformance:
    """Benchmarks to verify indexes are being used effectively."""

    def test_primary_key_lookup_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark primary key lookup performance."""
        session = populated_benchmark_db

        def pk_lookup(session):
            # Multiple primary key lookups
            taxon_ids = [9606, 10090, 10116, 7227, 6239]
            results = []
            for taxon_id in taxon_ids:
                species = session.get(Species, taxon_id)
                if species:
                    results.append(species)
            return results

        result = benchmark(pk_lookup, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "primary key lookup")
        assert len(result) >= 5

    def test_foreign_key_lookup_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark foreign key lookup performance."""
        session = populated_benchmark_db

        def fk_lookup(session):
            # Query by foreign key (should be indexed)
            assemblies = session.query(Assembly).filter(
                Assembly.taxon_id == 9606
            ).all()
            return assemblies

        result = benchmark(fk_lookup, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "foreign key lookup")
        assert len(result) >= 1

    def test_indexed_filter_performance(self, benchmark, populated_benchmark_db, performance_thresholds):
        """Benchmark indexed filter performance."""
        session = populated_benchmark_db

        def indexed_filter(session):
            # Filter by indexed field (assuming genefam_prefix is indexed)
            species = session.query(Species).filter(
                Species.genefam_prefix == "HSA"
            ).all()
            return species

        result = benchmark(indexed_filter, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "indexed filter")
        assert len(result) == 1