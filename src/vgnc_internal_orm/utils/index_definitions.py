"""SQLAlchemy index and constraint definitions for VGNC ORM models.

This module contains pre-defined indexes and constraints that map directly to
SQLAlchemy objects, providing optimal performance for common query patterns.
"""

from typing import Any

from sqlalchemy import CheckConstraint, Index, UniqueConstraint


class IndexDefinitions:
    """Pre-defined SQLAlchemy index definitions for optimal performance."""

    # Species table indexes
    SPECIES_INDEXES = [
        # Primary identification indexes - use actual column names, not hybrid properties
        Index("idx_species_scientific_name", "_scientific_name"),
        Index("idx_species_common_name", "_common_name"),
        Index(
            "idx_species_vgnc_prefix", "genefam_prefix"
        ),  # hybrid maps to genefam_prefix
        Index("idx_species_taxon_id", "taxon_id"),
        Index("idx_species_display_name", "display_name"),
        Index("idx_species_ensembl_name", "ensembl_species_name"),
        # Status and feature indexes
        Index("idx_species_is_live", "is_live"),
        # Composite indexes for common query patterns
        Index("idx_species_taxon_prefix", "taxon_id", "genefam_prefix"),
        Index("idx_species_prefix_live", "genefam_prefix", "is_live"),
        Index("idx_species_display_live", "display_name", "is_live"),
        # Full-text search indexes (defined separately for MySQL)
        # Index("fti_species_names", "_scientific_name", "_common_name", "display_name",
        #        mysql_prefix="FULLTEXT", mysql_with_parser="ngram")
    ]

    # Gene families table indexes
    GENEFAM_INDEXES = [
        # Core identification indexes
        Index("idx_genefams_name", "name"),
        Index("idx_genefams_version", "version"),
        Index("idx_genefams_family_type", "family_type"),
        Index("idx_genefams_functional_category", "functional_category"),
        # Classification indexes
        Index("idx_genefams_taxonomic_scope", "taxonomic_scope"),
        Index("idx_genefams_is_active", "is_active"),
        # External reference indexes
        Index("idx_genefams_external_id_source", "external_id", "external_source"),
        # Statistics indexes
        Index("idx_genefams_gene_count", "gene_count"),
        Index("idx_genefams_species_count", "species_count"),
        # Composite indexes for complex queries
        Index("idx_genefams_type_active", "family_type", "is_active"),
        Index("idx_genefams_category_type", "functional_category", "family_type"),
        # Full-text search indexes
        # Index("fti_genefam_info", "name", "description",
        #        mysql_prefix="FULLTEXT", mysql_with_parser="ngram")
    ]

    # Chromosomes table indexes
    CHROMOSOME_INDEXES = [
        # Core identification indexes
        Index("idx_chromosomes_species_id", "species_id"),
        Index("idx_chromosomes_chromosome_name", "chromosome_name"),
        Index("idx_chromosomes_chromosome_type", "chromosome_type"),
        # Assembly reference indexes
        Index("idx_chromosomes_assembly_name", "assembly_name"),
        # Status and completeness indexes
        Index("idx_chromosomes_is_active", "is_active"),
        Index("idx_chromosomes_is_complete", "is_complete"),
        # External reference indexes
        Index("idx_chromosomes_refseq_accession", "refseq_accession"),
        Index("idx_chromosomes_genbank_accession", "genbank_accession"),
        Index("idx_chromosomes_ensembl_id", "ensembl_id"),
        # Physical properties indexes
        Index("idx_chromosomes_length", "length"),
        # Composite indexes for common patterns
        Index("idx_chromosomes_species_chromosome", "species_id", "chromosome_name"),
        Index(
            "idx_chromosomes_assembly_chromosome", "assembly_name", "chromosome_name"
        ),
        Index("idx_chromosomes_species_type", "species_id", "chromosome_type"),
        Index("idx_chromosomes_active_type", "is_active", "chromosome_type"),
    ]

    # Assembly table indexes
    ASSEMBLY_INDEXES = [
        # Core identification indexes
        Index("idx_assemblies_species_id", "species_id"),
        Index("idx_assemblies_assembly_name", "assembly_name"),
        Index("idx_assemblies_assembly_version", "assembly_version"),
        # Accession number indexes
        Index("idx_assemblies_accession_number", "accession_number"),
        Index("idx_assemblies_refseq_accession", "refseq_accession"),
        Index("idx_assemblies_ensembl_accession", "ensembl_accession"),
        Index("idx_assemblies_ucsc_name", "ucsc_name"),
        # Physical properties indexes
        Index("idx_assemblies_total_length", "total_length"),
        # Status and quality indexes
        Index("idx_assemblies_is_primary", "is_primary"),
        Index("idx_assemblies_is_reference", "is_reference"),
        Index("idx_assemblies_is_active", "is_active"),
        Index("idx_assemblies_assembly_level", "assembly_level"),
        # Metadata indexes
        Index("idx_assemblies_release_date", "release_date"),
        # Composite indexes for common patterns
        Index("idx_assemblies_species_primary", "species_id", "is_primary"),
        Index("idx_assemblies_species_reference", "species_id", "is_reference"),
        Index("idx_assemblies_species_active", "species_id", "is_active"),
        Index("idx_assemblies_primary_reference", "is_primary", "is_reference"),
        # Unique constraint for accession numbers
        Index("idx_assemblies_accession_unique", "accession_number", unique=True),
    ]

    # Enhanced gene family-species associations indexes
    GENEFAM_SPECIES_ENHANCED_INDEXES = [
        # Core relationship indexes
        Index("idx_genefam_species_enhanced_gf_id", "genefam_id"),
        Index("idx_genefam_species_enhanced_sp_id", "species_id"),
        # Quality and evidence indexes
        Index("idx_genefam_species_enhanced_confidence", "confidence_score"),
        Index("idx_genefam_species_enhanced_evidence", "evidence_type"),
        Index("idx_genefam_species_enhanced_primary", "is_primary"),
        # Metadata indexes
        Index("idx_genefam_species_enhanced_date", "date_assigned"),
        # Composite indexes for complex queries
        Index(
            "idx_genefam_species_enhanced_gf_confidence",
            "genefam_id",
            "confidence_score",
        ),
        Index(
            "idx_genefam_species_enhanced_sp_confidence",
            "species_id",
            "confidence_score",
        ),
        Index(
            "idx_genefam_species_enhanced_primary_confidence",
            "is_primary",
            "confidence_score",
        ),
    ]

    # Orthology group indexes
    GENEFAM_ORTHOLOGY_GROUP_INDEXES = [
        # Core identification indexes
        Index("idx_genefam_orthology_group_name", "group_name"),
        Index("idx_genefam_orthology_group_id", "group_id"),
        # Quality indexes
        Index("idx_genefam_orthology_group_confidence", "confidence_score"),
        Index("idx_genefam_orthology_group_conservation", "conservation_level"),
        Index("idx_genefam_orthology_group_scope", "phylogenetic_scope"),
        Index("idx_genefam_orthology_group_active", "is_active"),
        # Metadata indexes
        Index("idx_genefam_orthology_group_date_created", "date_created"),
        # Composite indexes
        Index(
            "idx_genefam_orthology_group_conservation_active",
            "conservation_level",
            "is_active",
        ),
        Index(
            "idx_genefam_orthology_group_scope_confidence",
            "phylogenetic_scope",
            "confidence_score",
        ),
    ]

    # Orthology group members indexes
    GENEFAM_ORTHOLOGY_GROUP_MEMBERS_INDEXES = [
        # Core relationship indexes
        Index("idx_genefam_orthology_members_group", "group_id"),
        Index("idx_genefam_orthology_members_genefam", "genefam_id"),
        Index("idx_genefam_orthology_members_species", "species_id"),
        # Quality indexes
        Index("idx_genefam_orthology_members_confidence", "membership_confidence"),
        Index("idx_genefam_orthology_members_representative", "is_representative"),
        # Metadata indexes
        Index("idx_genefam_orthology_members_date_added", "date_added"),
        # Composite indexes for complex queries
        Index(
            "idx_genefam_orthology_members_group_representative",
            "group_id",
            "is_representative",
        ),
        Index(
            "idx_genefam_orthology_members_genefam_species", "genefam_id", "species_id"
        ),
        Index(
            "idx_genefam_orthology_members_confidence_date",
            "membership_confidence",
            "date_added",
        ),
    ]

    # Species relationships indexes
    SPECIES_RELATIONSHIP_INDEXES = [
        # Core relationship indexes
        Index("idx_species_relationship_species_a", "species_a_id"),
        Index("idx_species_relationship_species_b", "species_b_id"),
        Index("idx_species_relationship_type", "relationship_type"),
        # Quality metrics indexes
        Index("idx_species_relationship_distance", "evolutionary_distance"),
        Index("idx_species_relationship_divergence", "divergence_time_mya"),
        Index("idx_species_relationship_synteny", "synteny_score"),
        Index("idx_species_relationship_similarity", "genome_similarity"),
        # Status indexes
        Index("idx_species_relationship_active", "is_active"),
        # Metadata indexes
        Index("idx_species_relationship_date", "date_established"),
        # Composite indexes for complex queries
        Index("idx_species_relationship_pair", "species_a_id", "species_b_id"),
        Index("idx_species_relationship_type_active", "relationship_type", "is_active"),
        Index(
            "idx_species_relationship_divergence_type",
            "divergence_time_mya",
            "relationship_type",
        ),
        Index(
            "idx_species_relationship_similarity_active",
            "genome_similarity",
            "is_active",
        ),
    ]


