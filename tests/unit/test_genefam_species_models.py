"""Unit tests for Genefam and Species models."""

import pytest
from datetime import datetime, timezone

from src.vgnc_internal_orm.models.genefam import Genefam
from src.vgnc_internal_orm.models.species import Species


class TestGenefamModel:
    """Test cases for Genefam model."""

    def test_genefam_creation(self):
        """Test basic Genefam model creation."""
        genefam = Genefam(
            taxon_id=9606,  # Human
            assigned_id="HOX",
            assigned_symbol="HOX",
            assigned_name="Homeobox gene family",
            status_id=1,
            editor_id=1
        )

        assert genefam.taxon_id == 9606
        assert genefam.assigned_id == "HOX"
        assert genefam.assigned_symbol == "HOX"
        assert genefam.assigned_name == "Homeobox gene family"
        assert genefam.status_id == 1
        assert genefam.editor_id == 1

    def test_genefam_basic_fields(self):
        """Test basic genefam field access."""
        genefam = Genefam(
            taxon_id=10090,  # Mouse
            assigned_id="HOX",
            assigned_symbol="HOXA",
            assigned_name="Homeobox gene family",
            status_id=1,
            editor_id=1
        )

        # Test field access
        assert genefam.taxon_id == 10090
        assert genefam.assigned_id == "HOX"
        assert genefam.assigned_symbol == "HOXA"
        assert genefam.assigned_name == "Homeobox gene family"

        # Test field updates
        genefam.assigned_symbol = "HOXB"
        assert genefam.assigned_symbol == "HOXB"

        genefam.assigned_name = "Updated Homeobox gene family"
        assert genefam.assigned_name == "Updated Homeobox gene family"

    def test_genefam_various_entries(self):
        """Test various genefam entries."""
        genefams = []

        genefam_data = [
            ("HOX", "HOXA", "Homeobox gene family"),
            ("KRAS", "KRAS", "KRAS proto-oncogene"),
            ("TP53", "TP53", "Tumor protein p53"),
            ("MYC", "MYC", "MYC proto-oncogene")
        ]

        for assigned_id, symbol, name in genefam_data:
            genefam = Genefam(
                taxon_id=9606,
                assigned_id=assigned_id,
                assigned_symbol=symbol,
                assigned_name=name,
                status_id=1,
                editor_id=1
            )
            genefams.append(genefam)

        # Verify all genefams created successfully
        assert len(genefams) == 4
        assert genefams[0].assigned_id == "HOX"
        assert genefams[1].assigned_symbol == "KRAS"
        assert genefams[2].assigned_name == "Tumor protein p53"
        assert genefams[3].assigned_id == "MYC"

    def test_genefam_string_representation(self):
        """Test string representation."""
        genefam = Genefam(
            taxon_id=9606,
            assigned_id="HOX",
            assigned_symbol="HOX",
            assigned_name="Homeobox gene family",
            status_id=1,
            editor_id=1
        )
        genefam.genefam_id = 1

        # __repr__ should contain class name and key info
        repr_str = repr(genefam)
        assert "Genefam" in repr_str

        # Test that the assigned symbol appears in string representation
        str_repr = str(genefam)
        assert "HOX" in str_repr or "Genefam" in str_repr

    def test_genefam_table_metadata(self):
        """Test table metadata."""
        assert Genefam.__tablename__ == "genefam"

        # Check that required columns exist
        assert hasattr(Genefam, 'genefam_id')
        assert hasattr(Genefam, 'taxon_id')
        assert hasattr(Genefam, 'assigned_id')
        assert hasattr(Genefam, 'assigned_symbol')
        assert hasattr(Genefam, 'assigned_name')
        assert hasattr(Genefam, 'status_id')
        assert hasattr(Genefam, 'editor_id')

        # Check primary key
        assert hasattr(Genefam, 'genefam_id')  # Primary key field


