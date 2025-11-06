"""Specialized index implementations for VGNC ORM.

This module provides custom implementations for MySQL FULLTEXT indexes,
unique constraints with complex logic, and performance-optimized indexes
that integrate seamlessly with SQLAlchemy models.
"""

from typing import List, Dict, Any, Optional, Union, Callable
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy import Index, UniqueConstraint, CheckConstraint, text, Column, String, Text
from sqlalchemy.schema import DDLElement
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.sql import expression

from vgnc_internal_orm.utils.mysql_features import FullTextSearch


class IndexType(Enum):
    """Types of specialized indexes."""
    FULLTEXT = "fulltext"
    UNIQUE_COMPOSITE = "unique_composite"
    PARTIAL = "partial"
    FUNCTIONAL = "functional"
    EXPRESSION = "expression"


@dataclass
class FullTextIndex:
    """MySQL FULLTEXT index implementation."""
    name: str
    table_name: str
    columns: List[str]
    parser: str = "ngram"
    min_token_size: int = 2
    min_word_length: int = 4
    stopword_list: Optional[str] = None

    def to_sqlalchemy_index(self) -> Index:
        """Convert to SQLAlchemy Index object."""
        # Create a custom DDL element for FULLTEXT
        return Index(
            self.name,
            *self.columns,
            mysql_prefix="FULLTEXT",
            mysql_with_parser=self.parser,
            mysql_min_token_size=self.min_token_size,
            mysql_min_word_length=self.min_word_length
        )

    def to_ddl(self) -> str:
        """Generate DDL statement for MySQL."""
        columns_str = ", ".join(self.columns)
        parser_clause = f" WITH PARSER {self.parser}" if self.parser else ""

        ddl = f"CREATE FULLTEXT INDEX {self.name} ON {self.table_name} ({columns_str}){parser_clause}"

        if self.min_word_length != 4:
            ddl += f" MIN_WORD_LENGTH = {self.min_word_length}"

        if self.stopword_list:
            ddl += f" STOPWORD_LIST = '{self.stopword_list}'"

        return ddl


@dataclass
class UniqueCompositeIndex:
    """Unique constraint on multiple columns with optional conditions."""
    name: str
    table_name: str
    columns: List[str]
    condition: Optional[str] = None
    ignore_nulls: bool = True
    deferrable: Optional[str] = None

    def to_sqlalchemy_constraint(self) -> UniqueConstraint:
        """Convert to SQLAlchemy UniqueConstraint."""
        return UniqueConstraint(
            *self.columns,
            name=self.name,
            deferrable=self.deferrable
        )

    def to_ddl(self) -> str:
        """Generate DDL statement."""
        columns_str = ", ".join(self.columns)
        condition_clause = f" WHERE {self.condition}" if self.condition else ""
        ignore_nulls_clause = " IGNORE NULL" if self.ignore_nulls else ""
        deferrable_clause = f" DEFERRABLE {self.deferrable}" if self.deferrable else ""

        ddl = f"ALTER TABLE {self.table_name} ADD CONSTRAINT {self.name} "
        ddl += f"UNIQUE ({columns_str}){ignore_nulls_clause}{condition_clause}{deferrable_clause}"

        return ddl


@dataclass
class PartialIndex:
    """Partial index that applies only to rows matching a condition."""
    name: str
    table_name: str
    columns: List[str]
    where_condition: str
    index_type: str = "btree"
    unique: bool = False

    def to_sqlalchemy_index(self) -> Index:
        """Convert to SQLAlchemy Index (using PostgreSQL syntax)."""
        # Note: MySQL doesn't support partial indexes directly
        # This would need to be handled with filtered indexes in MySQL 8.0+
        return Index(
            self.name,
            *self.columns,
            unique=self.unique,
            postgresql_where=self.where_condition
        )

    def to_ddl(self) -> str:
        """Generate DDL statement (PostgreSQL syntax)."""
        columns_str = ", ".join(self.columns)
        unique_clause = "UNIQUE " if self.unique else ""
        where_clause = f" WHERE {self.where_condition}"

        ddl = f"CREATE {unique_clause}INDEX {self.name} ON {self.table_name} ({columns_str}){where_clause}"
        return ddl