class ConstraintDefinitions:
    """Pre-defined SQLAlchemy constraint definitions."""

    # Unique constraints
    SPECIES_UNIQUE_CONSTRAINTS = [
        UniqueConstraint("scientific_name", name="uq_species_scientific_name"),
        UniqueConstraint("vgnc_prefix", name="uq_species_vgnc_prefix"),
    ]

    GENEFAM_UNIQUE_CONSTRAINTS = [
        UniqueConstraint("name", name="uq_genefams_name"),
    ]

    CHROMOSOME_UNIQUE_CONSTRAINTS = [
        UniqueConstraint(
            "species_id", "chromosome_name", name="uq_chromosomes_species_chromosome"
        ),
    ]

    GENEFAM_ORTHOLOGY_GROUP_UNIQUE_CONSTRAINTS = [
        UniqueConstraint("group_id", name="uq_genefam_orthology_group_id"),
    ]

    # Check constraints
    SPECIES_CHECK_CONSTRAINTS = [
        CheckConstraint("taxon_id > 0", name="ck_species_taxon_id_positive"),
        CheckConstraint(
            "vgnc_prefix ~ '^[A-Z]{2,4}$'", name="ck_species_vgnc_prefix_format"
        ),
    ]

    GENEFAM_CHECK_CONSTRAINTS = [
        CheckConstraint("gene_count >= 0", name="ck_genefams_gene_count_non_negative"),
        CheckConstraint(
            "species_count >= 0", name="ck_genefams_species_count_non_negative"
        ),
    ]

    CHROMOSOME_CHECK_CONSTRAINTS = [
        CheckConstraint("length > 0", name="ck_chromosomes_length_positive"),
    ]

    ASSEMBLY_CHECK_CONSTRAINTS = [
        CheckConstraint("total_length > 0", name="ck_assemblies_total_length_positive"),
        CheckConstraint(
            "assembly_version ~ '^[0-9]+\\.[0-9]+$'",
            name="ck_assemblies_version_format",
        ),
    ]

    ORTHOLOGY_CHECK_CONSTRAINTS = [
        CheckConstraint(
            "confidence_score >= 0 AND confidence_score <= 1",
            name="ck_orthology_confidence_score_range",
        ),
        CheckConstraint(
            "membership_confidence >= 0 AND membership_confidence <= 1",
            name="ck_orthology_membership_confidence_range",
        ),
        CheckConstraint(
            "divergence_time_mya >= 0", name="ck_orthology_divergence_time_positive"
        ),
    ]


