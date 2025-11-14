# Configuration

The VGNC ORM uses a comprehensive configuration system built on Pydantic Settings that supports environment variable overrides, multiple database drivers, and flexible deployment scenarios.

## Environment Variables

All configuration can be set via environment variables using the `VGNC_` prefix (for app settings) or `DATABASE_` prefix (for database settings).

### Core Application Settings

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `VGNC_APP_NAME` | `VGNC ORM` | Application name for logging and identification | `My VGNC App` |
| `VGNC_VERSION` | `0.3.0` | Application version | `0.3.0` |
| `VGNC_DEBUG` | `false` | Enable debug mode (affects logging, error details) | `true` |
| `VGNC_ENVIRONMENT` | `development` | Environment: `development`, `testing`, `staging`, `production` | `production` |
| `VGNC_LOG_LEVEL` | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL` | `DEBUG` |

### Database Configuration

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `DATABASE_DRIVER` | `mysql+pymysql` | Database driver: `mysql+pymysql`, `mysql+aiomysql`, `sqlite`, `sqlite+aiosqlite` | `mysql+pymysql` |
| `DATABASE_HOST` | `localhost` | Database server hostname | `db.example.com` |
| `DATABASE_PORT` | `3306` | Database server port | `5432` |
| `DATABASE_USERNAME` | required (MySQL) | Database username | `vgnc_user` |
| `DATABASE_PASSWORD` | required (MySQL) | Database password | `secure_password123` |
| `DATABASE_DATABASE` | required | Database name | `vgnc_production` |
| `DATABASE_CHARSET` | `utf8mb4` | Character set for MySQL connections | `utf8mb4` |
| `DATABASE_COLLATION` | `utf8mb4_unicode_ci` | Database collation for MySQL | `utf8mb4_unicode_ci` |

### Database Pool Settings

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `DATABASE__POOL__POOL_SIZE` | `5` | Connection pool size (1-100) | `10` |
| `DATABASE__POOL__MAX_OVERFLOW` | `10` | Maximum overflow connections (0-100) | `20` |
| `DATABASE__POOL__POOL_TIMEOUT` | `30` | Connection timeout in seconds | `60` |
| `DATABASE__POOL__POOL_RECYCLE` | `3600` | Connection recycle time in seconds | `7200` |
| `DATABASE__POOL__POOL_PRE_PING` | `true` | Enable connection pre-ping validation | `true` |

### Database SSL Configuration (MySQL)

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `DATABASE_SSL_MODE` | unset | SSL mode: `DISABLED`, `PREFERRED`, `REQUIRED`, `VERIFY_CA`, `VERIFY_IDENTITY` | `REQUIRED` |
| `DATABASE_SSL_CERT` | unset | Path to SSL certificate file | `/path/to/client-cert.pem` |
| `DATABASE_SSL_KEY` | unset | Path to SSL private key file | `/path/to/client-key.pem` |
| `DATABASE_SSL_CA` | unset | Path to SSL CA certificate file | `/path/to/ca-cert.pem` |

### Additional Database Settings

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `DATABASE_CONNECT_TIMEOUT` | `10` | Connection timeout in seconds | `30` |
| `DATABASE_QUERY_TIMEOUT` | unset | Query timeout in seconds | `300` |
| `DATABASE_ISOLATION_LEVEL` | unset | Transaction isolation level | `REPEATABLE_READ` |
| `DATABASE_ECHO` | `false` | Enable SQLAlchemy query logging | `true` |
| `DATABASE_DB_SCHEMA` | unset | Database schema (if applicable) | `vgnc_schema` |

### API and Cache Settings

| Variable | Default | Description | Example |
|----------|---------|-------------|---------|
| `VGNC_API_HOST` | `0.0.3.0` | API server host | `127.0.3.0` |
| `VGNC_API_PORT` | `8000` | API server port | `8080` |
| `VGNC_REDIS_URL` | unset | Redis connection URL for caching | `redis://localhost:6379/0` |
| `VGNC_CACHE_TTL` | `3600` | Cache time-to-live in seconds | `7200` |

## Configuration Examples

### Development Environment (.env.development)

```bash
# Core application settings
VGNC_APP_NAME="VGNC ORM Development"
VGNC_DEBUG=true
VGNC_ENVIRONMENT=development
VGNC_LOG_LEVEL=DEBUG

# Database configuration (MySQL)
DATABASE_DRIVER=mysql+pymysql
DATABASE_HOST=localhost
DATABASE_PORT=3306
DATABASE_USERNAME=vgnc_dev
DATABASE_PASSWORD=dev_password_123
DATABASE_DATABASE=vgnc_dev
DATABASE_ECHO=true

# Pool settings (smaller for development)
DATABASE__POOL__POOL_SIZE=3
DATABASE__POOL__MAX_OVERFLOW=5
DATABASE__POOL__POOL_TIMEOUT=10
DATABASE__POOL__POOL_RECYCLE=1800
```

### Production Environment (.env.production)

