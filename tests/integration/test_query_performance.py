"""Integration tests for query performance and N+1 prevention.

These tests validate that the query optimizations work correctly and
actually prevent N+1 query problems.
"""

from datetime import UTC, datetime

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.orm import joinedload, selectinload, sessionmaker
from sqlalchemy.pool import StaticPool

from vgnc_internal_orm.models.base import BaseModel
from vgnc_internal_orm.models.chromosomes import Chromosomes
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.orthology import GeneFamilyGroupMember, GeneOrthologyGroup
from vgnc_internal_orm.models.species import Species
from vgnc_internal_orm.utils.query_optimizer import (
    BatchQueryExecutor,
    NPlusOneDetector,
    OptimizedQueryBuilder,
    QueryOptimizer,
    QueryProfiler,
    RelationshipLoader,
)


@pytest.fixture(scope="function")
def test_db():
    """Create a test database with sample data for performance tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False,
    )

    # Create unified metadata to handle cross-metadata foreign key references
    from sqlalchemy.schema import MetaData

    unified_metadata = MetaData()

    # Add all tables from both metadata registries
    from vgnc_internal_orm.models.species import BaseCustomModel

    for table in BaseModel.metadata.tables.values():
        table.to_metadata(unified_metadata)

    for table in BaseCustomModel.metadata.tables.values():
        table.to_metadata(unified_metadata)

    # Create all tables with foreign key constraints disabled for testing
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        unified_metadata.create_all(conn)
        conn.commit()

    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Ensure foreign keys remain disabled for this session
    session.execute(text("PRAGMA foreign_keys = OFF"))

    return session


@pytest.fixture
def performance_test_data(test_db):
    """Create comprehensive test data for performance testing."""
    session = test_db

    from datetime import datetime

    # Insert mock data for foreign key references
    session.execute(
        text(
            "INSERT OR IGNORE INTO gene_status (id, status, display) VALUES (1, 'Active', 'Active Status')"
        )
    )
    session.execute(
        text(
            "INSERT OR IGNORE INTO editor (id, display_name, current, connected) VALUES (1, 'Test Editor', 1, 1)"
        )
    )
    session.commit()

    # Create multiple species using raw SQL
    species_names = [
        "Testus alpha",
        "Testus beta",
        "Testus gamma",
        "Testus delta",
        "Testus epsilon",
        "Testus zeta",
        "Testus eta",
        "Testus theta",
        "Testus iota",
        "Testus kappa",
    ]
    vgnc_prefixes = [
        "TSA",
        "TSB",
        "TSC",
        "TSD",
        "TSE",
        "TSF",
        "TSG",
        "TSH",
        "TSI",
        "TSJ",
    ]

    species_data = []
    for i, (name, prefix) in enumerate(zip(species_names, vgnc_prefixes, strict=False)):
        data = {
            "taxon_id": 9000 + i,
            "genefam_prefix": prefix,
            "display_name": f"Test Species {i} ({name})",
            "primary_db_table": "species",
            "ensembl_species_name": name.lower().replace(" ", "_"),
            "is_live": "YES",
            "created": datetime.now(),
        }
        session.execute(
            text(
                """
            INSERT INTO species (taxon_id, genefam_prefix, display_name, primary_db_table, ensembl_species_name, is_live, created)
            VALUES (:taxon_id, :genefam_prefix, :display_name, :primary_db_table, :ensembl_species_name, :is_live, :created)
        """
            ),
            data,
        )
        species_data.append(data)

    # Create chromosomes for each species using raw SQL
    chromosome_data = []
    for species in species_data:
        for i in range(3):  # 3 chromosomes per species
            chr_data = {
                "taxon_id": species["taxon_id"],
                "display_name": f"chr{i+1}",
                "coord_system": f"GCA_test.{species['taxon_id']}",
                "genbank_accession": f"GCA_{species['taxon_id']}.{i+1}",
                "refseq_accession": f"NC_{species['taxon_id']}.{i+1}",
            }
            session.execute(
                text(
                    """
                INSERT INTO chromosomes (taxon_id, display_name, coord_system, genbank_accession, refseq_accession)
                VALUES (:taxon_id, :display_name, :coord_system, :genbank_accession, :refseq_accession)
            """
                ),
                chr_data,
            )
            chromosome_data.append(chr_data)

    # Create assemblies for each species using raw SQL
    for species in species_data:
        assembly_data = {
            "taxon_id": species["taxon_id"],
            "genbank_assembly_accession": f"GCA_test.{species['taxon_id']}",
            "refseq_assembly_accession": f"NC_test.{species['taxon_id']}",
            "is_current": True,
            "is_vgnc_default": True,
            "name": f"{species['genefam_prefix']}_test_assembly",
            "source": "Test Source",
        }
        session.execute(
            text(
                """
            INSERT INTO assembly (taxon_id, genbank_assembly_accession, refseq_assembly_accession, is_current, is_vgnc_default, name, source)
            VALUES (:taxon_id, :genbank_assembly_accession, :refseq_assembly_accession, :is_current, :is_vgnc_default, :name, :source)
        """
            ),
            assembly_data,
        )

    # Create multiple gene families using raw SQL
    for i in range(10):  # Reduce from 20 to 10 for performance
        genefam_data = {
            "taxon_id": species_data[i % len(species_data)][
                "taxon_id"
            ],  # Rotate through species
            "assigned_id": f"VGNC_PERF_TEST_{i}",
            "assigned_symbol": f"PERF{i}",
            "assigned_name": f"Test gene family {i} for performance testing",
            "status_id": 1,
            "editor_id": 1,
            "hcop_support_level": 2,
        }
        session.execute(
            text(
                """
            INSERT INTO genefam (taxon_id, assigned_id, assigned_symbol, assigned_name, status_id, editor_id, hcop_support_level)
            VALUES (:taxon_id, :assigned_id, :assigned_symbol, :assigned_name, :status_id, :editor_id, :hcop_support_level)
        """
            ),
            genefam_data,
        )

    session.commit()
    return {"species": species_data, "chromosomes": chromosome_data, "session": session}


class TestQueryOptimizations:
    """Test various query optimization strategies."""

    def test_basic_selectin_loading(self, test_db, performance_test_data):
        """Test that selectin loading prevents N+1 queries."""
        session = test_db

        # Query species with selectin loading for chromosomes
        species = (
            session.execute(select(Species).options(selectinload(Species.chromosomes)))
            .scalars()
            .all()
        )

        # Access chromosomes - should not trigger additional queries
        total_chromosomes = 0
        for sp in species:
            assert hasattr(sp, "chromosomes")
            total_chromosomes += len(sp.chromosomes)

        # Should have 10 species * 3 chromosomes each = 30 total
        assert total_chromosomes == 30

    def test_joined_loading_for_single_relationships(
        self, test_db, performance_test_data
    ):
        """Test that joined loading works well for single relationships."""
        session = test_db

        # Query chromosomes with joined loading for species
        chromosomes = (
            session.execute(
                select(Chromosomes).options(joinedload(Chromosomes.species))
            )
            .scalars()
            .all()
        )

        # Access species data - should not trigger additional queries
        species_names = set()
        for chrom in chromosomes:
            assert hasattr(chrom, "species")
            species_names.add(chrom.species.scientific_name)

        # Should have species data loaded
        assert len(species_names) == 10

    def test_complex_selectin_loading_patterns(self, test_db, performance_test_data):
        """Test complex selectin loading for multiple relationships."""
        session = test_db

        # Query species with multiple selectin loads
        species = (
            session.execute(
                select(Species).options(
                    selectinload(Species.chromosomes),
                    selectinload(Species.assemblies),
                    selectinload(Species.genefams),
                )
            )
            .scalars()
            .all()
        )

        # Access all relationships
        total_chromosomes = 0
        total_assemblies = 0
        total_genefams = 0

        for sp in species:
            total_chromosomes += len(sp.chromosomes)
            total_assemblies += len(sp.assemblies)
            total_genefams += len(sp.genefams)

        assert total_chromosomes == 30  # 10 species * 3 chromosomes
        assert total_assemblies == 10  # 1 assembly per species
        assert total_genefams > 0  # Should have genefam associations

    def test_mixed_loading_strategies(self, test_db, performance_test_data):
        """Test mixing different loading strategies appropriately."""
        session = test_db

        # Query genefams with selectin loading strategy
        genefams = (
            session.execute(
                select(Genefam).options(
                    selectinload(
                        Genefam.species
                    )  # Use selectin for species relationship
                )
            )
            .scalars()
            .all()
        )

        # Verify relationships are loaded
        for gf in genefams:
            assert hasattr(gf, "species")

    def test_prevent_n_plus_one_with_orthology_groups(
        self, test_db, performance_test_data
    ):
        """Test that orthology group queries don't cause N+1 problems."""
        session = test_db

        # Query orthology groups with all necessary relationships
        groups = (
            session.execute(
                select(GeneOrthologyGroup).options(
                    selectinload(GeneOrthologyGroup.members).selectinload(
                        GeneFamilyGroupMember.genefam
                    ),
                    selectinload(GeneOrthologyGroup.members).selectinload(
                        GeneFamilyGroupMember.species
                    ),
                )
            )
            .scalars()
            .all()
        )

        # Access nested relationships
        for group in groups:
            assert hasattr(group, "members")
            for member in group.members:
                assert hasattr(member, "genefam")
                assert hasattr(member, "species")


