"""Schema analyzer for VGNC ORM database indexes and constraints.

This module provides utilities to analyze the existing database schema,
catalog indexes and constraints, and generate recommendations for additional
performance-critical indexes and constraints.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import TYPE_CHECKING, Any

from sqlalchemy import CheckConstraint, ForeignKeyConstraint, Index, UniqueConstraint

if TYPE_CHECKING:
    pass


class IndexType(Enum):
    """Enumeration of database index types."""

    BTREE = "btree"
    HASH = "hash"
    FULLTEXT = "fulltext"
    SPATIAL = "spatial"
    GIN = "gin"


class ConstraintType(Enum):
    """Enumeration of constraint types."""

    PRIMARY_KEY = "primary_key"
    UNIQUE = "unique"
    FOREIGN_KEY = "foreign_key"
    CHECK = "check"
    NOT_NULL = "not_null"


@dataclass
class IndexInfo:
    """Information about a database index."""

    name: str
    table_name: str
    columns: list[str]
    index_type: IndexType
    is_unique: bool = False
    is_primary: bool = False
    filter_condition: str | None = None
    comment: str | None = None


@dataclass
class ConstraintInfo:
    """Information about a database constraint."""

    name: str
    table_name: str
    constraint_type: ConstraintType
    columns: list[str]
    condition: str | None = None
    comment: str | None = None
    referenced_table: str | None = None
    referenced_columns: list[str] | None = None


@dataclass
class TableInfo:
    """Information about a database table."""

    name: str
    columns: list[dict[str, Any]]
    primary_key_columns: list[str]
    foreign_keys: list[dict[str, Any]]
    indexes: list[IndexInfo] = field(default_factory=list)
    constraints: list[ConstraintInfo] = field(default_factory=list)
    row_count: int | None = None


@dataclass
class SchemaAnalysisResult:
    """Result of schema analysis."""

    tables: dict[str, TableInfo]
    total_indexes: int
    total_constraints: int
    performance_recommendations: list[str]
    missing_indexes: list[dict[str, Any]] = field(default_factory=list)
    redundant_indexes: list[dict[str, Any]] = field(default_factory=list)
    fulltext_opportunities: list[dict[str, Any]] = field(default_factory=list)


class SchemaAnalyzer:
    """Analyzes database schema for indexes and constraints."""

    def __init__(self) -> None:
        """Initialize SchemaAnalyzer with model references.

        Uses lazy imports to avoid side effects during module import
        (e.g., autodoc generation) and loads all available models
        and association tables for schema analysis.
        """
        # Lazy import to avoid side effects during module import (e.g., autodoc)
        self.models: list[Any] = []
        self.association_tables: list[Any] = []
        self._load_models()

    def _load_models(self) -> None:
        """Load all models and association tables for schema analysis.

        Dynamically imports models to avoid circular imports and side effects
        during module initialization. Populates the models and association_tables
        lists for later schema analysis operations.
        """
        try:
            from vgnc_internal_orm.models.assembly import Assembly as _Assembly

            # Note: gene_orthology_association and genefam_species_association don't exist
            # Using existing association tables instead
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
            self.models = []
            self.association_tables = []

    def analyze_current_schema(self) -> SchemaAnalysisResult:
        """Analyze the current ORM schema for indexes and constraints."""
        result = SchemaAnalysisResult(
            tables={},
            total_indexes=0,
            total_constraints=0,
            performance_recommendations=[],
        )

        # Analyze all model tables
        for model in self.models:
            table_info = self._analyze_model_table(model)
            result.tables[table_info.name] = table_info
            result.total_indexes += len(table_info.indexes)
            result.total_constraints += len(table_info.constraints)

        # Analyze association tables
        for association in self.association_tables:
            table_info = self._analyze_association_table(association)
            result.tables[table_info.name] = table_info
            result.total_indexes += len(table_info.indexes)
            result.total_constraints += len(table_info.constraints)

        # Generate recommendations
        result.performance_recommendations = self._generate_performance_recommendations(
            result.tables
        )
        result.missing_indexes = self._identify_missing_indexes(result.tables)
        result.redundant_indexes = self._identify_redundant_indexes(result.tables)
        result.fulltext_opportunities = self._identify_fulltext_opportunities(
            result.tables
        )

        return result

    def _analyze_model_table(self, model: Any) -> TableInfo:
        """Analyze a SQLAlchemy model table for indexes and constraints."""
        table_name = model.__tablename__

        # Extract column information first
        columns = []
        if hasattr(model, "__table__"):
            columns = self._extract_column_info(model.__table__)

        # Extract primary key and foreign keys
        primary_key_columns = self._extract_primary_key_columns(model)
        foreign_keys = self._extract_foreign_keys(model)

        table_info = TableInfo(
            name=table_name,
            columns=columns,
            primary_key_columns=primary_key_columns,
            foreign_keys=foreign_keys,
        )

        # Extract indexes from __table_args__
        if hasattr(model, "__table_args__"):
            for item in model.__table_args__:
                if isinstance(item, Index):
                    table_info.indexes.append(
                        self._extract_index_info(item, table_name)
                    )
                elif isinstance(
                    item, (UniqueConstraint, ForeignKeyConstraint, CheckConstraint)
                ):
                    table_info.constraints.append(
                        self._extract_constraint_info(item, table_name)
                    )

        return table_info

    def _analyze_association_table(self, association: Any) -> TableInfo:
        """Analyze an association table for indexes and constraints."""
        table_name = association.name
        table_info = TableInfo(
            name=table_name, columns=[], primary_key_columns=[], foreign_keys=[]
        )

        # Extract column information
        table_info.columns = self._extract_column_info(association)

        # Extract primary key (composite primary key for association tables)
        table_info.primary_key_columns = self._extract_primary_key_columns_from_table(
            association
        )

        # Look for indexes in the table definition
        if hasattr(association, "indexes"):
            for index in association.indexes:
                table_info.indexes.append(self._extract_index_info(index, table_name))

        return table_info

    def _extract_column_info(self, table: Any) -> list[dict[str, Any]]:
        """Extract column information from a SQLAlchemy table."""
        columns = []
        for column in table.columns:
            columns.append(
                {
                    "name": column.name,
                    "type": str(column.type),
                    "nullable": column.nullable,
                    "primary_key": column.primary_key,
                    "unique": column.unique,
                    "foreign_keys": (
                        list(column.foreign_keys)
                        if hasattr(column, "foreign_keys")
                        else []
                    ),
                    "comment": column.comment,
                }
            )
        return columns

    def _extract_primary_key_columns(self, model: Any) -> list[str]:
        """Extract primary key column names from a model."""
        if hasattr(model, "__table__"):
            return [col.name for col in model.__table__.primary_key.columns]
        return []

    def _extract_primary_key_columns_from_table(self, table: Any) -> list[str]:
        """Extract primary key column names from a table object."""
        return [col.name for col in table.primary_key.columns]

    def _extract_foreign_keys(self, model: Any) -> list[dict[str, Any]]:
        """Extract foreign key information from a model."""
        foreign_keys = []
        if hasattr(model, "__table__"):
            for fk in model.__table__.foreign_keys:
                foreign_key_info = {
                    "column": fk.parent.name,
                    "referenced_table": fk.column.table.name,
                    "referenced_column": fk.column.name,
                }
                foreign_keys.append(foreign_key_info)
        return foreign_keys

    def _extract_index_info(self, index: Index, table_name: str) -> IndexInfo:
        """Extract information from a SQLAlchemy Index object."""
        columns = [col.name for col in index.columns]

        # Determine index type from column types and index properties
        index_type = self._determine_index_type(index, columns)

        # Check if it's a unique index
        is_unique = index.unique or any(col.unique for col in index.columns)

        # Check if it's a primary key index
        is_primary = index.name == "pk__" + table_name

        return IndexInfo(
            name=str(index.name) if index.name else f"idx_{table_name}_auto",
            table_name=table_name,
            columns=columns,
            index_type=index_type,
            is_unique=is_unique,
            is_primary=is_primary,
            comment=getattr(index, "comment", None),
        )

    def _extract_constraint_info(
        self, constraint: Any, table_name: str
    ) -> ConstraintInfo:
        """Extract information from a SQLAlchemy constraint object."""
        if isinstance(constraint, UniqueConstraint):
            columns = [col.name for col in constraint.columns]
            return ConstraintInfo(
                name=(
                    str(constraint.name)
                    if constraint.name
                    else f"uq_{table_name}_{'_'.join(columns)}"
                ),
                table_name=table_name,
                constraint_type=ConstraintType.UNIQUE,
                columns=columns,
                comment=getattr(constraint, "comment", None),
            )
        elif isinstance(constraint, ForeignKeyConstraint):
            # Extract column names and referenced table/columns
            elements = constraint.elements
            columns = [element.parent.name for element in elements]
            referenced_table = elements[0].column.table.name if elements else None
            referenced_columns = [element.column.name for element in elements]

            return ConstraintInfo(
                name=(
                    str(constraint.name)
                    if constraint.name
                    else f"fk_{table_name}_{'_'.join(columns)}"
                ),
                table_name=table_name,
                constraint_type=ConstraintType.FOREIGN_KEY,
                columns=columns,
                referenced_table=referenced_table,
                referenced_columns=referenced_columns,
                comment=getattr(constraint, "comment", None),
            )
        elif isinstance(constraint, CheckConstraint):
            return ConstraintInfo(
                name=(
                    str(constraint.name)
                    if constraint.name
                    else f"chk_{table_name}_constraint"
                ),
                table_name=table_name,
                constraint_type=ConstraintType.CHECK,
                columns=[],
                condition=(
                    str(constraint.sqltext) if hasattr(constraint, "sqltext") else None
                ),
                comment=getattr(constraint, "comment", None),
            )
        else:
            # Fallback for unknown constraint types
            return ConstraintInfo(
                name=str(constraint),
                table_name=table_name,
                constraint_type=ConstraintType.UNIQUE,  # Default
                columns=[],
                comment=getattr(constraint, "comment", None),
            )

    def _determine_index_type(self, index: Index, columns: list[str]) -> IndexType:
        """Determine the appropriate index type based on column characteristics."""
        # Check if any column is a full-text searchable type
        for col in index.columns:
            if hasattr(col.type, "like") or "text" in str(col.type).lower():
                return IndexType.FULLTEXT

        # Default to BTREE for most cases
        return IndexType.BTREE

    def _generate_performance_recommendations(
        self, tables: dict[str, TableInfo]
    ) -> list[str]:
        """Generate performance recommendations based on current schema."""
        recommendations = []

        # Check for tables with high row counts but insufficient indexes
        for table_name, _table_info in tables.items():
            # Foreign key recommendations
            if table_name == "genefams":
                recommendations.append(
                    "Add index on genefams.family_type for filtering by gene family type"
                )
                recommendations.append(
                    "Add index on genefams.functional_category for filtering by functional category"
                )
                recommendations.append(
                    "Add composite index on (is_active, family_type) for active gene family queries"
                )
            elif table_name == "species":
                recommendations.append(
                    "Add index on species.is_model_organism for finding model organisms"
                )
                recommendations.append(
                    "Add composite index on (class_name, order_name) for taxonomic queries"
                )
                recommendations.append(
                    "Add index on species.taxon_id for scientific queries"
                )
            elif table_name == "chromosomes":
                recommendations.append(
                    "Add composite index on (species_id, chromosome_name) for chromosome lookups"
                )
            elif table_name == "genefam_species_enhanced":
                recommendations.append(
                    "Add index on confidence_score for filtering by quality"
                )
                recommendations.append(
                    "Add index on evidence_type for filtering by evidence source"
                )

        # Association table recommendations
        if "genefam_species_association" in tables:
            recommendations.append(
                "Ensure genefam_species_association has proper composite primary key index"
            )

        return recommendations

    def _identify_missing_indexes(
        self, tables: dict[str, TableInfo]
    ) -> list[dict[str, Any]]:
        """Identify indexes that should exist but are missing."""
        missing_indexes = []

        # Common query patterns that need indexes
        common_patterns = [
            {
                "table": "genefams",
                "columns": ["family_type"],
                "reason": "Filtering gene families by type",
                "priority": "high",
            },
            {
                "table": "genefams",
                "columns": ["is_active", "family_type"],
                "reason": "Finding active gene families of specific type",
                "priority": "high",
            },
            {
                "table": "species",
                "columns": ["vgnc_prefix"],
                "reason": "Fast lookup by VGNC prefix",
                "priority": "high",
            },
            {
                "table": "species",
                "columns": ["taxon_id"],
                "reason": "Scientific queries by taxonomy ID",
                "priority": "medium",
            },
            {
                "table": "species",
                "columns": ["is_model_organism"],
                "reason": "Finding model organisms",
                "priority": "high",
            },
            {
                "table": "chromosomes",
                "columns": ["species_id", "chromosome_name"],
                "reason": "Chromosomes lookups by species",
                "priority": "high",
            },
            {
                "table": "assemblies",
                "columns": ["accession_number"],
                "reason": "Assembly lookup by accession",
                "priority": "high",
            },
        ]

        for pattern in common_patterns:
            table_name = str(pattern["table"])  # Ensure string type
            if table_name in tables:
                table_info = tables[table_name]
                # Check if the index pattern already exists
                exists = any(
                    set(pattern["columns"]) == set(idx.columns)
                    for idx in table_info.indexes
                )

                if not exists:
                    missing_indexes.append(
                        {
                            "table": pattern["table"],
                            "columns": pattern["columns"],
                            "reason": pattern["reason"],
                            "priority": pattern["priority"],
                            "index_name": f"idx_{pattern['table']}_{'_'.join(pattern['columns'])}",
                        }
                    )

        return missing_indexes

    def _identify_redundant_indexes(
        self, tables: dict[str, TableInfo]
    ) -> list[dict[str, Any]]:
        """Identify potentially redundant indexes."""
        redundant_indexes = []

        for table_name, table_info in tables.items():
            existing_indexes = table_info.indexes

            # Check for indexes that are superseded by others
            for i, idx1 in enumerate(existing_indexes):
                for j, idx2 in enumerate(existing_indexes):
                    if i != j:
                        # Check if idx2 covers idx1
                        if set(idx1.columns).issubset(set(idx2.columns)):
                            if not idx1.is_primary and not idx1.is_unique:
                                redundant_indexes.append(
                                    {
                                        "table": table_name,
                                        "index_name": idx1.name,
                                        "superseded_by": idx2.name,
                                        "columns": idx1.columns,
                                        "superseding_columns": idx2.columns,
                                        "reason": f"Index {idx1.name} is covered by {idx2.name}",
                                    }
                                )

        return redundant_indexes

    def _identify_fulltext_opportunities(
        self, tables: dict[str, TableInfo]
    ) -> list[dict[str, Any]]:
        """Identify opportunities for full-text search indexes."""
        fulltext_opportunities = []

        # Look for text columns that could benefit from full-text indexing
        text_columns = [
            {
                "table": "genefams",
                "column": "name",
                "reason": "Gene family name search",
            },
            {
                "table": "genefams",
                "column": "description",
                "reason": "Gene family description search",
            },
            {
                "table": "species",
                "column": "scientific_name",
                "reason": "Species scientific name search",
            },
            {
                "table": "species",
                "column": "common_name",
                "reason": "Species common name search",
            },
            {
                "table": "chromosomes",
                "column": "assembly_name",
                "reference": "Assembly name search",
            },
        ]

        for text_col in text_columns:
            if text_col["table"] in tables:
                table_info = tables[text_col["table"]]

                # Check if the column exists and is text type
                column_info = next(
                    (
                        col
                        for col in table_info.columns
                        if col["name"] == text_col["column"]
                    ),
                    None,
                )

                if column_info and "text" in column_info["type"].lower():
                    # Check if full-text index already exists
                    has_fulltext = any(
                        idx.index_type == IndexType.FULLTEXT
                        and text_col["column"] in idx.columns
                        for idx in table_info.indexes
                    )

                    if not has_fulltext:
                        fulltext_opportunities.append(
                            {
                                "table": text_col["table"],
                                "column": text_col["column"],
                                "reason": text_col["reason"],
                                "index_name": f"ft_{text_col['table']}_{text_col['column']}",
                                "priority": "medium",
                            }
                        )

        return fulltext_opportunities

    def print_analysis_report(self, result: SchemaAnalysisResult) -> None:
        """Print a formatted analysis report."""
        print("\n" + "=" * 80)
        print("VGNC ORM SCHEMA ANALYSIS REPORT")
        print("=" * 80)

        print("\nSUMMARY:")
        print(f"  Total Tables: {len(result.tables)}")
        print(f"  Total Indexes: {result.total_indexes}")
        print(f"  Total Constraints: {result.total_constraints}")
        print(
            f"  Performance Recommendations: {len(result.performance_recommendations)}"
        )
        print(f"  Missing Indexes: {len(result.missing_indexes)}")
        print(f"  Redundant Indexes: {len(result.redundant_indexes)}")
        print(f"  Full-text Opportunities: {len(result.fulltext_opportunities)}")

        if result.performance_recommendations:
            print("\nPERFORMANCE RECOMMENDATIONS:")
            for i, rec in enumerate(result.performance_recommendations, 1):
                print(f"  {i}. {rec}")

        if result.missing_indexes:
            print("\nMISSING INDEXES:")
            for missing in result.missing_indexes:
                print(
                    f"  • {missing['index_name']} on {missing['table']}({', '.join(missing['columns'])})"
                )
                print(f"    Reason: {missing['reason']}")
                print(f"    Priority: {missing['priority']}")

        if result.redundant_indexes:
            print("\nPOTENTIALLY REDUNDANT INDEXES:")
            for redundant in result.redundant_indexes:
                print(f"  • {redundant['index_name']} on {redundant['table']}")
                print(f"    Covered by: {redundant['superseded_by']}")
                print(f"    Reason: {redundant['reason']}")

        if result.fulltext_opportunities:
            print("\nFULL-TEXT SEARCH OPPORTUNITIES:")
            for opportunity in result.fulltext_opportunities:
                print(
                    f"  • {opportunity['index_name']} on {opportunity['table']}({opportunity['column']})"
                )
                print(f"    Reason: {opportunity['reason']}")
                print(f"    Priority: {opportunity['priority']}")

        print("\nDETAILED TABLE ANALYSIS:")
        for table_name, table_info in sorted(result.tables.items()):
            print(f"\n  {table_name.upper()}:")
            print(f"    Columns: {len(table_info.columns)}")
            print(f"    Indexes: {len(table_info.indexes)}")
            print(f"    Constraints: {len(table_info.constraints)}")

            if table_info.indexes:
                print("    Indexes:")
                for idx in table_info.indexes:
                    status = ""
                    if idx.is_primary:
                        status = " (PRIMARY KEY)"
                    elif idx.is_unique:
                        status = " (UNIQUE)"
                    print(f"      • {idx.name} on {', '.join(idx.columns)} {status}")
                    print(f"        Type: {idx.index_type.value}")
                    if idx.comment:
                        print(f"        Comment: {idx.comment}")

            if table_info.constraints:
                print("    Constraints:")
                for constraint in table_info.constraints:
                    status = f"({constraint.constraint_type.value.upper()})"
                    print(f"      • {constraint.name} {status}")
                    if constraint.columns:
                        print(f"        Columns: {', '.join(constraint.columns)}")
                    if constraint.referenced_table:
                        print(f"        References: {constraint.referenced_table}")
                        if constraint.referenced_columns:
                            print(
                                f"        Ref Columns: {', '.join(constraint.referenced_columns)}"
                            )
                    if constraint.condition:
                        print(f"        Condition: {constraint.condition}")

        print("\n" + "=" * 80)


def analyze_current_schema() -> SchemaAnalysisResult:
    """Convenience function to analyze the current ORM schema."""
    analyzer = SchemaAnalyzer()
    return analyzer.analyze_current_schema()


def print_schema_analysis_report() -> None:
    """Convenience function to print schema analysis report."""
    result = analyze_current_schema()
    analyzer = SchemaAnalyzer()
    analyzer.print_analysis_report(result)
