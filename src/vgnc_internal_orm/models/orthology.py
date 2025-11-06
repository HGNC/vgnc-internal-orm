"""Orthology and complex relationship models for the VGNC ORM system.

This module contains models for complex many-to-many relationships with metadata
support, including orthology groups, gene orthology relationships, and species
relationships.
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, Text, DateTime, Boolean, Index, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func

from .base import BaseCustomModel

if TYPE_CHECKING:
    from .species import Species
    from .genefam import Genefam


class GeneFamilySpeciesEnhanced(BaseCustomModel):
    """Enhanced association model for GeneFamily-Species relationships with metadata.

    This model extends the basic many-to-many relationship between gene families
    and species to include metadata such as evidence, confidence scores, and
    curator information.
    """

    __tablename__ = "genefam_species_enhanced"
    __mapper_args__ = {}

    # Foreign keys (composite primary key)
    genefam_id: Mapped[int] = mapped_column(
        ForeignKey('genefam.genefam_id', ondelete='CASCADE'),
        primary_key=True,
        comment="Gene family ID"
    )

    species_id: Mapped[int] = mapped_column(
        ForeignKey('species.taxon_id', ondelete='CASCADE'),
        primary_key=True,
        comment="Species ID"
    )


    # Metadata fields
    gene_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of genes from this species in the family"
    )

    confidence_score: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Confidence score for the assignment"
    )

    evidence_type: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Type of evidence supporting this assignment"
    )

    evidence_source: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Source of the evidence"
    )

    curator_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes from the curator"
    )

    is_primary: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is a primary association"
    )

    date_assigned: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when this association was made"
    )

    last_reviewed: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when this association was last reviewed"
    )

    # Relationships
    genefam: Mapped["Genefam"] = relationship(
        "Genefam",
        lazy="joined"
    )

    species: Mapped["Species"] = relationship(
        "Species",
        lazy="joined"
    )

    # Indexes
    __table_args__ = (
        Index('idx_genefam_species_enhanced_gf_id', 'genefam_id'),
        Index('idx_genefam_species_enhanced_sp_id', 'species_id'),
        Index('idx_genefam_species_enhanced_confidence', 'confidence_score'),
        Index('idx_genefam_species_enhanced_evidence', 'evidence_type'),
        Index('idx_genefam_species_enhanced_primary', 'is_primary'),
        Index('idx_genefam_species_enhanced_date', 'date_assigned'),
    )

    def __init__(self, **kwargs):
        """Initialize with default values."""
        super().__init__(**kwargs)

        # Set current date if not provided
        if self.date_assigned is None:
            self.date_assigned = func.now()

    def __repr__(self) -> str:
        """String representation of the enhanced association."""
        return f"<GeneFamilySpeciesEnhanced(genefam_id={self.genefam_id}, species_id={self.species_id})>"


class GeneOrthologyGroup(BaseCustomModel):
    """Model representing orthology groups for gene families.

    Orthology groups represent collections of gene families across different
    species that are believed to be evolutionarily related.
    """

    __tablename__ = "genefam_orthology_group"
    __mapper_args__ = {}

    # Group identification
    group_id: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="Unique identifier for the orthology group"
    )


    group_name: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        comment="Human-readable name for the group"
    )

    group_description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Description of the orthology group"
    )

    # Metadata
    confidence_score: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Overall confidence score for the group"
    )

    conservation_level: Mapped[Optional[str]] = mapped_column(
        String(50),
        nullable=True,
        comment="Level of conservation (e.g., 'high', 'moderate', 'low')"
    )

    phylogenetic_scope: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Phylogenetic scope of the group"
    )

    creation_method: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Method used to create this group"
    )

    curator: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Name of the curator who created this group"
    )

    date_created: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        comment="Date when group was created"
    )

    last_updated: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when group was last updated"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this group is currently active"
    )

    # Relationships
    members: Mapped[list["GeneFamilyGroupMember"]] = relationship(
        "GeneFamilyGroupMember",
        back_populates="orthology_group",
        cascade="all, delete-orphan",
        lazy="selectin",
        order_by="GeneFamilyGroupMember.date_added.desc()"
    )

    # Indexes
    __table_args__ = (
        Index('idx_genefam_orthology_group_name', 'group_name'),
        Index('idx_genefam_orthology_group_confidence', 'confidence_score'),
        Index('idx_genefam_orthology_group_conservation', 'conservation_level'),
        Index('idx_genefam_orthology_group_scope', 'phylogenetic_scope'),
        Index('idx_genefam_orthology_group_active', 'is_active'),
        Index('idx_genefam_orthology_group_date_created', 'date_created'),
        Index('uq_genefam_orthology_group_id', 'group_id', unique=True),
    )

    def __repr__(self) -> str:
        """String representation of the orthology group."""
        return f"<GeneOrthologyGroup(group_id='{self.group_id}', name='{self.group_name}')>"

    def __str__(self) -> str:
        """String representation of the orthology group."""
        return f"OrthologyGroup('{self.group_name}')"

    # Helper methods
    def get_member_count(self) -> int:
        """Get the number of gene families in this group."""
        return len(self.members) if self.members else 0

    def get_species_count(self) -> int:
        """Get the number of species represented in this group."""
        if not self.members:
            return 0
        return len(set(member.species_id for member in self.members))

    def get_genefam_ids(self) -> list[int]:
        """Get all gene family IDs in this group."""
        return [member.genefam_id for member in self.members] if self.members else []

    def get_species_ids(self) -> list[int]:
        """Get all species IDs represented in this group."""
        return list(set(member.species_id for member in self.members)) if self.members else []

    def has_member(self, genefam_id: int, species_id: int) -> bool:
        """Check if a specific gene family from a species is in this group."""
        if not self.members:
            return False
        return any(
            member.genefam_id == genefam_id and member.species_id == species_id
            for member in self.members
        )

    def get_high_confidence_members(self) -> list["GeneFamilyGroupMember"]:
        """Get members with high confidence scores."""
        if not self.members:
            return []

        high_confidence = []
        for member in self.members:
            if member.membership_confidence and float(member.membership_confidence) >= 0.8:
                high_confidence.append(member)

        return high_confidence

    def activate(self) -> None:
        """Activate this orthology group."""
        self.is_active = True
        self.touch()

    def deactivate(self) -> None:
        """Deactivate this orthology group."""
        self.is_active = False
        self.touch()

    @classmethod
    def find_by_confidence(cls, session, min_confidence: float) -> list["GeneOrthologyGroup"]:
        """Find orthology groups with confidence score above threshold."""
        return session.query(cls).filter(
            cls.confidence_score.isnot(None),
            func.cast(cls.confidence_score, float) >= min_confidence,
            cls.is_active == True
        ).all()

    @classmethod
    def find_by_conservation(cls, session, conservation_level: str) -> list["GeneOrthologyGroup"]:
        """Find orthology groups by conservation level."""
        return session.query(cls).filter(
            cls.conservation_level == conservation_level,
            cls.is_active == True
        ).all()


class GeneFamilyGroupMember(BaseCustomModel):
    """Model representing membership of a gene family in an orthology group."""

    __tablename__ = "genefam_orthology_group_members"
    __mapper_args__ = {}

    # Foreign keys (composite primary key)
    group_id: Mapped[str] = mapped_column(
        ForeignKey('genefam_orthology_group.group_id', ondelete='CASCADE'),
        primary_key=True,
        comment="Orthology group ID"
    )

    genefam_id: Mapped[int] = mapped_column(
        ForeignKey('genefam.genefam_id', ondelete='CASCADE'),
        primary_key=True,
        comment="Gene family ID"
    )

    species_id: Mapped[int] = mapped_column(
        ForeignKey('species.taxon_id', ondelete='CASCADE'),
        primary_key=True,
        comment="Species ID"
    )


    # Membership metadata
    role_in_group: Mapped[Optional[str]] = mapped_column(
        String(100),
        nullable=True,
        comment="Role of this gene family in the group"
    )

    membership_confidence: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Confidence of this specific membership"
    )

    supporting_evidence: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Evidence supporting this membership"
    )

    date_added: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when this member was added"
    )

    added_by: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Who added this member"
    )

    is_representative: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this is a representative member"
    )

    # Relationships
    orthology_group: Mapped[GeneOrthologyGroup] = relationship(
        "GeneOrthologyGroup",
        back_populates="members",
        lazy="joined"
    )

    genefam: Mapped["Genefam"] = relationship(
        "Genefam",
        lazy="joined"
    )

    species: Mapped["Species"] = relationship(
        "Species",
        lazy="joined"
    )

    # Indexes
    __table_args__ = (
        Index('idx_genefam_orthology_members_group', 'group_id'),
        Index('idx_genefam_orthology_members_genefam', 'genefam_id'),
        Index('idx_genefam_orthology_members_species', 'species_id'),
        Index('idx_genefam_orthology_members_confidence', 'membership_confidence'),
        Index('idx_genefam_orthology_members_representative', 'is_representative'),
        Index('idx_genefam_orthology_members_date_added', 'date_added'),
    )

    def __init__(self, **kwargs):
        """Initialize with default values."""
        super().__init__(**kwargs)

        # Set current date if not provided
        if self.date_added is None:
            self.date_added = func.now()

    def __repr__(self) -> str:
        """String representation of the group member."""
        return f"<GeneFamilyGroupMember(group_id='{self.group_id}', genefam_id={self.genefam_id}, species_id={self.species_id})>"

    def set_as_representative(self, is_representative: bool = True) -> None:
        """Set this member as representative or not."""
        self.is_representative = is_representative
        self.touch()

    def update_confidence(self, confidence: str) -> None:
        """Update the membership confidence score."""
        self.membership_confidence = confidence
        self.touch()


class SpeciesRelationship(BaseCustomModel):
    """Model representing evolutionary and comparative relationships between species."""

    __tablename__ = "species_relationship"
    __mapper_args__ = {}

    # Foreign keys (ordered composite primary key to prevent duplicates)
    species_a_id: Mapped[int] = mapped_column(
        ForeignKey('species.taxon_id', ondelete='CASCADE'),
        primary_key=True,
        comment="First species ID (ordered to prevent duplicates)"
    )

    species_b_id: Mapped[int] = mapped_column(
        ForeignKey('species.taxon_id', ondelete='CASCADE'),
        primary_key=True,
        comment="Second species ID (ordered to prevent duplicates)"
    )

    relationship_type: Mapped[str] = mapped_column(
        String(50),
        primary_key=True,
        comment="Type of relationship (e.g., 'orthologous', 'paralogous', 'syntenic')"
    )


    # Relationship metadata
    evolutionary_distance: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Evolutionary distance estimate"
    )

    divergence_time_mya: Mapped[Optional[str]] = mapped_column(
        String(20),
        nullable=True,
        comment="Divergence time in million years ago"
    )

    synteny_score: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Synteny conservation score"
    )

    genome_similarity: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Overall genome similarity percentage"
    )

    ortholog_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of orthologs between species"
    )

    paralog_count: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Number of paralogs between species"
    )

    confidence_score: Mapped[Optional[str]] = mapped_column(
        String(10),
        nullable=True,
        comment="Confidence score for the relationship"
    )

    evidence_source: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Source of the relationship data"
    )

    publication_reference: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Reference publication"
    )

    curator_notes: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True,
        comment="Notes from the curator"
    )

    date_established: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when relationship was established"
    )

    last_reviewed: Mapped[Optional[DateTime]] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
        comment="Date when relationship was last reviewed"
    )

    is_active: Mapped[bool] = mapped_column(
        Boolean,
        nullable=False,
        default=True,
        comment="Whether this relationship is currently active"
    )

    # Relationships
    species_a: Mapped["Species"] = relationship(
        "Species",
        foreign_keys=[species_a_id],
        lazy="joined"
    )

    species_b: Mapped["Species"] = relationship(
        "Species",
        foreign_keys=[species_b_id],
        lazy="joined"
    )

    # Indexes
    __table_args__ = (
        Index('idx_species_relationship_species_a', 'species_a_id'),
        Index('idx_species_relationship_species_b', 'species_b_id'),
        Index('idx_species_relationship_type', 'relationship_type'),
        Index('idx_species_relationship_distance', 'evolutionary_distance'),
        Index('idx_species_relationship_divergence', 'divergence_time_mya'),
        Index('idx_species_relationship_synteny', 'synteny_score'),
        Index('idx_species_relationship_similarity', 'genome_similarity'),
        Index('idx_species_relationship_active', 'is_active'),
        Index('idx_species_relationship_date', 'date_established'),
        Index('idx_species_relationship_pair', 'species_a_id', 'species_b_id'),
    )

    def __init__(self, **kwargs):
        """Initialize with default values."""
        super().__init__(**kwargs)

        # Set current date if not provided
        if self.date_established is None:
            self.date_established = func.now()

    def __repr__(self) -> str:
        """String representation of the species relationship."""
        return f"<SpeciesRelationship(species_a_id={self.species_a_id}, species_b_id={self.species_b_id}, type='{self.relationship_type}')>"

    def __str__(self) -> str:
        """String representation of the species relationship."""
        return f"Relationship: {self.relationship_type} between species {self.species_a_id} and {self.species_b_id}"

    # Helper methods
    def get_distance_as_float(self) -> Optional[float]:
        """Get evolutionary distance as float if possible."""
        if self.evolutionary_distance is None:
            return None
        try:
            return float(self.evolutionary_distance)
        except ValueError:
            return None

    def get_similarity_as_float(self) -> Optional[float]:
        """Get genome similarity as float if possible."""
        if self.genome_similarity is None:
            return None
        try:
            return float(self.genome_similarity.rstrip('%'))
        except ValueError:
            return None

    def get_divergence_time_as_float(self) -> Optional[float]:
        """Get divergence time as float if possible."""
        if self.divergence_time_mya is None:
            return None
        try:
            return float(self.divergence_time_mya)
        except ValueError:
            return None

    def is_high_confidence(self) -> bool:
        """Check if this is a high-confidence relationship."""
        if self.confidence_score is None:
            return False
        try:
            return float(self.confidence_score) >= 0.8
        except ValueError:
            return False

    def activate(self) -> None:
        """Activate this relationship."""
        self.is_active = True
        self.touch()

    def deactivate(self) -> None:
        """Deactivate this relationship."""
        self.is_active = False
        self.touch()

    @classmethod
    def find_between_species(cls, session, species_a_id: int, species_b_id: int) -> list["SpeciesRelationship"]:
        """Find all relationships between two species (regardless of order)."""
        return session.query(cls).filter(
            cls.is_active == True,
            (
                (cls.species_a_id == species_a_id) & (cls.species_b_id == species_b_id) |
                (cls.species_a_id == species_b_id) & (cls.species_b_id == species_a_id)
            )
        ).all()

    @classmethod
    def find_by_type(cls, session, relationship_type: str) -> list["SpeciesRelationship"]:
        """Find relationships by type."""
        return session.query(cls).filter(
            cls.relationship_type == relationship_type,
            cls.is_active == True
        ).all()

    @classmethod
    def find_closest_species(cls, session, species_id: int, limit: int = 5) -> list["SpeciesRelationship"]:
        """Find closest species to a given species by evolutionary distance."""
        return session.query(cls).filter(
            cls.is_active == True,
            (
                (cls.species_a_id == species_id) |
                (cls.species_b_id == species_id)
            )
        ).order_by(cls.evolutionary_distance.asc()).limit(limit).all()