"""Query optimization utilities for the VGNC ORM system.

This module provides utilities and classes for optimizing database queries,
preventing N+1 problems, and managing efficient loading strategies.
"""

from collections.abc import Callable
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum
from typing import Any, TypeVar

from sqlalchemy import Select, select
from sqlalchemy.orm import (
    Load,
    Session,
    contains_eager,
    joinedload,
    selectinload,
    subqueryload,
)

# Generic type for model classes
T = TypeVar("T")


class LoadingStrategy(Enum):
    """Enumeration of available loading strategies."""

    SELECTIN = "selectin"
    JOINED = "joined"
    SUBQUERY = "subquery"
    CONTAINS_EAGER = "contains_eager"
    RAISE_ONLOAD = "raise_onload"
    LAZY = "lazy"
    NOLOAD = "noload"


@dataclass
class QueryOptimization:
    """Configuration for query optimization."""

    model: type
    loading_strategy: LoadingStrategy
    relationships: list[str]
    conditions: dict[str, Any] | None = None
    order_by: list[str] | None = None
    limit: int | None = None
    offset: int | None = None
    join_conditions: dict[str, str] | None = None


class QueryOptimizer:
    """Central class for optimizing queries and managing loading strategies."""

    def __init__(self, session: Session):
        """Initialize QueryOptimizer with database session.

        Args:
            session: SQLAlchemy Session instance for query execution
        """
        self.session = session
        self._loading_cache: dict[str, Load] = {}

    def get_optimized_query(
        self,
        model: type[T],
        optimizations: list[QueryOptimization],
        filter_conditions: dict[str, Any] | None = None,
    ) -> Select[Any]:
        """Build an optimized query with specified loading strategies."""
        query = select(model)

        # Apply loading strategies
        for opt in optimizations:
            query = self._apply_loading_strategy(query, opt)

        # Apply filter conditions
        if filter_conditions:
            query = self._apply_filters(query, model, filter_conditions)

        return query

    def _apply_loading_strategy(
        self, query: Select[Any], opt: QueryOptimization
    ) -> Select[Any]:
        """Apply a specific loading strategy to the query."""
        if opt.loading_strategy == LoadingStrategy.SELECTIN:
            for rel in opt.relationships:
                query = query.options(selectinload(getattr(opt.model, rel)))

        elif opt.loading_strategy == LoadingStrategy.JOINED:
            for rel in opt.relationships:
                query = query.options(joinedload(getattr(opt.model, rel)))

        elif opt.loading_strategy == LoadingStrategy.SUBQUERY:
            for rel in opt.relationships:
                query = query.options(subqueryload(getattr(opt.model, rel)))

        elif opt.loading_strategy == LoadingStrategy.CONTAINS_EAGER:
            for rel in opt.relationships:
                query = query.options(contains_eager(getattr(opt.model, rel)))

        elif opt.loading_strategy == LoadingStrategy.RAISE_ONLOAD:
            for rel in opt.relationships:
                query = query.options(
                    joinedload(getattr(opt.model, rel)).raiseload("*")
                )

        return query

    def _apply_filters(
        self, query: Select[Any], model: type[T], conditions: dict[str, Any]
    ) -> Select[Any]:
        """Apply filter conditions to the query."""
        for column, value in conditions.items():
            if hasattr(model, column):
                column_attr = getattr(model, column)
                if isinstance(value, (list, tuple)):
                    query = query.where(column_attr.in_(value))
                elif isinstance(value, dict) and "min" in value:
                    query = query.where(column_attr >= value["min"])
                elif isinstance(value, dict) and "max" in value:
                    query = query.where(column_attr <= value["max"])
                else:
                    query = query.where(column_attr == value)
        return query

    def execute_optimized_query(self, query: Select[Any]) -> list[Any]:
        """Execute an optimized query and return results."""
        results = self.session.execute(query).scalars().all()
        return list(results)

    def execute_optimized_single(self, query: Select[Any]) -> Any | None:
        """Execute an optimized query and return a single result."""
        return self.session.execute(query).scalar_one_or_none()