@dataclass
class FunctionalIndex:
    """Functional index on expression results."""
    name: str
    table_name: str
    expression: str
    index_type: str = "btree"
    unique: bool = False

    def to_sqlalchemy_index(self) -> Index:
        """Convert to SQLAlchemy Index."""
        return Index(
            self.name,
            text(self.expression),
            unique=self.unique
        )

    def to_ddl(self) -> str:
        """Generate DDL statement."""
        unique_clause = "UNIQUE " if self.unique else ""
        ddl = f"CREATE {unique_clause}INDEX {self.name} ON {self.table_name} ({self.expression})"
        return ddl


class VGNCIndexDefinitions:
    """Pre-defined specialized indexes for VGNC database patterns."""

    # Species table specialized indexes
    SPECIES_FULLTEXT_INDEXES = [
        FullTextIndex(
            name="fti_species_taxonomy",
            table_name="species",
            columns=["scientific_name", "common_name", "genus", "species"],
            parser="ngram"
        ),
        FullTextIndex(
            name="fti_species_classification",
            table_name="species",
            columns=["class_name", "order_name", "family_name"],
            parser="ngram"
        ),
    ]

    SPECIES_UNIQUE_INDEXES = [
        UniqueCompositeIndex(
            name="uq_species_taxonomy",
            table_name="species",
            columns=["genus", "species"],
            condition="is_active = true"
        ),
        UniqueCompositeIndex(
            name="uq_species_vgnc_class",
            table_name="species",
            columns=["vgnc_prefix", "class_name"]
        ),
    ]

    SPECIES_PARTIAL_INDEXES = [
        PartialIndex(
            name="idx_species_live_display",
            table_name="species",
            columns=["display_name"],
            where_condition="is_live = 'Y'"
        ),
        PartialIndex(
            name="idx_species_prefix_live",
            table_name="species",
            columns=["genefam_prefix"],
            where_condition="is_live = 'Y'"
        ),
    ]

    SPECIES_FUNCTIONAL_INDEXES = [
        FunctionalIndex(
            name="idx_species_name_upper",
            table_name="species",
            expression="UPPER(scientific_name)"
        ),
        FunctionalIndex(
            name="idx_species_vgnc_lower",
            table_name="species",
            expression="LOWER(vgnc_prefix)"
        ),
    ]

    # Gene families specialized indexes
    GENEFAM_FULLTEXT_INDEXES = [
        FullTextIndex(
            name="fti_genefam_search",
            table_name="genefams",
            columns=["name", "description"],
            parser="ngram"
        ),
        FullTextIndex(
            name="fti_genefam_taxonomy",
            table_name="genefams",
            columns=["family_type", "functional_category", "taxonomic_scope"],
            parser="ngram"
        ),
    ]

    GENEFAM_UNIQUE_INDEXES = [
        UniqueCompositeIndex(
            name="uq_genefam_version",
            table_name="genefams",
            columns=["name", "version"],
            condition="is_active = true"
        ),
        UniqueCompositeIndex(
            name="uq_genefam_external",
            table_name="genefams",
            columns=["external_id", "external_source"],
            condition="external_id IS NOT NULL"
        ),
    ]

    GENEFAM_PARTIAL_INDEXES = [
        PartialIndex(
            name="idx_genefam_active_type",
            table_name="genefams",
            columns=["name"],
            where_condition="is_active = true"
        ),
        PartialIndex(
            name="idx_genefam_protein_coding",
            table_name="genefams",
            columns=["description"],
            where_condition="family_type = 'protein_coding'"
        ),
    ]

    # Chromosomes specialized indexes
    CHROMOSOMES_UNIQUE_INDEXES = [
        UniqueCompositeIndex(
            name="uq_chromosome_species_accession",
            table_name="chromosomes",
            columns=["species_id", "refseq_accession"],
            condition="refseq_accession IS NOT NULL"
        ),
        UniqueCompositeIndex(
            name="uq_chromosome_species_ensembl",
            table_name="chromosomes",
            columns=["species_id", "ensembl_id"],
            condition="ensembl_id IS NOT NULL"
        ),
    ]

    CHROMOSOMES_PARTIAL_INDEXES = [
        PartialIndex(
            name="idx_chromosomes_active_length",
            table_name="chromosomes",
            columns=["length"],
            where_condition="is_active = true AND length > 1000000"
        ),
        PartialIndex(
            name="idx_chromosomes_complete_reference",
            table_name="chromosomes",
            columns=["assembly_name"],
            where_condition="is_complete = true AND is_reference = true"
        ),
    ]

    # Assembly specialized indexes
    ASSEMBLY_UNIQUE_INDEXES = [
        UniqueCompositeIndex(
            name="uq_assembly_species_accession",
            table_name="assembly",
            columns=["species_id", "accession_number"],
            condition="accession_number IS NOT NULL"
        ),
        UniqueCompositeIndex(
            name="uq_assembly_refseq_primary",
            table_name="assembly",
            columns=["refseq_accession"],
            condition="is_primary = true AND refseq_accession IS NOT NULL"
        ),
    ]

    ASSEMBLY_PARTIAL_INDEXES = [
        PartialIndex(
            name="idx_assembly_primary_active",
            table_name="assembly",
            columns=["assembly_name"],
            where_condition="is_primary = true AND is_active = true"
        ),
        PartialIndex(
            name="idx_assembly_reference_quality",
            table_name="assembly",
            columns=["assembly_level"],
            where_condition="is_reference = true AND assembly_level IN ('chromosome', 'scaffold')"
        ),
    ]

    # Orthology specialized indexes
    ORTHOLOGY_FULLTEXT_INDEXES = [
        FullTextIndex(
            name="fti_orthology_group",
            table_name="genefam_orthology_group",
            columns=["group_name", "phylogenetic_scope"],
            parser="ngram"
        ),
    ]

    ORTHOLOGY_UNIQUE_INDEXES = [
        UniqueCompositeIndex(
            name="uq_orthology_group_confidence",
            table_name="genefam_orthology_group",
            columns=["group_id", "confidence_score"],
            condition="is_active = true"
        ),
    ]

    ORTHOLOGY_PARTIAL_INDEXES = [
        PartialIndex(
            name="idx_orthology_high_confidence",
            table_name="genefam_orthology_group",
            columns=["group_name"],
            where_condition="confidence_score >= 0.9 AND is_active = true"
        ),
        PartialIndex(
            name="idx_orthology_broad_scope",
            table_name="genefam_orthology_group",
            columns=["conservation_level"],
            where_condition="phylogenetic_scope IN ('kingdom', 'phylum', 'class', 'order')"
        ),
    ]


