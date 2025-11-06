# Query Performance Optimization Guide

This document provides comprehensive guidance on optimizing database queries and preventing N+1 query problems in the VGNC ORM system.

## Overview

The VGNC ORM system is optimized for performance with built-in strategies to prevent common query performance issues like N+1 problems. This guide covers the implemented optimizations and best practices for efficient querying.

## Loading Strategies

### 1. Selectin Loading (`selectinload`)

**Purpose**: Optimize loading of collections to prevent N+1 queries.

**When to Use**:

- Loading collections (one-to-many, many-to-many relationships)
- When you need to access related objects for multiple parent objects
- Default choice for most collection relationships

**Example**:

```python
# Instead of lazy loading (causes N+1 queries)
species = session.query(Species).all()
for sp in species:
    print(len(sp.genefams))  # This triggers a query for each species

# Use selectin loading (single query)
species = session.execute(
    select(Species).options(selectinload(Species.genefams))
).scalars().all()
for sp in species:
    print(len(sp.genefams))  # No additional queries
```

### 2. Joined Loading (`joinedload`)

**Purpose**: Load related objects using a single JOIN query.

**When to Use**:

- Loading single related objects (many-to-one, one-to-one)
- When the related object is always needed with the parent
- For frequently accessed parent objects

**Example**:

```python
# Load chromosomes with their species in a single query
chromosomes = session.execute(
    select(Chromosome).options(joinedload(Chromosome.species))
).scalars().all()

# Access species data without additional queries
for chrom in chromosomes:
    print(chrom.species.scientific_name)
```

### 3. Subquery Loading (`subqueryload`)

**Purpose**: Load collections using a separate query with a subquery.

**When to Use**:

- Alternative to selectin loading for large collections
- When the parent objects are already loaded
- Legacy code compatibility

**Example**:

```python
species = session.execute(
    select(Species).options(subqueryload(Species.genefams))
).scalars().all()
```

## Current Optimizations

### Species Model Optimizations

```python
# Collection relationships use selectin loading
chromosomes: Mapped[list["Chromosome"]] = relationship(
    "Chromosome",
    back_populates="species",
    cascade="all, delete-orphan",
    lazy="selectin",  # Optimized loading
    order_by="Chromosome.chromosome_name",
    passive_deletes=True
)

assemblies: Mapped[list["Assembly"]] = relationship(
    "Assembly",
    back_populates="species",
    cascade="all, delete-orphan",
    lazy="selectin",  # Optimized loading
    order_by="Assembly.created_at.desc()",
    passive_deletes=True
)

genefams: Mapped[list["Genefam"]] = relationship(
    "Genefam",
    secondary=genefam_species_association,
    back_populates="species",
    lazy="selectin",  # Optimized loading
    passive_deletes=True
)
```

### GeneFamily Model Optimizations

```python
# Collection relationships use selectin loading
species: Mapped[list["Species"]] = relationship(
    "Species",
    secondary=genefam_species_association,
    back_populates="genefams",
    lazy="selectin",  # Optimized loading
    passive_deletes=True
)

enhanced_species_associations: Mapped[list[GeneFamilySpeciesEnhanced]] = relationship(
    "GeneFamilySpeciesEnhanced",
    back_populates="genefam",
    cascade="all, delete-orphan",
    lazy="selectin",  # Optimized loading
    passive_deletes=True
)
```

### Orthology Model Optimizations

```python
# Single relationships use joined loading
genefam: Mapped["Genefam"] = relationship(
    "Genefam",
    back_populates="enhanced_species_associations",
    lazy="joined"  # Optimized loading
)

species: Mapped["Species"] = relationship(
    "Species",
    back_populates="enhanced_genefam_associations",
    lazy="joined"  # Optimized loading
)
```

## Query Optimization Utilities

### QueryOptimizer Class

The `QueryOptimizer` class provides utilities for building optimized queries:

