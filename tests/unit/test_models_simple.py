"""
Simple unit tests for core models using the new testing framework.

Tests the basic functionality of Species, Assembly, and Chromosomes models
without complex foreign key dependencies.
"""

from datetime import datetime

import pytest

from tests.unit.base_test import BaseUnitTest, ModelTestMixin, DatabaseTestMixin
from src.vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from src.vgnc_internal_orm.models.assembly import Assembly
from src.vgnc_internal_orm.models.chromosomes import Chromosomes


class TestSpecies(BaseUnitTest, ModelTestMixin, DatabaseTestMixin):
    """Simple tests for Species model."""

    model_class = Species
    sample_data = {
        "taxon_id": 9606,
        "genefam_prefix": "HSA",
        "display_name": "human (Homo sapiens)",
        "is_live": SpeciesLiveStatus.YES,
        "created": datetime.now(),
    }
    required_fields = ["taxon_id", "genefam_prefix", "display_name", "is_live"]

    def test_species_creation(self):
        """Test basic species creation."""
        species = self.create_instance()
        assert species.taxon_id == 9606
        assert species.genefam_prefix == "HSA"
        assert species.is_live == SpeciesLiveStatus.YES

    def test_species_crud_operations(self):
        """Test CRUD operations for species."""
        self.test_crud_operations()

    def test_species_table_creation(self):
        """Test that species table is created correctly."""
        self.test_table_creation()

    def test_species_table_columns(self):
        """Test that species table has expected columns."""
        self.test_table_columns()


class TestAssembly(BaseUnitTest, ModelTestMixin, DatabaseTestMixin):
    """Simple tests for Assembly model."""

    model_class = Assembly
    sample_data = {
        "name": "GRCh38",
        "taxon_id": 9606,  # Will be overridden in actual test
        "source": "Ensembl",
        "genbank_assembly_accession": "GCA_000001405.28",
        "refseq_assembly_accession": "GCF_000001405.38",
        "is_current": True,
        "is_vgnc_default": True,
    }
    required_fields = ["name", "taxon_id", "source", "genbank_assembly_accession", "refseq_assembly_accession", "is_current", "is_vgnc_default"]

    @pytest.fixture(autouse=True)
    def setup_species(self, sample_species):
        """Setup a species for assembly tests."""
        self.species = sample_species
        # Update sample_data to use real species taxon_id
        self.sample_data["taxon_id"] = self.species.taxon_id

    def test_assembly_creation(self):
        """Test basic assembly creation."""
        assembly = self.create_instance()
        assert assembly.name == "GRCh38"
        assert assembly.taxon_id == self.species.taxon_id

    def test_assembly_crud_operations(self):
        """Test CRUD operations for assembly."""
        self.test_crud_operations()

    def test_assembly_table_creation(self):
        """Test that assembly table is created correctly."""
        self.test_table_creation()

    def test_assembly_table_columns(self):
        """Test that assembly table has expected columns."""
        self.test_table_columns()


class TestChromosomes(BaseUnitTest, ModelTestMixin, DatabaseTestMixin):
    """Simple tests for Chromosomes model."""

    model_class = Chromosomes
    sample_data = {
        "display_name": "chr1",
        "taxon_id": 9606,  # Will be overridden in actual test
        "coord_system": "GRCh38",
    }
    required_fields = ["display_name", "taxon_id"]

    @pytest.fixture(autouse=True)
    def setup_species(self, sample_species):
        """Setup a species for chromosome tests."""
        self.species = sample_species
        # Update sample_data to use real species taxon_id
        self.sample_data["taxon_id"] = self.species.taxon_id

    def test_chromosome_creation(self):
        """Test basic chromosome creation."""
        chromosome = self.create_instance()
        assert chromosome.display_name == "chr1"
        assert chromosome.taxon_id == self.species.taxon_id
        assert chromosome.coord_system == "GRCh38"

    def test_chromosome_crud_operations(self):
        """Test CRUD operations for chromosomes."""
        self.test_crud_operations()

    def test_chromosome_table_creation(self):
        """Test that chromosomes table is created correctly."""
        self.test_table_creation()

    def test_chromosome_table_columns(self):
        """Test that chromosomes table has expected columns."""
        self.test_table_columns()


