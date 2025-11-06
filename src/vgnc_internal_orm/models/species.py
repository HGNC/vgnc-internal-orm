"""Species model for the VGNC ORM system.

This model represents the species table from the actual genefam_production database.
"""

from typing import Optional, TYPE_CHECKING
from sqlalchemy import String, Integer, DateTime, Enum
from sqlalchemy.orm import Mapped, mapped_column, relationship
from enum import Enum as PyEnum

from .base import BaseCustomModel

if TYPE_CHECKING:
    from .assembly import Assembly
    from .chromosomes import Chromosomes
    from .genefam import Genefam


class SpeciesLiveStatus(str, PyEnum):
    """Enum for species live status values."""
    YES = "Y"
    NO = "N"
    CANCELLED = "C"
    TESTING = "T"
    FLAGGED = "F"


class Species(BaseCustomModel):
    """Model representing a species in the VGNC database.

    This model stores information about species for which gene nomenclature
    is managed by the VGNC project, based on the actual database schema.
    """

    __tablename__ = "species"

    # Primary key - taxon_id is the primary key in the real database
    taxon_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="NCBI taxonomy identifier - primary key"
    )

    # Species information
    genefam_prefix: Mapped[str] = mapped_column(
        String(11),
        nullable=False,
        default="",
        comment="VGNC gene family prefix for this species"
    )

    primary_db_table: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="Primary database table name"
    )

    display_name: Mapped[str] = mapped_column(
        String(128),
        nullable=False,
        comment="Display name for the species"
    )

    ensembl_species_name: Mapped[Optional[str]] = mapped_column(
        String(128),
        nullable=True,
        comment="Ensembl species name"
    )

    # Status information
    is_live: Mapped[SpeciesLiveStatus] = mapped_column(
        Enum(SpeciesLiveStatus),
        nullable=False,
        default=SpeciesLiveStatus.TESTING,
        comment="Species live status (Y/N/C/T/F)"
    )

    # Timestamps
    created: Mapped[DateTime] = mapped_column(
        DateTime,
        nullable=False,
        comment="Creation timestamp"
    )

    # Relationships to other tables
    # Relationships using string references to avoid circular imports
    assemblies: Mapped[list["Assembly"]] = relationship(
        "Assembly",
        back_populates="species",
        foreign_keys="Assembly.taxon_id"
    )

    chromosomes: Mapped[list["Chromosomes"]] = relationship(
        "Chromosomes",
        back_populates="species",
        foreign_keys="Chromosomes.taxon_id"
    )

    genefams: Mapped[list["Genefam"]] = relationship(
        "Genefam",
        back_populates="species",
        foreign_keys="Genefam.taxon_id"
    )

    # Indexes for performance
    __table_args__ = (
        {"comment": "Species table - contains species information for VGNC project"},
    )

    def __repr__(self) -> str:
        return f"<Species(taxon_id={self.taxon_id}, genefam_prefix='{self.genefam_prefix}', display_name='{self.display_name}')>"

    @property
    def is_active(self) -> bool:
        """Check if species is active (live status Y)."""
        return self.is_live == SpeciesLiveStatus.YES

    @property
    def common_name(self) -> Optional[str]:
        """Get a common name from display_name (for backward compatibility)."""
        # Try to extract common name from display_name
        if self.display_name:
            # Often display_name contains "Common Name (Scientific Name)"
            if "(" in self.display_name and self.display_name.endswith(")"):
                common_part = self.display_name.rsplit("(", 1)[0].strip()
                return common_part if common_part else None
        return self.display_name

    @property
    def scientific_name(self) -> Optional[str]:
        """Get scientific name from display_name or use ensembl_species_name."""
        # First try to extract from display_name
        if self.display_name and "(" in self.display_name and self.display_name.endswith(")"):
            scientific_part = self.display_name[self.display_name.rfind("(")+1:-1].strip()
            if scientific_part:
                return scientific_part

        # Fall back to ensembl_species_name
        return self.ensembl_species_name

    @property
    def vgnc_prefix(self) -> str:
        """Get VGNC prefix (alias for genefam_prefix)."""
        return self.genefam_prefix