```python
from vgnc_internal_orm.utils.query_optimizer import QueryOptimizer, LoadingStrategy, QueryOptimization

optimizer = QueryOptimizer(session)

# Build optimized query with multiple loading strategies
query = optimizer.get_optimized_query(
    Genefam,
    [
        QueryOptimization(
            model=Genefam,
            loading_strategy=LoadingStrategy.SELECTIN,
            relationships=['species', 'enhanced_species_associations']
        )
    ],
    filters={'is_active': True}
)

genefams = optimizer.execute_optimized_query(query)
```

### OptimizedQueryBuilder

The `OptimizedQueryBuilder` provides pre-configured optimized queries:

```python
from vgnc_internal_orm.utils.query_optimizer import OptimizedQueryBuilder

builder = OptimizedQueryBuilder(session)

# Get optimized gene family query
query = builder.build_genefam_query(
    include_species=True,
    include_enhanced=True,
    include_groups=True,
    filters={'is_active': True}
)

genefams = session.execute(query).scalars().all()
```

### RelationshipLoader

Pre-configured loading strategies for common use cases:

```python
from vgnc_internal_orm.utils.query_optimizer import RelationshipLoader

# Get optimized loading configuration for gene families
optimizations = RelationshipLoader.get_genefam_optimized_load()

# Apply to query
query = select(Genefam).options(
    selectinload(Genefam.species),
    joinedload(Genefam.enhanced_species_associations),
    selectinload(Genefam.group_memberships)
)
```

## Performance Best Practices

### 1. Choose the Right Loading Strategy

```python
# GOOD: Use selectin for collections
species = session.execute(
    select(Species).options(selectinload(Species.genefams))
).scalars().all()

# GOOD: Use joined for single objects
chromosomes = session.execute(
    select(Chromosome).options(joinedload(Chromosome.species))
).scalars().all()

# AVOID: Don't use joined for large collections
# This would cause duplicate parent rows
```

### 2. Be Specific About What You Need

```python
# GOOD: Load only what you need
species = session.execute(
    select(Species).options(
        selectinload(Species.genefams).selectinload(Genefam.enhanced_species_associations)
    )
).scalars().all()

# AVOID: Loading everything unless necessary
```

### 3. Use Filtering to Reduce Result Sets

```python
# GOOD: Filter before loading relationships
genefams = session.execute(
    select(Genefam).options(selectinload(Genefam.species))
    .where(Genefam.is_active == True)
    .where(Genefam.family_type == "protein_coding")
).scalars().all()

# AVOID: Loading everything and filtering in Python
```

### 4. Batch Operations for Large Datasets

```python
from vgnc_internal_orm.utils.query_optimizer import BatchQueryExecutor

# Process large datasets in batches
def process_species_batch(session, species_batch):
    # Process each species
    for species in species_batch:
        # Do work with optimized queries
        pass

# Execute in batches
all_species = session.execute(select(Species)).scalars().all()
BatchQueryExecutor.execute_in_batches(
    session, process_species_batch, all_species, batch_size=1000
)
```

## Performance Monitoring

### QueryProfiler

Use the `QueryProfiler` to monitor query performance:

```python
from vgnc_internal_orm.utils.query_optimizer import QueryProfiler

profiler = QueryProfiler(session)

with profiler.profile_query():
    species = session.execute(
        select(Species).options(selectinload(Species.genefams))
    ).scalars().all()

stats = profiler.get_stats()
print(f"Queries executed: {stats['query_count']}")
print(f"Total time: {stats['total_time']:.4f}s")
```

### N+1 Detection

Use the `NPlusOneDetector` to identify potential N+1 problems:

```python
from vgnc_internal_orm.utils.query_optimizer import NPlusOneDetector

detector = NPlusOneDetector(session)

# Analyze query patterns
analysis = detector.analyze_query_pattern(
    Species,
    ['genefams', 'chromosomes', 'assemblies']
)

for suggestion in analysis['suggestions']:
    print(f"Suggestion: {suggestion['suggestion']}")
```

## Common Performance Patterns

### 1. Load Species with All Related Data

