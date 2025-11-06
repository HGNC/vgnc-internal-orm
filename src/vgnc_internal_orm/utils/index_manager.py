"""Index and constraint manager for VGNC ORM.

This module provides a comprehensive management system for creating,
validating, and applying indexes and constraints to SQLAlchemy models.
"""

from typing import Dict, List, Any, Optional, Set, Tuple
from dataclasses import dataclass, field
from sqlalchemy import Index, UniqueConstraint, ForeignKeyConstraint, CheckConstraint
from sqlalchemy.schema import CreateTable, CreateIndex

from vgnc_internal_orm.utils.index_definitions import (
    get_all_indexes, get_all_constraints, get_association_indexes,
    get_performance_indexes, IndexValidator, PerformanceIndexSets
)
from vgnc_internal_orm.utils.mysql_features import FullTextSearch


@dataclass
class IndexApplicationResult:
    """Result of index application to models."""
    applied_indexes: Dict[str, List[str]] = field(default_factory=dict)
    applied_constraints: Dict[str, List[str]] = field(default_factory=dict)
    validation_results: Dict[str, Any] = field(default_factory=dict)
    performance_impact: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)


class IndexManager:
    """Manages indexes and constraints for VGNC ORM models."""

    def __init__(self):
        self.index_definitions = get_all_indexes()
        self.constraint_definitions = get_all_constraints()
        self.association_indexes = get_association_indexes()
        self.performance_indexes = get_performance_indexes()
        self.fulltext_indexes = self._generate_fulltext_indexes()

    def apply_indexes_to_models(self, models: Optional[List] = None) -> IndexApplicationResult:
        """Apply all defined indexes and constraints to models."""
        result = IndexApplicationResult()

        # Get all model classes if not provided
        if models is None:
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

            # Validate the index set for this table
            validation = self._validate_table_indexes(table_name)
            result.validation_results[table_name] = validation

            # Apply indexes to the model
            self._apply_indexes_to_model(model, result)

            # Apply constraints to the model
            self._apply_constraints_to_model(model, result)

        # Analyze performance impact
        result.performance_impact = self._analyze_performance_impact(result)

        return result

    def _validate_table_indexes(self, table_name: str) -> Dict[str, Any]:
        """Validate indexes for a specific table."""
        indexes = self.index_definitions.get(table_name, [])
        performance_indexes = self.performance_indexes.get(table_name, [])

        all_indexes = indexes + performance_indexes
        return IndexValidator.validate_index_set(all_indexes, table_name)

    def _apply_indexes_to_model(self, model, result: IndexApplicationResult) -> None:
        """Apply indexes to a specific model."""
        table_name = model.__tablename__

        # Get all index types for this table
        basic_indexes = self.index_definitions.get(table_name, [])
        performance_indexes = self.performance_indexes.get(table_name, [])
        fulltext_indexes = self.fulltext_indexes.get(table_name, [])

        all_indexes = basic_indexes + performance_indexes + fulltext_indexes

        # Apply indexes via __table_args__
        if hasattr(model, '__table_args__'):
            # Add to existing table args
            if isinstance(model.__table_args__, (list, tuple)):
                existing_args = list(model.__table_args__)
            else:
                existing_args = []

            # Add indexes that don't already exist
            existing_index_names = {
                getattr(idx, 'name', '') for idx in existing_args
                if isinstance(idx, Index)
            }

            for idx in all_indexes:
                if idx.name and idx.name not in existing_index_names:
                    existing_args.append(idx)
                    result.applied_indexes.setdefault(table_name, []).append(idx.name)

            # Update model __table_args__
            model.__table_args__ = tuple(existing_args)
        else:
            # Create new table args
            model.__table_args__ = tuple(all_indexes)
            result.applied_indexes[table_name] = [idx.name for idx in all_indexes if idx.name]

    def _apply_constraints_to_model(self, model, result: IndexApplicationResult) -> None:
        """Apply constraints to a specific model."""
        table_name = model.__tablename__

        constraints = self.constraint_definitions.get(table_name, [])

        if constraints:
            if hasattr(model, '__table_args__'):
                # Add to existing table args
                if isinstance(model.__table_args__, (list, tuple)):
                    existing_args = list(model.__table_args__)
                else:
                    existing_args = []

                # Add constraints
                for constraint in constraints:
                    existing_args.append(constraint)
                    result.applied_constraints.setdefault(table_name, []).append(constraint.name)

                # Update model __table_args__
                model.__table_args__ = tuple(existing_args)
            else:
                # Create new table args with constraints
                model.__table_args__ = tuple(constraints)
                result.applied_constraints[table_name] = [c.name for c in constraints]

    def _analyze_performance_impact(self, result: IndexApplicationResult) -> Dict[str, Any]:
        """Analyze the performance impact of applied indexes."""
        impact = {
            "total_indexes_applied": 0,
            "total_constraints_applied": 0,
            "index_coverage": {},
            "recommendations": []
        }

        # Count applied objects
        for table_name, indexes in result.applied_indexes.items():
            impact["total_indexes_applied"] += len(indexes)
            impact["index_coverage"][table_name] = len(indexes)

        for table_name, constraints in result.applied_constraints.items():
            impact["total_constraints_applied"] += len(constraints)

        # Generate recommendations
        impact["recommendations"] = self._generate_performance_recommendations(result)

        return impact

    def _generate_performance_recommendations(self, result: IndexApplicationResult) -> List[str]:
        """Generate performance recommendations based on applied indexes."""
        recommendations = []

        # Check for tables with few indexes
        for table_name, indexes in result.applied_indexes.items():
            if len(indexes) < 3:
                recommendations.append(
                    f"Table '{table_name}' has only {len(indexes)} indexes - "
                    f"consider adding more indexes for better query performance"
                )

        # Check validation results for issues
        for table_name, validation in result.validation_results.items():
            if validation.get("duplicate_indexes"):
                recommendations.append(
                    f"Table '{table_name}' has duplicate indexes - "
                    f"remove duplicates to optimize storage and performance"
                )

            if validation.get("overlapping_indexes"):
                recommendations.append(
                    f"Table '{table_name}' has overlapping indexes - "
                    f"consider consolidating to reduce maintenance overhead"
                )

        # Check for missing full-text indexes on text-heavy tables
        text_tables = ["species", "genefams"]
        for table_name in text_tables:
            if table_name not in result.applied_indexes:
                recommendations.append(
                    f"Consider adding full-text search indexes to table '{table_name}' "
                    f"for better text search performance"
                )

        return recommendations

    def _generate_fulltext_indexes(self) -> Dict[str, List[Index]]:
        """Generate full-text search indexes for text-heavy tables."""
        fulltext_indexes = {}

        # Species full-text indexes
        species_ft = FullTextSearch.create_fulltext_index(
            table_name="species",
            columns=["scientific_name", "common_name"],
            index_name="fti_species_names"
        )
        fulltext_indexes["species"] = [species_ft]

        # Gene families full-text indexes
        genefam_ft = FullTextSearch.create_fulltext_index(
            table_name="genefams",
            columns=["name", "description"],
            index_name="fti_genefam_info"
        )
        fulltext_indexes["genefams"] = [genefam_ft]

        return fulltext_indexes

    def generate_ddl_statements(self, engine=None) -> Dict[str, List[str]]:
        """Generate DDL statements for creating indexes and constraints."""
        ddl_statements = {
            "create_indexes": [],
            "create_constraints": [],
            "drop_indexes": [],
            "drop_constraints": []
        }

        # Generate CREATE INDEX statements
        for table_name, indexes in self.index_definitions.items():
            for index in indexes:
                if hasattr(index, 'compile'):
                    try:
                        # Use SQLAlchemy's DDL compilation
                        create_stmt = CreateIndex(index).compile(engine or None)
                        ddl_statements["create_indexes"].append(str(create_stmt))
                    except Exception as e:
                        ddl_statements["warnings"] = ddl_statements.get("warnings", [])
                        ddl_statements["warnings"].append(
                            f"Could not compile index {index.name}: {str(e)}"
                        )

        # Generate full-text index statements (MySQL-specific)
        for table_name, indexes in self.fulltext_indexes.items():
            for index in indexes:
                ddl_statement = (
                    f"CREATE FULLTEXT INDEX {index.name} "
                    f"ON {table_name} ({', '.join(index.columns)})"
                )
                ddl_statements["create_indexes"].append(ddl_statement)

        # Generate constraint statements
        for table_name, constraints in self.constraint_definitions.items():
            for constraint in constraints:
                if isinstance(constraint, UniqueConstraint):
                    stmt = (
                        f"ALTER TABLE {table_name} "
                        f"ADD CONSTRAINT {constraint.name} "
                        f"UNIQUE ({', '.join(constraint.columns)})"
                    )
                    ddl_statements["create_constraints"].append(stmt)
                elif isinstance(constraint, CheckConstraint):
                    stmt = (
                        f"ALTER TABLE {table_name} "
                        f"ADD CONSTRAINT {constraint.name} "
                        f"CHECK ({constraint.sqltext})"
                    )
                    ddl_statements["create_constraints"].append(stmt)

        return ddl_statements

    def create_missing_index_recommendations(self) -> List[Dict[str, Any]]:
        """Create recommendations for commonly missing performance indexes."""
        recommendations = []

        # Performance-critical indexes that are commonly needed
        critical_missing = [
            {
                "table": "genefam_species_association",
                "columns": ["genefam_id", "species_id"],
                "index_type": "composite",
                "reason": "Association table needs indexes for both foreign keys",
                "priority": "high"
            },
            {
                "table": "gene_orthology_association",
                "columns": ["gene_a_id", "gene_b_id"],
                "index_type": "composite",
                "reason": "Orthology association needs composite index for pair lookups",
                "priority": "high"
            },
            {
                "table": "chromosomes",
                "columns": ["species_id", "is_active"],
                "index_type": "composite",
                "reason": "Filter active chromosomes by species",
                "priority": "medium"
            },
            {
                "table": "genefams",
                "columns": ["is_active", "family_type"],
                "index_type": "composite",
                "reason": "Filter active gene families by type",
                "priority": "medium"
            }
        ]

        return critical_missing

    def optimize_index_set_for_query_pattern(self, query_pattern: str, tables: List[str]) -> List[Dict[str, Any]]:
        """Optimize index set for a specific query pattern."""
        optimizations = []

        # Analyze query pattern and suggest optimal indexes
        if "JOIN" in query_pattern.upper():
            # Join queries - suggest foreign key indexes
            optimizations.append({
                "type": "foreign_key_indexes",
                "description": "Add indexes on foreign key columns for JOIN performance",
                "tables": tables,
                "priority": "high"
            })

        if "ORDER BY" in query_pattern.upper():
            # Sorting queries - suggest sort column indexes
            optimizations.append({
                "type": "sort_indexes",
                "description": "Add indexes on ORDER BY columns",
                "tables": tables,
                "priority": "medium"
            })

        if "WHERE" in query_pattern.upper():
            # Filter queries - suggest filter column indexes
            optimizations.append({
                "type": "filter_indexes",
                "description": "Add indexes on WHERE clause columns",
                "tables": tables,
                "priority": "high"
            })

        return optimizations

    def create_migration_scripts(self) -> Dict[str, str]:
        """Create migration scripts for indexes and constraints."""
        migrations = {
            "create_indexes.sql": "",
            "create_constraints.sql": "",
            "drop_indexes.sql": "",
            "drop_constraints.sql": "",
            "performance_analysis.sql": ""
        }

        # Create indexes migration
        for table_name, indexes in self.index_definitions.items():
            for index in indexes:
                if hasattr(index, 'compile'):
                    migrations["create_indexes.sql"] += f"-- Index: {index.name}\n"
                    migrations["create_indexes.sql"] += f"CREATE INDEX {index.name} ON {table_name} ({', '.join(index.columns)});\n\n"

        # Create constraints migration
        for table_name, constraints in self.constraint_definitions.items():
            for constraint in constraints:
                if isinstance(constraint, UniqueConstraint):
                    migrations["create_constraints.sql"] += f"-- Unique Constraint: {constraint.name}\n"
                    migrations["create_constraints.sql"] += f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint.name} UNIQUE ({', '.join(constraint.columns)});\n\n"
                elif isinstance(constraint, CheckConstraint):
                    migrations["create_constraints.sql"] += f"-- Check Constraint: {constraint.name}\n"
                    migrations["create_constraints.sql"] += f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint.name} CHECK ({constraint.sqltext});\n\n"

        # Create performance analysis script
        migrations["performance_analysis.sql"] = """
-- Performance analysis queries
SELECT
    schemaname,
    tablename,
    indexname,
    indexdef
FROM pg_indexes
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY tablename, indexname;

-- Table sizes
SELECT
    schemaname,
    tablename,
    pg_size_pretty(pg_total_relation_size(schemaname||'.'||tablename)) AS size
FROM pg_tables
WHERE schemaname NOT IN ('pg_catalog', 'information_schema')
ORDER BY pg_total_relation_size(schemaname||'.'||tablename) DESC;
"""

        return migrations

    def validate_index_consistency(self, engine) -> Dict[str, Any]:
        """Validate that applied indexes match the database state."""
        validation = {
            "database_indexes": {},
            "model_indexes": {},
            "missing_from_database": [],
            "extra_in_database": [],
            "inconsistent": []
        }

        # This would connect to the actual database and compare
        # For now, provide a placeholder implementation
        try:
            with engine.connect() as conn:
                # Get database indexes (PostgreSQL example)
                result = conn.execute("""
                    SELECT schemaname, tablename, indexname, indexdef
                    FROM pg_indexes
                    WHERE schemaname = 'public'
                """).fetchall()

                for row in result:
                    table_name = row.tablename
                    index_name = row.indexname
                    if table_name not in validation["database_indexes"]:
                        validation["database_indexes"][table_name] = []
                    validation["database_indexes"][table_name].append(index_name)

        except Exception as e:
            validation["error"] = str(e)

        # Compare with model definitions
        for table_name in self.index_definitions.keys():
            model_index_names = [idx.name for idx in self.index_definitions[table_name] if idx.name]
            validation["model_indexes"][table_name] = model_index_names

        return validation