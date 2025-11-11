"""Supporting models for the VGNC ORM system.

These models represent supporting tables from the actual genefam_production database
that are referenced by the main models.
"""

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .base import BaseModel
from .genefam import Genefam


class GeneStatus(BaseModel):
    """Model representing gene status from the gene_status table."""

    __tablename__ = "gene_status"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False, comment="Primary key for gene status"
    )

    status: Mapped[str] = mapped_column(
        String(45), nullable=False, comment="Status name"
    )

    display: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Display name for status"
    )

    # Relationships
    genefams: Mapped[list["Genefam"]] = relationship("Genefam", back_populates="status")

    def __repr__(self) -> str:
        return f"<GeneStatus(id={self.id}, status='{self.status}')>"


class Editor(BaseModel):
    """Model representing editors from the editor table."""

    __tablename__ = "editor"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False, comment="Primary key for editor"
    )

    display_name: Mapped[str] = mapped_column(
        String(128), nullable=False, comment="Display name for editor"
    )

    first_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="First name"
    )

    last_name: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Last name"
    )

    email: Mapped[str | None] = mapped_column(
        String(128), nullable=True, comment="Email address"
    )

    password: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Password hash"
    )

    current: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="Whether this is the current editor"
    )

    connected: Mapped[bool] = mapped_column(
        Boolean, nullable=False, comment="Connection status"
    )

    # Relationships
    genefams: Mapped[list["Genefam"]] = relationship("Genefam", back_populates="editor")

    def __repr__(self) -> str:
        return f"<Editor(id={self.id}, display_name='{self.display_name}')>"


class AltName(BaseModel):
    """Model representing alternative names from the alt_name table."""

    __tablename__ = "alt_name"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="Primary key for alternative name",
    )

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Alternative name"
    )

    nomenclature_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("nomenclature_type.id"),
        nullable=False,
        comment="Foreign key to nomenclature type",
    )

    # Relationships
    genefams: Mapped[list["Genefam"]] = relationship(
        "Genefam", secondary="gene_alt_name", back_populates="alt_names"
    )

    nomenclature_type: Mapped["NomenclatureType"] = relationship(
        "NomenclatureType", back_populates="alt_names"
    )

    def __repr__(self) -> str:
        return f"<AltName(id={self.id}, name='{self.name}')>"


class AltSymbol(BaseModel):
    """Model representing alternative symbols from the alt_symbol table."""

    __tablename__ = "alt_symbol"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="Primary key for alternative symbol",
    )

    symbol: Mapped[str] = mapped_column(
        String(45), nullable=False, comment="Alternative symbol"
    )

    nomenclature_type_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("nomenclature_type.id"),
        nullable=False,
        comment="Foreign key to nomenclature type",
    )

    # Relationships
    genefams: Mapped[list["Genefam"]] = relationship(
        "Genefam", secondary="gene_alt_symbol", back_populates="alt_symbols"
    )

    nomenclature_type: Mapped["NomenclatureType"] = relationship(
        "NomenclatureType", back_populates="alt_symbols"
    )

    def __repr__(self) -> str:
        return f"<AltSymbol(id={self.id}, symbol='{self.symbol}')>"


class NomenclatureType(BaseModel):
    """Model representing nomenclature types from the nomenclature_type table."""

    __tablename__ = "nomenclature_type"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        nullable=False,
        comment="Primary key for nomenclature type",
    )

    type: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Nomenclature type"
    )

    # Relationships
    alt_names: Mapped[list["AltName"]] = relationship(
        "AltName", back_populates="nomenclature_type"
    )

    alt_symbols: Mapped[list["AltSymbol"]] = relationship(
        "AltSymbol", back_populates="nomenclature_type"
    )

    def __repr__(self) -> str:
        return f"<NomenclatureType(id={self.id}, type='{self.type}')>"


