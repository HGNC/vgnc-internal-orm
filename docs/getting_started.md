# Getting Started

## Installation

Install into your project environment:

```bash
pip install vgnc-internal-orm  # (or local editable install)
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
python -m vgnc_internal_orm.cli query-species --limit 10 --format table
```

## Next Steps

Read: `configuration.md`, `models_reference.md`, `sessions.md`, `utilities.md`. For deeper guides, see `advanced_topics.md`.
