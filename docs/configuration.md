# Configuration

`DatabaseConfig` centralizes driver, credentials, pooling, isolation, charset, SSL. Built via Pydantic Settings allowing env variable overrides.

## Key Fields

- `driver`: `postgres`, `mysql`, `sqlite`
- `host`, `port`, `user`, `password`, `database`
- `ssl_mode` / `ssl_cert_path`
- `pool_size`, `max_overflow`, `pool_timeout`
- `echo`, `statement_timeout`, `isolation_level`
- Computed: `database_url`, `async_database_url`

## URL Building Nuances

- MySQL: forces `charset=utf8mb4` & collation when needed.
- SQLite: file path vs memory, pragmas applied via events.
- Postgres: optional SSL segments.

## Access Pattern

```python
settings = get_settings()
url = settings.get_database_url(use_async=False)
```

## Validation

Config raises early errors for missing credentials for networked drivers, and ensures directory existence for SQLite file DBs.

## Environment Awareness

`Environment` enum can influence logging verbosity & debug toggles (development vs production).
