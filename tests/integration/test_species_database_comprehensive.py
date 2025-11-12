"""Comprehensive database-integrated tests for Species model functionality."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import text, sessionmaker

from src.vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from src.vgnc_internal_orm.sessions.factory import DatabaseFactory
from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestSpeciesModelComprehensive:
    """Comprehensive database-integrated tests for Species model."""

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

        # Create tables
        Species.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_species_crud_operations_complete(self):
        """Test complete CRUD operations for Species model."""
        now = datetime.now(timezone.utc)

        # Create
        species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human (Homo sapiens)",
            ensembl_species_name="homo_sapiens",
            is_live=SpeciesLiveStatus.YES,
            created=now
        )

        self.session.add(species)
        self.session.commit()

        # Verify creation
        assert species.taxon_id == 9606
        assert species.genefam_prefix == "HS"
        assert species.display_name == "Human (Homo sapiens)"
        assert species.is_live == SpeciesLiveStatus.YES
        assert species.id == 9606  # Test id property
        assert species.vgnc_prefix == "HS"  # Test vgnc_prefix property

        # Read
        retrieved = self.session.query(Species).filter_by(taxon_id=9606).first()
        assert retrieved is not None
        assert retrieved.display_name == "Human (Homo sapiens)"
        assert retrieved.genefam_prefix == "HS"

        # Update
        retrieved.display_name = "Updated Human (Homo sapiens)"
        retrieved.is_live = SpeciesLiveStatus.TESTING
        self.session.commit()

        # Verify update
        updated = self.session.query(Species).filter_by(taxon_id=9606).first()
        assert updated.display_name == "Updated Human (Homo sapiens)"
        assert updated.is_live == SpeciesLiveStatus.TESTING

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(Species).filter_by(taxon_id=9606).first()
        assert deleted is None

    def test_species_all_live_status_values(self):
        """Test Species model with all possible live status values."""
        status_values = list(SpeciesLiveStatus)
        base_taxon_id = 10000

        for i, status in enumerate(status_values):
            species = Species(
                taxon_id=base_taxon_id + i,
                genefam_prefix=f"TS{i}",
                display_name=f"Test Species {status.value}",
                is_live=status,
                created=datetime.now(timezone.utc)
            )

            self.session.add(species)

        self.session.commit()

        # Verify all status values were saved
        for i, status in enumerate(status_values):
            retrieved = self.session.query(Species).filter_by(taxon_id=base_taxon_id + i).first()
            assert retrieved is not None
            assert retrieved.is_live == status

    def test_species_properties_comprehensive(self):
        """Test all Species model properties."""
        # Test active species
        active_species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human (Homo sapiens)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        assert active_species.is_active is True
        assert active_species.id == 9606
        assert active_species.vgnc_prefix == "HS"

        # Test inactive species
        inactive_species = Species(
            taxon_id=10090,
            genefam_prefix="MM",
            display_name="Mouse (Mus musculus)",
            is_live=SpeciesLiveStatus.NO,
            created=datetime.now(timezone.utc)
        )

        assert inactive_species.is_active is False
        assert inactive_species.id == 10090

        # Test model organism detection
        model_organism = Species(
            taxon_id=9000,  # In the model organism range
            genefam_prefix="MD",
            display_name="Model Organism",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        assert model_organism.is_model_organism is True

        non_model = Species(
            taxon_id=9999,  # Not in the model organism range
            genefam_prefix="NM",
            display_name="Non-Model Organism",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        assert non_model.is_model_organism is False

    def test_species_name_properties_comprehensive(self):
        """Test species name property functionality."""
        # Test with explicit overrides
        species_with_overrides = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human (Homo sapiens)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        # Set explicit overrides
        species_with_overrides.common_name = "Human Override"
        species_with_overrides.scientific_name = "Homo sapiens Override"

        # Test overrides
        assert species_with_overrides.common_name == "Human Override"
        assert species_with_overrides.scientific_name == "Homo sapiens Override"

        # Test name extraction from display_name
        species_extracted = Species(
            taxon_id=10090,
            genefam_prefix="MM",
            display_name="Mouse (Mus musculus)",
            ensembl_species_name="mus_musculus",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        assert species_extracted.common_name == "Mouse"
        assert species_extracted.scientific_name == "Mus musculus"

        # Test fallback to ensembl_species_name
        species_fallback = Species(
            taxon_id=10116,
            genefam_prefix="RN",
            display_name="Rat",
            ensembl_species_name="rattus_norvegicus",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        assert species_fallback.common_name == "Rat"
        assert species_fallback.scientific_name == "rattus_norvegicus"

        # Test edge cases
        species_edge_case = Species(
            taxon_id=10211,
            genefam_prefix="CM",
            display_name="",  # Empty display name
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        assert species_edge_case.common_name is None
        assert species_edge_case.scientific_name is None

        species_no_parens = Species(
            taxon_id=13616,
            genefam_prefix="DM",
            display_name="No parentheses species name",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        assert species_no_parens.common_name == "No parentheses species name"
        assert species_no_parens.scientific_name is None

    def test_species_vgnc_prefix_property(self):
        """Test VGNC prefix property functionality."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        # Test getter
        assert species.vgnc_prefix == "HS"
        assert species.genefam_prefix == "HS"

        # Test setter
        species.vgnc_prefix = "HSA"
        assert species.genefam_prefix == "HSA"
        assert species.vgnc_prefix == "HSA"

    def test_species_field_utilities_comprehensive(self):
        """Test BaseModel field utilities with Species."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human (Homo sapiens)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        # Test get_field_value
        assert species.get_field_value("taxon_id") == 9606
        assert species.get_field_value("genefam_prefix") == "HS"
        assert species.get_field_value("is_live") == SpeciesLiveStatus.YES
        assert species.get_field_value("nonexistent") is None

        # Test set_field_value
        species.set_field_value("display_name", "Updated Human")
        assert species.display_name == "Updated Human"

        # Test has_field
        assert species.has_field("taxon_id") is True
        assert species.has_field("genefam_prefix") is True
        assert species.has_field("nonexistent") is False

        # Test get_field_type
        assert species.get_field_type("taxon_id") == int
        assert species.get_field_type("genefam_prefix") == str
        assert species.get_field_type("is_live") == SpeciesLiveStatus

    def test_species_dict_conversion_comprehensive(self):
        """Test Species dictionary conversion methods."""
        now = datetime.now(timezone.utc)

        species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human (Homo sapiens)",
            ensembl_species_name="homo_sapiens",
            is_live=SpeciesLiveStatus.YES,
            created=now
        )
        species._scientific_name = "Homo sapiens"
        species._common_name = "Human"

        # Test to_dict
        result = species.to_dict()
        assert isinstance(result, dict)
        assert result["taxon_id"] == 9606
        assert result["genefam_prefix"] == "HS"
        assert result["display_name"] == "Human (Homo sapiens)"
        assert result["is_live"] == "YES"
        assert "_scientific_name" in result
        assert "_common_name" in result

        # Test to_dict with exclude
        result_exclude = species.to_dict(exclude=["_scientific_name", "_common_name"])
        assert "_scientific_name" not in result_exclude
        assert "_common_name" not in result_exclude
        assert "taxon_id" in result_exclude

        # Test to_dict with include
        result_include = species.to_dict(include=["taxon_id", "display_name", "genefam_prefix"])
        assert len(result_include) == 3
        assert "taxon_id" in result_include
        assert "display_name" in result_include
        assert "genefam_prefix" in result_include
        assert "is_live" not in result_include

    def test_species_json_conversion_comprehensive(self):
        """Test Species JSON conversion methods."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human (Homo sapiens)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        # Test to_json
        json_str = species.to_json()
        assert isinstance(json_str, str)
        assert "taxon_id" in json_str
        assert "genefam_prefix" in json_str
        assert "9606" in json_str
        assert "HS" in json_str

    def test_species_update_from_dict_comprehensive(self):
        """Test Species update_from_dict method."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        # Test basic update
        update_data = {
            "display_name": "Updated Human (Homo sapiens)",
            "ensembl_species_name": "homo_sapiens",
            "genefam_prefix": "HSA"
        }

        species.update_from_dict(update_data)

        assert species.display_name == "Updated Human (Homo sapiens)"
        assert species.ensembl_species_name == "homo_sapiens"
        assert species.genefam_prefix == "HSA"

        # Test update with exclude
        update_data2 = {
            "display_name": "Should Not Change",
            "is_live": "NO"
        }

        species.update_from_dict(update_data2, exclude=["display_name"])

        assert species.display_name == "Updated Human (Homo sapiens)"  # Should not change
        assert species.is_live == SpeciesLiveStatus.NO

    def test_species_validation_methods(self):
        """Test Species validation methods."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human (Homo sapiens)",
            ensembl_species_name="homo_sapiens",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        # Test validate_utf8mb4_fields with valid data
        validation_results = species.validate_utf8mb4_fields(
            "display_name", "ensembl_species_name", "genefam_prefix"
        )

        assert isinstance(validation_results, dict)
        assert "display_name" in validation_results
        assert "ensembl_species_name" in validation_results
        assert "genefam_prefix" in validation_results

        for field_name, result in validation_results.items():
            assert "valid" in result
            assert "message" in result
            assert "has_unicode" in result

        # Test with unicode characters
        unicode_species = Species(
            taxon_id=99999,
            genefam_prefix="UN",
            display_name="测试物种",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        unicode_validation = unicode_species.validate_utf8mb4_fields("display_name")
        assert unicode_validation["display_name"]["valid"] is True
        # Should detect unicode characters
        assert isinstance(unicode_validation["display_name"]["has_unicode"], bool)

    def test_species_repr_and_str_methods(self):
        """Test Species representation methods."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human (Homo sapiens)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        # Test __repr__
        repr_str = repr(species)
        assert "Species" in repr_str
        assert "9606" in repr_str
        assert "HS" in repr_str
        assert "Human (Homo sapiens)" in repr_str

        # Test __str__ (inherited from BaseModel)
        str_str = str(species)
        assert "Species" in str_str

    def test_species_class_methods_comprehensive(self):
        """Test Species class methods."""
        # Test get_table_name
        assert Species.get_table_name() == "species"

        # Test get_column_names
        columns = Species.get_column_names()
        assert "taxon_id" in columns
        assert "genefam_prefix" in columns
        assert "display_name" in columns
        assert "is_live" in columns
        assert "created" in columns
        assert "_scientific_name" in columns
        assert "_common_name" in columns

        # Test get_primary_key_columns
        pk_columns = Species.get_primary_key_columns()
        assert pk_columns == ["taxon_id"]

        # Test has_column
        assert Species.has_column("taxon_id") is True
        assert Species.has_column("genefam_prefix") is True
        assert Species.has_column("is_live") is True
        assert Species.has_column("nonexistent") is False

        # Test get_column_type
        assert Species.get_column_type("taxon_id") == int
        assert Species.get_column_type("genefam_prefix") == str
        assert Species.get_column_type("is_live") == SpeciesLiveStatus
        assert Species.get_column_type("created") == datetime

    def test_species_edge_cases_comprehensive(self):
        """Test Species model edge cases."""
        # Test species with minimal required fields
        minimal_species = Species(
            taxon_id=9999,
            genefam_prefix="MN",
            display_name="Minimal Species",
            is_live=SpeciesLiveStatus.TESTING,
            created=datetime.now(timezone.utc)
        )

        self.session.add(minimal_species)
        self.session.commit()

        assert minimal_species.taxon_id == 9999
        assert minimal_species.ensembl_species_name is None
        assert minimal_species.primary_db_table is None
        assert minimal_species._scientific_name is None
        assert minimal_species._common_name is None

        # Test species with maximum length strings
        max_prefix = "x" * 11  # genefam_prefix max length
        max_display = "y" * 128  # display_name max length

        max_species = Species(
            taxon_id=8888,
            genefam_prefix=max_prefix,
            display_name=max_display,
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        self.session.add(max_species)
        self.session.commit()

        assert max_species.genefam_prefix == max_prefix
        assert max_species.display_name == max_display

        # Test species with special characters
        special_species = Species(
            taxon_id=7777,
            genefam_prefix="SC",
            display_name="Special & <Test> Species",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        self.session.add(special_species)
        self.session.commit()

        assert special_species.display_name == "Special & <Test> Species"

    def test_species_bulk_operations(self):
        """Test Species bulk operations."""
        # Create multiple species for bulk testing
        bulk_species = []
        for i in range(50):
            species = Species(
                taxon_id=2000 + i,
                genefam_prefix=f"BK{i:02d}",
                display_name=f"Bulk Species {i}",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(timezone.utc)
            )
            bulk_species.append(species)

        # Bulk insert
        self.session.add_all(bulk_species)
        self.session.commit()

        # Verify bulk insert
        count = self.session.query(Species).filter(
            Species.genefam_prefix.like("BK%")
        ).count()
        assert count == 50

        # Bulk update
        self.session.query(Species).filter(
            Species.genefam_prefix.like("BK%")
        ).update({"is_live": SpeciesLiveStatus.TESTING})
        self.session.commit()

        # Verify bulk update
        updated_count = self.session.query(Species).filter(
            Species.genefam_prefix.like("BK%"),
            Species.is_live == SpeciesLiveStatus.TESTING
        ).count()
        assert updated_count == 50

    def test_species_query_methods_comprehensive(self):
        """Test Species query methods and filters."""
        # Create test data with different properties
        test_species = [
            Species(taxon_id=9606, genefam_prefix="HS", display_name="Human", is_live=SpeciesLiveStatus.YES, created=datetime.now(timezone.utc)),
            Species(taxon_id=10090, genefam_prefix="MM", display_name="Mouse", is_live=SpeciesLiveStatus.NO, created=datetime.now(timezone.utc)),
            Species(taxon_id=10116, genefam_prefix="RN", display_name="Rat", is_live=SpeciesLiveStatus.TESTING, created=datetime.now(timezone.utc)),
            Species(taxon_id=9001, genefam_prefix="MD", display_name="Model Organism", is_live=SpeciesLiveStatus.YES, created=datetime.now(timezone.utc)),
        ]

        for species in test_species:
            self.session.add(species)
        self.session.commit()

        # Test query by live status
        active_species = self.session.query(Species).filter_by(is_live=SpeciesLiveStatus.YES).all()
        assert len(active_species) == 2

        # Test query by genefam_prefix pattern
        m_species = self.session.query(Species).filter(
            Species.genefam_prefix.like("M%")
        ).all()
        assert len(m_species) == 2  # MM and MD

        # Test query by taxon_id range
        range_species = self.session.query(Species).filter(
            Species.taxon_id.between(9500, 10500)
        ).all()
        assert len(range_species) == 3

        # Test ordering
        ordered_species = self.session.query(Species).order_by(
            Species.taxon_id
        ).all()
        assert ordered_species[0].taxon_id < ordered_species[-1].taxon_id

    def test_species_database_constraints(self):
        """Test Species database constraints and validation."""
        # Test primary key uniqueness
        species1 = Species(
            taxon_id=9606,
            genefam_prefix="HS1",
            display_name="Species 1",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        species2 = Species(
            taxon_id=9606,  # Same taxon_id - should cause conflict
            genefam_prefix="HS2",
            display_name="Species 2",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        self.session.add(species1)
        self.session.commit()

        self.session.add(species2)
        with pytest.raises(Exception):  # Should raise IntegrityError
            self.session.commit()

        # Clean up
        self.session.rollback()

        # Test NOT NULL constraint on required fields
        with pytest.raises(Exception):  # Should raise IntegrityError
            invalid_species = Species(
                taxon_id=1234,
                # Missing genefam_prefix
                display_name="Invalid",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(timezone.utc)
            )
            self.session.add(invalid_species)
            self.session.commit()

        self.session.rollback()

        # Test enum constraint on is_live
        with pytest.raises(Exception):  # Should raise error for invalid enum value
            # This test would need direct SQL injection since SQLAlchemy validates enum
            invalid_enum = Species(
                taxon_id=5678,
                genefam_prefix="IE",
                display_name="Invalid Enum",
                is_live="INVALID_VALUE",  # Not a valid enum value
                created=datetime.now(timezone.utc)
            )
            self.session.add(invalid_enum)
            self.session.commit()

        # In practice, SQLAlchemy would prevent this before it reaches the database
        self.session.rollback()


class TestSpeciesModelRelationships:
    """Test Species model relationship functionality (without actual related models)."""

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

        # Create tables
        Species.metadata.create_all(bind=self.engine)
        self.session = self.SessionLocal()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_species_relationship_attributes_exist(self):
        """Test that Species has expected relationship attributes."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        # Test that relationship attributes exist (even if no related models)
        assert hasattr(species, 'assemblies')
        assert hasattr(species, 'chromosomes')
        assert hasattr(species, 'genefams')

        # Initially should be empty (no related models in database)
        assert len(species.assemblies) == 0
        assert len(species.chromosomes) == 0
        assert len(species.genefams) == 0

    def test_species_has_genefam_method(self):
        """Test has_genefam method functionality."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )

        # Test with empty genefams list
        assert species.has_genefam("GENE1") is False

        # Test with Mock genefam objects (simulating relationship)
        class MockGenefam:
            def __init__(self, genefam_id, assigned_symbol):
                self.genefam_id = genefam_id
                self.assigned_symbol = assigned_symbol

        # Add mock genefams to the relationship
        species.genefams = [
            MockGenefam("GF001", "GENE1"),
            MockGenefam("GF002", "GENE2"),
        ]

        # Test string lookup
        assert species.has_genefam("GENE1") is True
        assert species.has_genefam("GENE2") is True
        assert species.has_genefam("GENE3") is False

        # Test object lookup
        mock_gf = MockGenefam("GF001", "GENE1")
        assert species.has_genefam(mock_gf) is True

        mock_gf_new = MockGenefam("GF003", "GENE3")
        assert species.has_genefam(mock_gf_new) is False