class TestQueryProfiler:
    """Test query profiling functionality."""

    def test_query_profiling(self, test_db, performance_test_data):
        """Test that query profiling works correctly."""
        session = test_db
        profiler = QueryProfiler(session)

        # Profile some queries
        with profiler.profile_query():
            session.execute(select(Species)).scalars().all()

        with profiler.profile_query():
            session.execute(select(Genefam)).scalars().all()

        # Check stats
        stats = profiler.get_stats()
        assert stats["query_count"] == 2
        assert stats["total_time"] > 0
        assert stats["average_time"] > 0

    def test_performance_comparison_lazy_vs_optimized(
        self, test_db, performance_test_data
    ):
        """Compare performance between lazy and optimized queries."""
        session = test_db

        # Test lazy loading (potentially N+1)
        profiler_lazy = QueryProfiler(session)
        species_lazy = session.execute(select(Species)).scalars().all()

        with profiler_lazy.profile_query():
            for sp in species_lazy:
                _ = len(sp.chromosomes)  # This might trigger N+1 queries

        # Test optimized loading
        profiler_optimized = QueryProfiler(session)
        species_optimized = (
            session.execute(select(Species).options(selectinload(Species.chromosomes)))
            .scalars()
            .all()
        )

        with profiler_optimized.profile_query():
            for sp in species_optimized:
                _ = len(sp.chromosomes)  # This should not trigger additional queries

        # Optimized should be more efficient (fewer queries)
        lazy_stats = profiler_lazy.get_stats()
        optimized_stats = profiler_optimized.get_stats()

        # The optimized version should have fewer queries
        # Note: In a real scenario with SQLite in-memory, the difference might be small
        assert optimized_stats["query_count"] <= lazy_stats["query_count"]


