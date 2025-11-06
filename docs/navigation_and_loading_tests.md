# Navigation and Loading Tests Documentation

This document provides comprehensive documentation for the integration tests covering relationship navigation and loading strategies in the VGNC ORM system.

## Overview

The VGNC ORM system includes comprehensive integration tests that validate complex navigation patterns through multiple relationship levels, bidirectional navigation consistency, and various loading strategies. These tests ensure that the ORM relationships work correctly and efficiently across all model types.

## Test Suite Structure

### 1. Test Files

| Test File | Focus | Coverage |
|-----------|-------|----------|
| `test_comprehensive_navigation.py` | Complex navigation patterns | Multi-level navigation, bidirectional consistency |
| `test_loading_strategies.py` | Loading strategy validation | Lazy, selectin, joined loading patterns |
| `test_query_performance_simple.py` | Query performance optimization | N+1 prevention, loading efficiency |
| `test_many_to_many_relationships.py` | Many-to-many relationships | Orthology groups, enhanced associations |

### 2. Test Categories

#### TestBasicNavigationPatterns

**Purpose**: Test basic navigation through single relationships.

**Test Cases**:

- `test_species_to_chromosomes_navigation` - Species → Chromosomes
- `test_chromosome_to_species_navigation` - Chromosome → Species
- `test_species_to_assemblies_navigation` - Species → Assemblies
- `test_bidirectional_navigation` - Bidirectional relationship consistency
- `test_filtered_navigation` - Navigation with query filtering

**Key Validations**:

- ✅ Relationships load correctly with appropriate loading strategies
- ✅ Navigation works in both directions
- ✅ Filtering and ordering work with loaded relationships
- ✅ Empty relationships are handled gracefully

#### TestComplexMultiLevelNavigation

**Purpose**: Test navigation through multiple relationship levels.

**Test Cases**:

- `test_three_level_navigation_species_chromosomes_assembly` - Species → Chromosomes → Assembly
- `test_four_level_navigation_genefam_enhanced_species_chromosomes` - Genefam → Enhanced → Species → Chromosomes
- `test_orthology_group_complex_navigation` - Group → Members → Genefam → Species
- `test_species_relationships_navigation` - Species → Relationships → Related Species

**Key Validations**:

- ✅ Deep navigation through 3-4 relationship levels
- ✅ Complex loading strategies (selectin + joined combinations)
- ✅ Orthology group navigation with member relationships
- ✅ Species relationship navigation

#### TestLoadingStrategyCombinations

**Purpose**: Test different combinations of loading strategies.

**Test Cases**:

- `test_mixed_selectin_joined_loading` - Mixed selectin and joined loading
- `test_deep_selectin_loading` - Deep selectin through multiple levels
- `test_loading_with_filtering` - Loading strategies with query filtering
- `test_loading_with_ordering` - Loading with result ordering

**Key Validations**:

- ✅ Mixed loading strategies work correctly
- ✅ Deep selectin loading prevents N+1 queries
- ✅ Filtering works with optimized loading
- ✅ Ordering is maintained with loaded relationships

#### TestBidirectionalNavigationValidation

**Purpose**: Test bidirectional navigation consistency.

**Test Cases**:

- `test_species_genefam_bidirectional_consistency` - Species ↔ Genefam consistency
- `test_enhanced_associations_bidirectional_consistency` - Enhanced associations
- `test_orthology_group_bidirectional_consistency` - Orthology group relationships
- `test_species_relationship_bidirectional_consistency` - Species relationships

**Key Validations**:

- ✅ Bidirectional relationships are consistent
- ✅ Enhanced associations link back correctly
- ✅ Orthology group memberships are bidirectional
- ✅ Species relationships navigate correctly in both directions

#### TestNavigationEdgeCases

**Purpose**: Test edge cases and error conditions.

**Test Cases**:

- `test_navigation_with_empty_relationships` - Empty relationship handling
- `test_navigation_with_null_foreign_keys` - Null foreign key handling
- `test_circular_reference_handling` - Circular reference prevention
- `test_large_collection_navigation_performance` - Large collection performance

**Key Validations**:

- ✅ Empty relationships handled gracefully
- ✅ Null foreign keys don't break navigation
- ✅ Circular references don't cause infinite loops
- ✅ Large collections remain performant

## Test Data Structure

### Comprehensive Test Data

The tests use comprehensive test data that includes:

#### Species Data

```python
species_data = [
    {
        "name": "Homo sapiens",
        "vgnc_prefix": "HSA",
        "taxon_id": 9606,
        "class_name": "Mammalia",
        "order_name": "Primates",
        "family_name": "Hominidae",
        "is_model_organism": True
    },
    # ... 4 more species with diverse characteristics
]
```

#### Gene Families

```python
genefam_data = [
    {
        "name": "HOX",
        "description": "Homeobox gene family",
        "family_type": "transcription_factor",
        "functional_category": "development"
    },
    # ... 4 more gene families with different characteristics
]
```

#### Orthology Groups

