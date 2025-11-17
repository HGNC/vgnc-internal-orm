"""Gene family model for the VGNC ORM system.

This model represents the genefam table from VGNC-style databases.
"""

from typing import TYPE_CHECKING, Any

from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseCustomModel

if TYPE_CHECKING:
    from .species import Species


class Genefam(BaseCustomModel):
    """Model representing a gene family entry in the VGNC database.

    This model stores information about gene families that are managed
    by the VGNC project, based on the actual database schema.
    """

    __tablename__ = "genefam"

    # Primary key
    genefam_id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="Auto-increment primary key for gene family entries",
    )

    # Foreign key to species
    taxon_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("species.taxon_id"),
        nullable=False,
        comment="Foreign key reference to species table",
    )

    # Gene family identification
    assigned_id: Mapped[str] = mapped_column(
        String(255),
        nullable=False,
        default="",
        comment="Assigned gene family identifier",
    )

    assigned_symbol: Mapped[str | None] = mapped_column(
        String(45), nullable=True, comment="Assigned gene symbol"
    )

    assigned_name: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Assigned gene name"
    )

    # Status and editor information
    status_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("gene_status.id"),
        nullable=False,
        comment="Foreign key reference to gene status",
    )

    editor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("editor.id"),
        nullable=False,
        comment="Foreign key reference to editor who assigned this",
    )

    # Optional support level
    hcop_support_level: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="HCOP support level rating"
    )

    # Relationships
    species: Mapped["Species"] = relationship(
        "Species", back_populates="genefams", foreign_keys=[taxon_id]
    )

    # Relationships to status and editor
    # Note: Relationships with back_populates disabled to avoid circular imports
    # status: Mapped["GeneStatus"] = relationship("GeneStatus", back_populates="genefams")
    # editor: Mapped["Editor"] = relationship("Editor", back_populates="genefams")

    # Alternative names and symbols
    # Note: Relationships disabled to avoid circular import issues
    # alt_names: Mapped[list["AltName"]] = relationship(
    #     "AltName",
    #     secondary="gene_alt_name",
    #     back_populates="genefams"
    # )
    #
    # alt_symbols: Mapped[list["AltSymbol"]] = relationship(
    #     "AltSymbol",
    #     secondary="gene_alt_symbol",
    #     back_populates="genefams"
    # )
    #
    # # Relationships to other tables
    # comments: Mapped[list["Comment"]] = relationship(
    #     "Comment",
    #     secondary="gene_has_comment",
    #     back_populates="genefams"
    # )
    #
    # flags: Mapped[list["GeneFlag"]] = relationship(
    #     "GeneFlag",
    #     secondary="gene_has_flag",
    #     back_populates="genefams"
    # )
    #
    # families: Mapped[list["FamilyNew"]] = relationship(
    #     "FamilyNew",
    #     secondary="gene_has_family",
    #     back_populates="genefams"
    # )
    #
    # # External database references
    # refseq_entries: Mapped[list["RefSeq"]] = relationship(
    #     "RefSeq",
    #     secondary="gene_has_refseq",
    #     back_populates="genefams"
    # )
    #
    # ensembl_entries: Mapped[list["Ensembl"]] = relationship(
    #     "Ensembl",
    #     secondary="gene_has_ensembl",
    #     back_populates="genefams"
    # )
    #
    # uniprot_entries: Mapped[list["Uniprot"]] = relationship(
    #     "Uniprot",
    #     secondary="gene_has_uniprot",
    #     back_populates="genefams"
    # )

    # Indexes for performance
    __table_args__ = (
        {
            "comment": "Genefam table - contains gene family information for VGNC project"
        },
    )

    def __repr__(self) -> str:
        """Return string representation of Genefam instance.

        Returns:
            str: Formatted string with genefam ID, assigned ID, and taxon ID.
        """
        return f"<Genefam(genefam_id={self.genefam_id}, assigned_id='{self.assigned_id}', taxon_id={self.taxon_id})>"

    @property
    def name(self) -> str:
        """Get the gene family name (alias for assigned_id for compatibility)."""
        return self.assigned_id

    @property
    def symbol(self) -> str | None:
        """Get the gene symbol (alias for assigned_symbol)."""
        return self.assigned_symbol

    @property
    def description(self) -> str | None:
        """Get the gene description (alias for assigned_name)."""
        return self.assigned_name

    @property
    def is_active(self) -> bool:
        """Check if gene family is active based on status.

        Note: This uses status_id directly since the relationship is disabled
        to avoid circular imports. For full status info, load the status separately.
        """
        # Statuses 1 and 2 typically represent Approved and Active
        return self.status_id in (1, 2)

    @property
    def status_text(self) -> str:
        """Get human-readable status text.

        Note: This uses status_id directly since the relationship is disabled
        to avoid circular imports. For full status info, load the status separately.
        """
        # Common status ID mappings
        status_map = {1: "Approved", 2: "Active", 3: "Retired"}
        return status_map.get(self.status_id, f"Status {self.status_id}")

    @property
    def editor_name(self) -> str:
        """Get editor display name.

        Note: This uses editor_id directly since the relationship is disabled
        to avoid circular imports. For full editor info, load the editor separately.
        """
        return f"Editor {self.editor_id}"

    @property
    def species_prefix(self) -> str:
        """Get the VGNC prefix from the species."""
        return self.species.genefam_prefix if self.species else ""

    @property
    def full_identifier(self) -> str:
        """Get full identifier with species prefix."""
        if self.species and self.assigned_id:
            return f"{self.species.genefam_prefix}:{self.assigned_id}"
        return self.assigned_id or ""

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary with backward compatibility."""
        return {
            "genefam_id": self.genefam_id,
            "taxon_id": self.taxon_id,
            "name": self.name,
            "symbol": self.symbol,
            "description": self.description,
            "assigned_id": self.assigned_id,
            "assigned_symbol": self.assigned_symbol,
            "assigned_name": self.assigned_name,
            "status_id": self.status_id,
            "editor_id": self.editor_id,
            "hcop_support_level": self.hcop_support_level,
            "status": self.status_text,
            "is_active": self.is_active,
            "species_prefix": self.species_prefix,
            "full_identifier": self.full_identifier,
            "editor_name": self.editor_name,
        }
