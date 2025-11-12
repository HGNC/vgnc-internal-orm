"""Comprehensive database-integrated tests for Chromosomes model functionality."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import text, sessionmaker

from src.vgnc_internal_orm.models.chromosomes import Chromosomes
from src.vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from src.vgnc_internal_orm.sessions.factory import DatabaseFactory
from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestChromosomesModelComprehensive:
    """Comprehensive database-integrated tests for Chromosomes model."""

    def setup_method(self):
        """Set up test database and session."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables for both Species and Chromosomes
        from src.vgnc_internal_orm.models.base import BaseModel
        BaseModel.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

        # Create test species for foreign key relationships
        self.test_species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human (Homo sapiens)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )
        self.session.add(self.test_species)
        self.session.commit()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_chromosomes_crud_operations_complete(self):
        """Test complete CRUD operations for Chromosomes model."""
        # Create
        chromosome = Chromosomes(
            taxon_id=9606,
            display_name="1",
            coord_system="GRCh38",
            refseq_accession="NC_000001.11",
            genbank_accession="CM000663.2",
            ensembl_accession="ENSG00000141510",
            type="autosome",
            assigned_to=1
        )

        self.session.add(chromosome)
        self.session.commit()

        # Verify creation
        assert chromosome.chr_id is not None
        assert chromosome.taxon_id == 9606
        assert chromosome.display_name == "1"
        assert chromosome.coord_system == "GRCh38"
        assert chromosome.type == "autosome"

        # Read
        retrieved = self.session.query(Chromosomes).filter_by(chr_id=chromosome.chr_id).first()
        assert retrieved is not None
        assert retrieved.display_name == "1"
        assert retrieved.coord_system == "GRCh38"

        # Update
        retrieved.coord_system = "GRCh37"
        retrieved.type = "reference"
        retrieved.assigned_to = 2
        self.session.commit()

        # Verify update
        updated = self.session.query(Chromosomes).filter_by(chr_id=chromosome.chr_id).first()
        assert updated.coord_system == "GRCh37"
        assert updated.type == "reference"
        assert updated.assigned_to == 2

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(Chromosomes).filter_by(chr_id=chromosome.chr_id).first()
        assert deleted is None

    def test_chromosomes_naming_patterns_comprehensive(self):
        """Test Chromosomes model with all valid naming patterns."""
        valid_names = [
            # Standard numeric
            "1", "2", "3", "10", "21", "22",
            # With chr prefix
            "chr1", "chr2", "chr3", "chr10", "chrX", "chrY", "chrMT",
            # Sex chromosomes
            "X", "Y", "MT",
            # Full names
            "Chromosome 1", "Chromosome 2", "Chromosome X", "Chromosome Y", "Chromosome MT",
            # With letters
            "1A", "2B", "chr1A", "chr2B",
            # Test patterns (for test data)
            "chrA", "chrB", "chr0",
            # Unassembled regions
            "Un", "Un1", "Un2",
            "scaffold_1", "scaffold_2",
            "contig_1", "contig_2",
            "patch_1", "patch_2",
            # Simplified patterns (should also work)
            "test_chr1", "test_chrX", "chr_test_1",
        ]

        for name in valid_names:
            chromosome = Chromosomes(
                taxon_id=9606,
                display_name=name,
                genbank_accession=f"GCA_{len(name):03d}.1"
            )
            self.session.add(chromosome)

        self.session.commit()

        # Verify all names were accepted
        for name in valid_names:
            retrieved = self.session.query(Chromosomes).filter_by(display_name=name).first()
            assert retrieved is not None
            assert retrieved.display_name == name

    def test_chromosomes_invalid_naming_patterns(self):
        """Test Chromosomes model with invalid naming patterns."""
        invalid_names = [
            "",  # Empty
            " ",  # Whitespace only
            "invalid_chromosome_name",  # Too complex
            "chr!!!",  # Invalid characters
            "123abc456",  # Too complex
            "@#$%",  # Special characters only
        ]

        for name in invalid_names:
            with pytest.raises(ValueError, match="display_name: Chromosome name must follow standard naming pattern"):
                Chromosomes(
                    taxon_id=9606,
                    display_name=name,
                    genbank_accession="GCA_INVALID.1"
                )

    def test_chromosomes_property_accessors_comprehensive(self):
        """Test all Chromosomes model property accessors."""
        # Test with full accession data
        chromosome_full = Chromosomes(
            taxon_id=9606,
            display_name="1",
            coord_system="GRCh38",
            refseq_accession="NC_000001.11",
            genbank_accession="CM000663.2",
            ensembl_accession="ENSG00000141510",
            type="autosome"
        )

        # Test name property
        assert chromosome_full.name == "1"

        # Test primary_accession property (RefSeq preferred)
        assert chromosome_full.primary_accession == "NC_000001.11"

        # Test chromosome_number property
        assert chromosome_full.chromosome_number == "1"

        # Test with different naming patterns
        test_cases = [
            ("chr1", "1"),
            ("Chromosome 1", "1"),
            ("chrX", "X"),
            ("Chromosome X", "X"),
            ("chrY", "Y"),
            ("chrMT", "MT"),
            ("10", "10"),
            ("chr10", "10"),
        ]

        for display_name, expected_number in test_cases:
            chromosome = Chromosomes(
                taxon_id=9606,
                display_name=display_name,
                genbank_accession="GCA_TEST.1"
            )
            assert chromosome.chromosome_number == expected_number

        # Test primary_accession priority (RefSeq > GenBank > Ensembl)
        chromosome_refseq = Chromosomes(
            taxon_id=9606,
            display_name="2",
            refseq_accession="NC_000002.12",
            genbank_accession="CM000664.1",
            ensembl_accession="ENSG00000171862"
        )
        assert chromosome_refseq.primary_accession == "NC_000002.12"

        chromosome_genbank = Chromosomes(
            taxon_id=9606,
            display_name="3",
            refseq_accession=None,
            genbank_accession="CM000665.1",
            ensembl_accession="ENSG00000141510"
        )
        assert chromosome_genbank.primary_accession == "CM000665.1"

        chromosome_ensembl = Chromosomes(
            taxon_id=9606,
            display_name="4",
            refseq_accession=None,
            genbank_accession="",
            ensembl_accession="ENSG00000141510"
        )
        assert chromosome_ensembl.primary_accession == "ENSG00000141510"

        chromosome_none = Chromosomes(
            taxon_id=9606,
            display_name="5",
            refseq_accession=None,
            genbank_accession="",
            ensembl_accession=None
        )
        assert chromosome_none.primary_accession == ""

        # Test species properties (without relationship)
        chromosome_no_species = Chromosomes(
            taxon_id=9999,  # Non-existent species
            display_name="chrX",
            genbank_accession="GCA_TEST.1"
        )

        assert chromosome_no_species.species_name == "Unknown"
        assert chromosome_no_species.full_identifier == "chrX"

    def test_chromosomes_relationship_with_species(self):
        """Test Chromosomes relationship with Species."""
        # Create chromosome with species relationship
        chromosome = Chromosomes(
            taxon_id=9606,
            display_name="chr1",
            coord_system="GRCh38",
            refseq_accession="NC_000001.11",
            genbank_accession="CM000663.2",
            type="autosome"
        )

        self.session.add(chromosome)
        self.session.commit()

        # Test relationship access
        assert chromosome.species is not None
        assert chromosome.species.taxon_id == 9606
        assert chromosome.species.display_name == "Human (Homo sapiens)"

        # Test properties with species relationship
        assert chromosome.species_name == "Human (Homo sapiens)"
        assert chromosome.full_identifier == "HS:chr1"

    def test_chromosomes_to_dict_comprehensive(self):
        """Test Chromosomes to_dict method with all fields."""
        chromosome = Chromosomes(
            taxon_id=9606,
            display_name="1",
            coord_system="GRCh38",
            refseq_accession="NC_000001.11",
            genbank_accession="CM000663.2",
            ensembl_accession="ENSG00000141510",
            type="autosome",
            assigned_to=1
        )

        self.session.add(chromosome)
        self.session.commit()

        # Test to_dict
        result = chromosome.to_dict()
        assert isinstance(result, dict)

        # Check all expected fields
        expected_fields = [
            "chr_id", "taxon_id", "display_name", "coord_system",
            "refseq_accession", "genbank_accession", "ensembl_accession",
            "type", "assigned_to",
            "name", "species_name", "primary_accession",
            "chromosome_number", "full_identifier"
        ]

        for field in expected_fields:
            assert field in result

        # Check values
        assert result["taxon_id"] == 9606
        assert result["display_name"] == "1"
        assert result["coord_system"] == "GRCh38"
        assert result["refseq_accession"] == "NC_000001.11"
        assert result["genbank_accession"] == "CM000663.2"
        assert result["ensembl_accession"] == "ENSG00000141510"
        assert result["type"] == "autosome"
        assert result["assigned_to"] == 1
        assert result["name"] == "1"
        assert result["primary_accession"] == "NC_000001.11"
        assert result["chromosome_number"] == "1"
        assert result["full_identifier"] == "1"  # No species relationship loaded

    def test_chromosomes_field_utilities_comprehensive(self):
        """Test BaseModel field utilities with Chromosomes."""
        chromosome = Chromosomes(
            taxon_id=9606,
            display_name="chrX",
            coord_system="GRCh38",
            refseq_accession="NC_000023.11",
            genbank_accession="CM000673.2",
            type="sex_chromosome",
            assigned_to=23
        )

        # Test get_field_value
        assert chromosome.get_field_value("chr_id") is not None  # Will be set after save
        assert chromosome.get_field_value("taxon_id") == 9606
        assert chromosome.get_field_value("display_name") == "chrX"
        assert chromosome.get_field_value("coord_system") == "GRCh38"
        assert chromosome.get_field_value("type") == "sex_chromosome"
        assert chromosome.get_field_value("assigned_to") == 23
        assert chromosome.get_field_value("nonexistent") is None

        # Test set_field_value
        chromosome.set_field_value("coord_system", "GRCh37")
        assert chromosome.coord_system == "GRCh37"

        chromosome.set_field_value("type", "reference")
        assert chromosome.type == "reference"

        chromosome.set_field_value("assigned_to", 99)
        assert chromosome.assigned_to == 99

        # Test has_field
        assert chromosome.has_field("chr_id") is True
        assert chromosome.has_field("taxon_id") is True
        assert chromosome.has_field("display_name") is True
        assert chromosome.has_field("coord_system") is True
        assert chromosome.has_field("nonexistent") is False

        # Test get_field_type
        assert chromosome.get_field_type("chr_id") == int
        assert chromosome.get_field_type("taxon_id") == int
        assert chromosome.get_field_type("display_name") == str
        assert chromosome.get_field_type("coord_system") == str
        assert chromosome.get_field_type("type") == str
        assert chromosome.get_field_type("assigned_to") == int

    def test_chromosomes_class_methods_comprehensive(self):
        """Test Chromosomes class methods."""
        # Test get_table_name
        assert Chromosomes.get_table_name() == "chromosomes"

        # Test get_column_names
        columns = Chromosomes.get_column_names()
        assert "chr_id" in columns
        assert "taxon_id" in columns
        assert "display_name" in columns
        assert "coord_system" in columns
        assert "refseq_accession" in columns
        assert "genbank_accession" in columns
        assert "ensembl_accession" in columns
        assert "type" in columns
        assert "assigned_to" in columns

        # Test get_primary_key_columns
        pk_columns = Chromosomes.get_primary_key_columns()
        assert pk_columns == ["chr_id"]

        # Test has_column
        assert Chromosomes.has_column("chr_id") is True
        assert Chromosomes.has_column("taxon_id") is True
        assert Chromosomes.has_column("display_name") is True
        assert Chromosomes.has_column("nonexistent") is False

        # Test get_column_type
        assert Chromosomes.get_column_type("chr_id") == int
        assert Chromosomes.get_column_type("taxon_id") == int
        assert Chromosomes.get_column_type("display_name") == str
        assert Chromosomes.get_column_type("coord_system") == str
        assert Chromosomes.get_column_type("type") == str
        assert Chromosomes.get_column_type("assigned_to") == int

    def test_chromosomes_edge_cases_comprehensive(self):
        """Test Chromosomes model edge cases."""
        # Test chromosome with minimal required fields
        minimal_chromosome = Chromosomes(
            taxon_id=9606,
            display_name="chrM",
            genbank_accession="GCA_MIN.1"
        )

        self.session.add(minimal_chromosome)
        self.session.commit()

        assert minimal_chromosome.chr_id is not None
        assert minimal_chromosome.coord_system is None
        assert minimal_chromosome.refseq_accession is None
        assert minimal_chromosome.ensembl_accession is None
        assert minimal_chromosome.type is None
        assert minimal_chromosome.assigned_to is None

        # Test chromosome with maximum length strings
        max_chromosome = Chromosomes(
            taxon_id=9606,
            display_name="chr" + "x" * 125,  # Near max length
            coord_system="x" * 128,  # max length
            refseq_accession="y" * 128,  # max length
            genbank_accession="z" * 128,  # max length
            ensembl_accession="w" * 128,  # max length
            type="x" * 128  # max length
        )

        self.session.add(max_chromosome)
        self.session.commit()

        assert max_chromosome.coord_system == "x" * 128
        assert max_chromosome.refseq_accession == "y" * 128

        # Test chromosome with empty string defaults
        empty_chromosome = Chromosomes(
            taxon_id=9606,
            display_name="chrUn",
            genbank_accession=""  # Empty string (default)
        )

        self.session.add(empty_chromosome)
        self.session.commit()

        assert empty_chromosome.genbank_accession == ""
        assert empty_chromosome.primary_accession == ""  # All accessions empty

    def test_chromosomes_foreign_key_constraints(self):
        """Test Chromosomes foreign key constraints."""
        # Test valid foreign key
        valid_chromosome = Chromosomes(
            taxon_id=9606,  # Valid species ID
            display_name="chr1",
            genbank_accession="GCA_VALID.1"
        )

        self.session.add(valid_chromosome)
        self.session.commit()
        assert valid_chromosome.chr_id is not None

        # Test invalid foreign key
        invalid_chromosome = Chromosomes(
            taxon_id=99999,  # Non-existent species ID
            display_name="chr1",
            genbank_accession="GCA_INVALID.1"
        )

        self.session.add(invalid_chromosome)

        # SQLite may not enforce foreign key constraints by default
        # but this tests the relationship structure
        try:
            self.session.commit()
        except Exception as e:
            # Foreign key constraint violation (if enabled)
            assert "foreign key" in str(e).lower() or "constraint" in str(e).lower()
        else:
            # If no constraint enforcement, at least test the relationship access
            assert invalid_chromosome.species is None

    def test_chromosomes_bulk_operations(self):
        """Test Chromosomes bulk operations."""
        # Create multiple chromosomes for bulk testing
        bulk_chromosomes = []
        chromosome_names = ["1", "2", "3", "X", "Y", "MT"]

        for i, name in enumerate(chromosome_names):
            chromosome = Chromosomes(
                taxon_id=9606,
                display_name=f"chr{name}",
                genbank_accession=f"GCA_BULK_{i:03d}.1",
                type="autosome" if name.isdigit() else "sex_chromosome"
            )
            bulk_chromosomes.append(chromosome)

        # Bulk insert
        self.session.add_all(bulk_chromosomes)
        self.session.commit()

        # Verify bulk insert
        count = self.session.query(Chromosomes).filter(
            Chromosomes.display_name.like("chr%")
        ).count()
        assert count == len(chromosome_names)

        # Bulk update
        self.session.query(Chromosomes).filter(
            Chromosomes.display_name.like("chr%")
        ).update({"coord_system": "GRCh37"})
        self.session.commit()

        # Verify bulk update
        updated_count = self.session.query(Chromosomes).filter(
            Chromosomes.display_name.like("chr%"),
            Chromosomes.coord_system == "GRCh37"
        ).count()
        assert updated_count == len(chromosome_names)

        # Bulk delete
        self.session.query(Chromosomes).filter(
            Chromosomes.display_name.like("chr%")
        ).delete()
        self.session.commit()

        # Verify bulk delete
        remaining_count = self.session.query(Chromosomes).filter(
            Chromosomes.display_name.like("chr%")
        ).count()
        assert remaining_count == 0

    def test_chromosomes_query_methods_comprehensive(self):
        """Test Chromosomes query methods and filters."""
        # Create test data with different properties
        test_chromosomes = [
            Chromosomes(taxon_id=9606, display_name="1", genbank_accession="GCA_001", type="autosome"),
            Chromosomes(taxon_id=9606, display_name="X", genbank_accession="GCA_002", type="sex_chromosome"),
            Chromosomes(taxon_id=9606, display_name="Y", genbank_accession="GCA_003", type="sex_chromosome"),
            Chromosomes(taxon_id=9606, display_name="MT", genbank_accession="GCA_004", type="mitochondrial"),
        ]

        for chromosome in test_chromosomes:
            self.session.add(chromosome)
        self.session.commit()

        # Test query by display_name
        chr_x = self.session.query(Chromosomes).filter_by(display_name="X").first()
        assert chr_x is not None
        assert chr_x.display_name == "X"

        # Test query by taxon_id
        human_chromosomes = self.session.query(Chromosomes).filter_by(taxon_id=9606).all()
        assert len(human_chromosomes) == 4

        # Test query by type
        sex_chromosomes = self.session.query(Chromosomes).filter_by(type="sex_chromosome").all()
        assert len(sex_chromosomes) == 2

        # Test complex query patterns
        numeric_chromosomes = self.session.query(Chromosomes).filter(
            Chromosomes.display_name.regexp_match(r'^\d+$')
        ).all()
        assert len(numeric_chromosomes) == 1

        # Test ordering
        ordered_chromosomes = self.session.query(Chromosomes).order_by(Chromosomes.chr_id).all()
        assert ordered_chromosomes[0].chr_id < ordered_chromosomes[-1].chr_id

    def test_chromosomes_repr_method(self):
        """Test Chromosomes __repr__ method."""
        chromosome = Chromosomes(
            taxon_id=9606,
            display_name="chr1",
            genbank_accession="GCA_TEST.1"
        )

        # Test before saving (no ID yet)
        repr_str = repr(chromosome)
        assert "Chromosomes" in repr_str
        assert "display_name='chr1'" in repr_str
        assert "taxon_id=9606" in repr_str

        # Test after saving
        self.session.add(chromosome)
        self.session.commit()

        repr_str = repr(chromosome)
        assert "Chromosomes" in repr_str
        assert str(chromosome.chr_id) in repr_str
        assert "display_name='chr1'" in repr_str

    def test_chromosomes_chromosome_number_edge_cases(self):
        """Test chromosome_number property with edge cases."""
        edge_cases = [
            ("chr1", "1"),
            ("chr10", "10"),
            ("chrX", "X"),
            ("chrY", "Y"),
            ("chrMT", "MT"),
            ("Chromosome 1", "1"),
            ("Chromosome X", "X"),
            ("Un", "Un"),
            ("scaffold_1", "scaffold_1"),  # Should return display_name if no number found
        ]

        for display_name, expected in edge_cases:
            chromosome = Chromosomes(
                taxon_id=9606,
                display_name=display_name,
                genbank_accession="GCA_EDGE.1"
            )
            assert chromosome.chromosome_number == expected