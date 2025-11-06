# Loading Strategy Analysis and Optimization

This document analyzes the current relationship loading strategies and provides recommendations for optimization.

## Current Loading Strategy Configuration

### Species Model

**Current Configuration:**

```python
chromosomes: Mapped[list["Chromosome"]] = relationship(
    "Chromosome",
    back_populates="species",
    cascade="all, delete-orphan",
    lazy="selectin",  # ✅ OPTIMIZED
    order_by="Chromosome.chromosome_name",
    passive_deletes=True
)

assemblies: Mapped[list["Assembly"]] = relationship(
    "Assembly",
    back_populates="species",
    cascade="all, delete-orphan",
    lazy="selectin",  # ✅ OPTIMIZED
    order_by="Assembly.created_at.desc()",  # Most recent first
    passive_deletes=True
)

genefams: Mapped[list["Genefam"]] = relationship(
    "Genefam",
    secondary=genefam_species_association,
    back_populates="species",
    lazy="selectin",  # ✅ OPTIMIZED
    passive_deletes=True
)
```

### Chromosome Model

**Current Configuration:**

```python
species: Mapped["Species"] = relationship(
    "Species",
    back_populates="chromosomes",
    lazy="joined",  # ✅ OPTIMIZED for frequently accessed parent
    innerjoin=True
)

assembly: Mapped[Optional["Assembly"]] = relationship(
    "Assembly",
    back_populates="chromosomes",
    lazy="joined",  # ✅ OPTIMIZED for frequently accessed parent
    innerjoin=True
)
```

### Genefam Model

**Current Configuration:**

```python
species: Mapped[list["Species"]] = relationship(
    "Species",
    secondary=genefam_species_association,
    back_populates="genefams",
    lazy="selectin",  # ✅ OPTIMIZED
    passive_deletes=True  # Better performance for cascade deletes
)
```

### Assembly Model

**Current Configuration:**

```python
species: Mapped["Species"] = relationship(
    "Species",
    back_populates="assemblies",
    lazy="joined",  # ✅ OPTIMIZED for frequently accessed parent
    innerjoin=True
)

chromosomes: Mapped[list["Chromosome"]] = relationship(
    "Chromosome",
    back_populates="assembly",
    lazy="selectin",  # ✅ OPTIMIZED
    order_by="Chromosome.chromosome_name",
    passive_deletes=True
)
```

## Loading Strategy Analysis

### 1. Species → Chromosomes (One-to-Many)

- **Current Strategy:** `lazy="selectin"`
- **Analysis:** ✅ **OPTIMAL**
- **Reasoning:**

  - Selectin loading is efficient for to-many relationships
  - Chromosomes are typically accessed together when working with a species
  - Prevents N+1 queries when loading multiple species
  - Includes ordering for predictable results

### 2. Species → Assemblies (One-to-Many)

- **Current Strategy:** `lazy="selectin"`
- **Analysis:** ✅ **OPTIMAL**
- **Reasoning:**
  - Selectin loading handles to-many relationships efficiently
  - Assemblies are frequently accessed together with species
  - Ordered by creation date (newest first) which is useful
  - Prevents N+1 queries when loading multiple species

### 3. Species → Genefams (Many-to-Many)

- **Current Strategy:** `lazy="selectin"`
- **Analysis:** ✅ **OPTIMAL**
- **Reasoning:**

  - Selectin loading is ideal for many-to-many relationships
  - Gene families are commonly analyzed together for a species
  - Efficiently handles the association table loading
  - Passive deletes provide good performance for cascade operations

### 4. Chromosome → Species (Many-to-One)

- **Current Strategy:** `lazy="joined"`
- **Analysis:** ✅ **OPTIMAL**
- **Reasoning:**

  - Joined loading is perfect for to-one relationships
  - Species information is almost always needed when working with chromosomes
  - Inner join optimization works well since species is always present
  - Eliminates additional queries completely

### 5. Chromosome → Assembly (Many-to-One)

- **Current Strategy:** `lazy="joined"`
- **Analysis:** ✅ **OPTIMAL**
- **Reasoning:**

  - Joined loading efficiently handles the to-one relationship
  - Assembly context is important for chromosome analysis
  - Inner join optimization provides good performance

