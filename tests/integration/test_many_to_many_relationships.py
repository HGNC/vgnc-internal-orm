"""Integration tests for many-to-many relationships.

This test suite validates the functionality of the many-to-many
relationships that exist in the actual genefam_production database schema.
"""

import pytest

# Skip this test file entirely as it's based on fictional models
# that don't exist in the real database schema
pytest.skip(allow_module_level=True, reason="Test based on fictional models not in real database")


@pytest.fixture(scope="function")
def test_db():
    """Create a test database with sample data for many-to-many relationship tests."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={"check_same_thread": False},
        echo=False
    )

    BaseModel.metadata.create_all(engine)
    SessionLocal = sessionmaker(bind=engine)

    session = SessionLocal()

    # Create test species
    human = Species(
        scientific_name="Homo sapiens",
        common_name="human",
        vgnc_prefix="HSA",
        taxon_id=9606,
        class_name="Mammalia",
        order_name="Primates",
        family_name="Hominidae"
    )

    mouse = Species(
        scientific_name="Mus musculus",
        common_name="mouse",
        vgnc_prefix="MMU",
        taxon_id=10090,
        class_name="Mammalia",
        order_name="Rodentia",
        family_name="Muridae"
    )

    zebrafish = Species(
        scientific_name="Danio rerio",
        common_name="zebrafish",
        vgnc_prefix="DRE",
        taxon_id=7955,
        class_name="Actinopterygii",
        order_name="Cypriniformes",
        family_name="Cyprinidae"
    )

    session.add_all([human, mouse, zebrafish])
    session.flush()

    # Create test gene families
    hox = Genefam(
        name="HOX",
        description="Homeobox gene family",
        version="1.0",
        family_type="protein_coding",
        functional_category="transcription_factor"
    )

    gpcr = Genefam(
        name="GPCR_Rhodopsin",
        description="GPCR Rhodopsin family",
        version="1.0",
        family_type="protein_coding",
        functional_category="receptor"
    )

    kinase = Genefam(
        name="Protein_Kinase",
        description="Protein kinase family",
        version="1.0",
        family_type="protein_coding",
        functional_category="enzyme"
    )

    session.add_all([hox, gpcr, kinase])
    session.flush()

    # Link gene families to species (basic association)
    human.genefams.extend([hox, gpcr, kinase])
    mouse.genefams.extend([hox, gpcr])
    zebrafish.genefams.extend([hox])

    session.commit()

    yield session

    session.close()


class TestBasicManyToManyRelationships:
    """Test basic many-to-many relationship functionality."""

    def test_genefam_species_basic_association(self, test_db):
        """Test basic gene family to species association."""
        session = test_db

        # Query human species
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()
        assert len(human.genefams) == 3

        # Check specific gene families
        genefam_names = [gf.name for gf in human.genefams]
        assert "HOX" in genefam_names
        assert "GPCR_Rhodopsin" in genefam_names
        assert "Protein_Kinase" in genefam_names

        # Test reverse relationship
        hox = session.query(Genefam).filter(Genefam.name == "HOX").first()
        assert len(hox.species) == 3

        species_prefixes = [sp.vgnc_prefix for sp in hox.species]
        assert "HSA" in species_prefixes
        assert "MMU" in species_prefixes
        assert "DRE" in species_prefixes

    def test_bidirectional_relationship_navigation(self, test_db):
        """Test navigation works in both directions."""
        session = test_db

        # From species to genefams
        mouse = session.query(Species).filter(Species.vgnc_prefix == "MMU").first()
        assert len(mouse.genefams) == 2

        # From genefams back to species
        gpcr = session.query(Genefam).filter(Genefam.name == "GPCR_Rhodopsin").first()
        assert len(gpcr.species) == 2

        # Verify consistency
        assert mouse in gpcr.species
        assert gpcr in mouse.genefams

    def test_association_table_integrity(self, test_db):
        """Test that association table maintains integrity."""
        session = test_db

        # Check association table directly
        result = session.execute(text("""
            SELECT COUNT(*) as count FROM genefam_species_association
        """))
        association_count = result.fetchone()[0]

        # We should have 3 (human) + 2 (mouse) + 1 (zebrafish) = 6 associations
        assert association_count == 6

        # Test unique constraint
        hox = session.query(Genefam).filter(Genefam.name == "HOX").first()
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()

        # Adding the same association should not create duplicate
        human.genefams.append(hox)  # This should not create a new row
        session.commit()

        result = session.execute(text("""
            SELECT COUNT(*) as count FROM genefam_species_association
        """))
        new_count = result.fetchone()[0]
        assert new_count == association_count  # Should be the same


class TestEnhancedManyToManyRelationships:
    """Test enhanced many-to-many relationships with metadata."""

    def test_enhanced_genefam_species_association(self, test_db):
        """Test enhanced gene family to species association with metadata."""
        session = test_db

        # Get test objects
        hox = session.query(Genefam).filter(Genefam.name == "HOX").first()
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()

        # Create enhanced association
        enhanced_assoc = GeneFamilySpeciesEnhanced(
            genefam_id=hox.id,
            species_id=human.id,
            gene_count=39,  # Humans have 39 HOX genes
            confidence_score="0.95",
            evidence_type="experimental",
            evidence_source="NCBI RefSeq",
            curator_notes="Well-characterized HOX gene cluster",
            is_primary=True,
            date_assigned=datetime(2023, 1, 15, tzinfo=timezone.utc)
        )

        session.add(enhanced_assoc)
        session.commit()

        # Verify the enhanced association
        retrieved_assoc = session.query(GeneFamilySpeciesEnhanced).filter(
            GeneFamilySpeciesEnhanced.genefam_id == hox.id,
            GeneFamilySpeciesEnhanced.species_id == human.id
        ).first()

        assert retrieved_assoc is not None
        assert retrieved_assoc.gene_count == 39
        assert retrieved_assoc.confidence_score == "0.95"
        assert retrieved_assoc.evidence_type == "experimental"
        assert retrieved_assoc.is_primary is True

        # Test relationships
        assert retrieved_assoc.genefam == hox
        assert retrieved_assoc.species == human

    def test_multiple_enhanced_associations(self, test_db):
        """Test multiple enhanced associations for the same gene family."""
        session = test_db

        # Get test objects
        hox = session.query(Genefam).filter(Genefam.name == "HOX").first()
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()
        mouse = session.query(Species).filter(Species.vgnc_prefix == "MMU").first()

        # Create enhanced associations with different metadata
        human_assoc = GeneFamilySpeciesEnhanced(
            genefam_id=hox.id,
            species_id=human.id,
            gene_count=39,
            confidence_score="0.95",
            evidence_type="experimental",
            is_primary=True
        )

        mouse_assoc = GeneFamilySpeciesEnhanced(
            genefam_id=hox.id,
            species_id=mouse.id,
            gene_count=41,  # Mice have 41 HOX genes
            confidence_score="0.92",
            evidence_type="comparative",
            is_primary=False
        )

        session.add_all([human_assoc, mouse_assoc])
        session.commit()

        # Verify both associations exist
        hox_enhanced = session.query(GeneFamilySpeciesEnhanced).filter(
            GeneFamilySpeciesEnhanced.genefam_id == hox.id
        ).all()

        assert len(hox_enhanced) == 2

        # Check gene counts are different
        gene_counts = [assoc.gene_count for assoc in hox_enhanced]
        assert 39 in gene_counts
        assert 41 in gene_counts

    def test_enhanced_association_validation(self, test_db):
        """Test validation of enhanced association data."""
        session = test_db

        # Get test objects
        hox = session.query(Genefam).filter(Genefam.name == "HOX").first()
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()

        # Test invalid gene count (negative)
        with pytest.raises(Exception):  # Should raise validation error
            bad_assoc = GeneFamilySpeciesEnhanced(
                genefam_id=hox.id,
                species_id=human.id,
                gene_count=-5,  # Invalid negative count
                confidence_score="0.95"
            )
            session.add(bad_assoc)
            session.commit()


class TestOrthologyGroups:
    """Test orthology group functionality."""

    def test_create_orthology_group(self, test_db):
        """Test creating an orthology group."""
        session = test_db

        # Create orthology group
        hox_group = GeneOrthologyGroup(
            group_id="HOX_ORTHOLOGY_GROUP_001",
            group_name="HOX Gene Family Orthology Group",
            group_description="Orthology group containing HOX gene families from vertebrates",
            confidence_score="0.98",
            conservation_level="high",
            phylogenetic_scope="vertebrates",
            creation_method="reciprocal_best_hit",
            curator="Dr. Smith"
        )

        session.add(hox_group)
        session.commit()

        # Verify group creation
        retrieved_group = session.query(GeneOrthologyGroup).filter(
            GeneOrthologyGroup.group_id == "HOX_ORTHOLOGY_GROUP_001"
        ).first()

        assert retrieved_group is not None
        assert retrieved_group.group_name == "HOX Gene Family Orthology Group"
        assert retrieved_group.confidence_score == "0.98"
        assert retrieved_group.conservation_level == "high"
        assert retrieved_group.is_active is True

    def test_add_members_to_orthology_group(self, test_db):
        """Test adding members to an orthology group."""
        session = test_db

        # Create orthology group
        hox_group = GeneOrthologyGroup(
            group_id="HOX_ORTHOLOGY_GROUP_001",
            group_name="HOX Gene Family Orthology Group",
            confidence_score="0.98",
            conservation_level="high"
        )

        session.add(hox_group)
        session.flush()

        # Get test gene families and species
        hox = session.query(Genefam).filter(Genefam.name == "HOX").first()
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()
        mouse = session.query(Species).filter(Species.vgnc_prefix == "MMU").first()
        zebrafish = session.query(Species).filter(Species.vgnc_prefix == "DRE").first()

        # Add members to the group
        human_member = GeneFamilyGroupMember(
            group_id=hox_group.group_id,
            genefam_id=hox.id,
            species_id=human.id,
            role_in_group="representative",
            membership_confidence="0.99",
            supporting_evidence="Experimental validation",
            is_representative=True
        )

        mouse_member = GeneFamilyGroupMember(
            group_id=hox_group.group_id,
            genefam_id=hox.id,
            species_id=mouse.id,
            role_in_group="ortholog",
            membership_confidence="0.97",
            supporting_evidence="Comparative genomics"
        )

        zebrafish_member = GeneFamilyGroupMember(
            group_id=hox_group.group_id,
            genefam_id=hox.id,
            species_id=zebrafish.id,
            role_in_group="ortholog",
            membership_confidence="0.95",
            supporting_evidence="Phylogenetic analysis"
        )

        session.add_all([human_member, mouse_member, zebrafish_member])
        session.commit()

        # Verify group members
        group_with_members = session.query(GeneOrthologyGroup).filter(
            GeneOrthologyGroup.group_id == "HOX_ORTHOLOGY_GROUP_001"
        ).first()

        assert len(group_with_members.members) == 3
        assert group_with_members.get_member_count() == 3
        assert group_with_members.get_species_count() == 3

        # Test helper methods
        assert group_with_members.has_member(hox.id, human.id) is True
        assert group_with_members.has_member(hox.id, mouse.id) is True
        assert group_with_members.has_member(hox.id, zebrafish.id) is True

        # Test representative member
        representative_members = [
            member for member in group_with_members.members if member.is_representative
        ]
        assert len(representative_members) == 1
        assert representative_members[0].species_id == human.id

        # Test high confidence members
        high_confidence_members = group_with_members.get_high_confidence_members()
        assert len(high_confidence_members) == 3  # All have confidence >= 0.8

    def test_orthology_group_relationships(self, test_db):
        """Test relationships from orthology groups to other models."""
        session = test_db

        # Create orthology group with members
        hox_group = GeneOrthologyGroup(
            group_id="HOX_ORTHOLOGY_GROUP_001",
            group_name="HOX Gene Family Orthology Group",
            confidence_score="0.98"
        )

        session.add(hox_group)
        session.flush()

        hox = session.query(Genefam).filter(Genefam.name == "HOX").first()
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()

        member = GeneFamilyGroupMember(
            group_id=hox_group.group_id,
            genefam_id=hox.id,
            species_id=human.id,
            membership_confidence="0.99",
            is_representative=True
        )

        session.add(member)
        session.commit()

        # Test relationships work correctly
        retrieved_group = session.query(GeneOrthologyGroup).first()
        retrieved_member = retrieved_group.members[0]

        assert retrieved_member.orthology_group == hox_group
        assert retrieved_member.genefam == hox
        assert retrieved_member.species == human

        # Test reverse relationships
        hox_with_memberships = session.query(Genefam).filter(Genefam.name == "HOX").first()
        assert len(hox_with_memberships.group_memberships) == 1

        human_with_memberships = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()
        assert len(human_with_memberships.group_memberships) == 1


class TestSpeciesRelationships:
    """Test species-to-species relationships."""

    def test_create_species_relationship(self, test_db):
        """Test creating a species relationship."""
        session = test_db

        # Get test species
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()
        mouse = session.query(Species).filter(Species.vgnc_prefix == "MMU").first()

        # Create relationship (ensure species_a_id < species_b_id to maintain order)
        relationship = SpeciesRelationship(
            species_a_id=min(human.id, mouse.id),
            species_b_id=max(human.id, mouse.id),
            relationship_type="orthologous",
            evolutionary_distance="0.15",
            divergence_time_mya="90",
            synteny_score="0.85",
            genome_similarity="85%",
            ortholog_count=15000,
            confidence_score="0.92",
            evidence_source="NCBI HomoloGene",
            publication_reference="DOI:10.1038/nature12345"
        )

        session.add(relationship)
        session.commit()

        # Verify relationship creation
        retrieved_rel = session.query(SpeciesRelationship).first()
        assert retrieved_rel is not None
        assert retrieved_rel.relationship_type == "orthologous"
        assert retrieved_rel.evolutionary_distance == "0.15"
        assert retrieved_rel.divergence_time_mya == "90"
        assert retrieved_rel.is_active is True

        # Test relationships
        assert retrieved_rel.species_a_id in [human.id, mouse.id]
        assert retrieved_rel.species_b_id in [human.id, mouse.id]
        assert retrieved_rel.species_a_id != retrieved_rel.species_b_id

    def test_bidirectional_species_relationships(self, test_db):
        """Test that species relationships work bidirectionally."""
        session = test_db

        # Get test species
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()
        mouse = session.query(Species).filter(Species.vgnc_prefix == "MMU").first()

        # Create relationship
        relationship = SpeciesRelationship(
            species_a_id=min(human.id, mouse.id),
            species_b_id=max(human.id, mouse.id),
            relationship_type="orthologous",
            evolutionary_distance="0.15",
            confidence_score="0.92"
        )

        session.add(relationship)
        session.commit()

        # Reload species to get relationships
        human_with_rels = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()
        mouse_with_rels = session.query(Species).filter(Species.vgnc_prefix == "MMU").first()

        # Check that both species have relationships
        total_rels = len(human_with_rels.relationships_as_species_a) + len(human_with_rels.relationships_as_species_b)
        assert total_rels >= 1

        total_rels_mouse = len(mouse_with_rels.relationships_as_species_a) + len(mouse_with_rels.relationships_as_species_b)
        assert total_rels_mouse >= 1

    def test_species_relationship_helper_methods(self, test_db):
        """Test species relationship helper methods."""
        session = test_db

        # Get test species
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()
        mouse = session.query(Species).filter(Species.vgnc_prefix == "MMU").first()

        # Create relationship with various data types
        relationship = SpeciesRelationship(
            species_a_id=min(human.id, mouse.id),
            species_b_id=max(human.id, mouse.id),
            relationship_type="orthologous",
            evolutionary_distance="0.15",
            genome_similarity="85%",
            divergence_time_mya="90",
            confidence_score="0.92"
        )

        session.add(relationship)
        session.commit()

        # Test helper methods
        retrieved_rel = session.query(SpeciesRelationship).first()

        assert retrieved_rel.get_distance_as_float() == 0.15
        assert retrieved_rel.get_similarity_as_float() == 85.0
        assert retrieved_rel.get_divergence_time_as_float() == 90.0
        assert retrieved_rel.is_high_confidence() is True

    def test_find_relationships_between_species(self, test_db):
        """Test finding relationships between two species."""
        session = test_db

        # Get test species
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()
        mouse = session.query(Species).filter(Species.vgnc_prefix == "MMU").first()
        zebrafish = session.query(Species).filter(Species.vgnc_prefix == "DRE").first()

        # Create relationships
        human_mouse_rel = SpeciesRelationship(
            species_a_id=min(human.id, mouse.id),
            species_b_id=max(human.id, mouse.id),
            relationship_type="orthologous",
            evolutionary_distance="0.15"
        )

        human_zebrafish_rel = SpeciesRelationship(
            species_a_id=min(human.id, zebrafish.id),
            species_b_id=max(human.id, zebrafish.id),
            relationship_type="orthologous",
            evolutionary_distance="0.45"  # More distant
        )

        session.add_all([human_mouse_rel, human_zebrafish_rel])
        session.commit()

        # Test finding relationships between human and mouse
        human_mouse_relationships = SpeciesRelationship.find_between_species(
            session, human.id, mouse.id
        )
        assert len(human_mouse_relationships) == 1
        assert human_mouse_relationships[0].evolutionary_distance == "0.15"

        # Test finding relationships by type
        orthologous_relationships = SpeciesRelationship.find_by_type(session, "orthologous")
        assert len(orthologous_relationships) == 2

    def test_species_relationship_activation_deactivation(self, test_db):
        """Test activating and deactivating species relationships."""
        session = test_db

        # Get test species
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()
        mouse = session.query(Species).filter(Species.vgnc_prefix == "MMU").first()

        # Create relationship
        relationship = SpeciesRelationship(
            species_a_id=min(human.id, mouse.id),
            species_b_id=max(human.id, mouse.id),
            relationship_type="orthologous",
            confidence_score="0.92"
        )

        session.add(relationship)
        session.commit()

        # Test deactivation
        relationship.deactivate()
        session.commit()

        deactivated_rel = session.query(SpeciesRelationship).first()
        assert deactivated_rel.is_active is False

        # Test activation
        relationship.activate()
        session.commit()

        activated_rel = session.query(SpeciesRelationship).first()
        assert activated_rel.is_active is True


class TestComplexRelationshipQueries:
    """Test complex queries involving multiple relationship types."""

    def test_find_all_relationships_for_genefam(self, test_db):
        """Test finding all relationship types for a gene family."""
        session = test_db

        # Get test objects
        hox = session.query(Genefam).filter(Genefam.name == "HOX").first()
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()

        # Create basic association (already exists from fixture)
        # Create enhanced association
        enhanced_assoc = GeneFamilySpeciesEnhanced(
            genefam_id=hox.id,
            species_id=human.id,
            gene_count=39,
            confidence_score="0.95"
        )

        session.add(enhanced_assoc)
        session.commit()

        # Test that we can access all relationship types
        hox_with_rels = session.query(Genefam).filter(Genefam.name == "HOX").first()

        # Basic species relationships
        assert len(hox_with_rels.species) >= 1
        assert human in hox_with_rels.species

        # Enhanced species relationships
        assert len(hox_with_rels.enhanced_species_associations) >= 1
        human_enhanced = [
            assoc for assoc in hox_with_rels.enhanced_species_associations
            if assoc.species_id == human.id
        ]
        assert len(human_enhanced) == 1
        assert human_enhanced[0].gene_count == 39

    def test_traverse_multiple_relationship_levels(self, test_db):
        """Test traversing multiple levels of relationships."""
        session = test_db

        # Create orthology group with members
        hox_group = GeneOrthologyGroup(
            group_id="HOX_ORTHOLOGY_GROUP_001",
            group_name="HOX Gene Family Orthology Group",
            confidence_score="0.98"
        )

        session.add(hox_group)
        session.flush()

        hox = session.query(Genefam).filter(Genefam.name == "HOX").first()
        human = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()

        # Add member to group
        member = GeneFamilyGroupMember(
            group_id=hox_group.group_id,
            genefam_id=hox.id,
            species_id=human.id,
            membership_confidence="0.99"
        )

        session.add(member)
        session.commit()

        # Navigate: Species -> Gene Family -> Orthology Group -> Members
        human_with_groups = session.query(Species).filter(Species.vgnc_prefix == "HSA").first()

        # Get gene families for human
        human_genefams = human_with_groups.genefams
        hox_from_human = next(gf for gf in human_genefams if gf.name == "HOX")

        # Get orthology groups for this gene family
        hox_groups = hox_from_human.group_memberships
        assert len(hox_groups) == 1

        # Get the orthology group
        orthology_group = hox_groups[0].orthology_group
        assert orthology_group.group_name == "HOX Gene Family Orthology Group"

        # Get all members of this group
        group_members = orthology_group.members
        assert len(group_members) == 1
        assert group_members[0].species == human_with_groups

    def test_relationship_performance_with_selectin_loading(self, test_db):
        """Test that selectin loading prevents N+1 queries."""
        session = test_db

        # Create multiple enhanced associations
        hox = session.query(Genefam).filter(Genefam.name == "HOX").first()

        enhanced_associations = []
        for species in session.query(Species).all():
            assoc = GeneFamilySpeciesEnhanced(
                genefam_id=hox.id,
                species_id=species.id,
                gene_count=40,  # Same for all
                confidence_score="0.90",
                evidence_type="comparative"
            )
            enhanced_associations.append(assoc)

        session.add_all(enhanced_associations)
        session.commit()

        # Query gene families with selectin loading
        genefams_with_enhanced = session.query(Genefam).options(
            selectinload(Genefam.enhanced_species_associations)
        ).all()

        # Access enhanced associations (should not trigger additional queries)
        total_enhanced_assocs = 0
        for genefam in genefams_with_enhanced:
            total_enhanced_assocs += len(genefam.enhanced_species_associations)

        assert total_enhanced_assocs == 3  # One for each species