```bash
# Core application settings
VGNC_APP_NAME="VGNC ORM Production"
VGNC_DEBUG=false
VGNC_ENVIRONMENT=production
VGNC_LOG_LEVEL=INFO

# Database configuration (MySQL with SSL)
DATABASE_DRIVER=mysql
DATABASE_HOST=db-prod.example.com
DATABASE_PORT=3306
DATABASE_USERNAME=vgnc_prod
DATABASE_PASSWORD=secure_production_password
DATABASE_DATABASE=vgnc_production
DATABASE_SSL_MODE=REQUIRED
DATABASE_SSL_CERT=/etc/ssl/certs/client-cert.pem
DATABASE_SSL_KEY=/etc/ssl/private/client-key.pem
DATABASE_SSL_CA=/etc/ssl/certs/ca-cert.pem

# Pool settings (larger for production)
DATABASE__POOL__POOL_SIZE=20
DATABASE__POOL__MAX_OVERFLOW=30
DATABASE__POOL__POOL_TIMEOUT=60
DATABASE__POOL__POOL_RECYCLE=14400
DATABASE_CONNECT_TIMEOUT=30
DATABASE_QUERY_TIMEOUT=300

# Performance settings
DATABASE_ISOLATION_LEVEL=REPEATABLE_READ

# Cache settings
VGNC_REDIS_URL=redis://cache.example.com:6379/0
VGNC_CACHE_TTL=7200
```

### Testing Environment (.env.testing)

```bash
# Core application settings
VGNC_APP_NAME="VGNC ORM Tests"
VGNC_DEBUG=false
VGNC_ENVIRONMENT=testing
VGNC_LOG_LEVEL=WARNING

# Database configuration (SQLite for testing)
DATABASE_DRIVER=sqlite
DATABASE_DATABASE=test_vgnc.db

# Disable connection pooling for SQLite
DATABASE__POOL__POOL_SIZE=1
DATABASE__POOL__MAX_OVERFLOW=0
```

### Docker Environment (.env.docker)

```bash
# Core application settings
VGNC_APP_NAME="VGNC ORM Docker"
VGNC_DEBUG=false
VGNC_ENVIRONMENT=production
VGNC_LOG_LEVEL=INFO

# Database configuration (MySQL in Docker network)
DATABASE_DRIVER=mysql
DATABASE_HOST=mysql-db
DATABASE_PORT=3306
DATABASE_USERNAME=root
DATABASE_PASSWORD=docker_mysql_password
DATABASE_DATABASE=vgnc_docker

# SSL disabled for internal Docker communication
DATABASE_SSL_MODE=DISABLED

# Pool settings optimized for containers
DATABASE__POOL__POOL_SIZE=10
DATABASE__POOL__MAX_OVERFLOW=15
DATABASE__POOL__POOL_TIMEOUT=30
DATABASE__POOL__POOL_RECYCLE=3600
```

## Database URL Generation

The ORM automatically generates database URLs from the configuration:

### MySQL Examples
```bash
# Basic MySQL connection
mysql://username:password@localhost:3306/database

# MySQL with charset and collation
mysql://user:pass@host:3306/db?charset=utf8mb4&collation=utf8mb4_unicode_ci

# MySQL with SSL and connection parameters
mysql://user:pass@host:3306/db?charset=utf8mb4&sslmode=require&connect_timeout=30
```

### SQLite Examples
```bash
# File-based SQLite
sqlite:///path/to/database.db

# In-memory SQLite
sqlite:///:memory:
```

### Async Database URLs
```bash
# MySQL Async
mysql+aiomysql://user:pass@host:3306/db

# SQLite Async
sqlite+aiosqlite:///path/to/database.db
```

## Configuration Validation

The configuration system includes comprehensive validation:

### Required Fields
- `DATABASE_DATABASE` is always required
- `DATABASE_USERNAME` and `DATABASE_PASSWORD` are required for MySQL
- SSL certificate paths are validated to exist if provided

### Type Validation
- Port numbers must be in valid range (1-65535)
- Pool settings must be within defined bounds
- Log levels are normalized to uppercase
- Boolean values accept various formats (`true`, `1`, `yes`, `on`)

## Environment-Specific Behavior

### Development Environment
- Shorter pool timeouts (10 seconds)
- Shorter connection recycle times (1 hour)
- Debug logging enabled by default
- More verbose error messages

### Production Environment
- Longer pool timeouts (30+ seconds)
- Extended connection recycle times (4 hours)
- Optimized pool sizes
- SSL recommended for database connections

### Testing Environment
- Minimal logging
- SQLite recommended for isolation
- Small connection pools
- Fast connection timeouts

## Accessing Configuration in Code

```python
from vgnc_internal_orm.config.settings import get_settings

# Get global settings instance
settings = get_settings()

# Access database configuration
db_config = settings.database
print(f"Driver: {db_config.driver}")
print(f"Database: {db_config.database}")

# Get database URLs
sync_url = settings.get_database_url(use_async=False)
async_url = settings.get_database_url(use_async=True)

# Check environment
if settings.is_production():
    print("Running in production mode")
```

## Migration from Previous Versions

If you're migrating from a version that supported PostgreSQL:

1. Update your `DATABASE_DRIVER` from `postgres` to `mysql`
2. Change the default port from `5432` to `3306` if not explicitly set
3. Remove PostgreSQL-specific SSL configurations
4. Update any connection pool settings if needed
5. Verify all environment variables use the `DATABASE_` prefix

The configuration system will automatically validate your settings and provide clear error messages for any issues.