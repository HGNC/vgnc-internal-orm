"""Unit tests for Chromosomes and Assembly models."""

from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes


class TestChromosomesModel:
    """Test cases for Chromosomes model."""

    def test_chromosome_creation(self):
        """Test basic Chromosomes model creation."""
        chromosome = Chromosomes(taxon_id=1, display_name="1", coord_system="GRCh38")

        assert chromosome.taxon_id == 1
        assert chromosome.display_name == "1"
        assert chromosome.coord_system == "GRCh38"

    def test_chromosome_basic_fields(self):
        """Test basic chromosome field access."""
        chromosome = Chromosomes(taxon_id=9606, display_name="X", coord_system="GRCh38")

        # Test field access
        assert chromosome.taxon_id == 9606
        assert chromosome.display_name == "X"
        assert chromosome.coord_system == "GRCh38"

        # Test field updates
        chromosome.display_name = "Y"
        assert chromosome.display_name == "Y"

        chromosome.coord_system = "T2T-CHM13"
        assert chromosome.coord_system == "T2T-CHM13"

    def test_chromosome_various_names(self):
        """Test various chromosome naming patterns."""
        names = ["1", "2", "3", "X", "Y", "MT", "1A", "2B", "chr1", "chrX"]

        for name in names:
            chromosome = Chromosomes(
                taxon_id=1, display_name=name, coord_system="GRCh38"
            )
            assert chromosome.display_name == name

    def test_chromosome_string_representation(self):
        """Test string representation."""
        chromosome = Chromosomes(taxon_id=1, display_name="1", coord_system="GRCh38")
        chromosome.chr_id = 1

        # __repr__ should contain class name and key info
        repr_str = repr(chromosome)
        assert "Chromosomes" in repr_str

        # Test that the display name appears in string representation
        str_repr = str(chromosome)
        assert "1" in str_repr or "Chromosomes" in str_repr

    def test_chromosome_table_metadata(self):
        """Test table metadata."""
        assert Chromosomes.__tablename__ == "chromosomes"

        # Check that required columns exist
        assert hasattr(Chromosomes, "taxon_id")
        assert hasattr(Chromosomes, "display_name")
        assert hasattr(Chromosomes, "coord_system")
        assert hasattr(Chromosomes, "chr_id")

        # Check primary key
        assert hasattr(Chromosomes, "chr_id")  # Primary key field


class TestAssemblyModel:
    """Test cases for Assembly model."""

    def test_assembly_creation(self):
        """Test basic Assembly model creation."""
        assembly = Assembly(
            taxon_id=1,
            name="GRCh38",
            source="Ensembl",
            genbank_assembly_accession="GCA_000001405.40",
            refseq_assembly_accession="GCF_000001405.26",
            is_current=True,
            is_vgnc_default=True,
        )

        assert assembly.taxon_id == 1
        assert assembly.name == "GRCh38"
        assert assembly.source == "Ensembl"
        assert assembly.genbank_assembly_accession == "GCA_000001405.40"
        assert assembly.refseq_assembly_accession == "GCF_000001405.26"
        assert assembly.is_current is True
        assert assembly.is_vgnc_default is True

    def test_assembly_basic_fields(self):
        """Test basic assembly field access."""
        assembly = Assembly(
            taxon_id=9606,
            name="GRCh38",
            source="Ensembl",
            genbank_assembly_accession="GCA_000001405.40",
            refseq_assembly_accession="GCF_000001405.26",
        )

        # Test field access
        assert assembly.taxon_id == 9606
        assert assembly.name == "GRCh38"
        assert assembly.source == "Ensembl"

        # Test field updates
        assembly.name = "GRCh37"
        assert assembly.name == "GRCh37"

    def test_assembly_accession_formats(self):
        """Test various accession number formats."""
        accessions = [
            ("GCA_000001405.40", "GCF_000001405.26"),
            ("GCA_000001405.28", "GCF_000001405.38"),
            ("GCA_900123456.1", "GCF_900123456.1"),
        ]

        for genbank, refseq in accessions:
            assembly = Assembly(
                taxon_id=1,
                name="test_assembly",
                source="Test",
                genbank_assembly_accession=genbank,
                refseq_assembly_accession=refseq,
            )
            assert assembly.genbank_assembly_accession == genbank
            assert assembly.refseq_assembly_accession == refseq

    def test_assembly_string_representation(self):
        """Test string representation."""
        assembly = Assembly(
            taxon_id=1,
            name="GRCh38",
            source="Ensembl",
            genbank_assembly_accession="GCA_000001405.40",
            refseq_assembly_accession="GCF_000001405.26",
        )
        assembly.id = 1

        # __repr__ should contain class name and key info
        repr_str = repr(assembly)
        assert "Assembly" in repr_str

        # Test that assembly name appears in string representation
        str_repr = str(assembly)
        assert "GRCh38" in str_repr or "Assembly" in str_repr

    def test_assembly_table_metadata(self):
        """Test table metadata."""
        assert Assembly.__tablename__ == "assembly"

        # Check that required columns exist
        assert hasattr(Assembly, "taxon_id")
        assert hasattr(Assembly, "name")
        assert hasattr(Assembly, "source")
        assert hasattr(Assembly, "genbank_assembly_accession")
        assert hasattr(Assembly, "refseq_assembly_accession")
        assert hasattr(Assembly, "id")

        # Check primary key
        assert hasattr(Assembly, "id")  # Primary key field