class AssociationTableIndexes:
    """Indexes for association tables (many-to-many relationships)."""

    # Gene family-species association indexes
    GENEFAM_SPECIES_ASSOCIATION_INDEXES = [
        Index("idx_genefam_species_assoc_gf_id", "genefam_id"),
        Index("idx_genefam_species_assoc_sp_id", "species_id"),
    ]

    # Gene orthology association indexes
    GENE_ORTHOLOGY_ASSOCIATION_INDEXES = [
        Index("idx_gene_orthology_assoc_gene_a", "gene_a_id"),
        Index("idx_gene_orthology_assoc_gene_b", "gene_b_id"),
        Index("idx_gene_orthology_assoc_species_a", "species_a_id"),
        Index("idx_gene_orthology_assoc_species_b", "species_b_id"),
    ]


def get_all_indexes() -> dict[str, list[Index]]:
    """Get all index definitions organized by table name."""
    return {
        "species": IndexDefinitions.SPECIES_INDEXES,
        "genefams": IndexDefinitions.GENEFAM_INDEXES,
        "chromosomes": IndexDefinitions.CHROMOSOME_INDEXES,
        "assembly": IndexDefinitions.ASSEMBLY_INDEXES,
        "genefam_species_enhanced": IndexDefinitions.GENEFAM_SPECIES_ENHANCED_INDEXES,
        "genefam_orthology_group": IndexDefinitions.GENEFAM_ORTHOLOGY_GROUP_INDEXES,
        "genefam_orthology_group_members": IndexDefinitions.GENEFAM_ORTHOLOGY_GROUP_MEMBERS_INDEXES,
        "species_relationship": IndexDefinitions.SPECIES_RELATIONSHIP_INDEXES,
    }


