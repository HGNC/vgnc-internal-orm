# Getting Started

**VGNC Internal ORM v0.5.0** - MIT License

## Installation

Install into your project environment:

```bash
# Install from PyPI (when available)
pip install vgnc-internal-orm

# Install from GitHub (latest development version)
pip install git+https://github.com/HGNC/vgnc-internal-orm.git

# Using uv (modern Python package manager)
uv install vgnc-internal-orm
uv install git+https://github.com/HGNC/vgnc-internal-orm.git

# Install with optional dependencies
pip install vgnc-internal-orm[mysql]      # MySQL support
pip install vgnc-internal-orm[dev]       # Development tools
uv install vgnc-internal-orm[mysql]
uv install vgnc-internal-orm[dev]
```

## Minimum Configuration

Set environment variables or `.env` for database connection pieces, then:

```python
from vgnc_internal_orm.config.settings import get_settings
settings = get_settings()
url = settings.get_database_url(use_async=False)
```

## Creating a Session

```python
from vgnc_internal_orm.sessions.factory import SessionFactory
from vgnc_internal_orm.config.settings import get_settings

sf = SessionFactory(get_settings().database)
with sf.get_session() as session:
    species = session.query(Species).limit(5).all()
```

Async:

```python
async with sf.get_async_session() as session:
    result = await session.execute(select(Species))
```

## First Query

```python
from vgnc_internal_orm.models.species import Species
items = Species.find(session, limit=10)  # helper wrapper
```

## CLI Usage

```bash
# Option 1: Using the installed command
vgnc-cli query-species --limit 10 --format table

# Option 2: Using Python module invocation
python -m vgnc_internal_orm.cli.main query-species --limit 10 --format table
```

## Next Steps

Read: `configuration.md`, `models_reference.md`, `sessions.md`, `utilities.md`. For deeper guides, see `advanced_topics.md`.
