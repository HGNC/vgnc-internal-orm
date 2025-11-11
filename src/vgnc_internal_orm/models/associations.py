"""Association tables for the VGNC ORM system.

This module defines association tables that exist in the actual genefam_production database.
These tables handle many-to-many relationships between the main models.
"""

from sqlalchemy import Column, Index, Integer, String, Table

from .base import BaseModel

# Import BaseCustomModel to get its metadata

# Association table for Assembly-Chromosome relationships
# Use a simpler approach without ForeignKey constraints to avoid metadata conflicts
assembly_has_chr = Table(
    "assembly_has_chr",
    BaseModel.metadata,
    Column("assembly_id", Integer, primary_key=True, comment="Assembly ID"),
    Column("chr_id", Integer, primary_key=True, comment="Chromosome ID"),
    Index("idx_assembly_has_chr_assembly", "assembly_id"),
    Index("idx_assembly_has_chr_chr", "chr_id"),
    comment="Association table linking assemblies to chromosomes",
)

# Association table for Genefam-AltName relationships
gene_alt_name = Table(
    "gene_alt_name",
    BaseModel.metadata,
    Column("id", Integer, primary_key=True, comment="Association ID"),
    Column("genefam_id", Integer, nullable=False, comment="Genefam ID"),
    Column("name_id", Integer, nullable=False, comment="Alternative name ID"),
    Index("idx_gene_alt_name_genefam", "genefam_id"),
    Index("idx_gene_alt_name_name_id", "name_id"),
    comment="Association table linking genefams to alternative names",
)

# Association table for Genefam-AltSymbol relationships
gene_alt_symbol = Table(
    "gene_alt_symbol",
    BaseModel.metadata,
    Column("id", Integer, primary_key=True, comment="Association ID"),
    Column("genefam_id", Integer, nullable=False, comment="Genefam ID"),
    Column("symbol_id", Integer, nullable=False, comment="Alternative symbol ID"),
    Index("idx_gene_alt_symbol_genefam", "genefam_id"),
    Index("idx_gene_alt_symbol_symbol_id", "symbol_id"),
    comment="Association table linking genefams to alternative symbols",
)

# Association table for Genefam-Comment relationships
gene_has_comment = Table(
    "gene_has_comment",
    BaseModel.metadata,
    Column("genefam_id", Integer, primary_key=True, comment="Genefam ID"),
    Column("comment_id", Integer, primary_key=True, comment="Comment ID"),
    Index("idx_gene_has_comment_genefam", "genefam_id"),
    Index("idx_gene_has_comment_comment", "comment_id"),
    comment="Association table linking genefams to comments",
)

# Association table for Genefam-Flag relationships
gene_has_flag = Table(
    "gene_has_flag",
    BaseModel.metadata,
    Column("genefam_id", Integer, primary_key=True, comment="Genefam ID"),
    Column("flag_id", Integer, primary_key=True, comment="Gene flag ID"),
    Index("idx_gene_has_flag_genefam", "genefam_id"),
    Index("idx_gene_has_flag_flag", "flag_id"),
    comment="Association table linking genefams to flags",
)

# Association table for Genefam-Family relationships
gene_has_family = Table(
    "gene_has_family",
    BaseModel.metadata,
    Column(
        "genefam_id", Integer, primary_key=True, nullable=False, comment="Genefam ID"
    ),
    Column("family_id", Integer, primary_key=True, nullable=False, comment="Family ID"),
    Column("url", String(255), nullable=True, comment="URL reference"),
    Column("custom_sort", String(255), nullable=True, comment="Custom sort order"),
    Index("idx_gene_has_family_genefam", "genefam_id"),
    Index("idx_gene_has_family_family", "family_id"),
    comment="Association table linking genefams to families",
)

# Note: External references (RefSeq, Ensembl, Uniprot) are handled through xref tables
# in the actual database, not through direct association tables