class RelationshipLoader:
    """Utility class for managing relationship loading patterns."""

    @staticmethod
    def get_genefam_optimized_load() -> list[QueryOptimization]:
        """Get optimized loading configuration for gene families."""
        from vgnc_internal_orm.models.genefam import Genefam

        return [
            QueryOptimization(
                model=Genefam,
                loading_strategy=LoadingStrategy.SELECTIN,
                relationships=["species"],  # Only use existing relationships
            )
        ]

    @staticmethod
    def get_species_optimized_load() -> list[QueryOptimization]:
        """Get optimized loading configuration for species."""
        from vgnc_internal_orm.models.species import Species

        return [
            QueryOptimization(
                model=Species,
                loading_strategy=LoadingStrategy.SELECTIN,
                relationships=[
                    "chromosomes",
                    "assemblies",
                    "genefams",
                ],  # Only existing relationships
            )
        ]

    @staticmethod
    def get_orthology_optimized_load() -> list[QueryOptimization]:
        """Get optimized loading configuration for orthology models."""
        from vgnc_internal_orm.models.orthology import (
            GeneFamilyGroupMember,
            GeneOrthologyGroup,
        )

        return [
            QueryOptimization(
                model=GeneOrthologyGroup,
                loading_strategy=LoadingStrategy.JOINED,
                relationships=["group_members"],
            ),
            QueryOptimization(
                model=GeneFamilyGroupMember,
                loading_strategy=LoadingStrategy.JOINED,
                relationships=["genefam", "species", "orthology_group"],
            ),
        ]


class QueryProfiler:
    """Utility class for profiling and analyzing query performance."""

    def __init__(self, session: Session):
        """Initialize QueryProfiler with database session.

        Args:
            session: SQLAlchemy Session instance for query execution
        """
        self.session = session
        self.query_count = 0
        self.query_times: list[float] = []

    @contextmanager
    def profile_query(self) -> Any:
        """Context manager for profiling a single query."""
        import time

        start_time = time.time()
        self.query_count += 1

        try:
            yield
        finally:
            end_time = time.time()
            query_time = end_time - start_time
            self.query_times.append(query_time)

    def get_stats(self) -> dict[str, Any]:
        """Get profiling statistics."""
        return {
            "query_count": self.query_count,
            "total_time": sum(self.query_times),
            "average_time": (
                sum(self.query_times) / len(self.query_times) if self.query_times else 0
            ),
            "max_time": max(self.query_times) if self.query_times else 0,
            "min_time": min(self.query_times) if self.query_times else 0,
        }


class NPlusOneDetector:
    """Utility class for detecting potential N+1 query problems."""

    def __init__(self, session: Session):
        """Initialize NPlusOneDetector with database session.

        Args:
            session: SQLAlchemy Session instance for query execution
        """
        self.session = session
        self.suspicious_patterns: list[dict[str, Any]] = []

    def analyze_query_pattern(
        self, model: type, relationships_to_check: list[str]
    ) -> dict[str, Any]:
        """Analyze a query pattern for potential N+1 issues."""
        # This would analyze the query pattern and suggest optimizations
        suggestions = []

        for rel in relationships_to_check:
            if hasattr(model, rel):
                rel_attr = getattr(model, rel)
                if hasattr(rel_attr, "property") and hasattr(rel_attr.property, "lazy"):
                    # Check if relationship is configured for lazy loading
                    if rel_attr.property.lazy == "select":
                        suggestions.append(
                            {
                                "relationship": rel,
                                "issue": "Potential N+1 problem detected",
                                "suggestion": f"Consider using selectinload() or joinedload() for {rel}",
                                "current_strategy": rel_attr.property.lazy,
                            }
                        )

        return {
            "model": model.__name__,
            "suggestions": suggestions,
            "recommendations": self._generate_recommendations(suggestions),
        }

    def _generate_recommendations(self, suggestions: list[dict[str, Any]]) -> list[str]:
        """Generate optimization recommendations."""
        recommendations = []

        if suggestions:
            recommendations.append(
                "Use explicit loading strategies (selectinload, joinedload)"
            )
            recommendations.append("Consider batching operations when possible")
            recommendations.append(
                "Use contains_eager for already joined relationships"
            )

        return recommendations


