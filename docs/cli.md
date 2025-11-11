# CLI Reference

Invoke with module path or entrypoint:

```bash
python -m vgnc_internal_orm.cli query-species --limit 20 --format table
```

Or using the installed command:

```bash
vgnc-cli query-species --limit 20 --format table
```

## Global Options

- `--db-url` override connection string.
- `--config-path` explicit settings file path.

## Commands

- `query-species`: list species (filters TBD in code evolution).
- `query-genefams`: list gene families.
- `query-genefam-species`: join families ↔ species.
- `export`: bulk export of specified entity set (CSV/JSON/XML).
- `export-query`: custom query export.

## Formats

`table`, `json`, `csv`, `xml` (XML helpers for structured element output).

## Example Export

```bash
python -m vgnc_internal_orm.cli export --entity species --format csv > species.csv
```

## Filtered Query Example

```bash
python -m vgnc_internal_orm.cli export-query --sql "SELECT taxon_id, display_name FROM species WHERE is_live=1 LIMIT 100" --format json
```

## XML Output Example

```bash
python -m vgnc_internal_orm.cli query-genefams --limit 10 --format xml > families.xml
```