class Comment(BaseModel):
    """Model representing comments from the comment table."""

    __tablename__ = "comment"

    id: Mapped[int] = mapped_column(
        Integer, nullable=False, primary_key=True, comment="Primary key for comment"
    )

    comment: Mapped[str] = mapped_column(Text, nullable=False, comment="Comment text")

    author_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("editor.id"),
        nullable=False,
        comment="Author who created the comment",
    )

    locked: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Lock status"
    )

    created: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, comment="Creation date"
    )

    publisher_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Publisher ID"
    )

    status: Mapped[str] = mapped_column(
        String(50), nullable=False, default="Pending", comment="Comment status"
    )

    status_date: Mapped[DateTime] = mapped_column(
        DateTime, nullable=False, comment="Status date"
    )

    replace_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Replace ID"
    )

    replacement_id: Mapped[int | None] = mapped_column(
        Integer, nullable=True, comment="Replacement ID"
    )

    # Relationships
    author: Mapped["Editor"] = relationship("Editor", foreign_keys=[author_id])

    genefams: Mapped[list["Genefam"]] = relationship(
        "Genefam", secondary="gene_has_comment", back_populates="comments"
    )

    def __repr__(self) -> str:
        return f"<Comment(id={self.id}, status='{self.status}')>"


class GeneFlag(BaseModel):
    """Model representing gene flags from the gene_flag table."""

    __tablename__ = "gene_flag"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False, comment="Primary key for gene flag"
    )

    type: Mapped[str] = mapped_column(String(255), nullable=False, comment="Flag type")

    flag_class_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("flag_class.id"),
        nullable=False,
        comment="Foreign key to flag class",
    )

    # Relationships
    flag_class: Mapped["FlagClass"] = relationship("FlagClass", back_populates="flags")

    genefams: Mapped[list["Genefam"]] = relationship(
        "Genefam", secondary="gene_has_flag", back_populates="flags"
    )

    def __repr__(self) -> str:
        return f"<GeneFlag(id={self.id}, type='{self.type}')>"


class FlagClass(BaseModel):
    """Model representing flag classes from the flag_class table."""

    __tablename__ = "flag_class"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False, comment="Primary key for flag class"
    )

    class_name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Flag class name"
    )

    # Relationships
    flags: Mapped[list["GeneFlag"]] = relationship(
        "GeneFlag", back_populates="flag_class"
    )

    def __repr__(self) -> str:
        return f"<FlagClass(id={self.id}, class_name='{self.class_name}')>"


class FamilyNew(BaseModel):
    """Model representing families from the family_new table."""

    __tablename__ = "family_new"

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, nullable=False, comment="Primary key for family"
    )

    abbreviation: Mapped[str] = mapped_column(
        String(255), nullable=True, default="", comment="Family abbreviation"
    )

    name: Mapped[str] = mapped_column(
        String(255), nullable=False, comment="Family name"
    )

    curator_comment: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Curator comment"
    )

    status: Mapped[str] = mapped_column(
        String(50), nullable=True, default="", comment="Family status"
    )

    external_note: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="External note"
    )

    type: Mapped[str] = mapped_column(
        String(50), nullable=True, default="", comment="Family type"
    )

    desc_comment: Mapped[str | None] = mapped_column(
        Text, nullable=True, comment="Description comment"
    )

    desc_label: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Description label"
    )

    desc_source: Mapped[str | None] = mapped_column(
        String(255), nullable=True, comment="Description source"
    )

    desc_go: Mapped[str | None] = mapped_column(
        String(255), nullable=True, default="", comment="Description GO annotation"
    )

    typical_gene: Mapped[str | None] = mapped_column(
        String(50), nullable=True, comment="Typical gene for this family"
    )

    editor_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("editor.id"),
        nullable=False,
        comment="Editor who created this family",
    )

    # Relationships
    genefams: Mapped[list["Genefam"]] = relationship(
        "Genefam", secondary="gene_has_family", back_populates="families"
    )

    def __repr__(self) -> str:
        return f"<FamilyNew(id={self.id}, name='{self.name}')>"


# Note: RefSeq, Ensembl, and Uniprot models removed as they don't exist in the actual database
# External references are handled through the xref system in the real database
