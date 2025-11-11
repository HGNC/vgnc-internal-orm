# Alembic Baseline Migration

This document describes the baseline migration setup for the VGNC ORM project.

## Overview

The baseline migration
(`2025_11_05_2253-2299f7d46a8d_initial_baseline.py`) represents the complete
database schema for the VGNC ORM system based on the actual
`genefam_production` database structure.

## Generated Schema

### Main Entity Tables (4 tables)

1. **species** - Core species information
   - Primary key: `taxon_id` (Integer)
   - Fields:
     - `genefam_prefix`
     - `primary_db_table`
     - `display_name`
     - `ensembl_species_name`
     - `is_live`
     - `created`

2. **genefam** - Gene family entries
   - Primary key: `genefam_id` (Integer)
   - Foreign key: `taxon_id` → `species.taxon_id`
   - Fields:
     - `assigned_id`
     - `assigned_symbol`
     - `assigned_name`
     - `status_id`
     - `editor_id`
     - `hcop_support_level`

3. **assembly** - Genome assembly information
   - Primary key: `id` (Integer)
   - Foreign key: `taxon_id` → `species.taxon_id`
   - Fields:
     - `source`
     - `name`
     - `genbank_assembly_accession`
     - `refseq_assembly_accession`
     - `is_current`
     - `is_vgnc_default`

4. **chromosomes** - Chromosome information
   - Primary key: `chr_id` (Integer)
   - Foreign key: `taxon_id` → `species.taxon_id`
   - Fields:
     - `display_name`
     - `coord_system`
     - `refseq_accession`
     - `genbank_accession`
     - `ensembl_accession`
     - `type`
     - `assigned_to`

### Supporting Tables (15 tables)

#### Reference Tables

- `editor` - Editor information
- `gene_status` - Gene status options
- `flag_class` - Flag classification
- `nomenclature_type` - Nomenclature type definitions

#### Content Tables

- `alt_name` - Alternative gene names
- `alt_symbol` - Alternative gene symbols
- `comment` - Gene comments
- `family_new` - Gene family information
- `gene_flag` - Gene flags

#### Association Tables (with indexes)

- `assembly_has_chr` - Assembly-chromosome relationships
- `gene_alt_name` - Gene-alternative name relationships
- `gene_alt_symbol` - Gene-alternative symbol relationships
- `gene_has_comment` - Gene-comment relationships
- `gene_has_family` - Gene-family relationships
- `gene_has_flag` - Gene-flag relationships

## Key Features

### Indexes Generated

- All association tables have proper indexes on foreign key columns.
- Optimized for join performance on large datasets.

### Foreign Key Constraints

- Genefam → Species (via `taxon_id`)
- Assembly → Species (via `taxon_id`)
- Chromosomes → Species (via `taxon_id`)
- Alt_name → Nomenclature_type
- Alt_symbol → Nomenclature_type
- Comment → Editor
- Family_new → Editor
- Gene_flag → Flag_class

### Data Types Used

- **Integer**: Primary keys and foreign keys
- **VARCHAR(255)**: Text fields with reasonable length limits
- **TEXT**: Long text content (comments, descriptions)
- **Boolean**: Status flags
- **DATETIME**: Timestamps with timezone support

## Usage

### Applying Baseline Migration

```bash
# Apply to new database
alembic upgrade head

# Check current version
alembic current

# View migration history
alembic history
```

### Testing the Baseline

```bash
# Run baseline validation tests
pytest tests/test_alembic_baseline.py -v
```

### Database Configuration

The baseline migration uses SQLite by default. For other databases:

```bash
# MySQL
export DATABASE_URL="mysql+pymysql://user:pass@localhost:3306/vgnc_database"

# Then run migration
alembic upgrade head
```

## Validation

The baseline migration has been validated with comprehensive tests that verify:

1. **Table Creation**: All 19 tables are created correctly.
2. **Schema Accuracy**: Table schemas match SQLAlchemy model definitions.
3. **Foreign Keys**: All foreign key constraints are properly enforced.
4. **Indexes**: Performance indexes are created on association tables.
5. **Model Integration**: SQLAlchemy models work correctly with the migrated database.
6. **Version Tracking**: Alembic version tracking functions properly.

## Model Alignment

This baseline migration is based on the actual database schema from
`genefam_production.txt` and includes:

- ✅ Correct primary key definitions (`taxon_id`, `genefam_id`, etc.)
- ✅ Accurate field names and data types
- ✅ Proper foreign key relationships
- ✅ Real association table structures
- ✅ All indexes and constraints from the source database

## Next Steps

After applying the baseline migration:

1. **Incremental Migrations**: Use `alembic revision --autogenerate` for schema
   changes.
2. **Testing**: Validate migrations in the development environment first.
3. **Safety Checks**: Review generated migrations for destructive operations.
4. **Backups**: Create database backups before applying migrations to production.

## File Structure

```text
alembic/
├── versions/
│   └── 2025_11_05_2253-2299f7d46a8d_initial_baseline.py  # Baseline migration
├── env.py              # Alembic environment configuration
├── script.py.mako      # Migration template
└── README              # Alembic documentation

alembic.ini             # Alembic configuration file
tests/test_alembic_baseline.py  # Baseline validation tests
```

## Notes

- This baseline represents the complete current schema.
- No downgrade function is provided for baseline migrations.
- The migration is designed to be applied to empty databases only.
- All models use the actual database schema from the genefam_production database.