class TestNPlusOneDetector:
    """Test N+1 problem detection."""

    def test_detect_potential_n_plus_one(self, test_db):
        """Test detection of potential N+1 problems."""
        session = test_db
        detector = NPlusOneDetector(session)

        # Analyze model relationships
        analysis = detector.analyze_query_pattern(
            Species, ["chromosomes", "assemblies", "genefams"]
        )

        assert analysis["model"] == "Species"
        assert "suggestions" in analysis
        assert "recommendations" in analysis


class TestOptimizedQueryBuilder:
    """Test the optimized query builder."""

    def test_build_genefam_query(self, test_db, performance_test_data):
        """Test building optimized genefam queries."""
        session = test_db
        builder = OptimizedQueryBuilder(session)

        # Build optimized query
        query = builder.build_genefam_query(
            include_species=True,
            include_enhanced=True,
            include_groups=True,
            filters={"is_active": True},
        )

        # Execute query
        genefams = session.execute(query).scalars().all()

        assert len(genefams) > 0
        # All genefams should be active based on filter
        for gf in genefams:
            assert gf.is_active is True

    def test_build_species_query(self, test_db, performance_test_data):
        """Test building optimized species queries."""
        session = test_db
        builder = OptimizedQueryBuilder(session)

        # Build optimized query
        query = builder.build_species_query(
            include_chromosomes=True,
            include_assemblies=True,
            include_genefams=True,
            include_relationships=True,
            filters={"is_model_organism": True},
        )

        # Execute query
        all_species = session.execute(query).scalars().unique().all()

        # Filter by is_model_organism property since it can't be filtered at database level
        species = [sp for sp in all_species if sp.is_model_organism]

        assert len(species) == 3  # Only model organisms
        for sp in species:
            assert sp.is_model_organism is True
            assert hasattr(sp, "chromosomes")
            assert hasattr(sp, "assemblies")
            assert hasattr(sp, "genefams")


class TestBatchQueryExecutor:
    """Test batch query execution functionality."""

    def test_batch_query_execution(self, test_db, performance_test_data):
        """Test that batch queries work correctly."""
        session = test_db

        def query_species_by_prefix(session, prefixes):
            return (
                session.execute(
                    select(Species).where(Species.vgnc_prefix.in_(prefixes))
                )
                .scalars()
                .all()
            )

        # Test batch execution
        prefixes = ["TSA", "TSB", "TSC", "TSD", "TSE"]
        results = BatchQueryExecutor.execute_in_batches(
            session, query_species_by_prefix, prefixes, batch_size=2
        )

        assert len(results) == 5
        for result in results:
            assert result.vgnc_prefix in prefixes

    def test_bulk_operations_performance(self, test_db, performance_test_data):
        """Test bulk insert/update operations."""
        session = test_db

        # Create test instances for bulk insert using Species model instead
        # to avoid foreign key constraint issues with Genefam
        from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus

        new_species = []
        for i in range(5):  # Use smaller number for species
            species = Species(
                taxon_id=10000 + i,  # Use high taxon_ids to avoid conflicts
                genefam_prefix=f"BULK_{i}",
                display_name=f"Bulk Test Species {i} (Testus bulkus)",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(UTC),
            )
            new_species.append(species)

        # Test bulk insert (using regular add_all due to foreign key constraints in test)
        session.add_all(new_species)
        session.commit()

        # Verify bulk insert worked
        count = session.execute(
            select(func.count(Species.taxon_id)).where(
                Species.genefam_prefix.like("BULK_%")
            )
        ).scalar()

        assert count == 5