def get_all_constraints() -> dict[str, list[Any]]:
    """Get all constraint definitions organized by table name."""
    return {
        "species": (
            ConstraintDefinitions.SPECIES_UNIQUE_CONSTRAINTS
            + ConstraintDefinitions.SPECIES_CHECK_CONSTRAINTS
        ),
        "genefams": (
            ConstraintDefinitions.GENEFAM_UNIQUE_CONSTRAINTS
            + ConstraintDefinitions.GENEFAM_CHECK_CONSTRAINTS
        ),
        "chromosomes": (
            ConstraintDefinitions.CHROMOSOME_UNIQUE_CONSTRAINTS
            + ConstraintDefinitions.CHROMOSOME_CHECK_CONSTRAINTS
        ),
        "assembly": (ConstraintDefinitions.ASSEMBLY_CHECK_CONSTRAINTS),
        "genefam_orthology_group": (
            ConstraintDefinitions.GENEFAM_ORTHOLOGY_GROUP_UNIQUE_CONSTRAINTS
            + ConstraintDefinitions.ORTHOLOGY_CHECK_CONSTRAINTS
        ),
        "species_relationship": (ConstraintDefinitions.ORTHOLOGY_CHECK_CONSTRAINTS),
    }


def get_association_indexes() -> dict[str, list[Index]]:
    """Get association table indexes."""
    return {
        "genefam_species_association": AssociationTableIndexes.GENEFAM_SPECIES_ASSOCIATION_INDEXES,
        "gene_orthology_association": AssociationTableIndexes.GENE_ORTHOLOGY_ASSOCIATION_INDEXES,
    }


# Performance-optimized index sets for common query patterns
class PerformanceIndexSets:
    """Optimized index sets for specific query patterns."""

    # For gene family browsing and search
    GENEFAM_BROWSING_INDEXES = [
        # Primary filters
        Index("idx_genefam_browse_type", "family_type", "is_active"),
        Index("idx_genefam_browse_category", "functional_category", "is_active"),
        Index("idx_genefam_browse_scope", "taxonomic_scope", "is_active"),
        # Sorting and pagination
        Index("idx_genefam_browse_name_active", "name", "is_active"),
        Index("idx_genefam_browse_species_count", "species_count", "is_active"),
        # Combined filters
        Index(
            "idx_genefam_browse_type_category",
            "family_type",
            "functional_category",
            "is_active",
        ),
    ]

    # For species taxonomy browsing
    SPECIES_TAXONOMY_INDEXES = [
        # Hierarchical classification
        Index("idx_species_tax_class_order", "class_name", "order_name", "family_name"),
        Index("idx_species_order_family", "order_name", "family_name"),
        Index("idx_species_class_model", "class_name", "is_model_organism"),
        # Scientific name searches
        Index("idx_species_name_prefix", "genus", "species"),
        Index("idx_species_taxon_active", "taxon_id", "is_active"),
    ]

    # For orthology analysis
    ORTHOLOGY_ANALYSIS_INDEXES = [
        # Group-based queries
        Index(
            "idx_orthology_group_analysis",
            "group_id",
            "conservation_level",
            "is_active",
        ),
        Index(
            "idx_orthology_member_analysis",
            "group_id",
            "membership_confidence",
            "is_representative",
        ),
        # Species-based queries
        Index(
            "idx_orthology_species_analysis",
            "species_id",
            "group_id",
            "membership_confidence",
        ),
        Index(
            "idx_orthology_relationship_analysis",
            "species_a_id",
            "species_b_id",
            "relationship_type",
            "is_active",
        ),
    ]

    # For genome assembly queries
    ASSEMBLY_QUERY_INDEXES = [
        # Quality-based queries
        Index("idx_assembly_quality", "is_primary", "is_reference", "assembly_level"),
        Index(
            "idx_assembly_species_quality", "species_id", "is_primary", "is_reference"
        ),
        # Size-based queries
        Index("idx_assembly_size_active", "total_length", "is_active"),
        Index("idx_assembly_species_size", "species_id", "total_length", "is_active"),
    ]


