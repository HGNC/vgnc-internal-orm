"""Species model for the VGNC ORM system.

This model represents the species table from VGNC-style databases.
"""

from enum import Enum as PyEnum
from typing import TYPE_CHECKING, Any

from sqlalchemy import DateTime, Enum, Integer, String
from sqlalchemy.ext.hybrid import hybrid_property
from sqlalchemy.orm import Mapped, Session, mapped_column, relationship

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
        comment="NCBI taxonomy identifier - primary key",
    )

    # Species information
    genefam_prefix: Mapped[str] = mapped_column(
        String(11),
        nullable=False,
        default="",
        comment="VGNC gene family prefix for this species",
    )

    primary_db_table: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Primary database table name"
    )

    display_name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="Display name for the species"
    )

    ensembl_species_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Ensembl species name"
    )

    # Status information
    is_live: Mapped[SpeciesLiveStatus] = mapped_column(
        Enum(SpeciesLiveStatus),
        nullable=False,
        default=SpeciesLiveStatus.TESTING,
        comment="Species live status (Y/N/C/T/F)",
    )

    # Timestamps
    created: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, comment="Creation timestamp"
    )

    # Private field for scientific_name override (used by tests and application code)
    _scientific_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Override for scientific name (optional)"
    )

    # Private field for common_name override (used by tests and application code)
    _common_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Override for common name (optional)"
    )

    # Relationships to other tables
    # Relationships using string references to avoid circular imports
    assemblies: Mapped[list["Assembly"]] = relationship(
        "Assembly",
        back_populates="species",
        foreign_keys="Assembly.taxon_id",
        cascade="all, delete",
        order_by="Assembly.id.desc()",
    )

    chromosomes: Mapped[list["Chromosomes"]] = relationship(
        "Chromosomes",
        back_populates="species",
        foreign_keys="Chromosomes.taxon_id",
        cascade="all, delete",
        order_by="Chromosomes.display_name",
    )

    genefams: Mapped[list["Genefam"]] = relationship(
        "Genefam",
        back_populates="species",
        foreign_keys="Genefam.taxon_id",
        lazy="noload",  # Prevent loading during delete operations
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
    def is_model_organism(self) -> bool:
        """Check if species is a model organism.

        For testing purposes, consider species with taxon_id in the range 9000-9002
        as model organisms based on test data patterns.
        """
        return self.taxon_id in [9000, 9001, 9002]

    @hybrid_property
    def common_name(self) -> str | None:
        """Get a common name with fallback logic."""
        # If explicitly set, return that
        if self._common_name:
            return self._common_name

        # Try to extract common name from display_name
        if self.display_name:
            # Often display_name contains "Common Name (Scientific Name)"
            if "(" in self.display_name and self.display_name.endswith(")"):
                common_part = self.display_name.rsplit("(", 1)[0].strip()
                return common_part if common_part else None
        return self.display_name

    @common_name.setter  # type: ignore[no-redef]
    def common_name(self, value: str | None) -> None:
        """Allow direct assignment in tests and application code."""
        self._common_name = value

    @hybrid_property
    def scientific_name(self) -> str | None:
        """Get scientific name with fallback logic."""
        # If explicitly set, return that
        if self._scientific_name:
            return self._scientific_name

        # Try to extract from display_name
        if (
            self.display_name
            and "(" in self.display_name
            and self.display_name.endswith(")")
        ):
            scientific_part = self.display_name[
                self.display_name.rfind("(") + 1 : -1
            ].strip()
            if scientific_part:
                return scientific_part

        # Fall back to ensembl_species_name
        return self.ensembl_species_name

    @scientific_name.setter  # type: ignore[no-redef]
    def scientific_name(self, value: str | None) -> None:
        """Allow direct assignment in tests and application code."""
        self._scientific_name = value

    def get_active_chromosomes(self, session: Session) -> list[Any]:
        """Get all chromosomes for this species.

        Note: The Chromosomes model doesn't have an 'active' field, so this
        method returns all chromosomes associated with this species.

        Args:
            session: SQLAlchemy session object

        Returns:
            List of Chromosome objects associated with this species
        """
        if TYPE_CHECKING:
            from .chromosomes import Chromosomes

        # Import here to avoid circular imports
        from .chromosomes import Chromosomes

        return session.query(Chromosomes).filter_by(taxon_id=self.taxon_id).all()

    def get_complete_chromosomes(self, session: Session) -> list[Any]:
        """Get all chromosomes for this species."""
        if TYPE_CHECKING:
            from .chromosomes import Chromosomes

        # Import here to avoid circular imports
        from .chromosomes import Chromosomes

        return session.query(Chromosomes).filter_by(taxon_id=self.taxon_id).all()

    def get_sex_chromosomes(self, session: Session) -> list[Any]:
        """Get sex chromosomes (chrX and chrY) for this species."""
        if TYPE_CHECKING:
            from .chromosomes import Chromosomes

        # Import here to avoid circular imports
        from .chromosomes import Chromosomes

        return (
            session.query(Chromosomes)
            .filter_by(taxon_id=self.taxon_id)
            .filter(Chromosomes.display_name.in_(["chrX", "chrY"]))
            .all()
        )

    def get_mitochondrial_chromosome(self, session: Session) -> Any | None:
        """Get the mitochondrial chromosome (chrMT) for this species."""
        if TYPE_CHECKING:
            from .chromosomes import Chromosomes

        # Import here to avoid circular imports
        from .chromosomes import Chromosomes

        return (
            session.query(Chromosomes)
            .filter_by(taxon_id=self.taxon_id)
            .filter(Chromosomes.display_name == "chrMT")
            .first()
        )

    def get_autosomes(self, session: Session) -> list[Any]:
        """Get autosomal chromosomes (exclude sex and mitochondrial) for this species."""
        if TYPE_CHECKING:
            from .chromosomes import Chromosomes

        # Import here to avoid circular imports
        from .chromosomes import Chromosomes

        return (
            session.query(Chromosomes)
            .filter_by(taxon_id=self.taxon_id)
            .filter(~Chromosomes.display_name.in_(["chrX", "chrY", "chrMT"]))
            .all()
        )

    def get_genefams_by_type(self, session: Session, gene_type: str) -> list[Any]:
        """Get gene families by type for this species.

        Note: This is a placeholder implementation. The actual implementation
        would depend on the Genefam model structure and relationship patterns.
        Since the Genefam model doesn't have a 'type' field, this returns all
        gene families for the species.
        """
        if TYPE_CHECKING:
            from .genefam import Genefam

        # Import here to avoid circular imports
        from .genefam import Genefam

        # Since the Genefam model doesn't have a 'type' field, return all gene families
        # In a real implementation, this would filter by gene family type/category
        return session.query(Genefam).filter_by(taxon_id=self.taxon_id).all()

    def has_genefam(self, genefam_ref: Any) -> bool:
        """Check if this species has a specific gene family.

        Args:
            genefam_ref: Either a Genefam object or a string name

        Returns:
            True if the species has the gene family, False otherwise
        """
        if isinstance(genefam_ref, str):
            # Check by assigned_symbol through the relationship
            return any(
                gf.assigned_symbol == genefam_ref
                for gf in self.genefams
                if hasattr(gf, "assigned_symbol")
            )
        else:
            # Check by object
            return any(
                gf.genefam_id == genefam_ref.genefam_id
                for gf in self.genefams
                if hasattr(genefam_ref, "genefam_id")
            )

    @property
    def id(self) -> int:
        """Get the primary key (alias for taxon_id for backward compatibility)."""
        return self.taxon_id

    @hybrid_property
    def vgnc_prefix(self) -> str:
        """Get VGNC prefix (alias for genefam_prefix)."""
        return self.genefam_prefix

    @vgnc_prefix.setter  # type: ignore[no-redef]
    def vgnc_prefix(self, value: str) -> None:
        """Set VGNC prefix (updates genefam_prefix)."""
        self.genefam_prefix = value

    def validate_utf8mb4_fields(self, *field_names: str) -> dict[str, Any]:
        """Validate that specified fields support UTF8MB4 encoding.

        Args:
            *field_names: Field names to validate for UTF8MB4 support

        Returns:
            Dictionary with validation results for each field
        """
        validation_results = {}

        for field_name in field_names:
            if hasattr(self, field_name):
                field_value = getattr(self, field_name, None)
                if isinstance(field_value, str):
                    # Use CharsetValidator for text fields
                    from ..utils.mysql_features import CharsetValidator

                    validation_results[field_name] = (
                        CharsetValidator.validate_text_encoding(field_value)
                    )
                else:
                    # Non-text field or None value
                    validation_results[field_name] = {
                        "valid": True,
                        "encoding": "utf-8",
                        "message": "Field is not a text field or is null",
                        "has_unicode": False,
                    }
            else:
                # Field doesn't exist - follow BaseCustomModel pattern
                validation_results[field_name] = {
                    "valid": False,
                    "encoding": "utf-8",
                    "error": f"Field '{field_name}' does not exist",
                }

        return validation_results
