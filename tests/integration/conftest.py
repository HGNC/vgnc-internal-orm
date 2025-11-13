"""Shared fixtures and utilities for integration tests.

This module provides common database setup utilities that handle the
complex foreign key dependencies between BaseModel and BaseCustomModel
metadata registries, as well as MySQL testcontainers support.
"""

import time
from collections.abc import Generator
from unittest.mock import Mock

import pytest
from sqlalchemy import MetaData, create_engine, text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import StaticPool

from vgnc_internal_orm.models.base import BaseModel
from vgnc_internal_orm.models.species import BaseCustomModel

# Import supporting models to ensure they are registered in metadata

# Try to import testcontainers, but make it optional
try:
    from testcontainers.mysql import MySqlContainer

    TESTCONTAINERS_AVAILABLE = True
except ImportError:
    TESTCONTAINERS_AVAILABLE = False
    MySqlContainer = None


@pytest.fixture(scope="function")
def integrated_test_db():
    """Create a test database with all models properly integrated."""
    engine = create_engine(
        "sqlite:///:memory:",
        poolclass=StaticPool,
        connect_args={
            "check_same_thread": False,
            "timeout": 20,
        },
        echo=False,
        # Disable deprecated datetime adapter warnings
        native_datetime=True,
    )

    # Create all tables using the unified metadata registry
    unified_metadata = MetaData()

    # Add all tables from the shared metadata registry
    for table in BaseModel.metadata.tables.values():
        table.to_metadata(unified_metadata)

    # Create all tables with foreign key constraints disabled for testing
    with engine.connect() as conn:
        conn.execute(text("PRAGMA foreign_keys = OFF"))
        unified_metadata.create_all(conn)
        conn.commit()

    # Create session
    SessionLocal = sessionmaker(bind=engine)
    session = SessionLocal()

    # Ensure foreign keys remain disabled for this session
    session.execute(text("PRAGMA foreign_keys = OFF"))

    try:
        yield session, engine
    finally:
        session.close()


@pytest.fixture(scope="function")
def integrated_test_session(integrated_test_db):
    """Provide a session from the integrated test database."""
    session, engine = integrated_test_db
    try:
        yield session
    finally:
        session.close()


# ============================================================================
# MySQL Testcontainers Fixtures
# ============================================================================


@pytest.fixture(scope="session")
def mysql_container() -> MySqlContainer:
    """Start a MySQL 8.0 container for integration testing.

    This fixture manages the lifecycle of a MySQL container with
    proper configuration for testing. The container is started once
    per test session and reused across tests.
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip(
            "testcontainers not available - install with: pip install testcontainers[mysql]"
        )

    # Configure MySQL 8.0 container with specific settings
    container = MySqlContainer(
        image="mysql:8.0",
        dialect="pymysql",
        username="testuser",
        password="testpass",
        dbname="vgnc_test",
        root_password="rootpass",
        # Additional MySQL configuration command
        command=[
            "--default-authentication-plugin=mysql_native_password",
            "--sql_mode=STRICT_TRANS_TABLES,NO_ZERO_DATE,NO_ZERO_IN_DATE,ERROR_FOR_DIVISION_BY_ZERO",
            "--character-set-server=utf8mb4",
            "--collation-server=utf8mb4_unicode_ci",
            "--innodb-buffer-pool-size=256M",
            "--innodb-log-file-size=64M",
        ],
    )

    try:
        # Start the container
        container.start()

        # Wait for MySQL to be ready
        max_retries = 30
        for attempt in range(max_retries):
            try:
                engine = create_engine(container.get_connection_url())
                with engine.connect() as conn:
                    conn.execute(text("SELECT 1"))
                break
            except Exception as e:
                if attempt == max_retries - 1:
                    raise RuntimeError(
                        f"MySQL container failed to start after {max_retries} attempts: {e}"
                    ) from e
                time.sleep(1)

        print(f"MySQL container started on port: {container.get_exposed_port(3306)}")
        yield container

    finally:
        # Cleanup: stop the container
        try:
            container.stop()
            print("MySQL container stopped")
        except Exception as e:
            print(f"Warning: Error stopping MySQL container: {e}")


@pytest.fixture(scope="function")
def mysql_engine(mysql_container: MySqlContainer) -> Generator:
    """Create a SQLAlchemy engine connected to the MySQL test container.

    Each test gets a fresh engine to ensure isolation.
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")

    connection_url = mysql_container.get_connection_url()

    # Create engine with MySQL-specific settings
    engine = create_engine(
        connection_url,
        echo=False,  # Set to True for SQL debugging
        pool_size=5,
        max_overflow=10,
        pool_pre_ping=True,
        pool_recycle=3600,
        # MySQL-specific connection arguments
        connect_args={
            "charset": "utf8mb4",
            "use_unicode": True,
            "autocommit": False,
        },
    )

    try:
        yield engine
    finally:
        engine.dispose()


