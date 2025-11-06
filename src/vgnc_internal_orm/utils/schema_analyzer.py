"""Schema analyzer for VGNC ORM database indexes and constraints.

This module provides utilities to analyze the existing database schema,
catalog indexes and constraints, and generate recommendations for additional
performance-critical indexes and constraints.
"""

from typing import Dict, List, Set, Tuple, Optional, Any
from dataclasses import dataclass, field
from enum import Enum

from sqlalchemy import (
    Index, UniqueConstraint, ForeignKeyConstraint,
    CheckConstraint, text, inspect, MetaData
)
from sqlalchemy.sql import visitors

from typing import TYPE_CHECKING
from vgnc_internal_orm.models.base import BaseModel
if TYPE_CHECKING:
    from vgnc_internal_orm.models.species import Species
    from vgnc_internal_orm.models.genefam import Genefam
    from vgnc_internal_orm.models.chromosomes import Chromosomes
    from vgnc_internal_orm.models.assembly import Assembly
    from vgnc_internal_orm.models.orthology import (
        GeneFamilySpeciesEnhanced, GeneOrthologyGroup,
        GeneFamilyGroupMember, SpeciesRelationship
    )
    from vgnc_internal_orm.models.associations import (
        genefam_species_association, gene_orthology_association
    )


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
    columns: List[str]
    index_type: IndexType
    is_unique: bool = False
    is_primary: bool = False
    filter_condition: Optional[str] = None
    comment: Optional[str] = None


@dataclass
class ConstraintInfo:
    """Information about a database constraint."""
    name: str
    table_name: str
    constraint_type: ConstraintType
    columns: List[str]
    condition: Optional[str] = None
    comment: Optional[str] = None
    referenced_table: Optional[str] = None
    referenced_columns: Optional[List[str]] = None


@dataclass
class TableInfo:
    """Information about a database table."""
    name: str
    columns: List[Dict[str, Any]]
    primary_key_columns: List[str]
    foreign_keys: List[Dict[str, Any]]
    indexes: List[IndexInfo] = field(default_factory=list)
    constraints: List[ConstraintInfo] = field(default_factory=list)
    row_count: Optional[int] = None


@dataclass
class SchemaAnalysisResult:
    """Result of schema analysis."""
    tables: Dict[str, TableInfo]
    total_indexes: int
    total_constraints: int
    performance_recommendations: List[str]
    missing_indexes: List[Dict[str, Any]] = field(default_factory=list)
    redundant_indexes: List[Dict[str, Any]] = field(default_factory=list)
    fulltext_opportunities: List[Dict[str, Any]] = field(default_factory=list)