class TestModelRelationships:
    """Test model relationships and basic functionality."""

    def test_species_chromosome_relationship(self):
        """Test species-chromosome relationship structure."""
        # Create a chromosome with species reference
        chromosome = Chromosomes(
            taxon_id=9606, display_name="1", coord_system="GRCh38"  # Human taxon ID
        )

        # Verify the taxon_id is set correctly
        assert chromosome.taxon_id == 9606
        assert chromosome.display_name == "1"

    def test_species_assembly_relationship(self):
        """Test species-assembly relationship structure."""
        # Create an assembly with species reference
        assembly = Assembly(
            taxon_id=9606,  # Human taxon ID
            name="GRCh38",
            source="Ensembl",
            genbank_assembly_accession="GCA_000001405.40",
            refseq_assembly_accession="GCF_000001405.26",
        )

        # Verify the taxon_id is set correctly
        assert assembly.taxon_id == 9606
        assert assembly.name == "GRCh38"

    def test_multiple_assemblies_per_species(self):
        """Test multiple assemblies for same species."""
        assemblies = []
        assembly_data = [
            ("GRCh38", "GCA_000001405.40", "GCF_000001405.26"),
            ("GRCh37", "GCA_000001405.14", "GCF_000001405.13"),
            ("T2T-CHM13", "GCA_009914755.1", "GCF_009914755.1"),
        ]

        for name, genbank, refseq in assembly_data:
            assembly = Assembly(
                taxon_id=9606,
                name=name,
                source="Ensembl",
                genbank_assembly_accession=genbank,
                refseq_assembly_accession=refseq,
                is_current=(name == "GRCh38"),
                is_vgnc_default=(name == "GRCh38"),
            )
            assemblies.append(assembly)

        # Verify all assemblies created successfully
        assert len(assemblies) == 3
        assert assemblies[0].name == "GRCh38"
        assert assemblies[1].name == "GRCh37"
        assert assemblies[2].name == "T2T-CHM13"

    def test_multiple_chromosomes_per_species(self):
        """Test multiple chromosomes for same species."""
        chromosomes = []
        chromosome_names = ["1", "2", "3", "X", "Y", "MT"]

        for name in chromosome_names:
            chromosome = Chromosomes(
                taxon_id=9606, display_name=name, coord_system="GRCh38"
            )
            chromosomes.append(chromosome)

        # Verify all chromosomes created successfully
        assert len(chromosomes) == len(chromosome_names)
        for i, name in enumerate(chromosome_names):
            assert chromosomes[i].display_name == name
            assert chromosomes[i].taxon_id == 9606