# Note: Model imports are intentionally deferred within methods to avoid
# side effects (like table re-definition) during autodoc and module reloads.


class OptimizedQueryBuilder:
    """Builder class for creating optimized queries."""

    def __init__(self, session: Session):
        """Initialize OptimizedQueryBuilder with database session.

        Args:
            session: SQLAlchemy Session instance for query execution
        """
        self.session = session
        self.optimizer = QueryOptimizer(session)
        self.profiler = QueryProfiler(session)

    def build_genefam_query(
        self,
        include_species: bool = True,
        include_enhanced: bool = True,
        include_groups: bool = True,
        filters: dict[str, Any] | None = None,
    ) -> Select[Any]:
        """Build an optimized query for gene families."""
        optimizations = []

        from vgnc_internal_orm.models.genefam import Genefam

        used_relationships = set()

        if include_species:
            optimizations.append(
                QueryOptimization(
                    model=Genefam,
                    loading_strategy=LoadingStrategy.SELECTIN,
                    relationships=["species"],
                )
            )
            used_relationships.add("species")

        if include_enhanced and "species" not in used_relationships:
            # Note: enhanced_species_associations relationship not implemented in Genefam model yet
            # Only add if species relationship hasn't been added already
            pass  # Skip to avoid conflicts

        if include_groups:
            # Note: group_memberships relationship not implemented in Genefam model yet
            # Since we can't add new relationships, this section is effectively a no-op
            pass

        # Remove is_active filter since it's a property that can't be filtered at database level
        # and the status relationship is disabled in the Genefam model
        if filters and "is_active" in filters:
            filters = filters.copy()
            filters.pop("is_active")

        return self.optimizer.get_optimized_query(Genefam, optimizations, filters)

    def build_species_query(
        self,
        include_chromosomes: bool = True,
        include_assemblies: bool = True,
        include_genefams: bool = True,
        include_relationships: bool = False,
        filters: dict[str, Any] | None = None,
    ) -> Select[Any]:
        """Build an optimized query for species."""
        optimizations = []

        from vgnc_internal_orm.models.species import Species

        if include_chromosomes:
            optimizations.append(
                QueryOptimization(
                    model=Species,
                    loading_strategy=LoadingStrategy.SELECTIN,
                    relationships=["chromosomes"],
                )
            )

        if include_assemblies:
            optimizations.append(
                QueryOptimization(
                    model=Species,
                    loading_strategy=LoadingStrategy.JOINED,
                    relationships=["assemblies"],
                )
            )

        if include_genefams:
            optimizations.append(
                QueryOptimization(
                    model=Species,
                    loading_strategy=LoadingStrategy.SELECTIN,
                    relationships=["genefams"],
                )
            )

        if include_relationships:
            # Note: relationship tables not implemented in Species model yet
            # Using existing relationships as fallback
            pass  # Skip to avoid non-existent relationships

        # Remove is_model_organism filter since it's a property that can't be filtered at database level
        if filters and "is_model_organism" in filters:
            filters = filters.copy()
            filters.pop("is_model_organism")

        return self.optimizer.get_optimized_query(Species, optimizations, filters)


class BatchQueryExecutor:
    """Utility class for executing batched queries efficiently."""

    @staticmethod
    def execute_in_batches(
        session: Session,
        query_func: Callable[[Any, Any], list[Any]],
        items: list[Any],
        batch_size: int = 1000,
    ) -> list[Any]:
        """Execute a query function in batches."""
        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i : i + batch_size]
            batch_results = query_func(session, batch)
            results.extend(batch_results)
        return results

    @staticmethod
    def bulk_insert_optimized(session: Session, model_instances: list[Any]) -> None:
        """Perform bulk insert with optimizations."""
        session.bulk_save_objects(model_instances, return_defaults=True)

    @staticmethod
    def bulk_update_optimized(session: Session, model_instances: list[Any]) -> None:
        """Perform bulk update with optimizations."""
        session.bulk_save_objects(model_instances, update_changed_only=True)