class SpecializedIndexManager:
    """Manages creation and application of specialized indexes."""

    def __init__(self):
        self.fulltext_indexes = {}
        self.unique_indexes = {}
        self.partial_indexes = {}
        self.functional_indexes = {}

        # Load all defined indexes
        self._load_all_indexes()

    def _load_all_indexes(self):
        """Load all predefined specialized indexes."""
        # Full-text indexes
        self.fulltext_indexes["species"] = VGNCIndexDefinitions.SPECIES_FULLTEXT_INDEXES
        self.fulltext_indexes["genefams"] = VGNCIndexDefinitions.GENEFAM_FULLTEXT_INDEXES
        self.fulltext_indexes["genefam_orthology_group"] = VGNCIndexDefinitions.ORTHOLOGY_FULLTEXT_INDEXES

        # Unique composite indexes
        self.unique_indexes["species"] = VGNCIndexDefinitions.SPECIES_UNIQUE_INDEXES
        self.unique_indexes["genefams"] = VGNCIndexDefinitions.GENEFAM_UNIQUE_INDEXES
        self.unique_indexes["chromosomes"] = VGNCIndexDefinitions.CHROMOSOMES_UNIQUE_INDEXES
        self.unique_indexes["assembly"] = VGNCIndexDefinitions.ASSEMBLY_UNIQUE_INDEXES
        self.unique_indexes["genefam_orthology_group"] = VGNCIndexDefinitions.ORTHOLOGY_UNIQUE_INDEXES

        # Partial indexes
        self.partial_indexes["species"] = VGNCIndexDefinitions.SPECIES_PARTIAL_INDEXES
        self.partial_indexes["genefams"] = VGNCIndexDefinitions.GENEFAM_PARTIAL_INDEXES
        self.partial_indexes["chromosomes"] = VGNCIndexDefinitions.CHROMOSOMES_PARTIAL_INDEXES
        self.partial_indexes["assembly"] = VGNCIndexDefinitions.ASSEMBLY_PARTIAL_INDEXES
        self.partial_indexes["genefam_orthology_group"] = VGNCIndexDefinitions.ORTHOLOGY_PARTIAL_INDEXES

        # Functional indexes
        self.functional_indexes["species"] = VGNCIndexDefinitions.SPECIES_FUNCTIONAL_INDEXES

    def create_fulltext_indexes(self, table_name: str) -> List[FullTextIndex]:
        """Create full-text search indexes for a table."""
        return self.fulltext_indexes.get(table_name, [])

    def create_unique_composite_indexes(self, table_name: str) -> List[UniqueCompositeIndex]:
        """Create unique composite indexes for a table."""
        return self.unique_indexes.get(table_name, [])

    def create_partial_indexes(self, table_name: str) -> List[PartialIndex]:
        """Create partial indexes for a table."""
        return self.partial_indexes.get(table_name, [])

    def create_functional_indexes(self, table_name: str) -> List[FunctionalIndex]:
        """Create functional indexes for a table."""
        return self.functional_indexes.get(table_name, [])

    def generate_mysql_ddl(self, table_name: str) -> List[str]:
        """Generate MySQL DDL statements for all specialized indexes."""
        ddl_statements = []

        # Full-text indexes
        for ft_index in self.create_fulltext_indexes(table_name):
            ddl_statements.append(ft_index.to_ddl())

        # Unique composite indexes
        for unique_index in self.create_unique_composite_indexes(table_name):
            ddl_statements.append(unique_index.to_ddl())

        # Note: Partial indexes are not directly supported in MySQL
        # These would need to be implemented as filtered indexes in MySQL 8.0+

        # Functional indexes (MySQL 8.0+)
        for func_index in self.create_functional_indexes(table_name):
            ddl_statements.append(func_index.to_ddl())

        return ddl_statements

    def generate_postgresql_ddl(self, table_name: str) -> List[str]:
        """Generate PostgreSQL DDL statements for all specialized indexes."""
        ddl_statements = []

        # Full-text indexes (PostgreSQL uses different syntax)
        for ft_index in self.create_fulltext_indexes(table_name):
            columns_str = ", ".join(ft_index.columns)
            ddl = f"CREATE INDEX {ft_index.name} ON {table_name} USING gin(to_tsvector('english', {columns_str}))"
            ddl_statements.append(ddl)

        # Unique composite indexes
        for unique_index in self.create_unique_composite_indexes(table_name):
            ddl_statements.append(unique_index.to_ddl())

        # Partial indexes
        for partial_index in self.create_partial_indexes(table_name):
            ddl_statements.append(partial_index.to_ddl())

        # Functional indexes
        for func_index in self.create_functional_indexes(table_name):
            ddl_statements.append(func_index.to_ddl())

        return ddl_statements

    def apply_to_models(self, models: Optional[List] = None) -> Dict[str, List[str]]:
        """Apply specialized indexes to SQLAlchemy models."""
        applied_indexes = {}

        if models is None:
            # Import models if not provided
            from vgnc_internal_orm.models.species import Species
            from vgnc_internal_orm.models.genefam import Genefam
            from vgnc_internal_orm.models.chromosomes import Chromosomes
            from vgnc_internal_orm.models.assembly import Assembly
            from vgnc_internal_orm.models.orthology import (
                GeneFamilySpeciesEnhanced, GeneOrthologyGroup,
                GeneFamilyGroupMember, SpeciesRelationship
            )
            models = [Species, Genefam, Chromosomes, Assembly,
                     GeneFamilySpeciesEnhanced, GeneOrthologyGroup,
                     GeneFamilyGroupMember, SpeciesRelationship]

        for model in models:
            table_name = model.__tablename__
            specialized_indexes = []

            # Convert specialized indexes to SQLAlchemy objects
            for ft_index in self.create_fulltext_indexes(table_name):
                specialized_indexes.append(ft_index.to_sqlalchemy_index())

            for unique_index in self.create_unique_composite_indexes(table_name):
                specialized_indexes.append(unique_index.to_sqlalchemy_constraint())

            # Note: Partial and functional indexes require specific database support
            # For now, we'll focus on what works with standard SQLAlchemy

            # Apply to model
            if hasattr(model, '__table_args__'):
                existing_args = list(model.__table_args__) if isinstance(model.__table_args__, (list, tuple)) else []
                for idx in specialized_indexes:
                    existing_args.append(idx)
                model.__table_args__ = tuple(existing_args)
            else:
                model.__table_args__ = tuple(specialized_indexes)

            applied_indexes[table_name] = [str(type(idx).__name__) for idx in specialized_indexes]

        return applied_indexes

    def analyze_index_usage(self, table_name: str, query_patterns: List[str]) -> Dict[str, Any]:
        """Analyze how well specialized indexes support common query patterns."""
        analysis = {
            "table_name": table_name,
            "available_indexes": {
                "fulltext": len(self.create_fulltext_indexes(table_name)),
                "unique_composite": len(self.create_unique_composite_indexes(table_name)),
                "partial": len(self.create_partial_indexes(table_name)),
                "functional": len(self.create_functional_indexes(table_name))
            },
            "query_support": {},
            "recommendations": []
        }

        # Analyze each query pattern
        for query in query_patterns:
            query_lower = query.lower()
            support_score = 0
            matching_indexes = []

            # Check for full-text search patterns
            if any(keyword in query_lower for keyword in ['search', 'like', 'contains']):
                if self.create_fulltext_indexes(table_name):
                    support_score += 3
                    matching_indexes.extend([idx.name for idx in self.create_fulltext_indexes(table_name)])

            # Check for unique constraint patterns
            if 'distinct' in query_lower or 'group by' in query_lower:
                if self.create_unique_composite_indexes(table_name):
                    support_score += 2
                    matching_indexes.extend([idx.name for idx in self.create_unique_composite_indexes(table_name)])

            # Check for filter patterns
            if 'where' in query_lower and ('is_active' in query_lower or 'is_' in query_lower):
                if self.create_partial_indexes(table_name):
                    support_score += 2
                    matching_indexes.extend([idx.name for idx in self.create_partial_indexes(table_name)])

            analysis["query_support"][query] = {
                "support_score": support_score,
                "matching_indexes": matching_indexes
            }

        # Generate recommendations
        if analysis["available_indexes"]["fulltext"] == 0:
            analysis["recommendations"].append(
                "Consider adding full-text search indexes for better text search performance"
            )

        if analysis["available_indexes"]["unique_composite"] == 0:
            analysis["recommendations"].append(
                "Consider adding unique composite indexes to prevent duplicate data"
            )

        return analysis