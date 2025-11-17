"""Index and constraint mapping utilities for VGNC ORM.

This module provides utilities to map existing database indexes and constraints
from the current model definitions and generate appropriate SQLAlchemy objects.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

import sqlalchemy
from sqlalchemy import Index, UniqueConstraint

if TYPE_CHECKING:
    pass

from vgnc_internal_orm.utils.mysql_features import FullTextSearch


class IndexType(Enum):
    """Enumeration of database index types."""

    BTREE = "btree"
    HASH = "hash"
    FULLTEXT = "fulltext"
    SPATIAL = "spatial"
    UNIQUE = "unique"


class ConstraintType(Enum):
    """Enumeration of constraint types."""

    PRIMARY_KEY = "primary_key"
    UNIQUE = "unique"
    FOREIGN_KEY = "foreign_key"
    CHECK = "check"
    NOT_NULL = "not_null"


@dataclass
class IndexDefinition:
    """Definition of a database index."""

    name: str
    table_name: str
    columns: list[str]
    index_type: IndexType
    is_unique: bool = False
    is_primary: bool = False
    filter_condition: str | None = None
    comment: str | None = None


@dataclass
class ConstraintDefinition:
    """Definition of a database constraint."""

    name: str
    table_name: str
    constraint_type: ConstraintType
    columns: list[str]
    condition: str | None = None
    comment: str | None = None
    referenced_table: str | None = None
    referenced_columns: list[str] | None = None


@dataclass
class IndexMappingResult:
    """Result of index and constraint mapping."""

    indexes: dict[str, list[IndexDefinition]] = field(default_factory=dict)
    constraints: dict[str, list[ConstraintDefinition]] = field(default_factory=dict)
    performance_recommendations: list[str] = field(default_factory=list)
    missing_indexes: list[dict[str, Any]] = field(default_factory=list)
    fulltext_opportunities: list[dict[str, Any]] = field(default_factory=list)


class IndexMapper:
    """Maps indexes and constraints from model definitions."""

    def __init__(self) -> None:
        """Initialize IndexMapper with model and association table references.

        Uses deferred runtime imports to avoid side effects during autodoc
        and to keep the module lightweight until index mapping is needed.
        """
        # Deferred runtime imports to avoid side effects during autodoc
        self.models: list[Any] = []
        self.association_tables: list[Any] = []
        self._load_models()

    def _load_models(self) -> None:
        """Import models lazily to reduce side effects when building docs."""
        try:
            from vgnc_internal_orm.models.assembly import Assembly as _Assembly
            from vgnc_internal_orm.models.associations import (
                assembly_has_chr as _assembly_has_chr,
            )
            from vgnc_internal_orm.models.associations import (
                gene_alt_name as _gene_alt_name,
            )
            from vgnc_internal_orm.models.associations import (
                gene_alt_symbol as _gene_alt_symbol,
            )
            from vgnc_internal_orm.models.associations import (
                gene_has_comment as _gene_has_comment,
            )
            from vgnc_internal_orm.models.associations import (
                gene_has_family as _gene_has_family,
            )
            from vgnc_internal_orm.models.associations import (
                gene_has_flag as _gene_has_flag,
            )
            from vgnc_internal_orm.models.chromosomes import Chromosomes as _Chromosomes
            from vgnc_internal_orm.models.genefam import Genefam as _Genefam
            from vgnc_internal_orm.models.orthology import (
                GeneFamilyGroupMember as _GeneFamilyGroupMember,
            )
            from vgnc_internal_orm.models.orthology import (
                GeneFamilySpeciesEnhanced as _GeneFamilySpeciesEnhanced,
            )
            from vgnc_internal_orm.models.orthology import (
                GeneOrthologyGroup as _GeneOrthologyGroup,
            )
            from vgnc_internal_orm.models.orthology import (
                SpeciesRelationship as _SpeciesRelationship,
            )
            from vgnc_internal_orm.models.species import Species as _Species

            self.models = [
                _Species,
                _Genefam,
                _Chromosomes,
                _Assembly,
                _GeneFamilySpeciesEnhanced,
                _GeneOrthologyGroup,
                _GeneFamilyGroupMember,
                _SpeciesRelationship,
            ]
            self.association_tables = [
                _assembly_has_chr,
                _gene_alt_name,
                _gene_alt_symbol,
                _gene_has_comment,
                _gene_has_flag,
                _gene_has_family,
            ]
        except Exception:
            # Leave lists empty if imports fail; tooling can handle absence
            self.models = []
            self.association_tables = []

    def analyze_current_indexes(self) -> IndexMappingResult:
        """Analyze current model definitions for indexes and constraints."""
        result = IndexMappingResult()

        # Analyze all model tables
        for model in self.models:
            table_name = model.__tablename__
            result.indexes[table_name] = []
            result.constraints[table_name] = []

            # Extract primary key
            pk_columns = self._extract_primary_key_columns(model)
            if pk_columns:
                pk_def = ConstraintDefinition(
                    name=f"pk_{table_name}",
                    table_name=table_name,
                    constraint_type=ConstraintType.PRIMARY_KEY,
                    columns=pk_columns,
                )
                result.constraints[table_name].append(pk_def)

            # Extract foreign keys
            fk_constraints = self._extract_foreign_key_constraints(model)
            result.constraints[table_name].extend(fk_constraints)

            # Extract unique constraints
            unique_constraints = self._extract_unique_constraints(model)
            result.constraints[table_name].extend(unique_constraints)

            # Extract indexes
            indexes = self._extract_indexes(model)
            result.indexes[table_name].extend(indexes)

        # Analyze association tables
        for association in self.association_tables:
            table_name = association.name
            result.indexes[table_name] = []
            result.constraints[table_name] = []

            # Extract primary key (usually composite)
            pk_columns = self._extract_association_primary_key(association)
            if pk_columns:
                pk_def = ConstraintDefinition(
                    name=f"pk_{table_name}",
                    table_name=table_name,
                    constraint_type=ConstraintType.PRIMARY_KEY,
                    columns=pk_columns,
                )
                result.constraints[table_name].append(pk_def)

            # Extract foreign keys
            fk_constraints = self._extract_association_foreign_keys(association)
            result.constraints[table_name].extend(fk_constraints)

        # Generate recommendations
        result.performance_recommendations = self._generate_performance_recommendations(
            result.indexes
        )
        result.missing_indexes = self._identify_missing_indexes(result.indexes)
        result.fulltext_opportunities = self._identify_fulltext_opportunities(
            result.indexes
        )

        return result

    def _extract_primary_key_columns(self, model: Any) -> list[str]:
        """Extract primary key columns from a model."""
        if hasattr(model, "__table__"):
            pk_columns = [col.name for col in model.__table__.primary_key.columns]
            return pk_columns
        return ["id"]  # Default primary key

    def _extract_foreign_key_constraints(
        self, model: Any
    ) -> list[ConstraintDefinition]:
        """Extract foreign key constraints from a model."""
        constraints = []

        if hasattr(model, "__table__"):
            for fk in model.__table__.foreign_keys:
                # Get column name (single column FK)
                column_name = fk.parent.name

                # Get referenced table and column - handle missing tables gracefully
                try:
                    referenced_table = fk.column.table.name
                    referenced_column = fk.column.name

                    fk_def = ConstraintDefinition(
                        name=fk.name or f"fk_{model.__tablename__}_{column_name}",
                        table_name=model.__tablename__,
                        constraint_type=ConstraintType.FOREIGN_KEY,
                        columns=[column_name],
                        referenced_table=referenced_table,
                        referenced_columns=[referenced_column],
                    )
                    constraints.append(fk_def)
                except (sqlalchemy.exc.NoReferencedTableError, AttributeError):
                    # Skip foreign keys that reference non-existent tables (circular import issues)
                    continue

        return constraints

    def _extract_unique_constraints(self, model: Any) -> list[ConstraintDefinition]:
        """Extract unique constraints from a model."""
        constraints = []

        if hasattr(model, "__table_args__"):
            table_args = model.__table_args__
            if isinstance(table_args, (list, tuple)):
                for item in table_args:
                    if isinstance(item, UniqueConstraint):
                        columns = [col.name for col in item.columns]
                        constraint_def = ConstraintDefinition(
                            name=str(item.name)
                            or f"uq_{model.__tablename__}_{'_'.join(columns)}",
                            table_name=model.__tablename__,
                            constraint_type=ConstraintType.UNIQUE,
                            columns=columns,
                        )
                        constraints.append(constraint_def)

        return constraints

    def _extract_indexes(self, model: Any) -> list[IndexDefinition]:
        """Extract indexes from a model."""
        indexes = []

        if hasattr(model, "__table_args__"):
            table_args = model.__table_args__
            if isinstance(table_args, (list, tuple)):
                for item in table_args:
                    if isinstance(item, Index):
                        columns = [col.name for col in item.columns]
                        index_def = IndexDefinition(
                            name=str(item.name),
                            table_name=model.__tablename__,
                            columns=columns,
                            index_type=IndexType.BTREE,  # Default type
                            is_unique=item.unique,
                        )
                        indexes.append(index_def)

        return indexes

    def _extract_association_primary_key(self, association: Any) -> list[str]:
        """Extract primary key columns from an association table."""
        pk_columns = [col.name for col in association.primary_key.columns]
        return pk_columns

    def _extract_association_foreign_keys(
        self, association: Any
    ) -> list[ConstraintDefinition]:
        """Extract foreign key constraints from an association table."""
        constraints = []

        for fk in association.foreign_keys:
            column_name = fk.parent.name
            referenced_table = fk.column.table.name
            referenced_column = fk.column.name

            fk_def = ConstraintDefinition(
                name=fk.name or f"fk_{association.name}_{column_name}",
                table_name=association.name,
                constraint_type=ConstraintType.FOREIGN_KEY,
                columns=[column_name],
                referenced_table=referenced_table,
                referenced_columns=[referenced_column],
            )
            constraints.append(fk_def)

        return constraints

    def _generate_performance_recommendations(
        self, indexes: dict[str, list[IndexDefinition]]
    ) -> list[str]:
        """Generate performance recommendations based on current indexes."""
        recommendations = []

        # Check for tables with no indexes
        for table_name, table_indexes in indexes.items():
            if not table_indexes:
                recommendations.append(
                    f"Table '{table_name}' has no indexes - consider adding indexes for frequently queried columns"
                )

        # Check for missing foreign key indexes
        for table_name, table_indexes in indexes.items():
            indexed_columns = set()
            for idx in table_indexes:
                indexed_columns.update(idx.columns)

            # Add recommendation for foreign key indexing
            if table_name in ["chromosomes", "assembly"]:
                if "species_id" not in indexed_columns:
                    recommendations.append(
                        f"Consider adding index on '{table_name}.species_id' for foreign key performance"
                    )

        return recommendations

    def _identify_missing_indexes(
        self, indexes: dict[str, list[IndexDefinition]]
    ) -> list[dict[str, Any]]:
        """Identify missing indexes that would improve performance."""
        missing = []

        # Common query patterns that would benefit from indexes
        common_patterns = [
            {
                "table": "species",
                "columns": ["vgnc_prefix"],
                "reason": "Frequent lookups by VGNC prefix",
            },
            {
                "table": "species",
                "columns": ["taxon_id"],
                "reason": "Frequent filtering by taxon ID",
            },
            {
                "table": "genefams",
                "columns": ["family_type"],
                "reason": "Filtering by gene family type",
            },
            {
                "table": "genefams",
                "columns": ["functional_category"],
                "reason": "Filtering by functional category",
            },
            {
                "table": "chromosomes",
                "columns": ["species_id", "chromosome_name"],
                "reason": "Combined species and chromosome queries",
            },
        ]

        for pattern in common_patterns:
            table_name = str(pattern["table"])  # Ensure string type
            if table_name in indexes:
                indexed_columns = set()
                for idx in indexes[table_name]:
                    indexed_columns.update(idx.columns)

                # Check if the recommended index already exists
                if not all(col in indexed_columns for col in pattern["columns"]):
                    missing.append(pattern)

        return missing

    def _identify_fulltext_opportunities(
        self, indexes: dict[str, list[IndexDefinition]]
    ) -> list[dict[str, Any]]:
        """Identify opportunities for full-text search indexes."""
        opportunities = []

        # Text fields that would benefit from full-text search
        text_fields = [
            {
                "table": "species",
                "columns": ["scientific_name", "common_name"],
                "reason": "Species name searches",
            },
            {
                "table": "genefam",
                "columns": ["assigned_name", "assigned_symbol", "assigned_id"],
                "reason": "Gene family name, symbol, and ID searches",
            },
        ]

        for text_field in text_fields:
            table_name = str(text_field["table"])  # Ensure string type
            if table_name in indexes:
                # Check if full-text index already exists
                has_fulltext = any(
                    idx.index_type == IndexType.FULLTEXT for idx in indexes[table_name]
                )

                if not has_fulltext:
                    opportunities.append(text_field)

        return opportunities

    def generate_sqlalchemy_indexes(self) -> dict[str, list[Index]]:
        """Generate SQLAlchemy Index objects for all models."""
        sqlalchemy_indexes = {}

        for model in self.models:
            table_name = model.__tablename__
            indexes = []

            # Primary key index
            pk_columns = self._extract_primary_key_columns(model)
            if pk_columns:
                pk_index = Index(f"pk_{table_name}", *pk_columns, unique=True)
                indexes.append(pk_index)

            # Foreign key indexes
            fk_constraints = self._extract_foreign_key_constraints(model)
            for fk in fk_constraints:
                if fk.columns:  # Only create index for single-column FKs
                    fk_index = Index(
                        f"idx_{table_name}_{'_'.join(fk.columns)}", *fk.columns
                    )
                    indexes.append(fk_index)

            # Unique constraints
            unique_constraints = self._extract_unique_constraints(model)
            for uc in unique_constraints:
                unique_index = Index(uc.name, *uc.columns, unique=True)
                indexes.append(unique_index)

            sqlalchemy_indexes[table_name] = indexes

        return sqlalchemy_indexes

    def generate_fulltext_indexes(self) -> dict[str, list[Index]]:
        """Generate full-text search indexes using MySQL features."""
        fulltext_indexes = {}

        # Generate full-text indexes for species
        species_ft_index = FullTextSearch.create_fulltext_index(
            table_name="species",
            columns=["scientific_name", "common_name"],
            index_name="fti_species_names",
        )
        fulltext_indexes["species"] = [species_ft_index]

        # Generate full-text indexes for gene families
        genefam_ft_index = FullTextSearch.create_fulltext_index(
            table_name="genefams",
            columns=["name", "description"],
            index_name="fti_genefam_info",
        )
        fulltext_indexes["genefams"] = [genefam_ft_index]

        return fulltext_indexes

    def create_missing_index_definitions(self) -> list[IndexDefinition]:
        """Create index definitions for missing performance-critical indexes."""

        # Performance-critical indexes for common query patterns
        critical_indexes = [
            IndexDefinition(
                name="idx_species_vgnc_prefix",
                table_name="species",
                columns=["vgnc_prefix"],
                index_type=IndexType.BTREE,
                comment="Index for VGNC prefix lookups",
            ),
            IndexDefinition(
                name="idx_species_taxon_id",
                table_name="species",
                columns=["taxon_id"],
                index_type=IndexType.BTREE,
                comment="Index for taxon filtering",
            ),
            IndexDefinition(
                name="idx_genefams_family_type",
                table_name="genefams",
                columns=["family_type"],
                index_type=IndexType.BTREE,
                comment="Index for family type filtering",
            ),
            IndexDefinition(
                name="idx_genefams_functional_category",
                table_name="genefams",
                columns=["functional_category"],
                index_type=IndexType.BTREE,
                comment="Index for functional category filtering",
            ),
            IndexDefinition(
                name="idx_chromosomes_species_chromosome",
                table_name="chromosomes",
                columns=["species_id", "chromosome_name"],
                index_type=IndexType.BTREE,
                comment="Composite index for species-chromosome queries",
            ),
            IndexDefinition(
                name="idx_assembly_species_version",
                table_name="assembly",
                columns=["species_id", "version"],
                index_type=IndexType.BTREE,
                comment="Composite index for species-version queries",
            ),
        ]

        return critical_indexes
