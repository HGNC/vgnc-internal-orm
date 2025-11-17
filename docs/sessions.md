# Sessions & Engines

**VGNC Internal ORM v0.4.1** - MIT License

`SessionFactory` centralizes engine creation and session provisioning (sync + async) using config-driven pooling and driver-specific connect args.

## Engine Events

- SQLite: pragmas (foreign_keys, journal_mode)
- MySQL: ensure UTF8MB4 settings
- Development: optional verbose logging when `echo` is true.

## Creating Sessions

```python
sf = SessionFactory(get_settings().database)
with sf.get_session() as session:
    ...
```

Async:

```python
async with sf.get_async_session() as session:
    ...
```

### Engine Inspection & Health

```python
engine = sf.get_engine()
info = sf.get_pool_info()  # size, overflow, timeout
sf.health_check()  # raises if connection broken
```

### Using Context Manager for Automatic Commit

```python
with sf.get_session(commit=True) as session:
    Species.create(session, taxon_id=1234, prefix="TST", common_name="Test")
```

### Async Health Check

```python
await sf.ahealth_check()  # ensures async engine responsive
```

## Health Checks

`SessionFactory.health_check()` / `ahealth_check()` verify connectivity and basic query execution.

## Manager Wrapper

`SessionManager` offers higher-level context patterns if preferred over direct factory calls.
