# CLI Reference

Invoke with module path or entrypoint:

```bash
python -m vgnc_internal_orm.cli.main query-species --limit 20 --format table
```

Or using the installed command:

```bash
vgnc-cli query-species --limit 20 --format table
```

## Global Options

- `--database-url` or `-d`: Override database connection string
- `--config` or `-c`: Explicit configuration file path
- `--verbose` or `-v`: Enable verbose output

## Commands

- `query-species`: List species with filtering and sorting options
- `query-genefams`: List gene families with filtering
- `query-genefam-species`: Query species associated with a specific gene family
- `export`: Bulk export of specified entity (species, genefams, assemblies, chromosomes) in CSV/JSON/XML
- `export-query`: Execute custom SQL query and export results

## Formats

`table`, `json`, `csv`, `xml` (XML helpers for structured element output).

## Example Export

```bash
vgnc-cli export --entity species --format csv --output species.csv
```

## Filtered Query Example

```bash
vgnc-cli export-query --query "SELECT taxon_id, display_name FROM species WHERE is_live=1 LIMIT 100" --format json --output species.json
```

## XML Output Example

```bash
vgnc-cli query-genefams --limit 10 --format xml > families.xml
```
