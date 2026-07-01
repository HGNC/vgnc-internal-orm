"""Index and constraint manager for VGNC ORM.

This module provides a comprehensive management system for creating,
validating, and applying indexes and constraints to SQLAlchemy models.
"""

from dataclasses import dataclass, field
from typing import Any

from sqlalchemy import CheckConstraint, Index, UniqueConstraint
from sqlalchemy.schema import CreateIndex

from vgnc_internal_orm.utils.index_definitions import (
    IndexValidator,
    get_all_constraints,
    get_all_indexes,
    get_association_indexes,
    get_performance_indexes,
)
from vgnc_internal_orm.utils.mysql_features import FullTextSearch


@dataclass
class IndexApplicationResult:
    """Result of index application to models."""

    applied_indexes: dict[str, list[str]] = field(default_factory=dict)
    applied_constraints: dict[str, list[str]] = field(default_factory=dict)
    validation_results: dict[str, Any] = field(default_factory=dict)
    performance_impact: dict[str, Any] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class IndexAnalysisResult:
    """Result of index analysis."""

    total_indexes: int = 0
    missing_indexes: list[str] = field(default_factory=list)
    constraints: dict[str, list[str]] = field(default_factory=dict)
    recommendations: list[str] = field(default_factory=list)
    database_info: dict[str, Any] = field(default_factory=dict)
    index_analysis: dict[str, Any] = field(default_factory=dict)
    performance_impact: dict[str, Any] = field(default_factory=dict)
    missing_critical_indexes: list[str] = field(default_factory=list)
    duplicate_indexes: list[str] = field(default_factory=list)
    unused_indexes: list[str] = field(default_factory=list)