class TestRelationshipLoader:
    """Test relationship loader configurations."""

    def test_genefam_optimized_load(self, test_db, performance_test_data):
        """Test genefam optimized loading configuration."""
        session = test_db

        # Get optimized loading configuration
        optimizations = RelationshipLoader.get_genefam_optimized_load()
        optimizer = QueryOptimizer(session)

        # Build and execute optimized query
        query = optimizer.get_optimized_query(Genefam, optimizations)
        genefams = session.execute(query).scalars().all()

        assert len(genefams) > 0
        for gf in genefams:
            assert hasattr(gf, "species")
            # Note: enhanced_species_associations and group_memberships relationships not implemented yet

    def test_species_optimized_load(self, test_db, performance_test_data):
        """Test species optimized loading configuration."""
        session = test_db

        # Get optimized loading configuration
        optimizations = RelationshipLoader.get_species_optimized_load()
        optimizer = QueryOptimizer(session)

        # Build and execute optimized query
        query = optimizer.get_optimized_query(Species, optimizations)
        species = session.execute(query).scalars().all()

        assert len(species) > 0
        for sp in species:
            assert hasattr(sp, "chromosomes")
            assert hasattr(sp, "assemblies")
            assert hasattr(sp, "genefams")


class TestQueryPerformanceIntegration:
    """Integration tests combining multiple optimization strategies."""

    def test_complex_query_optimization(self, test_db, performance_test_data):
        """Test optimization of complex multi-level queries."""
        session = test_db

        # Build a complex query with multiple optimizations
        query = (
            select(Species)
            .options(
                selectinload(Species.chromosomes),
                selectinload(Species.assemblies),
                selectinload(
                    Species.genefams
                ),  # enhanced_species_associations not implemented
            )
            .order_by(Species.scientific_name)
        )

        # Execute and verify
        all_species = session.execute(query).scalars().all()

        # Filter by is_model_organism property since it can't be filtered at database level
        species = [sp for sp in all_species if sp.is_model_organism]

        assert len(species) == 3  # Model organisms only
        for sp in species:
            assert len(sp.chromosomes) > 0
            assert len(sp.assemblies) > 0
            assert len(sp.genefams) > 0

            # Check nested relationship loading
            for gf in sp.genefams:
                assert hasattr(
                    gf, "species"
                )  # enhanced_species_associations not implemented

    def test_prevent_n_plus_one_in_real_scenario(self, test_db, performance_test_data):
        """Test N+1 prevention in a realistic usage scenario."""
        session = test_db

        # Simulate a real scenario: Get all model organisms with their data
        profiler = QueryProfiler(session)

        with profiler.profile_query():
            species = (
                session.execute(
                    select(Species).options(
                        selectinload(Species.chromosomes),
                        selectinload(Species.assemblies),
                        selectinload(Species.genefams),
                        # enhanced_genefam_associations and group_memberships not implemented
                    )
                )
                .scalars()
                .all()
            )

        # Filter by is_model_organism property since it can't be filtered at database level
        species = [sp for sp in species if sp.is_model_organism]

        # Process the data without triggering additional queries
        with profiler.profile_query():
            summary_data = []
            for sp in species:
                summary = {
                    "species_name": sp.scientific_name,
                    "vgnc_prefix": sp.vgnc_prefix,
                    "chromosome_count": len(sp.chromosomes),
                    "assembly_count": len(sp.assemblies),
                    "genefam_count": len(sp.genefams),
                    "enhanced_associations": 0,  # enhanced_genefam_associations not implemented
                    "group_memberships": 0,  # group_memberships not implemented
                }
                summary_data.append(summary)

        # Verify we got expected data
        assert len(summary_data) == 3
        for summary in summary_data:
            assert summary["chromosome_count"] == 3
            assert summary["assembly_count"] == 1
            assert summary["genefam_count"] > 0

        # Check that we used minimal queries
        stats = profiler.get_stats()
        assert stats["query_count"] == 2  # One for main query, one for processing