### 6. Assembly → Species (Many-to-One)

- **Current Strategy:** `lazy="joined"`
- **Analysis:** ✅ **OPTIMAL**
- **Reasoning:**

  - Species context is essential for assembly information
  - Joined loading provides immediate access without additional queries
  - Inner join is appropriate since assemblies always have a species

### 7. Assembly → Chromosomes (One-to-Many)

- **Current Strategy:** `lazy="selectin"`
- **Analysis:** ✅ **OPTIMAL**
- **Reasoning:**
  - Selectin loading handles to-many relationships efficiently
  - Chromosomes are commonly accessed when working with assemblies
  - Includes ordering for predictable chromosome access

### 8. Genefam → Species (Many-to-Many)

- **Current Strategy:** `lazy="selectin"`
- **Analysis:** ✅ **OPTIMAL**
- **Reasoning:**

  - Selectin loading is efficient for many-to-many relationships
  - Species context is frequently needed for gene family analysis
  - Handles the association table efficiently

## Performance Test Results

Based on the loading strategy tests, the following performance characteristics were observed:

### Query Count Analysis

#### Lazy Loading (N+1 Problem)

- Query 1: Load all species
- Query 2-N: Load chromosomes for each species individually
- **Total:** 1 + N queries (inefficient for multiple records)

#### Selectin Loading (Optimized)

- Query 1: Load all species
- Query 2: Load all chromosomes for those species
- **Total:** 2 queries (constant regardless of N)

#### Joined Loading (Optimized for To-One)

- Query 1: Load chromosomes with species in a single join
- **Total:** 1 query (most efficient)

### Memory Usage

- **Selectin Loading:** Moderate memory usage, loads related objects efficiently
- **Joined Loading:** Higher memory usage per query but fewer total queries
- **Lazy Loading:** Lowest initial memory usage but can lead to many small queries

## Usage Pattern Recommendations

### When to Override Default Loading Strategies

**Use `joinedload()` for:**

- Single record lookups where parent information is needed
- API responses requiring complete object graphs
- Reports that need all related data immediately

**Use `selectinload()` for:**

- List views where you need related collections
- Batch processing of multiple records
- Analysis requiring collection data for multiple entities

**Use `lazy loading` for:**

- Rarely accessed relationships
- Optional data that might not be needed
- Memory-critical applications

### Example Query Patterns

```python
# Pattern 1: Single species with all related data
species = session.query(Species).options(
    selectinload(Species.chromosomes),
    selectinload(Species.assemblies),
    selectinload(Species.genefams)
).filter(Species.vgnc_prefix == "HSA").first()

# Pattern 2: Multiple chromosomes with species (default is optimal)
chromosomes = session.query(Chromosome).filter(
    Chromosome.is_complete == True
).all()  # Species will be joined automatically

# Pattern 3: Gene family analysis across species
genefams = session.query(Genefam).options(
    selectinload(Genefam.species)
).filter(Genefam.family_type == "protein_coding").all()
```

## Monitoring and Optimization

### Query Performance Monitoring

#### Enable Query Logging

```python
engine = create_engine(database_url, echo=True)
```

#### Key Metrics to Monitor

1. Query count per operation
2. Query execution time
3. Memory usage patterns
4. N+1 query detection

### Performance Testing

The loading strategy tests should be run regularly to:

1. Verify relationship configurations remain optimal
2. Detect N+1 query regressions
3. Validate that ordering works correctly
4. Ensure cascade operations perform well

## Conclusion

The current loading strategy configuration is **well-optimized** for the expected usage patterns of the VGNC ORM system:

1. **To-one relationships** use `joined` loading for immediate access
2. **To-many relationships** use `selectin` loading to prevent N+1 queries
3. **Many-to-many relationships** use `selectin` loading for efficient association handling
4. **Proper ordering** is configured where it matters most
5. **Cascade operations** are optimized with passive deletes

The configuration follows SQLAlchemy best practices and should provide excellent performance for typical gene database operations.