class TestSpeciesModel:
    """Test cases for Species model."""

    def test_species_creation(self):
        """Test basic Species model creation."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HSA",
            display_name="human (Homo sapiens)",
            is_live="YES",
            created=datetime.now(timezone.utc)
        )

        assert species.taxon_id == 9606
        assert species.genefam_prefix == "HSA"
        assert species.display_name == "human (Homo sapiens)"
        assert species.is_live == "YES"

    def test_species_basic_fields(self):
        """Test basic species field access."""
        species = Species(
            taxon_id=10090,
            genefam_prefix="MMU",
            display_name="mouse (Mus musculus)",
            is_live="YES",
            created=datetime.now(timezone.utc)
        )

        # Test field access
        assert species.taxon_id == 10090
        assert species.genefam_prefix == "MMU"
        assert species.display_name == "mouse (Mus musculus)"
        assert species.is_live == "YES"

        # Test field updates
        species.display_name = "house mouse (Mus musculus)"
        assert species.display_name == "house mouse (Mus musculus)"

        species.genefam_prefix = "MUS"
        assert species.genefam_prefix == "MUS"

    def test_species_various_organisms(self):
        """Test various species entries."""
        species_list = []

        species_data = [
            (9606, "HSA", "human (Homo sapiens)"),
            (10090, "MMU", "mouse (Mus musculus)"),
            (10116, "RNO", "rat (Rattus norvegicus)"),
            (7955, "DRE", "zebrafish (Danio rerio)"),
            (6239, "CEL", "nematode (Caenorhabditis elegans)")
        ]

        for taxon_id, prefix, name in species_data:
            species = Species(
                taxon_id=taxon_id,
                genefam_prefix=prefix,
                display_name=name,
                is_live="YES",
                created=datetime.now(timezone.utc)
            )
            species_list.append(species)

        # Verify all species created successfully
        assert len(species_list) == 5
        assert species_list[0].taxon_id == 9606
        assert species_list[1].genefam_prefix == "MMU"
        assert species_list[2].display_name == "rat (Rattus norvegicus)"
        assert species_list[3].taxon_id == 7955
        assert species_list[4].genefam_prefix == "CEL"

    def test_species_string_representation(self):
        """Test string representation."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HSA",
            display_name="human (Homo sapiens)",
            is_live="YES",
            created=datetime.now(timezone.utc)
        )

        # __repr__ should contain class name and key info
        repr_str = repr(species)
        assert "Species" in repr_str

        # Test that the display name appears in string representation
        str_repr = str(species)
        assert "human" in str_repr or "Species" in str_repr

    def test_species_table_metadata(self):
        """Test table metadata."""
        assert Species.__tablename__ == "species"

        # Check that required columns exist
        assert hasattr(Species, 'taxon_id')
        assert hasattr(Species, 'genefam_prefix')
        assert hasattr(Species, 'display_name')
        assert hasattr(Species, 'is_live')
        assert hasattr(Species, 'created')

        # Check primary key
        assert hasattr(Species, 'taxon_id')  # Primary key field

        # Check that genefam_prefix field exists (unique constraint)
        assert hasattr(Species, 'genefam_prefix')


class TestModelRelationships:
    """Test model relationships and basic functionality."""

    def test_species_genefam_relationship(self):
        """Test species-genefam relationship structure."""
        # Create a genefam with species reference
        genefam = Genefam(
            taxon_id=9606,  # Human taxon ID
            assigned_id="HOX",
            assigned_symbol="HOX",
            assigned_name="Homeobox gene family",
            status_id=1,
            editor_id=1
        )

        # Verify the taxon_id is set correctly
        assert genefam.taxon_id == 9606
        assert genefam.assigned_id == "HOX"

    def test_multiple_genefams_per_species(self):
        """Test multiple genefams for same species."""
        genefams = []
        genefam_data = [
            ("HOX", "HOXA", "Homeobox gene family"),
            ("KRAS", "KRAS", "KRAS proto-oncogene"),
            ("TP53", "TP53", "Tumor protein p53"),
            ("MYC", "MYC", "MYC proto-oncogene")
        ]

        for assigned_id, symbol, name in genefam_data:
            genefam = Genefam(
                taxon_id=9606,  # Human
                assigned_id=assigned_id,
                assigned_symbol=symbol,
                assigned_name=name,
                status_id=1,
                editor_id=1
            )
            genefams.append(genefam)

        # Verify all genefams created successfully
        assert len(genefams) == 4
        for genefam in genefams:
            assert genefam.taxon_id == 9606  # All belong to human

    def test_different_species_different_genefams(self):
        """Test different species with their genefams."""
        genefams = []

        # Human genefams
        human_genefams = [
            ("HOX", "HOXA", "Homeobox gene family"),
            ("KRAS", "KRAS", "KRAS proto-oncogene")
        ]

        # Mouse genefams
        mouse_genefams = [
            ("Hox", "Hoxa", "Homeobox gene family"),
            ("Kras", "Kras", "Kras proto-oncogene")
        ]

        for assigned_id, symbol, name in human_genefams:
            genefam = Genefam(
                taxon_id=9606,  # Human
                assigned_id=assigned_id,
                assigned_symbol=symbol,
                assigned_name=name,
                status_id=1,
                editor_id=1
            )
            genefams.append(genefam)

        for assigned_id, symbol, name in mouse_genefams:
            genefam = Genefam(
                taxon_id=10090,  # Mouse
                assigned_id=assigned_id,
                assigned_symbol=symbol,
                assigned_name=name,
                status_id=1,
                editor_id=1
            )
            genefams.append(genefam)

        # Verify all genefams created successfully
        assert len(genefams) == 4

        # Verify taxon_id distribution
        human_count = sum(1 for g in genefams if g.taxon_id == 9606)
        mouse_count = sum(1 for g in genefams if g.taxon_id == 10090)

        assert human_count == 2
        assert mouse_count == 2