@pytest.fixture(scope="function")
def mysql_session(mysql_engine) -> Generator[Session, None, None]:
    """Create a SQLAlchemy session with the MySQL test database.

    This fixture provides a database session with automatic transaction
    rollback to ensure test isolation.
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")

    # Create unified metadata for testing
    unified_metadata = MetaData()

    # Add all tables from both metadata registries without duplicates
    # Start with BaseModel tables
    for table in BaseModel.metadata.tables.values():
        table.to_metadata(unified_metadata)

    # Add only tables from BaseCustomModel that don't already exist
    existing_table_names = set(unified_metadata.tables.keys())
    for table in BaseCustomModel.metadata.tables.values():
        if table.name not in existing_table_names:
            table.to_metadata(unified_metadata)

    # Create all tables
    unified_metadata.create_all(mysql_engine)

    # Create session factory
    SessionLocal = sessionmaker(bind=mysql_engine)
    session = SessionLocal()

    # Begin transaction for test isolation
    transaction = session.begin()

    try:
        yield session
    finally:
        # Always rollback to ensure test isolation
        try:
            transaction.rollback()
        except Exception:
            pass  # Transaction might already be rolled back

        session.close()

        # Drop all tables for clean state
        try:
            unified_metadata.drop_all(mysql_engine)
        except Exception:
            pass  # Tables might not exist


@pytest.fixture(scope="function")
def mysql_populated_session(mysql_session: Session, sample_species_mysql) -> Session:
    """Provide a session with pre-populated test data in MySQL."""
    return mysql_session


@pytest.fixture(scope="function")
def sample_species_mysql(mysql_session: Session):
    """Create a sample species record in MySQL."""
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")

    from datetime import datetime

    from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus

    species = Species(
        taxon_id=9606,
        genefam_prefix="HSA",
        display_name="human (Homo sapiens)",
        is_live=SpeciesLiveStatus.YES,
        created=datetime.now(),
    )

    mysql_session.add(species)
    mysql_session.commit()
    mysql_session.refresh(species)
    return species


@pytest.fixture(scope="session")
def mysql_connection_info(mysql_container: MySqlContainer) -> dict:
    """Provide connection information for the MySQL container.

    Useful for tests that need to create their own connections
    or verify connection parameters.
    """
    if not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available")

    return {
        "host": mysql_container.get_container_host_ip(),
        "port": mysql_container.get_exposed_port(3306),
        "database": "vgnc_test",
        "username": "testuser",
        "password": "testpass",
        "url": mysql_container.get_connection_url(),
    }


@pytest.fixture
def mock_mysql_container():
    """Provide a mock MySQL container for testing without real containers.

    This is useful for CI environments where Docker might not be available
    or for faster test execution during development.
    """
    mock_container = Mock()
    mock_container.get_connection_url.return_value = (
        "mysql+pymysql://testuser:testpass@localhost:3306/vgnc_test"
    )
    mock_container.get_container_host_ip.return_value = "localhost"
    mock_container.get_exposed_port.return_value = 3306
    mock_container.start.return_value = None
    mock_container.stop.return_value = None
    return mock_container


# Skip integration tests if Docker is not available
def pytest_configure(config):
    """Configure pytest to handle Docker availability."""
    if TESTCONTAINERS_AVAILABLE:
        try:
            # Try to import and create a test container
            from testcontainers.core.docker_client import DockerClient

            client = DockerClient()
            client.ping()
        except Exception:
            # Docker is not available, add a marker to skip MySQL tests
            config.addinivalue_line(
                "markers",
                "skip_if_no_docker: mark test to skip when Docker is not available",
            )


@pytest.fixture(autouse=True)
def skip_if_no_docker(request):
    """Automatically skip MySQL tests if Docker is not available."""
    if (
        "mysql" in request.fixturenames or "mysql_container" in request.fixturenames
    ) and not TESTCONTAINERS_AVAILABLE:
        pytest.skip("testcontainers not available - skipping MySQL integration test")
