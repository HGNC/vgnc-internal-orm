"""Chromosomes model for the VGNC ORM system.

This model represents the chromosomes table from the actual genefam_production database.
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, ForeignKey
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseCustomModel

if TYPE_CHECKING:
    from .species import Species
    from .assembly import Assembly


class Chromosomes(BaseCustomModel):
    """Model representing a chromosome in the VGNC database.

    This model stores information about chromosomes for different species,
    based on the actual database schema.
    """

    __tablename__ = "chromosomes"

    # Primary key
    chr_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="Auto-increment primary key for chromosome"
    )

    # Foreign key to species
    taxon_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("species.taxon_id"),
        nullable=False,
        comment="Foreign key reference to species table"
    )

    # Chromosome identification
    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Display name for the chromosome"
    )

    coord_system: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Coordinate system"
    )

    # Accession numbers
    refseq_accession: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="RefSeq accession number"
    )

    genbank_accession: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        default="",
        comment="GenBank accession number"
    )

    ensembl_accession: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Ensembl accession number"
    )

    # Type and assignment
    type: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Chromosome type"
    )

    assigned_to: Mapped[Optional[int]] = mapped_column(
        Integer,
        nullable=True,
        comment="Assignment information"
    )

    # Relationships
    species: Mapped["Species"] = relationship(
        "Species",
        back_populates="chromosomes",
        foreign_keys=[taxon_id]
    )

    # Note: Assembly relationship disabled to avoid cross-metadata association table issues
    # assemblies: Mapped[list["Assembly"]] = relationship(
    #     "Assembly",
    #     secondary="assembly_has_chr",
    #     back_populates="chromosomes"
    # )

    # Indexes for performance
    __table_args__ = (
        {"comment": "Chromosomes table - contains chromosome information for VGNC project"},
    )

    def __repr__(self) -> str:
        return f"<Chromosomes(chr_id={self.chr_id}, display_name='{self.display_name}', taxon_id={self.taxon_id})>"

    @property
    def name(self) -> str:
        """Get chromosome name (alias for display_name)."""
        return self.display_name

    @property
    def species_name(self) -> str:
        """Get the species display name."""
        return self.species.display_name if self.species else "Unknown"

    @property
    def primary_accession(self) -> str:
        """Get the primary accession number."""
        return self.refseq_accession or self.genbank_accession or self.ensembl_accession or ""

    @property
    def chromosome_number(self) -> str:
        """Extract chromosome number from display name."""
        # Try to extract number from names like "Chromosome 1", "Chr1", "1"
        if self.display_name:
            import re
            # Match patterns like "Chromosome 1", "Chr1", "1", "X", "Y", "MT"
            match = re.search(r'(?:Chromosome\s*|Chr)?([1-9XYMT]|10|[1-9][0-9]*)', self.display_name)
            if match:
                return match.group(1)
        return self.display_name

    @property
    def full_identifier(self) -> str:
        """Get full identifier with species prefix."""
        species_prefix = self.species.genefam_prefix if self.species else ""
        if species_prefix and self.display_name:
            return f"{species_prefix}:{self.display_name}"
        return self.display_name

    def to_dict(self) -> dict:
        """Convert to dictionary."""
        return {
            'chr_id': self.chr_id,
            'taxon_id': self.taxon_id,
            'display_name': self.display_name,
            'coord_system': self.coord_system,
            'refseq_accession': self.refseq_accession,
            'genbank_accession': self.genbank_accession,
            'ensembl_accession': self.ensembl_accession,
            'type': self.type,
            'assigned_to': self.assigned_to,
            'name': self.name,
            'species_name': self.species_name,
            'primary_accession': self.primary_accession,
            'chromosome_number': self.chromosome_number,
            'full_identifier': self.full_identifier
        }