def get_performance_indexes() -> dict[str, list[Index]]:
    """Get performance-optimized index sets."""
    return {
        "genefams": PerformanceIndexSets.GENEFAM_BROWSING_INDEXES,
        "species": PerformanceIndexSets.SPECIES_TAXONOMY_INDEXES,
        "genefam_orthology_group": PerformanceIndexSets.ORTHOLOGY_ANALYSIS_INDEXES,
        "genefam_orthology_group_members": PerformanceIndexSets.ORTHOLOGY_ANALYSIS_INDEXES,
        "species_relationship": PerformanceIndexSets.ORTHOLOGY_ANALYSIS_INDEXES,
        "assembly": PerformanceIndexSets.ASSEMBLY_QUERY_INDEXES,
    }


# Index validation utilities
class IndexValidator:
    """Validates index definitions for conflicts and optimizations."""

    @staticmethod
    def validate_index_set(indexes: list[Index], table_name: str) -> dict[str, Any]:
        """Validate a set of indexes for a table."""
        validation_result: dict[str, Any] = {
            "table_name": table_name,
            "total_indexes": len(indexes),
            "duplicate_indexes": [],
            "overlapping_indexes": [],
            "recommendations": [],
        }

        # Check for duplicate index names
        index_names = [idx.name for idx in indexes if idx.name]
        duplicate_names = [name for name in index_names if index_names.count(name) > 1]
        validation_result["duplicate_indexes"] = list(set(duplicate_names))

        # Check for overlapping indexes (same columns)
        column_sets = []
        for idx in indexes:
            columns = tuple(sorted(idx.columns))
            column_sets.append(columns)

        overlapping = [cols for cols in column_sets if column_sets.count(cols) > 1]
        validation_result["overlapping_indexes"] = overlapping

        # Generate recommendations
        if validation_result["duplicate_indexes"]:
            validation_result["recommendations"].append("Remove duplicate index names")

        if validation_result["overlapping_indexes"]:
            validation_result["recommendations"].append(
                "Consider consolidating overlapping indexes"
            )

        return validation_result

    @staticmethod
    def analyze_index_usage_pattern(
        indexes: list[Index], common_queries: list[str]
    ) -> dict[str, Any]:
        """Analyze how well indexes match common query patterns."""
        analysis = {
            "total_indexes": len(indexes),
            "query_coverage": {},
            "missing_indexes": [],
            "underutilized_indexes": [],
        }

        # Extract all indexed columns
        indexed_columns: set[str] = set()
        for idx in indexes:
            # idx.columns is a ReadOnlyColumnCollection, convert to list of strings
            column_names = [str(col) for col in idx.columns]
            indexed_columns.update(column_names)

        # This would require actual query analysis in a real implementation
        # For now, provide a placeholder analysis
        analysis["query_coverage"] = {
            "SELECT * FROM species WHERE scientific_name = ?": (
                "covered" if "scientific_name" in indexed_columns else "missing"
            ),
            "SELECT * FROM genefams WHERE family_type = ?": (
                "covered" if "family_type" in indexed_columns else "missing"
            ),
        }

        return analysis