class TestModelRelationships:
    """Simple tests for model relationships."""

    def test_species_with_assemblies(self, test_db_session, sample_species):
        """Test species with multiple assemblies."""
        # Create assemblies for the species
        assemblies = []
        for i in range(3):
            assembly_data = {
                "name": f"assembly_{i}",
                "taxon_id": sample_species.taxon_id,
                "source": "Test Source",
                "genbank_assembly_accession": f"GCA_{i:010d}",
                "refseq_assembly_accession": f"GCF_{i:010d}",
                "is_current": i == 0,  # Only first one is current
                "is_vgnc_default": i == 0,  # Only first one is VGNC default
            }
            assembly = Assembly(**assembly_data)
            test_db_session.add(assembly)
            assemblies.append(assembly)

        test_db_session.commit()

        # Verify assemblies are linked to the species
        count = test_db_session.query(Assembly).filter(
            Assembly.taxon_id == sample_species.taxon_id
        ).count()
        assert count == 3

    def test_species_with_chromosomes(self, test_db_session, sample_species):
        """Test species with multiple chromosomes."""
        # Create chromosomes for the species
        chromosome_names = ["chr1", "chr2", "chrX"]

        for name in chromosome_names:
            chr_data = {
                "display_name": name,
                "taxon_id": sample_species.taxon_id,
                "coord_system": "TestCoordSystem",
            }
            chromosome = Chromosomes(**chr_data)
            test_db_session.add(chromosome)

        test_db_session.commit()

        # Verify count
        count = test_db_session.query(Chromosomes).filter(
            Chromosomes.taxon_id == sample_species.taxon_id
        ).count()
        assert count == len(chromosome_names)


class TestModelQueries:
    """Simple tests for model queries."""

    def test_species_queries(self, test_db_session):
        """Test various species queries."""
        # Create test species
        species_data = [
            {"taxon_id": 9606, "genefam_prefix": "HSA", "display_name": "human"},
            {"taxon_id": 10090, "genefam_prefix": "MMU", "display_name": "mouse"},
        ]

        for data in species_data:
            species = Species(
                **data,
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            test_db_session.add(species)

        test_db_session.commit()

        # Test queries
        hsa_species = test_db_session.query(Species).filter(
            Species.genefam_prefix == "HSA"
        ).first()
        assert hsa_species is not None
        assert hsa_species.display_name == "human"

        all_species = test_db_session.query(Species).all()
        assert len(all_species) == 2

    def test_assembly_queries(self, test_db_session, sample_species):
        """Test assembly queries."""
        # Create assemblies
        for i in range(3):
            assembly = Assembly(
                name=f"assembly_{i}",
                taxon_id=sample_species.taxon_id,
                source="Test Source",
                genbank_assembly_accession=f"GCA_{i:010d}",
                refseq_assembly_accession=f"GCF_{i:010d}",
                is_current=i == 0,  # Only first one is current
                is_vgnc_default=i == 0,  # Only first one is VGNC default
            )
            test_db_session.add(assembly)

        test_db_session.commit()

        # Query by species
        assemblies = test_db_session.query(Assembly).filter(
            Assembly.taxon_id == sample_species.taxon_id
        ).all()
        assert len(assemblies) == 3

    def test_chromosome_queries(self, test_db_session, sample_species):
        """Test chromosome queries."""
        # Create chromosomes with different names
        names = ["chr1", "chr2", "chrX"]

        for name in names:
            chromosome = Chromosomes(
                display_name=name,
                taxon_id=sample_species.taxon_id,
                coord_system="TestCoordSystem",
            )
            test_db_session.add(chromosome)

        test_db_session.commit()

        # Query by coord system
        test_chromosomes = test_db_session.query(Chromosomes).filter(
            Chromosomes.coord_system == "TestCoordSystem"
        ).all()
        assert len(test_chromosomes) == len(names)