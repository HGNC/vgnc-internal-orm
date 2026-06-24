"""
Basic unit tests to validate the unit testing framework functionality.

These tests verify that the SQLite in-memory database setup,
fixtures, and basic model operations work correctly.
"""

from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes
from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus


class TestSpeciesBasic:
    """Basic tests for Species model."""

    def test_species_creation_simple(self, test_db_session):
        """Test basic species creation."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HSA",
            display_name="human (Homo sapiens)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        )

        test_db_session.add(species)
        test_db_session.commit()
        test_db_session.refresh(species)

        assert species.taxon_id == 9606
        assert species.genefam_prefix == "HSA"
        assert species.is_live == SpeciesLiveStatus.YES
        assert species.created is not None

    def test_species_query(self, test_db_session):
        """Test querying species."""
        # Create a species
        species = Species(
            taxon_id=10090,
            genefam_prefix="MMU",
            display_name="mouse",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        )
        test_db_session.add(species)
        test_db_session.commit()

        # Query it back
        found = test_db_session.query(Species).filter(Species.taxon_id == 10090).first()
        assert found is not None
        assert found.genefam_prefix == "MMU"

    def test_species_unique_constraint(self, test_db_session):
        """Test species unique constraint on taxon_id."""
        species1 = Species(
            taxon_id=9606,
            genefam_prefix="HSA",
            display_name="human",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        )
        test_db_session.add(species1)
        test_db_session.commit()
        test_db_session.expunge_all()  # Clear session to avoid instance conflict

        # Try to create another species with same taxon_id
        species2 = Species(
            taxon_id=9606,  # Same taxon_id
            genefam_prefix="HSA2",
            display_name="human2",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        )

        with pytest.raises(IntegrityError):  # Should raise integrity error
            test_db_session.add(species2)
            test_db_session.commit()
            test_db_session.expunge_all()  # Clean up after test


class TestAssemblyBasic:
    """Basic tests for Assembly model."""

    def test_assembly_creation(self, test_db_session, sample_species):
        """Test basic assembly creation."""
        assembly = Assembly(
            name="GRCh38",
            taxon_id=sample_species.taxon_id,
            source="Ensembl",
            genbank_assembly_accession="GCA_000001405.28",
            refseq_assembly_accession="GCF_000001405.38",
            is_current=True,
            is_vgnc_default=True,
        )

        test_db_session.add(assembly)
        test_db_session.commit()
        test_db_session.refresh(assembly)

        assert assembly.name == "GRCh38"
        assert assembly.taxon_id == sample_species.taxon_id
        assert assembly.source == "Ensembl"
        assert assembly.id is not None

    def test_assembly_foreign_key(self, test_db_session, sample_species):
        """Test assembly foreign key to species."""
        assembly = Assembly(
            name="test_assembly",
            taxon_id=sample_species.taxon_id,
            source="NCBI",
            genbank_assembly_accession="GCA_000001405.28",
            refseq_assembly_accession="GCF_000001405.38",
            is_current=False,  # Different from first assembly
            is_vgnc_default=False,
        )
        test_db_session.add(assembly)
        test_db_session.commit()

        # Verify the foreign key relationship
        assert assembly.taxon_id == sample_species.taxon_id

    def test_assembly_invalid_species(self, test_db_session):
        """Test assembly with invalid species_id."""
        assembly = Assembly(
            name="test_assembly",
            taxon_id=99999,  # Non-existent species
            source="NCBI",
        )

        # This might not fail until commit depending on foreign key constraints
        test_db_session.add(assembly)

        with pytest.raises(IntegrityError):  # Should raise foreign key constraint error
            test_db_session.commit()


class TestChromosomesBasic:
    """Basic tests for Chromosomes model."""

    def test_chromosome_creation(self, test_db_session, sample_species):
        """Test basic chromosome creation."""
        chromosome = Chromosomes(
            display_name="chr1",
            taxon_id=sample_species.taxon_id,
        )

        test_db_session.add(chromosome)
        test_db_session.commit()
        test_db_session.refresh(chromosome)

        assert chromosome.display_name == "chr1"
        assert chromosome.taxon_id == sample_species.taxon_id
        assert chromosome.chr_id is not None

    def test_chromosome_foreign_key(self, test_db_session, sample_species):
        """Test chromosome foreign key to species."""
        chromosome = Chromosomes(
            display_name="chrX",
            taxon_id=sample_species.taxon_id,
        )
        test_db_session.add(chromosome)
        test_db_session.commit()

        # Verify the foreign key relationship
        assert chromosome.taxon_id == sample_species.taxon_id

    def test_chromosome_multiple_per_species(self, test_db_session, sample_species):
        """Test multiple chromosomes for one species."""
        chromosome_names = ["chr1", "chr2", "chrX", "chrY"]

        for name in chromosome_names:
            chromosome = Chromosomes(
                display_name=name,
                taxon_id=sample_species.taxon_id,
            )
            test_db_session.add(chromosome)

        test_db_session.commit()

        # Verify count
        count = (
            test_db_session.query(Chromosomes)
            .filter(Chromosomes.taxon_id == sample_species.taxon_id)
            .count()
        )
        assert count == len(chromosome_names)


class TestTableCreation:
    """Test that tables are created correctly."""

    def test_species_table_exists(self, test_db_session):
        """Test that species table exists."""
        # Simple query to verify table exists
        result = test_db_session.execute(
            text("SELECT name FROM sqlite_master WHERE type='table' AND name='species'")
        )
        tables = [row[0] for row in result]
        assert "species" in tables

    def test_assembly_table_exists(self, test_db_session):
        """Test that assembly table exists."""
        result = test_db_session.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='assembly'"
            )
        )
        tables = [row[0] for row in result]
        assert "assembly" in tables

    def test_chromosomes_table_exists(self, test_db_session):
        """Test that chromosomes table exists."""
        result = test_db_session.execute(
            text(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='chromosomes'"
            )
        )
        tables = [row[0] for row in result]
        assert "chromosomes" in tables


class TestQueryOperations:
    """Test various query operations."""

    def test_filter_by_enum(self, test_db_session):
        """Test filtering by enum values."""
        # Create species with different statuses
        statuses = [
            SpeciesLiveStatus.YES,
            SpeciesLiveStatus.NO,
            SpeciesLiveStatus.TESTING,
        ]

        for i, status in enumerate(statuses):
            species = Species(
                taxon_id=1000 + i,
                genefam_prefix=f"TEST{i}",
                display_name=f"Test species {i}",
                is_live=status,
                created=datetime.now(),
            )
            test_db_session.add(species)

        test_db_session.commit()

        # Query by specific status
        live_species = (
            test_db_session.query(Species)
            .filter(Species.is_live == SpeciesLiveStatus.YES)
            .all()
        )
        assert len(live_species) == 1
        assert live_species[0].is_live == SpeciesLiveStatus.YES

    def test_order_by_operations(self, test_db_session, sample_species):
        """Test ORDER BY operations."""
        # Create chromosomes with different display names
        names = ["chrA", "chrB", "chrC", "chrD"]

        for name in names:
            chromosome = Chromosomes(
                display_name=name,
                taxon_id=sample_species.taxon_id,
                coord_system="test_coord_system",
            )
            test_db_session.add(chromosome)

        test_db_session.commit()

        # Query ordered by display_name
        ordered = (
            test_db_session.query(Chromosomes)
            .order_by(Chromosomes.display_name.asc())
            .all()
        )

        # Verify order
        assert ordered[0].display_name == "chrA"
        assert ordered[1].display_name == "chrB"
        assert ordered[2].display_name == "chrC"
        assert ordered[3].display_name == "chrD"

    def test_aggregate_functions(self, test_db_session, sample_species):
        """Test aggregate functions."""
        # Create multiple chromosomes
        for i in range(5):
            chromosome = Chromosomes(
                display_name=f"chr_{i}",
                taxon_id=sample_species.taxon_id,
                coord_system="test_coord_system",
            )
            test_db_session.add(chromosome)

        test_db_session.commit()

        # Test count
        from sqlalchemy import func

        count = (
            test_db_session.query(func.count(Chromosomes.chr_id))
            .filter(Chromosomes.taxon_id == sample_species.taxon_id)
            .scalar()
        )
        assert count == 5