```python
# Load species with chromosomes, assemblies, and gene families
species = session.execute(
    select(Species).options(
        selectinload(Species.chromosomes),
        selectinload(Species.assemblies),
        selectinload(Species.genefams)
    )
    .where(Species.is_model_organism == True)
).scalars().all()
```

### 2. Load Gene Families with Enhanced Associations

```python
# Load gene families with species and enhanced data
genefams = session.execute(
    select(Genefam).options(
        selectinload(Genefam.species),
        joinedload(Genefam.enhanced_species_associations)
    )
    .where(Genefam.family_type == "protein_coding")
).scalars().all()
```

### 3. Load Orthology Groups with Members

```python
# Load orthology groups with all member data
groups = session.execute(
    select(GeneOrthologyGroup).options(
        selectinload(GeneOrthologyGroup.group_members)
        .selectinload(GeneFamilyGroupMember.genefam),
        selectinload(GeneOrthologyGroup.group_members)
        .selectinload(GeneFamilyGroupMember.species)
    )
).scalars().all()
```

## Testing Performance

### Performance Tests

Use the provided performance tests to validate optimizations:

```bash
# Run performance tests
python -m pytest tests/integration/test_query_performance_simple.py -v
```

### Test Coverage

The test suite includes:

- ✅ Selectin loading prevents N+1 queries
- ✅ Joined loading for single relationships
- ✅ Mixed loading strategies
- ✅ Lazy loading behavior validation
- ✅ Query count validation with optimizations

## Migration Guide

### From Lazy Loading to Optimized Loading

```python
# BEFORE (causes N+1 queries)
species = session.query(Species).all()
for sp in species:
    genefams = sp.genefams  # Query per species
    for gf in genefams:
        enhanced = gf.enhanced_species_associations  # Another query per genefam

# AFTER (optimized single queries)
species = session.execute(
    select(Species).options(
        selectinload(Species.genefams)
        .selectinload(Genefam.enhanced_species_associations)
    )
).scalars().all()
# All data loaded with minimal queries
```

## Performance Benefits

### Query Count Reduction

- **Lazy Loading**: 1 + N + N×M queries (parent + children + grandchildren)
- **Selectin Loading**: 1 + N queries (parents + grandchildren)
- **Joined Loading**: 1 query (everything in single JOIN)

### Memory Efficiency

- **Selectin Loading**: Minimal memory overhead, good for large collections
- **Joined Loading**: More memory usage but faster for small-to-medium datasets
- **Mixed Strategy**: Balance between memory and performance

### Network Efficiency

- **Single Query Pattern**: Reduces database round trips
- **Batch Loading**: Processes multiple related objects efficiently
- **Connection Pooling**: Reuses database connections effectively

## Troubleshooting

### Common Issues

1. **"unique() method must be invoked" Error**
   - Cause: Using joinedload on collection relationships
   - Fix: Use selectinload for collections

2. **High Memory Usage**
   - Cause: Loading too much data with joinedload
   - Fix: Use selectinload or add filtering

3. **Still Getting N+1 Queries**
   - Cause: Missing relationship in loading options
   - Fix: Add all needed relationships to options

### Debugging Tips

```python
# Enable query logging to see what's happening
engine = create_engine("sqlite:///:memory:", echo=True)

# Use QueryProfiler to measure performance
profiler = QueryProfiler(session)
with profiler.profile_query():
    # Your query here
    pass
print(profiler.get_stats())

# Use NPlusOneDetector to find issues
detector = NPlusOneDetector(session)
analysis = detector.analyze_query_pattern(YourModel, ['relationship1', 'relationship2'])
```

## Future Enhancements

1. **Automatic Query Optimization**: AI-powered loading strategy selection
2. **Query Caching**: Cache frequently accessed query results
3. **Connection Pooling**: Advanced connection management
4. **Bulk Operations**: Enhanced bulk insert/update/delete operations
5. **Query Analysis**: Advanced query performance analysis and recommendations

This comprehensive query optimization system ensures that the VGNC ORM maintains high performance even with complex many-to-many relationships and large datasets.