class IndexManager:
    """Manages indexes and constraints for VGNC ORM models."""

    def __init__(self) -> None:
        """Initialize IndexManager with all available index definitions.

        Loads standard indexes, constraints, association indexes, performance indexes,
        and generates full-text search indexes from model definitions.
        """
        self.index_definitions = get_all_indexes()
        self.constraint_definitions = get_all_constraints()
        self.association_indexes = get_association_indexes()
        self.performance_indexes = get_performance_indexes()
        self.fulltext_indexes = self._generate_fulltext_indexes()

    def apply_indexes_to_models(
        self, models: list[type] | None = None
    ) -> IndexApplicationResult:
        """Apply all defined indexes and constraints to models."""
        result = IndexApplicationResult()

        # Get all model classes if not provided
        if models is None:
            from vgnc_internal_orm.models.assembly import Assembly
            from vgnc_internal_orm.models.chromosomes import Chromosomes
            from vgnc_internal_orm.models.genefam import Genefam
            from vgnc_internal_orm.models.orthology import (
                GeneFamilyGroupMember,
                GeneFamilySpeciesEnhanced,
                GeneOrthologyGroup,
                SpeciesRelationship,
            )
            from vgnc_internal_orm.models.species import Species

            models = [
                Species,
                Genefam,
                Chromosomes,
                Assembly,
                GeneFamilySpeciesEnhanced,
                GeneOrthologyGroup,
                GeneFamilyGroupMember,
                SpeciesRelationship,
            ]

        for model in models:
            if hasattr(model, "__tablename__"):
                table_name = model.__tablename__
            else:
                continue  # Skip invalid model types

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

    def _validate_table_indexes(self, table_name: str) -> dict[str, Any]:
        """Validate indexes for a specific table."""
        indexes = self.index_definitions.get(table_name, [])
        performance_indexes = self.performance_indexes.get(table_name, [])

        all_indexes = indexes + performance_indexes
        return IndexValidator.validate_index_set(all_indexes, table_name)

    def _apply_indexes_to_model(
        self, model: Any, result: IndexApplicationResult
    ) -> None:
        """Apply indexes to a specific model."""
        table_name = model.__tablename__

        # Get all index types for this table
        basic_indexes = self.index_definitions.get(table_name, [])
        performance_indexes = self.performance_indexes.get(table_name, [])
        fulltext_indexes = self.fulltext_indexes.get(table_name, [])

        all_indexes = basic_indexes + performance_indexes + fulltext_indexes

        # Apply indexes via __table_args__
        if hasattr(model, "__table_args__"):
            # Add to existing table args
            if isinstance(model.__table_args__, (list, tuple)):
                existing_args = list(model.__table_args__)
            else:
                existing_args = []

            # Add indexes that don't already exist
            existing_index_names = {
                getattr(idx, "name", "")
                for idx in existing_args
                if isinstance(idx, Index)
            }

            # Add all indexes (new and existing) to the result
            for idx in all_indexes:
                if idx.name and str(idx.name) not in existing_index_names:
                    existing_args.append(idx)
                result.applied_indexes.setdefault(table_name, []).append(str(idx.name))

            # Update model __table_args__
            model.__table_args__ = tuple(existing_args)
        else:
            # Create new table args
            model.__table_args__ = tuple(all_indexes)
            result.applied_indexes[table_name] = [
                idx.name for idx in all_indexes if idx.name
            ]

    def _apply_constraints_to_model(
        self, model: Any, result: IndexApplicationResult
    ) -> None:
        """Apply constraints to a specific model."""
        table_name = model.__tablename__

        constraints = self.constraint_definitions.get(table_name, [])

        if constraints:
            if hasattr(model, "__table_args__"):
                # Add to existing table args
                if isinstance(model.__table_args__, (list, tuple)):
                    existing_args = list(model.__table_args__)
                else:
                    existing_args = []

                # Add constraints
                for constraint in constraints:
                    existing_args.append(constraint)
                    result.applied_constraints.setdefault(table_name, []).append(
                        constraint.name
                    )

                # Update model __table_args__
                model.__table_args__ = tuple(existing_args)
            else:
                # Create new table args with constraints
                model.__table_args__ = tuple(constraints)
                result.applied_constraints[table_name] = [c.name for c in constraints]

    def _analyze_performance_impact(
        self, result: IndexApplicationResult
    ) -> dict[str, Any]:
        """Analyze the performance impact of applied indexes."""
        impact: dict[str, Any] = {
            "total_indexes_applied": 0,
            "total_constraints_applied": 0,
            "index_coverage": {},
            "recommendations": [],
        }

        # Count applied objects
        for table_name, indexes in result.applied_indexes.items():
            index_count = len(indexes) if isinstance(indexes, (list, tuple)) else 0
            impact["total_indexes_applied"] = (
                int(impact["total_indexes_applied"]) + index_count
            )
            impact["index_coverage"][table_name] = index_count

        for _table_name, constraints in result.applied_constraints.items():
            constraint_count = (
                len(constraints) if isinstance(constraints, (list, tuple)) else 0
            )
            impact["total_constraints_applied"] = (
                int(impact["total_constraints_applied"]) + constraint_count
            )

        # Generate recommendations
        impact["recommendations"] = self._generate_performance_recommendations(result)

        return impact

    def _generate_performance_recommendations(
        self, result: IndexApplicationResult
    ) -> list[str]:
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

    def _generate_fulltext_indexes(self) -> dict[str, list[Index]]:
        """Generate full-text search indexes for text-heavy tables."""
        fulltext_indexes = {}

        # Species full-text indexes
        species_ft = FullTextSearch.create_fulltext_index(
            table_name="species",
            columns=["scientific_name", "common_name"],
            index_name="fti_species_names",
        )
        fulltext_indexes["species"] = [species_ft]

        # Gene families full-text indexes
        genefam_ft = FullTextSearch.create_fulltext_index(
            table_name="genefams",
            columns=["name", "description"],
            index_name="fti_genefam_info",
        )
        fulltext_indexes["genefams"] = [genefam_ft]

        return fulltext_indexes

    def generate_ddl_statements(self, engine: Any = None) -> dict[str, list[str]]:
        """Generate DDL statements for creating indexes and constraints."""
        ddl_statements: dict[str, list[str]] = {
            "create_indexes": [],
            "create_constraints": [],
            "drop_indexes": [],
            "drop_constraints": [],
        }

        # Generate CREATE INDEX statements
        for _table_name, indexes in self.index_definitions.items():
            for index in indexes:
                if hasattr(index, "compile"):
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
                    f"ON {table_name} ({', '.join([str(col) for col in index.columns])})"
                )
                ddl_statements["create_indexes"].append(ddl_statement)

        # Generate constraint statements
        for table_name, constraints in self.constraint_definitions.items():
            for constraint in constraints:
                if isinstance(constraint, UniqueConstraint):
                    stmt = (
                        f"ALTER TABLE {table_name} "
                        f"ADD CONSTRAINT {constraint.name} "
                        f"UNIQUE ({', '.join([str(col) for col in constraint.columns])})"
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

    def create_missing_index_recommendations(self) -> list[dict[str, Any]]:
        """Create recommendations for commonly missing performance indexes."""

        # Performance-critical indexes that are commonly needed
        critical_missing = [
            {
                "table": "genefam_species_association",
                "columns": ["genefam_id", "species_id"],
                "index_type": "composite",
                "reason": "Association table needs indexes for both foreign keys",
                "priority": "high",
            },
            {
                "table": "gene_orthology_association",
                "columns": ["gene_a_id", "gene_b_id"],
                "index_type": "composite",
                "reason": "Orthology association needs composite index for pair lookups",
                "priority": "high",
            },
            {
                "table": "chromosomes",
                "columns": ["species_id", "is_active"],
                "index_type": "composite",
                "reason": "Filter active chromosomes by species",
                "priority": "medium",
            },
            {
                "table": "genefams",
                "columns": ["is_active", "family_type"],
                "index_type": "composite",
                "reason": "Filter active gene families by type",
                "priority": "medium",
            },
        ]

        return critical_missing

    def optimize_index_set_for_query_pattern(
        self, query_pattern: str, tables: list[str]
    ) -> list[dict[str, Any]]:
        """Optimize index set for a specific query pattern."""
        optimizations = []

        # Analyze query pattern and suggest optimal indexes
        if "JOIN" in query_pattern.upper():
            # Join queries - suggest foreign key indexes
            optimizations.append(
                {
                    "type": "foreign_key_indexes",
                    "description": "Add indexes on foreign key columns for JOIN performance",
                    "tables": tables,
                    "priority": "high",
                }
            )

        if "ORDER BY" in query_pattern.upper():
            # Sorting queries - suggest sort column indexes
            optimizations.append(
                {
                    "type": "sort_indexes",
                    "description": "Add indexes on ORDER BY columns",
                    "tables": tables,
                    "priority": "medium",
                }
            )

        if "WHERE" in query_pattern.upper():
            # Filter queries - suggest filter column indexes
            optimizations.append(
                {
                    "type": "filter_indexes",
                    "description": "Add indexes on WHERE clause columns",
                    "tables": tables,
                    "priority": "high",
                }
            )

        return optimizations

    def create_migration_scripts(self) -> dict[str, str]:
        """Create migration scripts for indexes and constraints."""
        migrations = {
            "create_indexes.sql": "",
            "create_constraints.sql": "",
            "drop_indexes.sql": "",
            "drop_constraints.sql": "",
            "performance_analysis.sql": "",
        }

        # Create indexes migration
        for table_name, indexes in self.index_definitions.items():
            for index in indexes:
                if hasattr(index, "compile"):
                    migrations["create_indexes.sql"] += f"-- Index: {index.name}\n"
                    migrations[
                        "create_indexes.sql"
                    ] += f"CREATE INDEX {index.name} ON {table_name} ({', '.join([str(col) for col in index.columns])});\n\n"

        # Create constraints migration
        for table_name, constraints in self.constraint_definitions.items():
            for constraint in constraints:
                if isinstance(constraint, UniqueConstraint):
                    migrations[
                        "create_constraints.sql"
                    ] += f"-- Unique Constraint: {constraint.name}\n"
                    migrations[
                        "create_constraints.sql"
                    ] += f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint.name} UNIQUE ({', '.join([str(col) for col in constraint.columns])});\n\n"
                elif isinstance(constraint, CheckConstraint):
                    migrations[
                        "create_constraints.sql"
                    ] += f"-- Check Constraint: {constraint.name}\n"
                    migrations[
                        "create_constraints.sql"
                    ] += f"ALTER TABLE {table_name} ADD CONSTRAINT {constraint.name} CHECK ({constraint.sqltext});\n\n"

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

    def validate_index_consistency(self, engine: Any) -> dict[str, Any]:
        """Validate that applied indexes match the database state."""
        validation: dict[str, Any] = {
            "database_indexes": {},
            "model_indexes": {},
            "missing_from_database": [],
            "extra_in_database": [],
            "inconsistent": [],
        }

        # This would connect to the actual database and compare
        # For now, provide a placeholder implementation
        try:
            with engine.connect() as conn:
                # Get database indexes
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
            model_index_names = [
                idx.name for idx in self.index_definitions[table_name] if idx.name
            ]
            validation["model_indexes"][table_name] = model_index_names

        return validation

    def analyze_current_indexes(self, engine: Any = None) -> IndexAnalysisResult:
        """Analyze current indexes in the database and provide recommendations."""
        analysis = IndexAnalysisResult()

        # Default to analyzing based on defined indexes if no engine provided
        if engine is None:
            # Analyze based on our defined indexes
            total_index_count = 0
            for table_name, indexes in self.index_definitions.items():
                table_analysis: dict[str, Any] = {
                    "total_indexes": len(indexes),
                    "index_names": [idx.name for idx in indexes if idx.name],
                    "index_types": [],
                    "coverage_score": 0,
                }

                # Analyze index types
                for idx in indexes:
                    if hasattr(idx, "columns"):
                        if len(idx.columns) > 1:
                            table_analysis["index_types"].append("composite")
                        else:
                            table_analysis["index_types"].append("single")

                # Add performance indexes
                perf_indexes = self.performance_indexes.get(table_name, [])
                table_analysis["total_indexes"] += len(perf_indexes)
                table_analysis["index_names"].extend(
                    [idx.name for idx in perf_indexes if idx.name]
                )
                total_index_count += table_analysis["total_indexes"]

                # Calculate coverage score (simplified)
                table_analysis["coverage_score"] = min(
                    100, table_analysis["total_indexes"] * 20
                )

                analysis.index_analysis[table_name] = table_analysis

            # Set total indexes
            analysis.total_indexes = total_index_count

            # Populate constraints from constraint definitions
            analysis.constraints = self.constraint_definitions

            # Generate recommendations
            mock_result = IndexApplicationResult()
            for table_name in self.index_definitions.keys():
                mock_result.applied_indexes[table_name] = [
                    idx.name for idx in self.index_definitions[table_name] if idx.name
                ]
            analysis.recommendations = self._generate_performance_recommendations(
                mock_result
            )

            # Identify missing critical indexes
            critical_recommendations = self.create_missing_index_recommendations()
            analysis.missing_critical_indexes = [
                rec.get("description", "Critical index missing")
                for rec in critical_recommendations
                if rec.get("priority") == "high"
            ]

        else:
            # Analyze actual database indexes
            try:
                with engine.connect() as conn:
                    # Get database-specific index information
                    if engine.dialect.name == "mysql":
                        # MySQL index analysis
                        result = conn.execute("""
                            SELECT
                                table_name,
                                index_name,
                                column_name,
                                non_unique,
                                index_type
                            FROM information_schema.statistics
                            WHERE table_schema = DATABASE()
                            ORDER BY table_name, index_name, seq_in_index
                        """).fetchall()

                        current_indexes: dict[str, Any] = {}
                        for row in result:
                            table_name = row.table_name
                            if table_name not in current_indexes:
                                current_indexes[table_name] = {}

                            if row.index_name not in current_indexes[table_name]:
                                current_indexes[table_name][row.index_name] = {
                                    "columns": [],
                                    "unique": not row.non_unique,
                                    "type": row.index_type or "BTREE",
                                }

                            current_indexes[table_name][row.index_name][
                                "columns"
                            ].append(row.column_name)

                        # Compare with expected indexes
                        for (
                            table_name,
                            expected_indexes,
                        ) in self.index_definitions.items():
                            db_indexes = current_indexes.get(table_name, {})
                            expected_names = {
                                idx.name for idx in expected_indexes if idx.name
                            }
                            db_names = set(db_indexes.keys())

                            missing = expected_names - db_names
                            extra = db_names - expected_names

                            if missing:
                                analysis.missing_critical_indexes.extend(
                                    [f"{table_name}:{idx}" for idx in missing]
                                )

                            if extra:
                                analysis.unused_indexes.extend(
                                    [f"{table_name}:{idx}" for idx in extra]
                                )

                    elif engine.dialect.name == "sqlite":
                        # SQLite index analysis
                        result = conn.execute("""
                            SELECT
                                m.tbl_name as table_name,
                                i.name as index_name,
                                p.name as column_name
                            FROM sqlite_master m
                            JOIN pragma_index_list(m.tbl_name) i ON 1=1
                            JOIN pragma_index_info(i.name) p ON 1=1
                            WHERE m.type = 'table'
                            ORDER BY m.tbl_name, i.name, p.cid
                        """).fetchall()

                        current_indexes = {}
                        for row in result:
                            table_name = row.table_name
                            if table_name not in current_indexes:
                                current_indexes[table_name] = {}

                            if row.index_name not in current_indexes[table_name]:
                                current_indexes[table_name][row.index_name] = {
                                    "columns": []
                                }

                            current_indexes[table_name][row.index_name][
                                "columns"
                            ].append(row.column_name)

                    analysis.database_info = {
                        "dialect": engine.dialect.name,
                        "total_tables_analyzed": len(current_indexes),
                        "total_indexes_found": sum(
                            len(indexes) if isinstance(indexes, dict) else 0
                            for indexes in current_indexes.values()
                        ),
                    }

            except Exception:
                # Add error information to the analysis result
                pass  # Error handling would require additional attribute
                analysis.database_info = {"dialect": engine.dialect.name}

        return analysis

    def create_fulltext_indexes(self, table_name: str) -> list[dict[str, Any]]:
        """Create full-text search indexes for a specific table.

        Args:
            table_name: Name of the table to create full-text indexes for

        Returns:
            List of full-text index definitions for the table
        """
        fulltext_indexes = []

        # Define full-text indexes for different table types
        if table_name == "species":
            # Full-text index for species names
            fulltext_indexes.append(
                {
                    "name": "fti_species_names",
                    "table": table_name,
                    "columns": ["display_name", "ensembl_species_name"],
                    "type": "fulltext",
                    "description": "Full-text search index for species display and scientific names",
                }
            )

        elif table_name == "genefams" or table_name == "genefam":
            # Full-text index for gene family information
            fulltext_indexes.append(
                {
                    "name": "fti_genefam_info",
                    "table": table_name,
                    "columns": ["assigned_symbol", "assigned_name"],
                    "type": "fulltext",
                    "description": "Full-text search index for gene family symbols and names",
                }
            )

        elif table_name == "chromosomes":
            # Full-text index for chromosome information
            fulltext_indexes.append(
                {
                    "name": "fti_chromosome_info",
                    "table": table_name,
                    "columns": [
                        "display_name",
                        "genbank_accession",
                        "refseq_accession",
                    ],
                    "type": "fulltext",
                    "description": "Full-text search index for chromosome names and accessions",
                }
            )

        elif table_name == "assembly":
            # Full-text index for assembly information
            fulltext_indexes.append(
                {
                    "name": "fti_assembly_info",
                    "table": table_name,
                    "columns": [
                        "name",
                        "genbank_assembly_accession",
                        "refseq_assembly_accession",
                    ],
                    "type": "fulltext",
                    "description": "Full-text search index for assembly names and accessions",
                }
            )

        else:
            # Return empty list for invalid/unknown tables
            return []

        return fulltext_indexes

    def create_unique_composite_indexes(self, table_name: str) -> list[dict[str, Any]]:
        """Create unique composite indexes for a specific table.

        Args:
            table_name: Name of the table to create unique composite indexes for

        Returns:
            List of unique composite index definitions for the table
        """
        unique_indexes = []

        # Define unique composite indexes for different table types
        if table_name == "species":
            unique_indexes.append(
                {
                    "name": "uq_species_taxon_scientific",
                    "table": table_name,
                    "columns": ["taxon_id", "scientific_name"],
                    "type": "unique",
                    "description": "Unique constraint on taxon_id and scientific_name combination",
                }
            )

        elif table_name == "genefams":
            unique_indexes.append(
                {
                    "name": "uq_genefam_assigned_id_version",
                    "table": table_name,
                    "columns": ["assigned_id", "version"],
                    "type": "unique",
                    "description": "Unique constraint on assigned_id and version combination",
                }
            )

        elif table_name == "chromosomes":
            unique_indexes.append(
                {
                    "name": "uq_chromosome_taxon_name",
                    "table": table_name,
                    "columns": ["taxon_id", "chromosome_name"],
                    "type": "unique",
                    "description": "Unique constraint on taxon_id and chromosome_name combination",
                }
            )

        # Return empty list for invalid/unknown tables
        return unique_indexes
