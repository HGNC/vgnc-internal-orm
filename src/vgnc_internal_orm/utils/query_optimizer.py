"""Query optimization utilities for the VGNC ORM system.

This module provides utilities and classes for optimizing database queries,
preventing N+1 problems, and managing efficient loading strategies.
"""

from typing import Any, Dict, List, Optional, Set, Type, TypeVar, Union
from contextlib import contextmanager
from dataclasses import dataclass
from enum import Enum

from sqlalchemy import (
    and_, func, or_, select, text, desc, asc, Join,
    outerjoin, Select
)
from sqlalchemy.orm import (
    Session, joinedload, selectinload, subqueryload,
    contains_eager, Load, aliased, relationship
)
from sqlalchemy.sql import Selectable

# Generic type for model classes
T = TypeVar('T')

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
    model: Type
    loading_strategy: LoadingStrategy
    relationships: List[str]
    conditions: Optional[Dict[str, Any]] = None
    order_by: Optional[List[str]] = None
    limit: Optional[int] = None
    offset: Optional[int] = None
    join_conditions: Optional[Dict[str, str]] = None

class QueryOptimizer:
    """Central class for optimizing queries and managing loading strategies."""

    def __init__(self, session: Session):
        self.session = session
        self._loading_cache: Dict[str, Load] = {}

    def get_optimized_query(
        self,
        model: Type[T],
        optimizations: List[QueryOptimization],
        filter_conditions: Optional[Dict[str, Any]] = None
    ) -> Select:
        """Build an optimized query with specified loading strategies."""
        query = select(model)

        # Apply loading strategies
        for opt in optimizations:
            query = self._apply_loading_strategy(query, opt)

        # Apply filter conditions
        if filter_conditions:
            query = self._apply_filters(query, model, filter_conditions)

        return query

    def _apply_loading_strategy(self, query: Select, opt: QueryOptimization) -> Select:
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
                query = query.options(joinedload(getattr(opt.model, rel)).raiseload('*'))

        return query

    def _apply_filters(self, query: Select, model: Type[T], conditions: Dict[str, Any]) -> Select:
        """Apply filter conditions to the query."""
        for column, value in conditions.items():
            if hasattr(model, column):
                column_attr = getattr(model, column)
                if isinstance(value, (list, tuple)):
                    query = query.where(column_attr.in_(value))
                elif isinstance(value, dict) and 'min' in value:
                    query = query.where(column_attr >= value['min'])
                elif isinstance(value, dict) and 'max' in value:
                    query = query.where(column_attr <= value['max'])
                else:
                    query = query.where(column_attr == value)
        return query

    def execute_optimized_query(self, query: Select) -> List[T]:
        """Execute an optimized query and return results."""
        return self.session.execute(query).scalars().all()

    def execute_optimized_single(self, query: Select) -> Optional[T]:
        """Execute an optimized query and return a single result."""
        return self.session.execute(query).scalar_one_or_none()

class RelationshipLoader:
    """Utility class for managing relationship loading patterns."""

    @staticmethod
    def get_genefam_optimized_load():
        """Get optimized loading configuration for gene families."""
        from vgnc_internal_orm.models.genefam import Genefam
        return [
            QueryOptimization(
                model=Genefam,
                loading_strategy=LoadingStrategy.SELECTIN,
                relationships=['species', 'enhanced_species_associations', 'group_memberships']
            )
        ]

    @staticmethod
    def get_species_optimized_load():
        """Get optimized loading configuration for species."""
        from vgnc_internal_orm.models.species import Species
        return [
            QueryOptimization(
                model=Species,
                loading_strategy=LoadingStrategy.SELECTIN,
                relationships=['chromosomes', 'assemblies', 'genefams', 'enhanced_genefam_associations']
            ),
            QueryOptimization(
                model=Species,
                loading_strategy=LoadingStrategy.JOINED,
                relationships=['relationships_as_species_a', 'relationships_as_species_b']
            )
        ]

    @staticmethod
    def get_orthology_optimized_load():
        """Get optimized loading configuration for orthology models."""
        from vgnc_internal_orm.models.orthology import (
            GeneOrthologyGroup, GeneFamilyGroupMember
        )
        return [
            QueryOptimization(
                model=GeneOrthologyGroup,
                loading_strategy=LoadingStrategy.JOINED,
                relationships=['group_members']
            ),
            QueryOptimization(
                model=GeneFamilyGroupMember,
                loading_strategy=LoadingStrategy.JOINED,
                relationships=['genefam', 'species', 'orthology_group']
            )
        ]

class QueryProfiler:
    """Utility class for profiling and analyzing query performance."""

    def __init__(self, session: Session):
        self.session = session
        self.query_count = 0
        self.query_times: List[float] = []

    @contextmanager
    def profile_query(self):
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

    def get_stats(self) -> Dict[str, Any]:
        """Get profiling statistics."""
        return {
            'query_count': self.query_count,
            'total_time': sum(self.query_times),
            'average_time': sum(self.query_times) / len(self.query_times) if self.query_times else 0,
            'max_time': max(self.query_times) if self.query_times else 0,
            'min_time': min(self.query_times) if self.query_times else 0
        }

