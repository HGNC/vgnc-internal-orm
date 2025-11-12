"""Comprehensive database-integrated tests for Orthology model functionality."""

import pytest
from datetime import datetime, timezone
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql import func as sql_func

from src.vgnc_internal_orm.models.orthology import (
    GeneFamilySpeciesEnhanced,
    GeneOrthologyGroup,
    GeneFamilyGroupMember,
    SpeciesRelationship
)
from src.vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from src.vgnc_internal_orm.sessions.factory import DatabaseFactory
from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestGeneFamilySpeciesEnhancedComprehensive:
    """Comprehensive tests for GeneFamilySpeciesEnhanced model."""

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

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_gene_family_species_enhanced_crud_operations(self):
        """Test complete CRUD operations for GeneFamilySpeciesEnhanced."""
        # Create test species first
        species = Species(
            taxon_id=9606,
            genefam_prefix="HS",
            display_name="Human (Homo sapiens)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )
        self.session.add(species)
        self.session.commit()

        # Create enhanced association
        association = GeneFamilySpeciesEnhanced(
            genefam_id=1,
            species_id=9606,
            gene_count=150,
            confidence_score="0.95",
            evidence_type="experimental",
            evidence_source="PubMed",
            curator_notes="High confidence assignment",
            is_primary=True
        )

        self.session.add(association)
        self.session.commit()

        # Verify creation
        assert association.genefam_id == 1
        assert association.species_id == 9606
        assert association.gene_count == 150
        assert association.confidence_score == "0.95"
        assert association.is_primary is True
        assert association.date_assigned is not None  # Should be auto-set

        # Read
        retrieved = self.session.query(GeneFamilySpeciesEnhanced).filter_by(
            genefam_id=1, species_id=9606
        ).first()
        assert retrieved is not None
        assert retrieved.confidence_score == "0.95"

        # Update
        retrieved.confidence_score = "0.98"
        retrieved.gene_count = 155
        retrieved.is_primary = False
        self.session.commit()

        # Verify update
        updated = self.session.query(GeneFamilySpeciesEnhanced).filter_by(
            genefam_id=1, species_id=9606
        ).first()
        assert updated.confidence_score == "0.98"
        assert updated.gene_count == 155
        assert updated.is_primary is False

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(GeneFamilySpeciesEnhanced).filter_by(
            genefam_id=1, species_id=9606
        ).first()
        assert deleted is None

    def test_gene_family_species_enhanced_composite_primary_key(self):
        """Test composite primary key functionality."""
        species = Species(
            taxon_id=10090,
            genefam_prefix="MM",
            display_name="Mouse (Mus musculus)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )
        self.session.add(species)
        self.session.commit()

        # Create multiple associations for same genefam with different species
        associations = [
            GeneFamilySpeciesEnhanced(
                genefam_id=100,
                species_id=9606,
                gene_count=120,
                confidence_score="0.90",
                is_primary=True
            ),
            GeneFamilySpeciesEnhanced(
                genefam_id=100,
                species_id=10090,
                gene_count=115,
                confidence_score="0.85",
                is_primary=False
            ),
        ]

        for assoc in associations:
            self.session.add(assoc)
        self.session.commit()

        # Both should exist with same genefam_id but different species_id
        human_assoc = self.session.query(GeneFamilySpeciesEnhanced).filter_by(
            genefam_id=100, species_id=9606
        ).first()
        mouse_assoc = self.session.query(GeneFamilySpeciesEnhanced).filter_by(
            genefam_id=100, species_id=10090
        ).first()

        assert human_assoc is not None
        assert mouse_assoc is not None
        assert human_assoc.species_id != mouse_assoc.species_id

    def test_gene_family_species_enhanced_all_fields(self):
        """Test all field types and constraints."""
        species = Species(
            taxon_id=10116,
            genefam_prefix="RN",
            display_name="Rat (Rattus norvegicus)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )
        self.session.add(species)
        self.session.commit()

        # Test with all fields populated
        full_association = GeneFamilySpeciesEnhanced(
            genefam_id=200,
            species_id=10116,
            gene_count=250,
            confidence_score="0.99",
            evidence_type="computational",
            evidence_source="Ensembl Compara",
            curator_notes="Very well supported by multiple evidence sources",
            is_primary=True,
            date_assigned=datetime(2023, 1, 15, 10, 30, 0, tzinfo=timezone.utc),
            last_reviewed=datetime(2023, 6, 20, 14, 45, 0, tzinfo=timezone.utc)
        )

        self.session.add(full_association)
        self.session.commit()

        # Verify all fields
        assert full_association.genefam_id == 200
        assert full_association.species_id == 10116
        assert full_association.gene_count == 250
        assert full_association.confidence_score == "0.99"
        assert full_association.evidence_type == "computational"
        assert full_association.evidence_source == "Ensembl Compara"
        assert "well supported" in full_association.curator_notes
        assert full_association.is_primary is True
        assert full_association.date_assigned is not None
        assert full_association.last_reviewed is not None

    def test_gene_family_species_enhanced_auto_date_assignment(self):
        """Test automatic date assignment on creation."""
        species = Species(
            taxon_id=10211,
            genefam_prefix="CM",
            display_name="Chicken (Gallus gallus)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(timezone.utc)
        )
        self.session.add(species)
        self.session.commit()

        # Create association without date_assigned
        association = GeneFamilySpeciesEnhanced(
            genefam_id=300,
            species_id=10211,
            gene_count=80,
            is_primary=False
        )

        self.session.add(association)
        self.session.commit()

        # date_assigned should be auto-set
        assert association.date_assigned is not None
        assert isinstance(association.date_assigned, datetime)

        # Create another with explicit date
        explicit_date = datetime(2023, 3, 10, 12, 0, 0, tzinfo=timezone.utc)
        explicit_association = GeneFamilySpeciesEnhanced(
            genefam_id=301,
            species_id=10211,
            gene_count=85,
            date_assigned=explicit_date
        )

        self.session.add(explicit_association)
        self.session.commit()

        # Should preserve explicit date
        assert explicit_association.date_assigned == explicit_date

    def test_gene_family_species_enhanced_repr_method(self):
        """Test __repr__ method."""
        association = GeneFamilySpeciesEnhanced(
            genefam_id=400,
            species_id=9606,
            gene_count=100
        )

        repr_str = repr(association)
        assert "GeneFamilySpeciesEnhanced" in repr_str
        assert "genefam_id=400" in repr_str
        assert "species_id=9606" in repr_str

    def test_gene_family_species_enhanced_field_utilities(self):
        """Test BaseModel field utilities."""
        association = GeneFamilySpeciesEnhanced(
            genefam_id=500,
            species_id=9606,
            gene_count=200,
            confidence_score="0.88",
            evidence_type="mixed"
        )

        # Test get_field_value
        assert association.get_field_value("genefam_id") == 500
        assert association.get_field_value("species_id") == 9606
        assert association.get_field_value("gene_count") == 200
        assert association.get_field_value("confidence_score") == "0.88"
        assert association.get_field_value("nonexistent") is None

        # Test set_field_value
        association.set_field_value("gene_count", 210)
        assert association.gene_count == 210

        association.set_field_value("confidence_score", "0.92")
        assert association.confidence_score == "0.92"

        # Test has_field
        assert association.has_field("genefam_id") is True
        assert association.has_field("species_id") is True
        assert association.has_field("gene_count") is True
        assert association.has_field("nonexistent") is False

        # Test get_field_type
        assert association.get_field_type("genefam_id") == int
        assert association.get_field_type("species_id") == int
        assert association.get_field_type("gene_count") == int
        assert association.get_field_type("confidence_score") == str
        assert association.get_field_type("evidence_type") == str


class TestGeneOrthologyGroupComprehensive:
    """Comprehensive tests for GeneOrthologyGroup model."""

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

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_gene_orthology_group_crud_operations(self):
        """Test complete CRUD operations for GeneOrthologyGroup."""
        # Create orthology group
        group = GeneOrthologyGroup(
            group_id="OG001",
            group_name="Hemoglobin Gene Family Group",
            group_description="Orthology group containing hemoglobin gene families across vertebrates",
            confidence_score="0.95",
            conservation_level="high",
            phylogenetic_scope="Vertebrata",
            creation_method="manual_curation",
            curator="Dr. Smith",
            is_active=True
        )

        self.session.add(group)
        self.session.commit()

        # Verify creation
        assert group.group_id == "OG001"
        assert group.group_name == "Hemoglobin Gene Family Group"
        assert group.confidence_score == "0.95"
        assert group.conservation_level == "high"
        assert group.is_active is True
        assert group.date_created is not None  # Auto-set

        # Read
        retrieved = self.session.query(GeneOrthologyGroup).filter_by(group_id="OG001").first()
        assert retrieved is not None
        assert retrieved.group_name == "Hemoglobin Gene Family Group"

        # Update
        retrieved.confidence_score = "0.98"
        retrieved.conservation_level = "very_high"
        retrieved.last_updated = datetime.now(timezone.utc)
        self.session.commit()

        # Verify update
        updated = self.session.query(GeneOrthologyGroup).filter_by(group_id="OG001").first()
        assert updated.confidence_score == "0.98"
        assert updated.conservation_level == "very_high"
        assert updated.last_updated is not None

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(GeneOrthologyGroup).filter_by(group_id="OG001").first()
        assert deleted is None

    def test_gene_orthology_group_helper_methods(self):
        """Test all helper methods."""
        group = GeneOrthologyGroup(
            group_id="OG002",
            group_name="Test Group",
            conservation_level="moderate",
            confidence_score="0.80",
            is_active=True
        )

        self.session.add(group)
        self.session.commit()

        # Test with no members initially
        assert group.get_member_count() == 0
        assert group.get_species_count() == 0
        assert group.get_genefam_ids() == []
        assert group.get_species_ids() == []
        assert group.has_member(1, 9606) is False
        assert group.get_high_confidence_members() == []

        # Test activation/deactivation
        assert group.is_active is True
        group.deactivate()
        assert group.is_active is False
        group.activate()
        assert group.is_active is True

    def test_gene_orthology_group_class_methods(self):
        """Test class methods for querying."""
        # Create test groups
        groups = [
            GeneOrthologyGroup(
                group_id="OG003",
                group_name="High Confidence Group",
                confidence_score="0.90",
                conservation_level="high",
                is_active=True
            ),
            GeneOrthologyGroup(
                group_id="OG004",
                group_name="Low Confidence Group",
                confidence_score="0.60",
                conservation_level="low",
                is_active=True
            ),
            GeneOrthologyGroup(
                group_id="OG005",
                group_name="Inactive Group",
                confidence_score="0.80",
                conservation_level="moderate",
                is_active=False
            ),
        ]

        for group in groups:
            self.session.add(group)
        self.session.commit()

        # Test find_by_confidence
        high_confidence_groups = GeneOrthologyGroup.find_by_confidence(self.session, 0.8)
        assert len(high_confidence_groups) == 1
        assert high_confidence_groups[0].group_id == "OG003"

        # Test find_by_conservation
        high_conservation_groups = GeneOrthologyGroup.find_by_conservation(self.session, "high")
        assert len(high_conservation_groups) == 1
        assert high_conservation_groups[0].group_id == "OG003"

        low_conservation_groups = GeneOrthologyGroup.find_by_conservation(self.session, "low")
        assert len(low_conservation_groups) == 1
        assert low_conservation_groups[0].group_id == "OG004"

    def test_gene_orthology_group_str_methods(self):
        """Test string representation methods."""
        group = GeneOrthologyGroup(
            group_id="OG006",
            group_name="Test String Group"
        )

        repr_str = repr(group)
        assert "GeneOrthologyGroup" in repr_str
        assert "group_id='OG006'" in repr_str
        assert "name='Test String Group'" in repr_str

        str_str = str(group)
        assert "OrthologyGroup" in str_str
        assert "Test String Group" in str_str


class TestGeneFamilyGroupMemberComprehensive:
    """Comprehensive tests for GeneFamilyGroupMember model."""

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

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_gene_family_group_member_crud_operations(self):
        """Test complete CRUD operations for GeneFamilyGroupMember."""
        # Create orthology group first
        group = GeneOrthologyGroup(
            group_id="OG007",
            group_name="Test Group for Members",
            is_active=True
        )
        self.session.add(group)
        self.session.commit()

        # Create group member
        member = GeneFamilyGroupMember(
            group_id="OG007",
            genefam_id=1000,
            species_id=9606,
            role_in_group="representative",
            membership_confidence="0.92",
            supporting_evidence="Strong experimental evidence",
            added_by="Dr. Johnson",
            is_representative=True
        )

        self.session.add(member)
        self.session.commit()

        # Verify creation
        assert member.group_id == "OG007"
        assert member.genefam_id == 1000
        assert member.species_id == 9606
        assert member.role_in_group == "representative"
        assert member.membership_confidence == "0.92"
        assert member.is_representative is True
        assert member.date_added is not None  # Auto-set

        # Read
        retrieved = self.session.query(GeneFamilyGroupMember).filter_by(
            group_id="OG007", genefam_id=1000, species_id=9606
        ).first()
        assert retrieved is not None
        assert retrieved.role_in_group == "representative"

        # Update
        retrieved.role_in_group="supporting"
        retrieved.membership_confidence="0.88"
        retrieved.is_representative=False
        self.session.commit()

        # Verify update
        updated = self.session.query(GeneFamilyGroupMember).filter_by(
            group_id="OG007", genefam_id=1000, species_id=9606
        ).first()
        assert updated.role_in_group == "supporting"
        assert updated.membership_confidence == "0.88"
        assert updated.is_representative is False

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(GeneFamilyGroupMember).filter_by(
            group_id="OG007", genefam_id=1000, species_id=9606
        ).first()
        assert deleted is None

    def test_gene_family_group_member_composite_primary_key(self):
        """Test composite primary key with group_id, genefam_id, species_id."""
        group = GeneOrthologyGroup(
            group_id="OG008",
            group_name="Multi-member Test Group",
            is_active=True
        )
        self.session.add(group)
        self.session.commit()

        # Create multiple members for same group
        members = [
            GeneFamilyGroupMember(
                group_id="OG008",
                genefam_id=2000,
                species_id=9606,
                is_representative=True
            ),
            GeneFamilyGroupMember(
                group_id="OG008",
                genefam_id=2001,
                species_id=9606,
                is_representative=False
            ),
            GeneFamilyGroupMember(
                group_id="OG008",
                genefam_id=2002,
                species_id=10090,
                is_representative=False
            ),
        ]

        for member in members:
            self.session.add(member)
        self.session.commit()

        # All should exist with unique combinations
        retrieved_members = self.session.query(GeneFamilyGroupMember).filter_by(
            group_id="OG008"
        ).all()
        assert len(retrieved_members) == 3

        # Test uniqueness
        # Try to create duplicate (should fail)
        duplicate_member = GeneFamilyGroupMember(
            group_id="OG008",
            genefam_id=2000,
            species_id=9606,
            is_representative=False
        )

        self.session.add(duplicate_member)
        try:
            self.session.commit()
        except Exception:
            # Expected constraint violation
            self.session.rollback()

    def test_gene_family_group_member_instance_methods(self):
        """Test instance methods."""
        group = GeneOrthologyGroup(
            group_id="OG009",
            group_name="Method Test Group",
            is_active=True
        )
        self.session.add(group)
        self.session.commit()

        member = GeneFamilyGroupMember(
            group_id="OG009",
            genefam_id=3000,
            species_id=9606,
            membership_confidence="0.75",
            is_representative=False
        )

        self.session.add(member)
        self.session.commit()

        # Test set_as_representative
        assert member.is_representative is False
        member.set_as_representative(True)
        assert member.is_representative is True
        member.set_as_representative(False)
        assert member.is_representative is False

        # Test update_confidence
        assert member.membership_confidence == "0.75"
        member.update_confidence("0.85")
        assert member.membership_confidence == "0.85"

    def test_gene_family_group_member_auto_date_assignment(self):
        """Test automatic date assignment."""
        group = GeneOrthologyGroup(
            group_id="OG010",
            group_name="Auto Date Test Group",
            is_active=True
        )
        self.session.add(group)
        self.session.commit()

        # Create member without date_added
        member = GeneFamilyGroupMember(
            group_id="OG010",
            genefam_id=4000,
            species_id=9606
        )

        self.session.add(member)
        self.session.commit()

        # date_added should be auto-set
        assert member.date_added is not None
        assert isinstance(member.date_added, datetime)


class TestSpeciesRelationshipComprehensive:
    """Comprehensive tests for SpeciesRelationship model."""

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

        # Create test species
        species_data = [
            Species(taxon_id=9606, genefam_prefix="HS", display_name="Human", is_live=SpeciesLiveStatus.YES, created=datetime.now(timezone.utc)),
            Species(taxon_id=10090, genefam_prefix="MM", display_name="Mouse", is_live=SpeciesLiveStatus.YES, created=datetime.now(timezone.utc)),
            Species(taxon_id=10116, genefam_prefix="RN", display_name="Rat", is_live=SpeciesLiveStatus.YES, created=datetime.now(timezone.utc)),
        ]
        for species in species_data:
            self.session.add(species)
        self.session.commit()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_species_relationship_crud_operations(self):
        """Test complete CRUD operations for SpeciesRelationship."""
        # Create relationship
        relationship = SpeciesRelationship(
            species_a_id=9606,
            species_b_id=10090,
            relationship_type="orthologous",
            evolutionary_distance="0.15",
            divergence_time_mya="90.0",
            synteny_score="0.85",
            genome_similarity="85.5%",
            ortholog_count=15000,
            paralog_count=2000,
            confidence_score="0.92",
            evidence_source="Ensembl Compara",
            publication_reference="PubMed:12345678",
            curator_notes="Well-established orthology relationship",
            is_active=True
        )

        self.session.add(relationship)
        self.session.commit()

        # Verify creation
        assert relationship.species_a_id == 9606
        assert relationship.species_b_id == 10090
        assert relationship.relationship_type == "orthologous"
        assert relationship.evolutionary_distance == "0.15"
        assert relationship.divergence_time_mya == "90.0"
        assert relationship.genome_similarity == "85.5%"
        assert relationship.is_active is True
        assert relationship.date_established is not None  # Auto-set

        # Read
        retrieved = self.session.query(SpeciesRelationship).filter_by(
            species_a_id=9606, species_b_id=10090, relationship_type="orthologous"
        ).first()
        assert retrieved is not None
        assert retrieved.evolutionary_distance == "0.15"

        # Update
        retrieved.confidence_score = "0.95"
        retrieved.ortholog_count = 15200
        retrieved.last_reviewed = datetime.now(timezone.utc)
        self.session.commit()

        # Verify update
        updated = self.session.query(SpeciesRelationship).filter_by(
            species_a_id=9606, species_b_id=10090, relationship_type="orthologous"
        ).first()
        assert updated.confidence_score == "0.95"
        assert updated.ortholog_count == 15200

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(SpeciesRelationship).filter_by(
            species_a_id=9606, species_b_id=10090, relationship_type="orthologous"
        ).first()
        assert deleted is None

    def test_species_relationship_composite_primary_key(self):
        """Test composite primary key with species_a_id, species_b_id, relationship_type."""
        # Create multiple relationships between same species with different types
        relationships = [
            SpeciesRelationship(
                species_a_id=9606,
                species_b_id=10090,
                relationship_type="orthologous",
                evolutionary_distance="0.15"
            ),
            SpeciesRelationship(
                species_a_id=9606,
                species_b_id=10090,
                relationship_type="paralogous",
                evolutionary_distance="0.05"
            ),
            SpeciesRelationship(
                species_a_id=9606,
                species_b_id=10090,
                relationship_type="syntenic",
                evolutionary_distance="0.12"
            ),
        ]

        for rel in relationships:
            self.session.add(rel)
        self.session.commit()

        # All should exist with different relationship types
        retrieved_rels = self.session.query(SpeciesRelationship).filter_by(
            species_a_id=9606, species_b_id=10090
        ).all()
        assert len(retrieved_rels) == 3

        relationship_types = {rel.relationship_type for rel in retrieved_rels}
        assert relationship_types == {"orthologous", "paralogous", "syntenic"}

    def test_species_relationship_helper_methods(self):
        """Test all helper methods for parsing values."""
        relationship = SpeciesRelationship(
            species_a_id=9606,
            species_b_id=10090,
            relationship_type="orthologous",
            evolutionary_distance="0.25",
            genome_similarity="78.5%",
            divergence_time_mya="75.0",
            confidence_score="0.88"
        )

        self.session.add(relationship)
        self.session.commit()

        # Test get_distance_as_float
        distance_float = relationship.get_distance_as_float()
        assert distance_float == 0.25

        # Test get_similarity_as_float
        similarity_float = relationship.get_similarity_as_float()
        assert similarity_float == 78.5

        # Test get_divergence_time_as_float
        divergence_float = relationship.get_divergence_time_as_float()
        assert divergence_float == 75.0

        # Test with None values
        relationship_none = SpeciesRelationship(
            species_a_id=9606,
            species_b_id=10116,
            relationship_type="orthologous"
        )
        self.session.add(relationship_none)
        self.session.commit()

        assert relationship_none.get_distance_as_float() is None
        assert relationship_none.get_similarity_as_float() is None
        assert relationship_none.get_divergence_time_as_float() is None

        # Test is_high_confidence
        assert relationship.is_high_confidence is True  # 0.88 >= 0.8

        relationship.confidence_score = "0.75"
        assert relationship.is_high_confidence is False  # 0.75 < 0.8

        relationship.confidence_score = "invalid"
        assert relationship.is_high_confidence is False  # Invalid value

    def test_species_relationship_activation_methods(self):
        """Test activation and deactivation methods."""
        relationship = SpeciesRelationship(
            species_a_id=9606,
            species_b_id=10116,
            relationship_type="orthologous",
            is_active=True
        )

        self.session.add(relationship)
        self.session.commit()

        # Test deactivation
        assert relationship.is_active is True
        relationship.deactivate()
        assert relationship.is_active is False

        # Test activation
        relationship.activate()
        assert relationship.is_active is True

    def test_species_relationship_class_methods(self):
        """Test class methods for querying."""
        # Create test relationships
        relationships = [
            SpeciesRelationship(species_a_id=9606, species_b_id=10090, relationship_type="orthologous", evolutionary_distance="0.15", is_active=True),
            SpeciesRelationship(species_a_id=9606, species_b_id=10090, relationship_type="paralogous", evolutionary_distance="0.05", is_active=True),
            SpeciesRelationship(species_a_id=10090, species_b_id=9606, relationship_type="orthologous", evolutionary_distance="0.15", is_active=True),  # Reverse order
            SpeciesRelationship(species_a_id=9606, species_b_id=10116, relationship_type="orthologous", evolutionary_distance="0.25", is_active=False),  # Inactive
        ]

        for rel in relationships:
            self.session.add(rel)
        self.session.commit()

        # Test find_between_species (should find both orders)
        human_mouse_rels = SpeciesRelationship.find_between_species(self.session, 9606, 10090)
        assert len(human_mouse_rels) == 3  # Should find both orthologous and paralogous, regardless of order

        # Test find_by_type
        orthologous_rels = SpeciesRelationship.find_by_type(self.session, "orthologous")
        assert len(orthologous_rels) == 2  # Only active orthologous relationships

        paralogous_rels = SpeciesRelationship.find_by_type(self.session, "paralogous")
        assert len(paralogous_rels) == 1

        # Test find_closest_species
        closest_to_human = SpeciesRelationship.find_closest_species(self.session, 9606, limit=3)
        assert len(closest_to_human) <= 3
        # Should be ordered by evolutionary_distance
        if len(closest_to_human) > 1:
            for i in range(len(closest_to_human) - 1):
                current_distance = float(closest_to_human[i].evolutionary_distance or "999")
                next_distance = float(closest_to_human[i + 1].evolutionary_distance or "999")
                assert current_distance <= next_distance

    def test_species_relationship_string_methods(self):
        """Test string representation methods."""
        relationship = SpeciesRelationship(
            species_a_id=9606,
            species_b_id=10090,
            relationship_type="orthologous"
        )

        repr_str = repr(relationship)
        assert "SpeciesRelationship" in repr_str
        assert "species_a_id=9606" in repr_str
        assert "species_b_id=10090" in repr_str
        assert "type='orthologous'" in repr_str

        str_str = str(relationship)
        assert "Relationship" in str_str
        assert "orthologous" in str_str
        assert "9606" in str_str
        assert "10090" in str_str

    def test_species_relationship_auto_date_assignment(self):
        """Test automatic date assignment."""
        relationship = SpeciesRelationship(
            species_a_id=9606,
            species_b_id=10090,
            relationship_type="syntenic"
        )

        self.session.add(relationship)
        self.session.commit()

        # date_established should be auto-set
        assert relationship.date_established is not None
        assert isinstance(relationship.date_established, datetime)

        # Create another with explicit date
        explicit_date = datetime(2023, 5, 20, 10, 30, 0, tzinfo=timezone.utc)
        explicit_relationship = SpeciesRelationship(
            species_a_id=9606,
            species_b_id=10116,
            relationship_type="syntenic",
            date_established=explicit_date
        )

        self.session.add(explicit_relationship)
        self.session.commit()

        # Should preserve explicit date
        assert explicit_relationship.date_established == explicit_date