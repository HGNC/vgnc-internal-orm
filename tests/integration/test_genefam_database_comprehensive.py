"""Comprehensive database-integrated tests for Genefam model functionality."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker

from src.vgnc_internal_orm.models.genefam import Genefam
from src.vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from src.vgnc_internal_orm.models.supporting import GeneStatus, Editor
from src.vgnc_internal_orm.sessions.factory import DatabaseFactory
from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestGenefamModelComprehensive:
    """Comprehensive database-integrated tests for Genefam model."""

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

        # Create tables for all models
        from src.vgnc_internal_orm.models.base import BaseModel
        BaseModel.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

        # Create test data for foreign key relationships
        self.test_species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human (Homo sapiens)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )
        self.session.add(self.test_species)

        self.test_status = GeneStatus(status="approved", display="Approved")
        self.session.add(self.test_status)

        self.test_editor = Editor(
            display_name="Test Editor",
            current=True,
            connected=True
        )
        self.session.add(self.test_editor)

        self.session.commit()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_genefam_crud_operations_complete(self):
        """Test complete CRUD operations for Genefam model."""
        # Create
        genefam = Genefam(
            taxon_id=9606,
            assigned_id="HGNC:12345",
            assigned_symbol="TEST1",
            assigned_name="Test Gene Family 1",
            status_id=self.test_status.id,
            editor_id=self.test_editor.id,
            hcop_support_level=3
        )

        self.session.add(genefam)
        self.session.commit()

        # Verify creation
        assert genefam.genefam_id is not None
        assert genefam.taxon_id == 9606
        assert genefam.assigned_id == "HGNC:12345"
        assert genefam.assigned_symbol == "TEST1"
        assert genefam.assigned_name == "Test Gene Family 1"
        assert genefam.status_id == self.test_status.id
        assert genefam.editor_id == self.test_editor.id
        assert genefam.hcop_support_level == 3

        # Read
        retrieved = self.session.query(Genefam).filter_by(assigned_id="HGNC:12345").first()
        assert retrieved is not None
        assert retrieved.assigned_symbol == "TEST1"

        # Update
        retrieved.assigned_symbol = "TEST1_UPDATED"
        retrieved.hcop_support_level = 4
        self.session.commit()

        # Verify update
        updated = self.session.query(Genefam).filter_by(assigned_id="HGNC:12345").first()
        assert updated.assigned_symbol == "TEST1_UPDATED"
        assert updated.hcop_support_level == 4

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(Genefam).filter_by(assigned_id="HGNC:12345").first()
        assert deleted is None

    def test_genefam_all_assigned_id_formats(self):
        """Test Genefam with various assigned_id formats."""
        assigned_ids = [
            "HGNC:12345",
            "ENTREZ:67890",
            "UNIPROT:P12345",
            "ENSEMBL:ENSG000001",
            "REFSEQ:NM_001256",
            "CUSTOM:FAM001",
            "SIMPLE001",
            "complex-format-with-dashes",
            "FAMILY_001",
            "GeneFamily001"
        ]

        for i, assigned_id in enumerate(assigned_ids):
            genefam = Genefam(
                taxon_id=9606,
                assigned_id=assigned_id,
                assigned_symbol=f"SYM{i}",
                status_id=self.test_status.id,
                editor_id=self.test_editor.id
            )
            self.session.add(genefam)

        self.session.commit()

        # Verify all assigned_ids were saved
        for assigned_id in assigned_ids:
            retrieved = self.session.query(Genefam).filter_by(assigned_id=assigned_id).first()
            assert retrieved is not None
            assert retrieved.assigned_id == assigned_id

    def test_genefam_all_symbol_formats(self):
        """Test Genefam with various symbol formats."""
        symbol_formats = [
            "GENE1",
            "GENEFAM1",
            "HGNC:12345",
            "ENTREZ:67890",
            "PROT_001",
            "enzyme_001",
            "receptor-1",
            "transporter_2A",
            "complex-protein",
            "PROTEIN_KINASE"
        ]

        for i, symbol in enumerate(symbol_formats):
            genefam = Genefam(
                taxon_id=9606,
                assigned_id=f"FAM{i:03d}",
                assigned_symbol=symbol,
                status_id=self.test_status.id,
                editor_id=self.test_editor.id
            )
            self.session.add(genefam)

        self.session.commit()

        # Verify all symbols were saved
        for symbol in symbol_formats:
            retrieved = self.session.query(Genefam).filter_by(assigned_symbol=symbol).first()
            assert retrieved is not None
            assert retrieved.assigned_symbol == symbol

    def test_genefam_foreign_key_relationships(self):
        """Test Genefam foreign key relationships."""
        genefam = Genefam(
            taxon_id=9606,
            assigned_id="REL_TEST",
            status_id=self.test_status.id,
            editor_id=self.test_editor.id
        )

        self.session.add(genefam)
        self.session.commit()

        # Test species relationship
        assert genefam.species is not None
        assert genefam.species.taxon_id == 9606
        assert genefam.species.genefam_prefix == "HS"

        # Test that foreign keys are properly set
        assert genefam.status_id == self.test_status.id
        assert genefam.editor_id == self.test_editor.id

    def test_genefam_property_accessors_comprehensive(self):
        """Test all Genefam model property accessors."""
        genefam = Genefam(
            taxon_id=9606,
            assigned_id="PROP_TEST",
            assigned_symbol="PROPSYM",
            assigned_name="Property Test Gene Family",
            status_id=self.test_status.id,
            editor_id=self.test_editor.id
        )

        self.session.add(genefam)
        self.session.commit()

        # Test name property (alias for assigned_id)
        assert genefam.name == "PROP_TEST"
        assert genefam.name == genefam.assigned_id

        # Test symbol property (alias for assigned_symbol)
        assert genefam.symbol == "PROPSYM"
        assert genefam.symbol == genefam.assigned_symbol

        # Test description property (alias for assigned_name)
        assert genefam.description == "Property Test Gene Family"
        assert genefam.description == genefam.assigned_name

        # Test is_active property (always True since relationship is disabled)
        assert genefam.is_active is True

        # Test status_text property (default since relationship is disabled)
        assert genefam.status_text == "Active"

        # Test editor_name property (fallback using editor_id)
        assert genefam.editor_name == f"Editor {self.test_editor.id}"

        # Test species_prefix property
        assert genefam.species_prefix == "HS"

        # Test full_identifier property
        assert genefam.full_identifier == "HS:PROP_TEST"

        # Test with None assigned_id
        genefam_no_id = Genefam(
            taxon_id=9606,
            assigned_id="",
            status_id=self.test_status.id,
            editor_id=self.test_editor.id
        )
        self.session.add(genefam_no_id)
        self.session.commit()

        assert genefam_no_id.full_identifier == ""  # Empty assigned_id

    def test_genefam_to_dict_comprehensive(self):
        """Test Genefam to_dict method with all fields."""
        genefam = Genefam(
            taxon_id=9606,
            assigned_id="DICT_TEST",
            assigned_symbol="DICTSYM",
            assigned_name="Dict Test Gene Family",
            status_id=self.test_status.id,
            editor_id=self.test_editor.id,
            hcop_support_level=5
        )

        self.session.add(genefam)
        self.session.commit()

        # Test to_dict
        result = genefam.to_dict()
        assert isinstance(result, dict)

        # Check all expected fields
        expected_fields = [
            "genefam_id", "taxon_id", "name", "symbol", "description",
            "assigned_id", "assigned_symbol", "assigned_name",
            "status_id", "editor_id", "hcop_support_level",
            "status", "is_active", "species_prefix",
            "full_identifier", "editor_name"
        ]

        for field in expected_fields:
            assert field in result

        # Check values
        assert result["taxon_id"] == 9606
        assert result["assigned_id"] == "DICT_TEST"
        assert result["assigned_symbol"] == "DICTSYM"
        assert result["assigned_name"] == "Dict Test Gene Family"
        assert result["status_id"] == self.test_status.id
        assert result["editor_id"] == self.test_editor.id
        assert result["hcop_support_level"] == 5
        assert result["name"] == "DICT_TEST"  # Property alias
        assert result["symbol"] == "DICTSYM"  # Property alias
        assert result["description"] == "Dict Test Gene Family"  # Property alias
        assert result["status"] == "Active"  # Property default
        assert result["is_active"] is True  # Property default
        assert result["species_prefix"] == "HS"  # Property relationship
        assert result["full_identifier"] == "HS:DICT_TEST"  # Property
        assert result["editor_name"] == f"Editor {self.test_editor.id}"  # Property fallback

    def test_genefam_edge_cases_comprehensive(self):
        """Test Genefam model edge cases."""
        # Test with None optional fields
        genefam_none_fields = Genefam(
            taxon_id=9606,
            assigned_id="NONE_TEST",
            assigned_symbol=None,
            assigned_name=None,
            status_id=self.test_status.id,
            editor_id=self.test_editor.id,
            hcop_support_level=None
        )

        self.session.add(genefam_none_fields)
        self.session.commit()

        assert genefam_none_fields.assigned_symbol is None
        assert genefam_none_fields.assigned_name is None
        assert genefam_none_fields.hcop_support_level is None
        assert genefam_none_fields.symbol is None  # Property alias
        assert genefam_none_fields.description is None  # Property alias

        # Test with empty strings for default values
        genefam_empty_strings = Genefam(
            taxon_id=9606,
            assigned_id="",  # Empty string (default value)
            status_id=self.test_status.id,
            editor_id=self.test_editor.id
        )

        self.session.add(genefam_empty_strings)
        self.session.commit()

        assert genefam_empty_strings.assigned_id == ""
        assert genefam_empty_strings.name == ""  # Property alias

        # Test with maximum length strings
        max_genefam = Genefam(
            taxon_id=9606,
            assigned_id="x" * 255,  # max length
            assigned_symbol="y" * 45,   # max length
            assigned_name="z" * 255,   # max length
            status_id=self.test_status.id,
            editor_id=self.test_editor.id
        )

        self.session.add(max_genefam)
        self.session.commit()

        assert len(max_genefam.assigned_id) == 255
        assert len(max_genefam.assigned_symbol) == 45
        assert len(max_genefam.assigned_name) == 255

    def test_genefam_field_utilities_comprehensive(self):
        """Test BaseModel field utilities with Genefam."""
        genefam = Genefam(
            taxon_id=9606,
            assigned_id="UTIL_TEST",
            assigned_symbol="UTILSYM",
            status_id=self.test_status.id,
            editor_id=self.test_editor.id,
            hcop_support_level=3
        )

        # Test get_field_value
        assert genefam.get_field_value("genefam_id") is not None  # Will be set after save
        assert genefam.get_field_value("taxon_id") == 9606
        assert genefam.get_field_value("assigned_id") == "UTIL_TEST"
        assert genefam.get_field_value("assigned_symbol") == "UTILSYM"
        assert genefam.get_field_value("status_id") == self.test_status.id
        assert genefam.get_field_value("editor_id") == self.test_editor.id
        assert genefam.get_field_value("hcop_support_level") == 3
        assert genefam.get_field_value("nonexistent") is None

        # Test set_field_value
        genefam.set_field_value("assigned_id", "UTIL_UPDATED")
        assert genefam.assigned_id == "UTIL_UPDATED"

        genefam.set_field_value("assigned_symbol", "UTILSYM_UPDATED")
        assert genefam.assigned_symbol == "UTILSYM_UPDATED"

        genefam.set_field_value("hcop_support_level", 5)
        assert genefam.hcop_support_level == 5

        # Test has_field
        assert genefam.has_field("genefam_id") is True
        assert genefam.has_field("taxon_id") is True
        assert genefam.has_field("assigned_id") is True
        assert genefam.has_field("assigned_symbol") is True
        assert genefam.has_field("status_id") is True
        assert genefam.has_field("editor_id") is True
        assert genefam.has_field("hcop_support_level") is True
        assert genefam.has_field("nonexistent") is False

        # Test get_field_type
        assert genefam.get_field_type("genefam_id") == int
        assert genefam.get_field_type("taxon_id") == int
        assert genefam.get_field_type("assigned_id") == str
        assert genefam.get_field_type("assigned_symbol") == str
        assert genefam.get_field_type("status_id") == int
        assert genefam.get_field_type("editor_id") == int
        assert genefam.get_field_type("hcop_support_level") == int

    def test_genefam_class_methods_comprehensive(self):
        """Test Genefam class methods."""
        # Test get_table_name
        assert Genefam.get_table_name() == "genefam"

        # Test get_column_names
        columns = Genefam.get_column_names()
        assert "genefam_id" in columns
        assert "taxon_id" in columns
        assert "assigned_id" in columns
        assert "assigned_symbol" in columns
        assert "assigned_name" in columns
        assert "status_id" in columns
        assert "editor_id" in columns
        assert "hcop_support_level" in columns

        # Test get_primary_key_columns
        pk_columns = Genefam.get_primary_key_columns()
        assert pk_columns == ["genefam_id"]

        # Test has_column
        assert Genefam.has_column("genefam_id") is True
        assert Genefam.has_column("taxon_id") is True
        assert Genefam.has_column("assigned_id") is True
        assert Genefam.has_column("assigned_symbol") is True
        assert Genefam.has_column("nonexistent") is False

        # Test get_column_type
        assert Genefam.get_column_type("genefam_id") == int
        assert Genefam.get_column_type("taxon_id") == int
        assert Genefam.get_column_type("assigned_id") == str
        assert Genefam.get_column_type("assigned_symbol") == str
        assert Genefam.get_column_type("status_id") == int
        assert Genefam.get_column_type("editor_id") == int
        assert Genefam.get_column_type("hcop_support_level") == int

    def test_genefam_repr_method(self):
        """Test Genefam __repr__ method."""
        genefam = Genefam(
            taxon_id=9606,
            assigned_id="REPR_TEST",
            status_id=self.test_status.id,
            editor_id=self.test_editor.id
        )

        # Test before saving (no ID yet)
        repr_str = repr(genefam)
        assert "Genefam" in repr_str
        assert "assigned_id='REPR_TEST'" in repr_str
        assert "taxon_id=9606" in repr_str

        # Test after saving
        self.session.add(genefam)
        self.session.commit()

        repr_str = repr(genefam)
        assert "Genefam" in repr_str
        assert str(genefam.genefam_id) in repr_str
        assert "assigned_id='REPR_TEST'" in repr_str

    def test_genefam_query_methods_comprehensive(self):
        """Test Genefam query methods and filters."""
        # Create test data with different properties
        test_genefams = [
            Genefam(taxon_id=9606, assigned_id="QUERY_TEST_1", assigned_symbol="SYM1", status_id=self.test_status.id, editor_id=self.test_editor.id, hcop_support_level=1),
            Genefam(taxon_id=9606, assigned_id="QUERY_TEST_2", assigned_symbol="SYM2", status_id=self.test_status.id, editor_id=self.test_editor.id, hcop_support_level=2),
            Genefam(taxon_id=9606, assigned_id="QUERY_TEST_3", assigned_symbol="SYM3", status_id=self.test_status.id, editor_id=self.test_editor.id, hcop_support_level=3),
            Genefam(taxon_id=9606, assigned_id="QUERY_TEST_4", assigned_symbol="SYM4", status_id=self.test_status.id, editor_id=self.test_editor.id, hcop_support_level=None),
        ]

        for genefam in test_genefams:
            self.session.add(genefam)
        self.session.commit()

        # Test query by assigned_id pattern
        query_test_fams = self.session.query(Genefam).filter(
            Genefam.assigned_id.like("QUERY_TEST_%")
        ).all()
        assert len(query_test_fams) == 4

        # Test query by assigned_symbol
        sym1_fam = self.session.query(Genefam).filter_by(assigned_symbol="SYM1").first()
        assert sym1_fam is not None
        assert sym1_fam.assigned_id == "QUERY_TEST_1"

        # Test query by taxon_id
        human_genefams = self.session.query(Genefam).filter_by(taxon_id=9606).all()
        assert len(human_genefams) == 4

        # Test query by hcop_support_level
        level_3_fams = self.session.query(Genefam).filter_by(hcop_support_level=3).all()
        assert len(level_3_fams) == 1

        # Test query with None values
        null_support_fams = self.session.query(Genefam).filter(Genefam.hcop_support_level.is_(None)).all()
        assert len(null_support_fams) == 1

        # Test complex query
        high_support_fams = self.session.query(Genefam).filter(
            Genefam.taxon_id == 9606,
            Genefam.hcop_support_level >= 2
        ).all()
        assert len(high_support_fams) == 2

        # Test ordering
        ordered_fams = self.session.query(Genefam).order_by(Genefam.genefam_id).all()
        assert ordered_fams[0].genefam_id < ordered_fams[-1].genefam_id

    def test_genefam_bulk_operations(self):
        """Test Genefam bulk operations."""
        # Create multiple genefams for bulk testing
        bulk_genefams = []
        for i in range(25):
            genefam = Genefam(
                taxon_id=9606,
                assigned_id=f"BULK_FAM_{i:03d}",
                assigned_symbol=f"BULK{i}",
                status_id=self.test_status.id,
                editor_id=self.test_editor.id,
                hcop_support_level=i % 5
            )
            bulk_genefams.append(genefam)

        # Bulk insert
        self.session.add_all(bulk_genefams)
        self.session.commit()

        # Verify bulk insert
        count = self.session.query(Genefam).filter(
            Genefam.assigned_id.like("BULK_FAM_%")
        ).count()
        assert count == 25

        # Bulk update
        self.session.query(Genefam).filter(
            Genefam.assigned_id.like("BULK_FAM_%")
        ).update({"hcop_support_level": 5})
        self.session.commit()

        # Verify bulk update
        updated_count = self.session.query(Genefam).filter(
            Genefam.assigned_id.like("BULK_FAM_%"),
            Genefam.hcop_support_level == 5
        ).count()
        assert updated_count == 25

        # Bulk delete
        self.session.query(Genefam).filter(
            Genefam.assigned_id.like("BULK_FAM_%")
        ).delete()
        self.session.commit()

        # Verify bulk delete
        remaining_count = self.session.query(Genefam).filter(
            Genefam.assigned_id.like("BULK_FAM_%")
        ).count()
        assert remaining_count == 0

    def test_genefam_transaction_handling(self):
        """Test Genefam transaction handling."""
        # Start a transaction
        genefam = Genefam(
            taxon_id=9606,
            assigned_id="TRANS_TEST",
            status_id=self.test_status.id,
            editor_id=self.test_editor.id
        )

        self.session.add(genefam)
        self.session.flush()  # Make visible but don't commit yet

        # Test property access before commit
        assert genefam.name == "TRANS_TEST"
        assert genefam.full_identifier == "HS:TRANS_TEST"

        # In another session, this shouldn't be visible yet
        with self.SessionLocal() as other_session:
            not_visible = other_session.query(Genefam).filter_by(assigned_id="TRANS_TEST").first()
            assert not_visible is None

        # Now commit
        self.session.commit()

        # After commit, it should be visible
        with self.SessionLocal() as final_session:
            visible = final_session.query(Genefam).filter_by(assigned_id="TRANS_TEST").first()
            assert visible is not None

    def test_genefam_different_species_relationships(self):
        """Test Genefam with different species relationships."""
        # Create additional species
        mouse_species = Species(
            taxon_id=10090,
            genefam_prefix="MM",
            display_name="Mouse (Mus musculus)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )
        self.session.add(mouse_species)
        self.session.commit()

        # Create genefams for different species
        human_genefam = Genefam(
            taxon_id=9606,
            assigned_id="HS_GENE",
            assigned_symbol="HSG",
            status_id=self.test_status.id,
            editor_id=self.test_editor.id
        )

        mouse_genefam = Genefam(
            taxon_id=10090,
            assigned_id="MM_GENE",
            assigned_symbol="MMG",
            status_id=self.test_status.id,
            editor_id=self.test_editor.id
        )

        self.session.add(human_genefam)
        self.session.add(mouse_genefam)
        self.session.commit()

        # Test species relationships
        assert human_genefam.species.taxon_id == 9606
        assert human_genefam.species.genefam_prefix == "HS"
        assert human_genefam.full_identifier == "HS:HS_GENE"

        assert mouse_genefam.species.taxon_id == 10090
        assert mouse_genefam.species.genefam_prefix == "MM"
        assert mouse_genefam.full_identifier == "MM:MM_GENE"

        # Test species_prefix property
        assert human_genefam.species_prefix == "HS"
        assert mouse_genefam.species_prefix == "MM"