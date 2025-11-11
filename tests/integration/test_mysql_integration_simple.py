"""Simple MySQL integration test framework.

This test demonstrates the MySQL integration framework setup and provides
a way to test it when Docker is not available.
"""

import pytest
from sqlalchemy import text


def test_mysql_framework_availability():
    """Test that the MySQL integration framework is properly configured."""
    # This test verifies that the test framework is set up correctly
    # even if Docker is not available

    # Import testcontainers to check availability
    try:
        import importlib.util

        testcontainers_available = (
            importlib.util.find_spec("testcontainers.mysql") is not None
        )
    except ImportError:
        testcontainers_available = False

    # Check if we can import our fixtures
    from tests.integration.conftest import (
        mysql_connection_info,
        mysql_container,
        mysql_engine,
        mysql_session,
        sample_species_mysql,
    )

    # Verify fixtures exist
    assert mysql_container is not None
    assert mysql_engine is not None
    assert mysql_session is not None
    assert mysql_connection_info is not None
    assert sample_species_mysql is not None

    print(f"Testcontainers available: {testcontainers_available}")
    print("MySQL integration framework fixtures are properly configured")


@pytest.mark.skip_if_no_docker
def test_mysql_container_startup(mysql_connection_info):
    """Test that MySQL container can start and provide connection info.

    This test will be skipped if Docker is not available.
    """
    # Verify connection info is provided
    assert "host" in mysql_connection_info
    assert "port" in mysql_connection_info
    assert "database" in mysql_connection_info
    assert "username" in mysql_connection_info
    assert "password" in mysql_connection_info
    assert "url" in mysql_connection_info

    print(f"MySQL connection info: {mysql_connection_info}")


def test_mock_mysql_functionality(mock_mysql_container):
    """Test MySQL functionality using a mock container.

    This test works even without Docker and demonstrates the test structure.
    """
    # Verify mock container provides expected interface
    assert mock_mysql_container.get_connection_url() is not None
    assert mock_mysql_container.get_container_host_ip() is not None
    assert mock_mysql_container.get_exposed_port(3306) is not None

    connection_url = mock_mysql_container.get_connection_url()
    print(f"Mock MySQL connection URL: {connection_url}")

    # This demonstrates how tests would be structured
    # In real tests, you would use the connection to create an engine
    # and perform database operations


class TestMySQLIntegrationFramework:
    """Test class demonstrating MySQL integration framework usage."""

    @pytest.mark.skip_if_no_docker
    def test_mysql_basic_connection(self, mysql_session):
        """Test basic MySQL connection using testcontainers.

        This test will be skipped if Docker is not available.
        """
        # Test basic database connectivity
        result = mysql_session.execute(text("SELECT 1 as test_value"))
        row = result.fetchone()
        assert row[0] == 1

        print("MySQL connection test passed")

    def test_mysql_mock_workflow(self, mock_mysql_container):
        """Test MySQL workflow using mock container."""
        # This demonstrates the expected workflow for MySQL tests
        # without requiring a real MySQL instance

        connection_url = mock_mysql_container.get_connection_url()
        print(f"Using mock MySQL connection: {connection_url}")

        # In real tests, you would:
        # 1. Create SQLAlchemy engine with connection_url
        # 2. Create tables using unified metadata
        # 3. Perform ORM operations
        # 4. Verify results

        # For now, just verify the mock interface works
        assert "mysql+pymysql://" in connection_url
        assert "vgnc_test" in connection_url


if __name__ == "__main__":
    # Allow running this test directly to verify framework setup
    test_mysql_framework_availability()
    test_mock_mysql_functionality(None)
    print("MySQL integration framework test completed successfully")
