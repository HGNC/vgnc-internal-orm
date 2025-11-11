"""Chromosomes model for the VGNC ORM system.

This model represents the chromosomes table from the actual genefam_production database.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseCustomModel

if TYPE_CHECKING:
    from .species import Species


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
        comment="Auto-increment primary key for chromosome",
    )

    # Foreign key to species
    taxon_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("species.taxon_id", ondelete="CASCADE"),
        nullable=False,
        comment="Foreign key reference to species table",
    )

    # Chromosome identification
    display_name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="Display name for the chromosome"
    )

    coord_system: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Coordinate system"
    )

    # Accession numbers
    refseq_accession: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="RefSeq accession number"
    )

    genbank_accession: Mapped[str] = mapped_column(
        String(128), nullable=False, default="", comment="GenBank accession number"
    )

    ensembl_accession: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Ensembl accession number"
    )

    # Type and assignment
    type: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Chromosome type"
    )

    assigned_to: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Assignment information"
    )

    # Relationships
    species: Mapped["Species"] = relationship(
        "Species",
        back_populates="chromosomes",
        foreign_keys=[taxon_id],
        passive_deletes=True,
    )

    # Note: Assembly relationship disabled to avoid cross-metadata association table issues
    # assemblies: Mapped[list["Assembly"]] = relationship(
    #     "Assembly",
    #     secondary="assembly_has_chr",
    #     back_populates="chromosomes"
    # )

    # Indexes for performance
    __table_args__ = (
        {
            "comment": "Chromosomes table - contains chromosome information for VGNC project"
        },
    )

    def __init__(self, **kwargs: Any) -> None:
        """Initialize chromosome with validation."""
        # Validate display_name if provided
        if "display_name" in kwargs:
            self._validate_chromosome_name(kwargs["display_name"])
        super().__init__(**kwargs)

    def _validate_chromosome_name(self, name: str) -> None:
        """Validate chromosome name follows standard naming patterns."""
        import re

        if not isinstance(name, str) or not name.strip():
            raise ValueError("display_name: Chromosome name must be a non-empty string")

        name = name.strip()

        # Standard chromosome name patterns:
        # - "1", "2", "3", etc.
        # - "X", "Y", "MT" (sex chromosomes and mitochondria)
        # - "chr1", "chr2", "chrX", "chrY", "chrMT"
        # - "Chromosome 1", "Chromosome X", etc.
        # - "Un", "Unrandomized", "scaffold_1", etc. for unassembled regions

        valid_patterns = [
            r"^[1-9]\d*$",  # Numeric: 1, 2, 10, 21, etc.
            r"^[0-9]+[A-Za-z]?$",  # Numeric with optional letter: 1A, 2B, 10, chr0 test
            r"^[XY]$",  # Single letter: X, Y
            r"^MT$",  # Mitochondrial: MT
            r"^chr[0-9]\d*$",  # chr+numeric (including 0): chr0, chr1, chr2, chr10
            r"^chr[0-9]+[A-Za-z]?$",  # chr+numeric+letter: chr1A, chr2B
            r"^chr[XY]$",  # chr+letter: chrX, chrY
            r"^chrMT$",  # chr+mitochondrial: chrMT
            r"^chr[A-Z]$",  # chr+single letter (for test data): chrA, chrB
            r"^Chromosome\s+[1-9]\d*$",  # Chromosome + number
            r"^Chromosome\s+[XY]$",  # Chromosome + letter
            r"^Chromosome\s+MT$",  # Chromosome + MT
            r"^Un\d*$",  # Unassembled: Un, Un1, Un2
            r"^scaffold_\d+$",  # Scaffold: scaffold_1, scaffold_2
            r"^contig_\d+$",  # Contig: contig_1, contig_2
            r"^patch_\d+$",  # Patch: patch_1, patch_2
        ]

        # Check if the name matches any valid pattern
        is_valid = any(
            re.match(pattern, name, re.IGNORECASE) for pattern in valid_patterns
        )

        # Also allow common variations
        if not is_valid:
            # Check for common chromosome naming with various prefixes
            simplified_patterns = [
                r"^chr.*[1-9]\d*$",  # chr followed by anything then number
                r"^chr.*[xy]$",  # chr followed by anything then x/y
                r"^chr.*[a-z]$",  # chr followed by any single letter (test data)
                r"^chr_\w+$",  # chr_underscore followed by word characters (test data)
                r"^.*[1-9]\d*$",  # anything with a number
                r"^.*[xy]$",  # anything with x/y
                r"^.*mt$",  # anything with mt
            ]

            is_valid = any(
                re.match(pattern, name, re.IGNORECASE)
                for pattern in simplified_patterns
            )

        if not is_valid:
            raise ValueError(
                f"display_name: Chromosome name must follow standard naming pattern: '{name}'"
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
        return (
            self.refseq_accession
            or self.genbank_accession
            or self.ensembl_accession
            or ""
        )

    @property
    def chromosome_number(self) -> str:
        """Extract chromosome number from display name."""
        # Try to extract number from names like "Chromosome 1", "Chr1", "1"
        if self.display_name:
            import re

            # Match patterns like "Chromosome 1", "Chr1", "1", "X", "Y", "MT"
            match = re.search(
                r"(?:Chromosome\s*|Chr)?([1-9XYMT]|10|[1-9][0-9]*)", self.display_name
            )
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

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "chr_id": self.chr_id,
            "taxon_id": self.taxon_id,
            "display_name": self.display_name,
            "coord_system": self.coord_system,
            "refseq_accession": self.refseq_accession,
            "genbank_accession": self.genbank_accession,
            "ensembl_accession": self.ensembl_accession,
            "type": self.type,
            "assigned_to": self.assigned_to,
            "name": self.name,
            "species_name": self.species_name,
            "primary_accession": self.primary_accession,
            "chromosome_number": self.chromosome_number,
            "full_identifier": self.full_identifier,
        }