```python
orthology_groups = [
    {
        "group_id": "ORTHO_HOX_MAMMALS",
        "name": "HOX Gene Family Orthology - Mammals",
        "confidence_score": "0.98",
        "conservation_level": "high"
    },
    # ... 2 more orthology groups
]
```

### Relationship Mapping

The test data creates comprehensive relationships:

1. **Species → Chromosomes**: 5-8 chromosomes per species
2. **Species → Assemblies**: 1 assembly per species
3. **Species ↔ Genefam**: Many-to-many associations
4. **Genefam → Enhanced Associations**: Rich metadata associations
5. **Orthology Groups → Members**: Group memberships across species
6. **Species ↔ Species**: Evolutionary relationships

## Loading Strategy Validation

### 1. Selectin Loading (`selectinload`)

**Use Cases**:

- Collection relationships (one-to-many, many-to-many)
- Preventing N+1 query problems
- Large collections where joined loading would be expensive

**Test Validation**:

```python
species = session.execute(
    select(Species).options(selectinload(Species.genefams))
).scalars().all()

# Accessing genefams doesn't trigger additional queries
for sp in species:
    count = len(sp.genefams)  # No additional queries
```

### 2. Joined Loading (`joinedload`)

**Use Cases**:

- Single object relationships (many-to-one, one-to-one)
- When related objects are always needed
- Small-to-medium sized collections

**Test Validation**:

```python
chromosomes = session.execute(
    select(Chromosome).options(joinedload(Chromosome.species))
).scalars().all()

# Species data is pre-loaded
for chrom in chromosomes:
    name = chrom.species.scientific_name  # No additional query
```

### 3. Mixed Loading Strategies

**Use Cases**:

- Complex navigation patterns
- Different relationship types in the same query
- Performance optimization for specific use cases

**Test Validation**:

```python
species = session.execute(
    select(Species).options(
        selectinload(Species.chromosomes),           # Collection
        joinedload(Species.assemblies),               # Single object
        selectinload(Species.genefams)
        .selectinload(Genefam.enhanced_species_associations)
        .joinedload(GeneFamilySpeciesEnhanced.species) # Single object in collection
    )
).scalars().all()
```

## Navigation Pattern Testing

### 1. Single-Level Navigation

**Pattern**: `Model → RelatedModel`

**Examples**:

- Species → Chromosomes
- Genefam → Species
- OrthologyGroup → Members

**Test Validation**:

```python
# Load species with chromosomes
species = session.execute(
    select(Species).options(selectinload(Species.chromosomes))
).scalar_one()

# Navigate without additional queries
chromosome_count = len(species.chromosomes)
```

### 2. Multi-Level Navigation

**Pattern**: `Model → RelatedModel → RelatedModel2`

**Examples**:

- Species → Chromosomes → Assembly
- Genefam → EnhancedAssociations → Species
- OrthologyGroup → Members → Genefam

**Test Validation**:

```python
# Four-level navigation
genefams = session.execute(
    select(Genefam).options(
        selectinload(Genefam.enhanced_species_associations)
        .selectinload(GeneFamilySpeciesEnhanced.species)
        .selectinload(Species.chromosomes)
    )
).scalars().all()

# Navigate through all levels
for gf in genefams:
    for assoc in gf.enhanced_species_associations:
        species = assoc.species
        for chrom in species.chromosomes:
            # All data is pre-loaded
            assert chrom.chromosome_name is not None
```

### 3. Complex Navigation with Filtering

**Pattern**: Navigation with query constraints

**Examples**:

- Filter model organisms → Load relationships
- Filter by taxonomic class → Navigate hierarchies

**Test Validation**:

```python
model_species = session.execute(
    select(Species).options(
        selectinload(Species.genefams),
        selectinload(Species.chromosomes)
    )
    .where(Species.is_model_organism == True)
    .where(Species.class_name == "Mammalia")
).scalars().all()
```

## Bidirectional Relationship Testing

### 1. Consistency Validation

**Purpose**: Ensure bidirectional relationships are consistent.

**Test Pattern**:

```python
# Load all relationships in both directions
species = session.execute(
    select(Species).options(selectinload(Species.genefams))
).scalars().all()

genefams = session.execute(
    select(Genefam).options(selectinload(Genefam.species))
).scalars().all()

# Build bidirectional maps and validate consistency
species_to_genefams = {sp.id: set(gf.id for gf in sp.genefams) for sp in species}
genefam_to_species = {gf.id: set(sp.id for sp in gf.species) for gf in genefams}

# Validate consistency
for species_id, genefam_ids in species_to_genefams.items():
    for genefam_id in genefam_ids:
        assert species_id in genefam_to_species.get(genefam_id, set())
```

### 2. Back Population Validation

**Purpose**: Ensure `back_populates` relationships work correctly.

**Test Pattern**:

```python
# Load enhanced associations
assoc = session.execute(
    select(GeneFamilySpeciesEnhanced).options(
        joinedload(GeneFamilySpeciesEnhanced.genefam),
        joinedload(GeneFamilySpeciesEnhanced.species)
    )
).scalar_one()

# Verify back navigation
assert assoc in assoc.genefam.enhanced_species_associations
assert assoc in assoc.species.enhanced_genefam_associations
```