class NPlusOneDetector:
    """Utility class for detecting potential N+1 query problems."""

    def __init__(self, session: Session):
        self.session = session
        self.suspicious_patterns: List[Dict[str, Any]] = []

    def analyze_query_pattern(self, model: Type, relationships_to_check: List[str]) -> Dict[str, Any]:
        """Analyze a query pattern for potential N+1 issues."""
        # This would analyze the query pattern and suggest optimizations
        suggestions = []

        for rel in relationships_to_check:
            if hasattr(model, rel):
                rel_attr = getattr(model, rel)
                if hasattr(rel_attr, 'property') and hasattr(rel_attr.property, 'lazy'):
                    # Check if relationship is configured for lazy loading
                    if rel_attr.property.lazy == 'select':
                        suggestions.append({
                            'relationship': rel,
                            'issue': 'Potential N+1 problem detected',
                            'suggestion': f'Consider using selectinload() or joinedload() for {rel}',
                            'current_strategy': rel_attr.property.lazy
                        })

        return {
            'model': model.__name__,
            'suggestions': suggestions,
            'recommendations': self._generate_recommendations(suggestions)
        }

    def _generate_recommendations(self, suggestions: List[Dict[str, Any]]) -> List[str]:
        """Generate optimization recommendations."""
        recommendations = []

        if suggestions:
            recommendations.append("Use explicit loading strategies (selectinload, joinedload)")
            recommendations.append("Consider batching operations when possible")
            recommendations.append("Use contains_eager for already joined relationships")

        return recommendations

# Note: Model imports are intentionally deferred within methods to avoid
# side effects (like table re-definition) during autodoc and module reloads.

class OptimizedQueryBuilder:
    """Builder class for creating optimized queries."""

    def __init__(self, session: Session):
        self.session = session
        self.optimizer = QueryOptimizer(session)
        self.profiler = QueryProfiler(session)

    def build_genefam_query(
        self,
        include_species: bool = True,
        include_enhanced: bool = True,
        include_groups: bool = True,
        filters: Optional[Dict[str, Any]] = None
    ) -> Select:
        """Build an optimized query for gene families."""
        optimizations = []

        from vgnc_internal_orm.models.genefam import Genefam
        if include_species:
            optimizations.append(QueryOptimization(
                model=Genefam,
                loading_strategy=LoadingStrategy.SELECTIN,
                relationships=['species']
            ))

        if include_enhanced:
            optimizations.append(QueryOptimization(
                model=Genefam,
                loading_strategy=LoadingStrategy.JOINED,
                relationships=['enhanced_species_associations']
            ))

        if include_groups:
            optimizations.append(QueryOptimization(
                model=Genefam,
                loading_strategy=LoadingStrategy.SELECTIN,
                relationships=['group_memberships']
            ))

        return self.optimizer.get_optimized_query(Genefam, optimizations, filters)

    def build_species_query(
        self,
        include_chromosomes: bool = True,
        include_assemblies: bool = True,
        include_genefams: bool = True,
        include_relationships: bool = False,
        filters: Optional[Dict[str, Any]] = None
    ) -> Select:
        """Build an optimized query for species."""
        optimizations = []

        from vgnc_internal_orm.models.species import Species
        if include_chromosomes:
            optimizations.append(QueryOptimization(
                model=Species,
                loading_strategy=LoadingStrategy.SELECTIN,
                relationships=['chromosomes']
            ))

        if include_assemblies:
            optimizations.append(QueryOptimization(
                model=Species,
                loading_strategy=LoadingStrategy.JOINED,
                relationships=['assemblies']
            ))

        if include_genefams:
            optimizations.append(QueryOptimization(
                model=Species,
                loading_strategy=LoadingStrategy.SELECTIN,
                relationships=['genefams']
            ))

        if include_relationships:
            optimizations.append(QueryOptimization(
                model=Species,
                loading_strategy=LoadingStrategy.JOINED,
                relationships=['relationships_as_species_a', 'relationships_as_species_b']
            ))

        return self.optimizer.get_optimized_query(Species, optimizations, filters)

class BatchQueryExecutor:
    """Utility class for executing batched queries efficiently."""

    @staticmethod
    def execute_in_batches(
        session: Session,
        query_func: callable,
        items: List[Any],
        batch_size: int = 1000
    ) -> List[Any]:
        """Execute a query function in batches."""
        results = []
        for i in range(0, len(items), batch_size):
            batch = items[i:i + batch_size]
            batch_results = query_func(session, batch)
            results.extend(batch_results)
        return results

    @staticmethod
    def bulk_insert_optimized(session: Session, model_instances: List[Any]) -> None:
        """Perform bulk insert with optimizations."""
        session.bulk_save_objects(model_instances, return_defaults=True)

    @staticmethod
    def bulk_update_optimized(session: Session, model_instances: List[Any]) -> None:
        """Perform bulk update with optimizations."""
        session.bulk_save_objects(model_instances, update_changed_only=True)