class SchemaAnalyzer:
    """Analyzes database schema for indexes and constraints."""

    def __init__(self):
        # Lazy import to avoid side effects during module import (e.g., autodoc)
        self.models = []
        self.association_tables = []
        self._load_models()

    def _load_models(self) -> None:
        try:
            from vgnc_internal_orm.models.species import Species as _Species
            from vgnc_internal_orm.models.genefam import Genefam as _Genefam
            from vgnc_internal_orm.models.chromosomes import Chromosomes as _Chromosomes
            from vgnc_internal_orm.models.assembly import Assembly as _Assembly
            from vgnc_internal_orm.models.orthology import (
                GeneFamilySpeciesEnhanced as _GeneFamilySpeciesEnhanced,
                GeneOrthologyGroup as _GeneOrthologyGroup,
                GeneFamilyGroupMember as _GeneFamilyGroupMember,
                SpeciesRelationship as _SpeciesRelationship
            )
            from vgnc_internal_orm.models.associations import (
                genefam_species_association as _genefam_species_association,
                gene_orthology_association as _gene_orthology_association
            )

            self.models = [
                _Species, _Genefam, _Chromosomes, _Assembly,
                _GeneFamilySpeciesEnhanced, _GeneOrthologyGroup,
                _GeneFamilyGroupMember, _SpeciesRelationship
            ]
            self.association_tables = [
                _genefam_species_association,
                _gene_orthology_association
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
            performance_recommendations=[]
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
        result.performance_recommendations = self._generate_performance_recommendations(result.tables)
        result.missing_indexes = self._identify_missing_indexes(result.tables)
        result.redundant_indexes = self._identify_redundant_indexes(result.tables)
        result.fulltext_opportunities = self._identify_fulltext_opportunities(result.tables)

        return result

    def _analyze_model_table(self, model) -> TableInfo:
        """Analyze a SQLAlchemy model table for indexes and constraints."""
        table_name = model.__tablename__

        # Extract column information first
        columns = []
        if hasattr(model, '__table__'):
            columns = self._extract_column_info(model.__table__)

        # Extract primary key and foreign keys
        primary_key_columns = self._extract_primary_key_columns(model)
        foreign_keys = self._extract_foreign_keys(model)

        table_info = TableInfo(
            name=table_name,
            columns=columns,
            primary_key_columns=primary_key_columns,
            foreign_keys=foreign_keys
        )

        # Extract indexes from __table_args__
        if hasattr(model, '__table_args__'):
            for item in model.__table_args__:
                if isinstance(item, Index):
                    table_info.indexes.append(self._extract_index_info(item, table_name))
                elif isinstance(item, (UniqueConstraint, ForeignKeyConstraint, CheckConstraint)):
                    table_info.constraints.append(self._extract_constraint_info(item, table_name))

        return table_info

    def _analyze_association_table(self, association) -> TableInfo:
        """Analyze an association table for indexes and constraints."""
        table_name = association.name
        table_info = TableInfo(name=table_name, columns=[])

        # Extract column information
        table_info.columns = self._extract_column_info(association)

        # Extract primary key (composite primary key for association tables)
        table_info.primary_key_columns = self._extract_primary_key_columns_from_table(association)

        # Look for indexes in the table definition
        if hasattr(association, 'indexes'):
            for index in association.indexes:
                table_info.indexes.append(self._extract_index_info(index, table_name))

        return table_info

    def _extract_column_info(self, table) -> List[Dict[str, Any]]:
        """Extract column information from a SQLAlchemy table."""
        columns = []
        for column in table.columns:
            columns.append({
                'name': column.name,
                'type': str(column.type),
                'nullable': column.nullable,
                'primary_key': column.primary_key,
                'unique': column.unique,
                'foreign_keys': list(column.foreign_keys) if hasattr(column, 'foreign_keys') else [],
                'comment': column.comment
            })
        return columns

    def _extract_primary_key_columns(self, model) -> List[str]:
        """Extract primary key column names from a model."""
        if hasattr(model, '__table__'):
            return [col.name for col in model.__table__.primary_key.columns]
        return []

    def _extract_primary_key_columns_from_table(self, table) -> List[str]:
        """Extract primary key column names from a table object."""
        return [col.name for col in table.primary_key.columns]

    def _extract_index_info(self, index: Index, table_name: str) -> IndexInfo:
        """Extract information from a SQLAlchemy Index object."""
        columns = [col.name for col in index.columns]

        # Determine index type from column types and index properties
        index_type = self._determine_index_type(index, columns)

        # Check if it's a unique index
        is_unique = index.unique or any(
            col.unique for col in index.columns
        )

        # Check if it's a primary key index
        is_primary = index.name == 'pk__' + table_name

        return IndexInfo(
            name=index.name,
            table_name=table_name,
            columns=columns,
            index_type=index_type,
            is_unique=is_unique,
            is_primary=is_primary,
            comment=getattr(index, 'comment', None)
        )

    def _extract_constraint_info(self, constraint, table_name: str) -> ConstraintInfo:
        """Extract information from a SQLAlchemy constraint object."""
        if isinstance(constraint, UniqueConstraint):
            columns = [col.name for col in constraint.columns]
            return ConstraintInfo(
                name=constraint.name or f"uq_{table_name}_{'_'.join(columns)}",
                table_name=table_name,
                constraint_type=ConstraintType.UNIQUE,
                columns=columns,
                comment=getattr(constraint, 'comment', None)
            )
        elif isinstance(constraint, ForeignKeyConstraint):
            # Extract column names and referenced table/columns
            elements = constraint.elements
            columns = [element.parent.name for element in elements]
            referenced_table = elements[0].column.table.name if elements else None
            referenced_columns = [element.column.name for element in elements]

            return ConstraintInfo(
                name=constraint.name or f"fk_{table_name}_{'_'.join(columns)}",
                table_name=table_name,
                constraint_type=ConstraintType.FOREIGN_KEY,
                columns=columns,
                referenced_table=referenced_table,
                referenced_columns=referenced_columns,
                comment=getattr(constraint, 'comment', None)
            )
        elif isinstance(constraint, CheckConstraint):
            return ConstraintInfo(
                name=constraint.name or f"chk_{table_name}_constraint",
                table_name=table_name,
                constraint_type=ConstraintType.CHECK,
                columns=[],
                condition=str(constraint.sqltext) if hasattr(constraint, 'sqltext') else None,
                comment=getattr(constraint, 'comment', None)
            )
        else:
            # Fallback for unknown constraint types
            return ConstraintInfo(
                name=str(constraint),
                table_name=table_name,
                constraint_type=ConstraintType.UNIQUE,  # Default
                columns=[],
                comment=getattr(constraint, 'comment', None)
            )

    def _determine_index_type(self, index: Index, columns: List[str]) -> IndexType:
        """Determine the appropriate index type based on column characteristics."""
        # Check if any column is a full-text searchable type
        for col in index.columns:
            if hasattr(col.type, 'like') or 'text' in str(col.type).lower():
                return IndexType.FULLTEXT

        # Default to BTREE for most cases
        return IndexType.BTREE

    def _generate_performance_recommendations(self, tables: Dict[str, TableInfo]) -> List[str]:
        """Generate performance recommendations based on current schema."""
        recommendations = []

        # Check for tables with high row counts but insufficient indexes
        for table_name, table_info in tables.items():
            # Foreign key recommendations
            if table_name == 'genefams':
                recommendations.append(
                    "Add index on genefams.family_type for filtering by gene family type"
                )
                recommendations.append(
                    "Add index on genefams.functional_category for filtering by functional category"
                )
                recommendations.append(
                    "Add composite index on (is_active, family_type) for active gene family queries"
                )
            elif table_name == 'species':
                recommendations.append(
                    "Add index on species.is_model_organism for finding model organisms"
                )
                recommendations.append(
                    "Add composite index on (class_name, order_name) for taxonomic queries"
                )
                recommendations.append(
                    "Add index on species.taxon_id for scientific queries"
                )
            elif table_name == 'chromosomes':
                recommendations.append(
                    "Add composite index on (species_id, chromosome_name) for chromosome lookups"
                )
            elif table_name == 'genefam_species_enhanced':
                recommendations.append(
                    "Add index on confidence_score for filtering by quality"
                )
                recommendations.append(
                    "Add index on evidence_type for filtering by evidence source"
                )

        # Association table recommendations
        if 'genefam_species_association' in tables:
            recommendations.append(
                "Ensure genefam_species_association has proper composite primary key index"
            )

        return recommendations

    def _identify_missing_indexes(self, tables: Dict[str, TableInfo]) -> List[Dict[str, Any]]:
        """Identify indexes that should exist but are missing."""
        missing_indexes = []

        # Common query patterns that need indexes
        common_patterns = [
            {
                'table': 'genefams',
                'columns': ['family_type'],
                'reason': 'Filtering gene families by type',
                'priority': 'high'
            },
            {
                'table': 'genefams',
                'columns': ['is_active', 'family_type'],
                'reason': 'Finding active gene families of specific type',
                'priority': 'high'
            },
            {
                'table': 'species',
                'columns': ['vgnc_prefix'],
                'reason': 'Fast lookup by VGNC prefix',
                'priority': 'high'
            },
            {
                'table': 'species',
                'columns': ['taxon_id'],
                'reason': 'Scientific queries by taxonomy ID',
                'priority': 'medium'
            },
            {
                'table': 'species',
                'columns': ['is_model_organism'],
                'reason': 'Finding model organisms',
                'priority': 'high'
            },
            {
                'table': 'chromosomes',
                'columns': ['species_id', 'chromosome_name'],
                'reason': 'Chromosomes lookups by species',
                'priority': 'high'
            },
            {
                'table': 'assemblies',
                'columns': ['accession_number'],
                'reason': 'Assembly lookup by accession',
                'priority': 'high'
            }
        ]

        for pattern in common_patterns:
            if pattern['table'] in tables:
                table_info = tables[pattern['table']]
                existing_columns = [idx.columns for idx in table_info.indexes]

                # Check if the index pattern already exists
                exists = any(
                    set(pattern['columns']) == set(idx.columns)
                    for idx in existing_columns
                )

                if not exists:
                    missing_indexes.append({
                        'table': pattern['table'],
                        'columns': pattern['columns'],
                        'reason': pattern['reason'],
                        'priority': pattern['priority'],
                        'index_name': f"idx_{pattern['table']}_{'_'.join(pattern['columns'])}"
                    })

        return missing_indexes

    def _identify_redundant_indexes(self, tables: Dict[str, TableInfo]) -> List[Dict[str, Any]]:
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
                                redundant_indexes.append({
                                    'table': table_name,
                                    'index_name': idx1.name,
                                    'superseded_by': idx2.name,
                                    'columns': idx1.columns,
                                    'superseding_columns': idx2.columns,
                                    'reason': f"Index {idx1.name} is covered by {idx2.name}"
                                })

        return redundant_indexes

    def _identify_fulltext_opportunities(self, tables: Dict[str, TableInfo]) -> List[Dict[str, Any]]:
        """Identify opportunities for full-text search indexes."""
        fulltext_opportunities = []

        # Look for text columns that could benefit from full-text indexing
        text_columns = [
            {'table': 'genefams', 'column': 'name', 'reason': 'Gene family name search'},
            {'table': 'genefams', 'column': 'description', 'reason': 'Gene family description search'},
            {'table': 'species', 'column': 'scientific_name', 'reason': 'Species scientific name search'},
            {'table': 'species', 'column': 'common_name', 'reason': 'Species common name search'},
            {'table': 'chromosomes', 'column': 'assembly_name', 'reference': 'Assembly name search'},
        ]

        for text_col in text_columns:
            if text_col['table'] in tables:
                table_info = tables[text_col['table']]

                # Check if the column exists and is text type
                column_info = next(
                    (col for col in table_info.columns
                     if col['name'] == text_col['column']),
                    None
                )

                if column_info and 'text' in column_info['type'].lower():
                    # Check if full-text index already exists
                    has_fulltext = any(
                        idx.index_type == IndexType.FULLTEXT and
                        text_col['column'] in idx.columns
                        for idx in table_info.indexes
                    )

                    if not has_fulltext:
                        fulltext_opportunities.append({
                            'table': text_col['table'],
                            'column': text_col['column'],
                            'reason': text_col['reason'],
                            'index_name': f"ft_{text_col['table']}_{text_col['column']}",
                            'priority': 'medium'
                        })

        return fulltext_opportunities

    def print_analysis_report(self, result: SchemaAnalysisResult):
        """Print a formatted analysis report."""
        print("\n" + "="*80)
        print("VGNC ORM SCHEMA ANALYSIS REPORT")
        print("="*80)

        print(f"\nSUMMARY:")
        print(f"  Total Tables: {len(result.tables)}")
        print(f"  Total Indexes: {result.total_indexes}")
        print(f"  Total Constraints: {result.total_constraints}")
        print(f"  Performance Recommendations: {len(result.performance_recommendations)}")
        print(f"  Missing Indexes: {len(result.missing_indexes)}")
        print(f"  Redundant Indexes: {len(result.redundant_indexes)}")
        print(f"  Full-text Opportunities: {len(result.fulltext_opportunities)}")

        if result.performance_recommendations:
            print(f"\nPERFORMANCE RECOMMENDATIONS:")
            for i, rec in enumerate(result.performance_recommendations, 1):
                print(f"  {i}. {rec}")

        if result.missing_indexes:
            print(f"\nMISSING INDEXES:")
            for missing in result.missing_indexes:
                print(f"  • {missing['index_name']} on {missing['table']}({', '.join(missing['columns'])})")
                print(f"    Reason: {missing['reason']}")
                print(f"    Priority: {missing['priority']}")

        if result.redundant_indexes:
            print(f"\nPOTENTIALLY REDUNDANT INDEXES:")
            for redundant in result.redundant_indexes:
                print(f"  • {redundant['index_name']} on {redundant['table']}")
                print(f"    Covered by: {redundant['superseded_by']}")
                print(f"    Reason: {redundant['reason']}")

        if result.fulltext_opportunities:
            print(f"\nFULL-TEXT SEARCH OPPORTUNITIES:")
            for opportunity in result.fulltext_opportunities:
                print(f"  • {opportunity['index_name']} on {opportunity['table']}({opportunity['column']})")
                print(f"    Reason: {opportunity['reason']}")
                print(f"    Priority: {opportunity['priority']}")

        print(f"\nDETAILED TABLE ANALYSIS:")
        for table_name, table_info in sorted(result.tables.items()):
            print(f"\n  {table_name.upper()}:")
            print(f"    Columns: {len(table_info.columns)}")
            print(f"    Indexes: {len(table_info.indexes)}")
            print(f"    Constraints: {len(table_info.constraints)}")

            if table_info.indexes:
                print(f"    Indexes:")
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
                print(f"    Constraints:")
                for constraint in table_info.constraints:
                    status = f"({constraint.constraint_type.value.upper()})"
                    print(f"      • {constraint.name} {status}")
                    if constraint.columns:
                        print(f"        Columns: {', '.join(constraint.columns)}")
                    if constraint.referenced_table:
                        print(f"        References: {constraint.referenced_table}")
                        if constraint.referenced_columns:
                            print(f"        Ref Columns: {', '.join(constraint.referenced_columns)}")
                    if constraint.condition:
                        print(f"        Condition: {constraint.condition}")

        print("\n" + "="*80)


def analyze_current_schema() -> SchemaAnalysisResult:
    """Convenience function to analyze the current ORM schema."""
    analyzer = SchemaAnalyzer()
    return analyzer.analyze_current_schema()


def print_schema_analysis_report():
    """Convenience function to print schema analysis report."""
    result = analyze_current_schema()
    analyzer = SchemaAnalyzer()
    analyzer.print_analysis_report(result)