# Models Reference

**VGNC Internal ORM v0.5.1** - MIT License

## BaseModel

Provides:

- Columns: `id`, `created_at`, `updated_at`
- Serialization: `to_dict()`, `to_json()` (with deep relationship control)
- CRUD: `create`, `find`, `update`, `delete`, `count`, `exists`
- Async variants: `acreate`, `afind`, etc.
- Charset utilities: `validate_utf8mb4_fields`, `requires_utf8mb4`, sanitization helpers.

## Domain Models

- `Species`: keyed by `taxon_id`; live status enum; properties `common_name`, `scientific_name`.
- `Chromosomes`: `chr_id` primary key; FK to species; helper `full_identifier`.
- `Assembly`: assembly metadata & active state flags.
- `Genefam`: gene family with editorial/status metadata.

## Orthology & Relationships

`orthology.py` defines composite-key entities for groups and membership (`GeneOrthologyGroup`, `GeneFamilyGroupMember`, `SpeciesRelationship`). Includes activate/deactivate helpers and indexed search patterns.

## Supporting Tables

Statuses, editors, alt names/symbols, flags, nomenclature types — stored in `supporting.py` plus association tables in `associations.py` (lightweight, minimal constraints for flexibility).

## Relationship Notes

Some relationships are intentionally commented out to avoid circular metadata or premature joins. This is by design to keep import sequences stable.

## Usage Example

```python
species = Species.create(session, taxon_id=9606, prefix="HGNC", common_name="Human")
family = Genefam.create(session, genefam_id=123, taxon_id=9606, symbol="GF123", name="Example Family")
```

### Async CRUD

```python
from sqlalchemy.ext.asyncio import AsyncSession
async with async_session as a_session:  # AsyncSession instance
    created = await Species.acreate(a_session, taxon_id=10090, prefix="MGNC", common_name="Mouse")
    found = await Species.afind(a_session, limit=5)
    await created.aupdate(a_session, display_name="Lab Mouse")
    await created.adelete(a_session)
```

### Query Filtering Helper

```python
results = Species.find(session, filters={"taxon_id": [9606, 10090]}, limit=50)
```

### UTF8MB4 Evaluation

```python
if Species.requires_utf8mb4("Gene 😃 Symbol"):
    # apply utf8mb4 connection / index strategy
    pass
```
