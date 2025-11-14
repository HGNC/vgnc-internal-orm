"""Assembly model for the VGNC ORM system.

This model represents the assembly table from VGNC-style databases.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import Boolean, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseCustomModel

if TYPE_CHECKING:
    from .species import Species


class Assembly(BaseCustomModel):
    """Model representing a genome assembly in the VGNC database.

    This model stores information about genome assemblies for different species,
    based on the actual database schema.
    """

    __tablename__ = "assembly"

    # Primary key
    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="Auto-increment primary key for assembly",
    )

    # Foreign key to species
    taxon_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("species.taxon_id", ondelete="CASCADE"),
        nullable=False,
        comment="Foreign key reference to species table",
    )

    # Assembly source information
    source: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="Assembly source (e.g., Ensembl, NCBI)"
    )

    name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="Assembly name"
    )

    # Accession numbers
    genbank_assembly_accession: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="GenBank assembly accession"
    )

    refseq_assembly_accession: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="RefSeq assembly accession"
    )

    # Status flags
    is_current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="Whether this is the current assembly"
    )

    is_vgnc_default: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="Whether this is the VGNC default assembly"
    )

    # Relationships
    species: Mapped["Species"] = relationship(
        "Species",
        back_populates="assemblies",
        foreign_keys=[taxon_id],
        passive_deletes=True,
    )

    # Note: Chromosomes relationship disabled to avoid cross-metadata association table issues
    # chromosomes: Mapped[list["Chromosomes"]] = relationship(
    #     "Chromosomes",
    #     secondary="assembly_has_chr",
    #     back_populates="assemblies"
    # )

    # Indexes for performance
    __table_args__ = (
        {"comment": "Assembly table - contains genome assembly information"},
    )

    def __repr__(self) -> str:
        return f"<Assembly(id={self.id}, name='{self.name}', taxon_id={self.taxon_id})>"

    @property
    def accession(self) -> str:
        """Get the primary accession number."""
        return self.refseq_assembly_accession or self.genbank_assembly_accession

    @property
    def species_name(self) -> str:
        """Get the species display name."""
        return self.species.display_name if self.species else "Unknown"

    @property
    def is_active(self) -> bool:
        """Check if assembly is active (current and VGNC default)."""
        return self.is_current and self.is_vgnc_default

    @property
    def full_name(self) -> str:
        """Get full assembly name with species."""
        species_name = self.species_name
        assembly_name = self.name
        if species_name and assembly_name:
            return f"{species_name} - {assembly_name}"
        return assembly_name or species_name

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "taxon_id": self.taxon_id,
            "source": self.source,
            "name": self.name,
            "genbank_assembly_accession": self.genbank_assembly_accession,
            "refseq_assembly_accession": self.refseq_assembly_accession,
            "is_current": self.is_current,
            "is_vgnc_default": self.is_vgnc_default,
            "accession": self.accession,
            "species_name": self.species_name,
            "is_active": self.is_active,
            "full_name": self.full_name,
        }