## Performance Testing

### 1. N+1 Query Prevention

**Validation**: Ensure optimized loading prevents N+1 queries.

**Test Pattern**:

```python
profiler = QueryProfiler(session)

with profiler.profile_query():
    species = session.execute(
        select(Species).options(selectinload(Species.genefams))
    ).scalars().all()

    # Navigate through relationships
    for sp in species:
        for gf in sp.genefams:
            # This should not trigger additional queries
            pass

stats = profiler.get_stats()
assert stats['query_count'] == 1  # Only the initial query
```

### 2. Loading Strategy Performance

**Validation**: Compare performance of different loading strategies.

**Test Patterns**:

- Lazy loading vs. selectin loading
- Joined loading vs. selectin loading for different collection sizes
- Memory usage comparison

## Error Handling Testing

### 1. Invalid Foreign Keys

**Test**: Navigation with broken foreign key references.

```python
# Create association with invalid foreign keys
invalid_assoc = GeneFamilySpeciesEnhanced(
    genefam_id=999999,  # Non-existent
    species_id=999999   # Non-existent
)

# Valid navigation should still work for valid data
valid_genefams = session.execute(
    select(Genefam).options(
        selectinload(Genefam.enhanced_species_associations)
    )
).scalars().all()
```

### 2. Empty Relationships

**Test**: Navigation when relationships are empty.

```python
# Create species with no relationships
isolated_species = Species(...)
session.add(isolated_species)

# Load and navigate
loaded_species = session.execute(
    select(Species).options(
        selectinload(Species.genefams),
        selectinload(Species.chromosomes)
    )
).scalar_one()

# Empty relationships should be handled gracefully
assert len(loaded_species.genefams) == 0
assert len(loaded_species.chromosomes) == 0
```

## Running the Tests

### Individual Test Classes

```bash
# Run basic navigation tests
python -m pytest tests/integration/test_comprehensive_navigation.py::TestBasicNavigationPatterns -v

# Run complex navigation tests
python -m pytest tests/integration/test_comprehensive_navigation.py::TestComplexMultiLevelNavigation -v

# Run loading strategy tests
python -m pytest tests/integration/test_comprehensive_navigation.py::TestLoadingStrategyCombinations -v

# Run bidirectional validation tests
python -m pytest tests/integration/test_comprehensive_navigation.py::TestBidirectionalNavigationValidation -v
```

### All Navigation Tests

```bash
# Run all comprehensive navigation tests
python -m pytest tests/integration/test_comprehensive_navigation.py -v

# Run all navigation and loading related tests
python -m pytest tests/integration/ -k "navigation or loading" -v
```

### Performance/Efficency Testing

```bash
# Run with query logging to see SQL
python -m pytest tests/integration/test_query_performance_simple.py -v -s

# Run performance-focused tests
python -m pytest tests/integration/test_query_performance.py -v
```

## Test Coverage Summary

### ✅ **Covered Navigation Patterns**

1. **Single-Level Navigation**: All model-to-model relationships
2. **Multi-Level Navigation**: 2-4 level deep navigation patterns
3. **Complex Navigation**: Mixed relationship types and loading strategies
4. **Bidirectional Navigation**: Consistency validation for all relationships
5. **Filtered Navigation**: Navigation with query constraints
6. **Performance Navigation**: Efficient loading strategies

### ✅ **Covered Loading Strategies**

1. **Selectin Loading**: Collection relationships, N+1 prevention
2. **Joined Loading**: Single object relationships, immediate access
3. **Mixed Loading**: Complex navigation patterns
4. **Deep Loading**: Multiple relationship levels
5. **Filtered Loading**: Loading with query constraints

### ✅ **Covered Model Types**

1. **Species**: Chromosomes, assemblies, gene families, relationships
2. **GeneFamily**: Species, enhanced associations, group memberships
3. **Chromosome**: Species navigation
4. **Assembly**: Species navigation
5. **GeneFamilySpeciesEnhanced**: Genefam and species navigation
6. **GeneOrthologyGroup**: Member navigation
7. **GeneFamilyGroupMember**: Genefam, species, and group navigation
8. **SpeciesRelationship**: Species navigation

### ✅ **Covered Edge Cases**

1. **Empty Relationships**: Graceful handling of empty collections
2. **Null Foreign Keys**: Broken reference handling
3. **Circular References**: Infinite loop prevention
4. **Large Collections**: Performance with big datasets
5. **Invalid Data**: Error handling and validation

## Benefits

1. **Comprehensive Coverage**: Tests all relationship types and navigation patterns
2. **Performance Validation**: Ensures N+1 queries are prevented
3. **Bidirectional Consistency**: Validates relationships work in both directions
4. **Real-World Scenarios**: Tests with realistic data structures
5. **Edge Case Handling**: Robust error handling and validation
6. **Performance Monitoring**: Built-in performance testing capabilities

This comprehensive test suite ensures that the VGNC ORM navigation and loading functionality works correctly, efficiently, and reliably across all use cases and relationship patterns.
