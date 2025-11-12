"""Comprehensive database-integrated tests for Assembly model functionality."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import text, sessionmaker, ForeignKeyConstraint
from sqlalchemy.orm import relationship

from src.vgnc_internal_orm.models.assembly import Assembly
from src.vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from src.vgnc_internal_orm.sessions.factory import DatabaseFactory
from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestAssemblyModelComprehensive:
    """Comprehensive database-integrated tests for Assembly model."""

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

        # Create tables for both Species and Assembly
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

    def test_assembly_crud_operations_complete(self):
        """Test complete CRUD operations for Assembly model."""
        # Create
        assembly = Assembly(
            taxon_id=9606,
            source="Ensembl",
            name="GRCh38",
            genbank_assembly_accession="GCA_000001405.15",
            refseq_assembly_accession="GCF_000001405.26",
            is_current=True,
            is_vgnc_default=True
        )

        self.session.add(assembly)
        self.session.commit()

        # Verify creation
        assert assembly.id is not None
        assert assembly.taxon_id == 9606
        assert assembly.source == "Ensembl"
        assert assembly.name == "GRCh38"
        assert assembly.is_current is True
        assert assembly.is_vgnc_default is True

        # Read
        retrieved = self.session.query(Assembly).filter_by(id=assembly.id).first()
        assert retrieved is not None
        assert retrieved.name == "GRCh38"
        assert retrieved.source == "Ensembl"

        # Update
        retrieved.name = "GRCh38.p13"
        retrieved.is_current = False
        self.session.commit()

        # Verify update
        updated = self.session.query(Assembly).filter_by(id=assembly.id).first()
        assert updated.name == "GRCh38.p13"
        assert updated.is_current is False

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(Assembly).filter_by(id=assembly.id).first()
        assert deleted is None

    def test_assembly_all_sources(self):
        """Test Assembly model with all possible sources."""
        sources = [
            "Ensembl",
            "NCBI",
            "UCSC",
            "GenBank",
            "RefSeq",
            "ENA",
            "DDBJ"
        ]

        for i, source in enumerate(sources):
            assembly = Assembly(
                taxon_id=9606,
                source=source,
                name=f"Assembly {source}",
                genbank_assembly_accession=f"GCA_{i:09d}.1",
                refseq_assembly_accession=f"GCF_{i:09d}.1",
                is_current=i == 0,  # First one is current
                is_vgnc_default=i == 0
            )
            self.session.add(assembly)

        self.session.commit()

        # Verify all sources were saved
        for i, source in enumerate(sources):
            retrieved = self.session.query(Assembly).filter_by(source=source).first()
            assert retrieved is not None
            assert retrieved.source == source

    def test_assembly_property_accessors_comprehensive(self):
        """Test all Assembly model property accessors."""
        # Test with RefSeq accession
        assembly_refseq = Assembly(
            taxon_id=9606,
            source="NCBI",
            name="Test RefSeq",
            genbank_assembly_accession="GCA_000001405.15",
            refseq_assembly_accession="GCF_000001405.26",
            is_current=True,
            is_vgnc_default=True
        )

        assert assembly_refseq.accession == "GCF_000001405.26"  # RefSeq preferred

        # Test with only GenBank accession
        assembly_genbank = Assembly(
            taxon_id=9606,
            source="GenBank",
            name="Test GenBank",
            genbank_assembly_accession="GCA_000001405.15",
            refseq_assembly_accession="",  # Empty
            is_current=False,
            is_vgnc_default=False
        )

        assert assembly_genbank.accession == "GCA_000001405.15"  # Fallback to GenBank

        # Test is_active property
        assert assembly_refseq.is_active is True  # Both current and VGNC default
        assembly_refseq.is_current = False
        assert assembly_refseq.is_active is False  # Not current anymore

        assembly_genbank.is_current = True
        assembly_genbank.is_vgnc_default = True
        assert assembly_genbank.is_active is True  # Now both true

        # Test species_name property (without relationship)
        assembly_no_species = Assembly(
            taxon_id=9999,  # Non-existent species
            source="Test",
            name="Test Assembly",
            genbank_assembly_accession="GCA_TEST.1",
            refseq_assembly_accession="GCF_TEST.1",
            is_current=False,
            is_vgnc_default=False
        )

        assert assembly_no_species.species_name == "Unknown"

        # Test full_name property
        assert assembly_refseq.full_name == "Unknown - Test RefSeq"  # No species relationship
        assert assembly_genbank.full_name == "Unknown - Test GenBank"

    def test_assembly_relationship_with_species(self):
        """Test Assembly relationship with Species."""
        # Create assembly with species relationship
        assembly = Assembly(
            taxon_id=9606,
            source="Ensembl",
            name="GRCh38",
            genbank_assembly_accession="GCA_000001405.15",
            refseq_assembly_accession="GCF_000001405.26",
            is_current=True,
            is_vgnc_default=True
        )

        self.session.add(assembly)
        self.session.commit()

        # Test relationship access
        assert assembly.species is not None
        assert assembly.species.taxon_id == 9606
        assert assembly.species.display_name == "Human (Homo sapiens)"

        # Test properties with species relationship
        assert assembly.species_name == "Human (Homo sapiens)"
        assert assembly.full_name == "Human (Homo sapiens) - GRCh38"

    def test_assembly_to_dict_comprehensive(self):
        """Test Assembly to_dict method with all fields."""
        assembly = Assembly(
            taxon_id=9606,
            source="Ensembl",
            name="GRCh38",
            genbank_assembly_accession="GCA_000001405.15",
            refseq_assembly_accession="GCF_000001405.26",
            is_current=True,
            is_vgnc_default=False
        )

        self.session.add(assembly)
        self.session.commit()

        # Test to_dict
        result = assembly.to_dict()
        assert isinstance(result, dict)

        # Check all expected fields
        expected_fields = [
            "id", "taxon_id", "source", "name",
            "genbank_assembly_accession", "refseq_assembly_accession",
            "is_current", "is_vgnc_default",
            "accession", "species_name", "is_active", "full_name"
        ]

        for field in expected_fields:
            assert field in result

        # Check values
        assert result["taxon_id"] == 9606
        assert result["source"] == "Ensembl"
        assert result["name"] == "GRCh38"
        assert result["genbank_assembly_accession"] == "GCA_000001405.15"
        assert result["refseq_assembly_accession"] == "GCF_000001405.26"
        assert result["is_current"] is True
        assert result["is_vgnc_default"] is False
        assert result["accession"] == "GCF_000001405.26"
        assert result["is_active"] is False
        assert result["full_name"] == "Unknown - GRCh38"

    def test_assembly_field_utilities_comprehensive(self):
        """Test BaseModel field utilities with Assembly."""
        assembly = Assembly(
            taxon_id=9606,
            source="NCBI",
            name="Test Assembly",
            genbank_assembly_accession="GCA_TEST.1",
            refseq_assembly_accession="GCF_TEST.1",
            is_current=True,
            is_vgnc_default=True
        )

        # Test get_field_value
        assert assembly.get_field_value("taxon_id") == 9606
        assert assembly.get_field_value("source") == "NCBI"
        assert assembly.get_field_value("name") == "Test Assembly"
        assert assembly.get_field_value("is_current") is True
        assert assembly.get_field_value("nonexistent") is None

        # Test set_field_value
        assembly.set_field_value("name", "Updated Assembly")
        assert assembly.name == "Updated Assembly"

        assembly.set_field_value("is_current", False)
        assert assembly.is_current is False

        # Test has_field
        assert assembly.has_field("taxon_id") is True
        assert assembly.has_field("source") is True
        assert assembly.has_field("is_current") is True
        assert assembly.has_field("nonexistent") is False

        # Test get_field_type
        assert assembly.get_field_type("taxon_id") == int
        assert assembly.get_field_type("source") == str
        assert assembly.get_field_type("name") == str
        assert assembly.get_field_type("is_current") == bool

    def test_assembly_class_methods_comprehensive(self):
        """Test Assembly class methods."""
        # Test get_table_name
        assert Assembly.get_table_name() == "assembly"

        # Test get_column_names
        columns = Assembly.get_column_names()
        assert "id" in columns
        assert "taxon_id" in columns
        assert "source" in columns
        assert "name" in columns
        assert "genbank_assembly_accession" in columns
        assert "refseq_assembly_accession" in columns
        assert "is_current" in columns
        assert "is_vgnc_default" in columns

        # Test get_primary_key_columns
        pk_columns = Assembly.get_primary_key_columns()
        assert pk_columns == ["id"]

        # Test has_column
        assert Assembly.has_column("id") is True
        assert Assembly.has_column("taxon_id") is True
        assert Assembly.has_column("source") is True
        assert Assembly.has_column("nonexistent") is False

        # Test get_column_type
        assert Assembly.get_column_type("id") == int
        assert Assembly.get_column_type("taxon_id") == int
        assert Assembly.get_column_type("source") == str
        assert Assembly.get_column_type("name") == str
        assert Assembly.get_column_type("is_current") == bool

    def test_assembly_edge_cases_comprehensive(self):
        """Test Assembly model edge cases."""
        # Test assembly with minimal required fields
        minimal_assembly = Assembly(
            taxon_id=9606,
            source="Test",
            name="Minimal",
            genbank_assembly_accession="GCA_MIN.1",
            refseq_assembly_accession="GCF_MIN.1",
            is_current=False,
            is_vgnc_default=False
        )

        self.session.add(minimal_assembly)
        self.session.commit()

        assert minimal_assembly.id is not None
        assert minimal_assembly.species_name == "Unknown"

        # Test assembly with maximum length strings
        max_assembly = Assembly(
            taxon_id=9606,
            source="x" * 128,  # max length
            name="y" * 128,  # max length
            genbank_assembly_accession="z" * 128,  # max length
            refseq_assembly_accession="w" * 128,  # max length
            is_current=True,
            is_vgnc_default=True
        )

        self.session.add(max_assembly)
        self.session.commit()

        assert max_assembly.source == "x" * 128
        assert max_assembly.name == "y" * 128

        # Test assembly with empty strings
        empty_assembly = Assembly(
            taxon_id=9606,
            source="",
            name="",
            genbank_assembly_accession="",
            refseq_assembly_accession="",
            is_current=False,
            is_vgnc_default=False
        )

        self.session.add(empty_assembly)
        self.session.commit()

        assert empty_assembly.source == ""
        assert empty_assembly.accession == ""  # Both empty

    def test_assembly_foreign_key_constraints(self):
        """Test Assembly foreign key constraints."""
        # Test valid foreign key
        valid_assembly = Assembly(
            taxon_id=9606,  # Valid species ID
            source="Valid",
            name="Valid Assembly",
            genbank_assembly_accession="GCA_VALID.1",
            refseq_assembly_accession="GCF_VALID.1",
            is_current=True,
            is_vgnc_default=True
        )

        self.session.add(valid_assembly)
        self.session.commit()
        assert valid_assembly.id is not None

        # Test invalid foreign key
        invalid_assembly = Assembly(
            taxon_id=99999,  # Non-existent species ID
            source="Invalid",
            name="Invalid Assembly",
            genbank_assembly_accession="GCA_INVALID.1",
            refseq_assembly_accession="GCF_INVALID.1",
            is_current=False,
            is_vgnc_default=False
        )

        self.session.add(invalid_assembly)

        # SQLite may not enforce foreign key constraints by default
        # but this tests the relationship structure
        try:
            self.session.commit()
        except Exception as e:
            # Foreign key constraint violation (if enabled)
            assert "foreign key" in str(e).lower() or "constraint" in str(e).lower()
        else:
            # If no constraint enforcement, at least test the relationship access
            assert invalid_assembly.species is None

    def test_assembly_bulk_operations(self):
        """Test Assembly bulk operations."""
        # Create multiple assemblies for bulk testing
        bulk_assemblies = []
        for i in range(20):
            assembly = Assembly(
                taxon_id=9606,
                source=f"Source {i}",
                name=f"Bulk Assembly {i}",
                genbank_assembly_accession=f"GCA_BULK_{i:03d}.1",
                refseq_assembly_accession=f"GCF_BULK_{i:03d}.1",
                is_current=i == 0,  # First one is current
                is_vgnc_default=i == 0
            )
            bulk_assemblies.append(assembly)

        # Bulk insert
        self.session.add_all(bulk_assemblies)
        self.session.commit()

        # Verify bulk insert
        count = self.session.query(Assembly).filter(
            Assembly.name.like("Bulk Assembly%")
        ).count()
        assert count == 20

        # Bulk update
        self.session.query(Assembly).filter(
            Assembly.name.like("Bulk Assembly%")
        ).update({"is_current": False})
        self.session.commit()

        # Verify bulk update
        updated_count = self.session.query(Assembly).filter(
            Assembly.name.like("Bulk Assembly%"),
            Assembly.is_current == False
        ).count()
        assert updated_count == 20

        # Bulk delete
        self.session.query(Assembly).filter(
            Assembly.name.like("Bulk Assembly%")
        ).delete()
        self.session.commit()

        # Verify bulk delete
        remaining_count = self.session.query(Assembly).filter(
            Assembly.name.like("Bulk Assembly%")
        ).count()
        assert remaining_count == 0

    def test_assembly_query_methods_comprehensive(self):
        """Test Assembly query methods and filters."""
        # Create test data with different properties
        test_assemblies = [
            Assembly(taxon_id=9606, source="Ensembl", name="GRCh38", genbank_assembly_accession="GCA_001", refseq_assembly_accession="GCF_001", is_current=True, is_vgnc_default=True),
            Assembly(taxon_id=9606, source="NCBI", name="GRCh37", genbank_assembly_accession="GCA_002", refseq_assembly_accession="GCF_002", is_current=False, is_vgnc_default=False),
            Assembly(taxon_id=9606, source="UCSC", name="hg19", genbank_assembly_accession="GCA_003", refseq_assembly_accession="GCF_003", is_current=False, is_vgnc_default=False),
        ]

        for assembly in test_assemblies:
            self.session.add(assembly)
        self.session.commit()

        # Test query by source
        ensembl_assemblies = self.session.query(Assembly).filter_by(source="Ensembl").all()
        assert len(ensembl_assemblies) == 1

        # Test query by current status
        current_assemblies = self.session.query(Assembly).filter_by(is_current=True).all()
        assert len(current_assemblies) == 1

        # Test query by VGNC default
        vgnc_default_assemblies = self.session.query(Assembly).filter_by(is_vgnc_default=True).all()
        assert len(vgnc_default_assemblies) == 1

        # Test query by taxon_id
        human_assemblies = self.session.query(Assembly).filter_by(taxon_id=9606).all()
        assert len(human_assemblies) == 3

        # Test complex query (active assemblies)
        active_assemblies = self.session.query(Assembly).filter(
            Assembly.is_current == True,
            Assembly.is_vgnc_default == True
        ).all()
        assert len(active_assemblies) == 1

        # Test ordering
        ordered_assemblies = self.session.query(Assembly).order_by(Assembly.id).all()
        assert ordered_assemblies[0].id < ordered_assemblies[-1].id

    def test_assembly_repr_method(self):
        """Test Assembly __repr__ method."""
        assembly = Assembly(
            taxon_id=9606,
            source="Test",
            name="Test Assembly",
            genbank_assembly_accession="GCA_TEST.1",
            refseq_assembly_accession="GCF_TEST.1",
            is_current=False,
            is_vgnc_default=False
        )

        # Test before saving (no ID yet)
        repr_str = repr(assembly)
        assert "Assembly" in repr_str
        assert "name='Test Assembly'" in repr_str
        assert "taxon_id=9606" in repr_str

        # Test after saving
        self.session.add(assembly)
        self.session.commit()

        repr_str = repr(assembly)
        assert "Assembly" in repr_str
        assert str(assembly.id) in repr_str