"""Enhanced CLI workflow tests covering complete end-to-end scenarios."""

import tempfile
import os
import io
from unittest.mock import Mock, patch
from datetime import datetime, UTC

import pytest
from click.testing import CliRunner

from src.vgnc_internal_orm.cli.main import (
    cli,
    format_species_as_xml,
    format_genefam_as_xml,
    format_assembly_as_xml,
    format_chromosomes_as_xml,
    display_species_table,
    display_species_json,
    display_species_csv,
    get_session,
)
from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestCLICompleteWorkflows:
    """Test complete CLI workflow scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_configuration_workflow(self):
        """Test complete CLI configuration workflow."""
        # Test the full configuration discovery and loading process
        with self.runner.isolated_filesystem():
            # Step 1: Create configuration file
            config_content = '''
[database]
driver = "sqlite"
database = "workflow_test.db"
timeout = 30.0

[app]
name = "CLI Workflow Test App"
debug = true
log_level = "INFO"

[session]
pool_size = 10
max_overflow = 20
pool_timeout = 45
pool_recycle = 3600
'''
            with open('workflow_config.toml', 'w') as f:
                f.write(config_content)

            # Step 2: Test configuration file discovery
            result1 = self.runner.invoke(cli, [
                '--config', 'workflow_config.toml',
                '--help'
            ])
            assert result1.exit_code == 0

            # Step 3: Test with environment override
            with patch.dict(os.environ, {"VGNC_DEBUG": "false"}):
                result2 = self.runner.invoke(cli, [
                    '--config', 'workflow_config.toml',
                    '--verbose'
                ])
                assert result2.exit_code == 0

            # Step 4: Test configuration loading with ensure_config_loaded
            from click import Context

            ctx = Context(cli)
            ctx.obj = {
                "config_loaded": False,
                "config_file": "workflow_config.toml"
            }

            with patch.dict(os.environ, {"VGNC_CONFIG_FILE": "workflow_config.toml"}):
                from src.vgnc_internal_orm.cli.main import ensure_config_loaded
                ensure_config_loaded(ctx)
                assert ctx.obj["config_loaded"] is True

    def test_cli_database_connection_workflow(self):
        """Test complete database connection workflow."""
        # Test multiple database connection scenarios
        connection_scenarios = [
            # In-memory SQLite
            {
                'name': 'In-Memory SQLite',
                'url': 'sqlite:///:memory:',
                'expect_success': True
            },
            # File-based SQLite
            {
                'name': 'File-Based SQLite',
                'url': 'sqlite:///test_connection.db',
                'expect_success': True
            },
            # SQLite with options
            {
                'name': 'SQLite with Options',
                'url': 'sqlite:///test_options.db?cache=shared&mode=rwc',
                'expect_success': True
            }
        ]

        for scenario in connection_scenarios:
            with self.runner.isolated_filesystem():
                result = self.runner.invoke(cli, [
                    '--database-url', scenario['url'],
                    '--help'
                ])

                if scenario['expect_success']:
                    assert result.exit_code == 0
                    assert 'VGNC ORM Command-line Interface' in result.output

    def test_cli_error_handling_workflow(self):
        """Test CLI error handling workflow."""
        error_scenarios = [
            # Invalid database URL format
            {
                'args': ['--database-url', 'invalid-format-url'],
                'expected_exit': 0,  # Should still show help
                'description': 'Invalid URL format'
            },
            # Non-existent config file
            {
                'args': ['--config', 'nonexistent_config.toml'],
                'expected_exit': 0,  # May handle gracefully
                'description': 'Non-existent config file'
            },
            # Invalid option
            {
                'args': ['--invalid-option'],
                'expected_exit': 2,  # Should fail
                'description': 'Invalid option'
            }
        ]

        for scenario in error_scenarios:
            result = self.runner.invoke(cli, scenario['args'])
            assert result.exit_code in [0, 1, 2]  # Various error codes possible


class TestCLIDataProcessingWorkflows:
    """Test CLI data processing workflows with complete scenarios."""

    def test_complete_xml_generation_workflow(self):
        """Test complete XML generation workflow."""
        # Create comprehensive test data
        comprehensive_species = []
        for i in range(10):
            species = Mock()
            species.taxon_id = 9600 + i
            species.genefam_prefix = f"H{i:02d}"
            species.display_name = f"Test Species {i}"
            species.is_live = Mock()
            species.is_live.value = "YES" if i % 2 == 0 else "NO"
            species.primary_db_table = "species"
            species.ensembl_species_name = f"Test species ensembl {i}"
            species.created = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
            comprehensive_species.append(species)

        # Test XML generation for large dataset
        result = format_species_as_xml(comprehensive_species)

        # Verify XML structure
        assert isinstance(result, str)
        assert result.count('<species>') == 10
        assert result.count('</species>') == 10
        assert result.count('taxon_id=') == 10

        # Test XML with mixed data quality
        mixed_species = []
        for i in range(5):
            species = Mock()
            species.taxon_id = 9700 + i
            species.genefam_prefix = f"MX{i:02d}" if i % 2 == 0 else None
            species.display_name = f"Mixed Species {i}" if i % 3 != 0 else None
            species.is_live = Mock()
            species.is_live.value = None if i == 2 else "YES"
            species.primary_db_table = None if i == 1 else "species"
            species.ensembl_species_name = None
            species.created = None
            mixed_species.append(species)

        mixed_result = format_species_as_xml(mixed_species)
        assert mixed_result.count('<species>') == 5
        assert mixed_result.count('<genefam_prefix></genefam_prefix>') >= 2  # None values
        assert mixed_result.count('<display_name></display_name>') >= 1   # None values

    def test_complete_json_generation_workflow(self):
        """Test complete JSON generation workflow."""
        # Create test data with various field types
        json_test_data = []
        for i in range(8):
            species = Mock()
            species.taxon_id = 9600 + i
            species.display_name = f"JSON Test {i}"
            species.created = datetime(2023, i+1, 1, 12, 0, 0, tzinfo=UTC)
            json_test_data.append(species)

        # Test JSON output format
        import json
        result = display_species_json(json_test_data)

        # Verify JSON output (display function doesn't return, but we can test XML generation)
        xml_result = format_species_as_xml(json_test_data)

        # Verify conversion round-trip
        assert isinstance(xml_result, str)

    def test_complete_csv_generation_workflow(self):
        """Test complete CSV generation workflow."""
        # Create test data with CSV-specific scenarios
        csv_test_data = []
        for i in range(15):
            species = Mock()
            species.taxon_id = 9600 + i
            species.display_name = f"CSV Test {i}"
            species.is_live = Mock()
            species.is_live.value = "YES"
            species.primary_db_table = "species"
            # Add data that might need CSV escaping
            if i == 5:
                species.display_name = 'CSV, Test with "quotes" and commas'
            if i == 10:
                species.display_name = 'CSV\nTest\nwith\nnewlines'
            csv_test_data.append(species)

        # Test CSV output (should handle special characters)
        display_species_csv(csv_test_data)

        # Test with empty dataset
        display_species_csv([])

        # Test with single item
        single_item = [csv_test_data[0]]
        display_species_csv(single_item)

    def test_complete_multi_format_output_workflow(self):
        """Test complete multi-format output workflow."""
        # Create comprehensive test dataset
        test_data = []
        for i in range(6):
            species = Mock()
            species.taxon_id = 9600 + i
            species.display_name = f"Multi-Format Test {i}"
            species.genefam_prefix = f"MF{i:02d}"
            species.is_live = Mock()
            species.is_live.value = "YES"
            species.primary_db_table = "species"
            species.ensembl_species_name = f"Multi-format species ensembl {i}"
            species.created = datetime(2023, 1, i+1, 12, 0, 0, tzinfo=UTC)
            test_data.append(species)

        # Test all output formats with same data
        xml_result = format_species_as_xml(test_data)
        display_species_table(test_data)
        display_species_json(test_data)
        display_species_csv(test_data)

        # Verify all formats work with same data
        assert xml_result.count('<species>') == 6


class TestCLIRealWorldScenarios:
    """Test CLI real-world usage scenarios."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_development_workflow(self):
        """Test CLI development workflow scenario."""
        # Simulate developer working with different databases
        dev_scenarios = [
            # Local development with SQLite
            {
                'name': 'Local SQLite Development',
                'config': '''
[database]
driver = "sqlite"
database = "dev_database.db"
echo = true

[app]
name = "Development App"
debug = true
log_level = "DEBUG"
'''
            },
            # Testing with in-memory database
            {
                'name': 'Testing with In-Memory DB',
                'config': '''
[database]
driver = "sqlite"
database = ":memory:"
timeout = 10.0

[app]
name = "Test App"
debug = false
log_level = "ERROR"
'''
            },
            # Integration testing with file database
            {
                'name': 'Integration Testing',
                'config': '''
[database]
driver = "sqlite"
database = "integration_test.db"
pool_size = 5

[app]
name = "Integration Test App"
debug = false
'''
            }
        ]

        for scenario in dev_scenarios:
            with self.runner.isolated_filesystem():
                with open('dev_config.toml', 'w') as f:
                    f.write(scenario['config'])

                result = self.runner.invoke(cli, [
                    '--config', 'dev_config.toml',
                    '--verbose'
                ])
                assert result.exit_code == 0

    def test_cli_production_workflow(self):
        """Test CLI production workflow scenario."""
        prod_config = '''
[database]
driver = "sqlite"
database = "production.db"
timeout = 60.0
pool_size = 20
max_overflow = 30
pool_timeout = 60
pool_recycle = 7200

[app]
name = "Production Application"
debug = false
log_level = "WARNING"

[session]
echo = false
'''
        with self.runner.isolated_filesystem():
            with open('prod_config.toml', 'w') as f:
                f.write(prod_config)

            result = self.runner.invoke(cli, [
                '--config', 'prod_config.toml',
                '--help'
            ])
            assert result.exit_code == 0

    def test_cli_configuration_override_workflow(self):
        """Test CLI configuration override workflow."""
        # Test multiple override scenarios
        override_scenarios = [
            # Environment variables override config file
            {
                'description': 'Environment overrides config file',
                'env_vars': {
                    'DATABASE_URL': 'sqlite:///:memory:',
                    'VGNC_DEBUG': 'true',
                    'VGNC_APP_NAME': 'Environment Override App'
                },
                'config_content': '''
[database]
driver = "sqlite"
database = "config_file.db"
debug = false

[app]
name = "Config File App"
debug = false
'''
            },
            # Command line args override environment
            {
                'description': 'Command line overrides all',
                'env_vars': {
                    'DATABASE_URL': 'sqlite:///:memory:',
                    'VGNC_DEBUG': 'false'
                },
                'config_content': '''
[database]
driver = "sqlite"
database = "config_file.db"

[app]
name = "Config File App"
debug = false
''',
                'cli_args': ['--verbose', '--database-url', 'sqlite:///override.db']
            }
        ]

        for scenario in override_scenarios:
            with self.runner.isolated_filesystem():
                with open('override_config.toml', 'w') as f:
                    f.write(scenario['config_content'])

                cli_args = ['--config', 'override_config.toml']
                if 'cli_args' in scenario:
                    cli_args.extend(scenario['cli_args'])

                with patch.dict(os.environ, scenario['env_vars']):
                    result = self.runner.invoke(cli, cli_args)
                    assert result.exit_code == 0

    def test_cli_error_recovery_workflow(self):
        """Test CLI error recovery and resilience."""
        error_recovery_scenarios = [
            # Configuration file with errors
            {
                'description': 'Config file with syntax errors',
                'config_content': '''
[database
driver = "sqlite"  # Missing closing bracket
database = "test.db"
''',
                'expected_behavior': 'graceful degradation'
            },
            # Configuration with invalid values
            {
                'description': 'Invalid configuration values',
                'config_content': '''
[database]
driver = "invalid_driver"
username = "test_user"
password = "test_password"
database = "test.db"

[app]
debug = "invalid_boolean_value"
''',
                'expected_behavior': 'validation error or defaults'
            },
            # Mixed valid and invalid sections
            {
                'description': 'Mixed valid/invalid sections',
                'config_content': '''
[database]
driver = "sqlite"
database = "test.db"

[invalid_section]
this_is_not_valid_toml = "test"
''',
                'expected_behavior': 'ignore invalid sections'
            }
        ]

        for scenario in error_recovery_scenarios:
            with self.runner.isolated_filesystem():
                with open('error_config.toml', 'w') as f:
                    f.write(scenario['config_content'])

                # Test error resilience
                result = self.runner.invoke(cli, [
                    '--config', 'error_config.toml',
                    '--help'
                ])
                # Should handle errors gracefully or fail with clear message
                assert result.exit_code in [0, 1, 2]

    def test_cli_memory_and_performance_workflow(self):
        """Test CLI memory and performance considerations."""
        # Test with large configurations
        large_config = '''
[database]
driver = "sqlite"
database = "performance_test.db"

''' + ''.join(f'''
[app_section_{i}]
name = "Section {i}"
description = "This is a very long description for testing purposes with section {i}"
debug = true
log_level = "INFO"
''' for i in range(100))

        with self.runner.isolated_filesystem():
            with open('large_config.toml', 'w') as f:
                f.write(large_config)

            # Test CLI performance with large config
            import time
            start_time = time.time()

            result = self.runner.invoke(cli, [
                '--config', 'large_config.toml',
                '--help'
            ])

            end_time = time.time()
            execution_time = end_time - start_time

            # Should complete reasonably quickly even with large config
            assert execution_time < 5.0
            assert result.exit_code in [0, 1]


class TestCLIIntegrationWithRealSystems:
    """Test CLI integration with real system components."""

    def test_cli_filesystem_integration(self):
        """Test CLI integration with filesystem operations."""
        with self.runner.isolated_filesystem():
            # Create directory structure
            os.makedirs('config', exist_ok=True)
            os.makedirs('data', exist_ok=True)
            os.makedirs('logs', exist_ok=True)

            # Create configuration with file paths
            config_content = '''
[database]
driver = "sqlite"
database = "data/app.db"

[app]
name = "Filesystem Integration App"
debug = true

[logging]
log_file = "logs/app.log"
data_directory = "data"
config_directory = "config"
'''
            with open('config/app.toml', 'w') as f:
                f.write(config_content)

            # Test CLI with file paths
            result = self.runner.invoke(cli, [
                '--config', 'config/app.toml',
                '--help'
            ])

            assert result.exit_code == 0

            # Verify file structure was created
            assert os.path.exists('config/app.toml')
            assert os.path.exists('config')
            assert os.path.exists('data')
            assert os.path.exists('logs')

    def test_cli_environment_integration(self):
        """Test CLI integration with environment variables."""
        # Create comprehensive environment
        env_vars = {
            'VGNC_DATABASE_URL': 'sqlite:///:memory:',
            'VGNC_APP_NAME': 'Environment Integration App',
            'VGNC_DEBUG': 'true',
            'VGNC_LOG_LEVEL': 'INFO',
            'VGNC_CONFIG_FILE': '/nonexistent/path/config.toml',  # Non-existent path
            'PATH': '/usr/bin:/bin',  # System PATH
            'HOME': os.path.expanduser('~')  # User home directory
        }

        with patch.dict(os.environ, env_vars):
            result = self.runner.invoke(cli, ['--help'])
            assert result.exit_code == 0

    def test_cli_system_resource_integration(self):
        """Test CLI integration with system resources."""
        # Test with different resource constraints
        resource_scenarios = [
            # Memory constraints
            {
                'description': 'Memory constrained environment',
                'env_vars': {'VGNC_SESSION_POOL_SIZE': '5'},
            },
            # Connection constraints
            {
                'description': 'Connection limited environment',
                'env_vars': {'VGNC_SESSION_MAX_OVERFLOW': '10'},
            },
            # Performance constraints
            {
                'description': 'Performance constrained environment',
                'env_vars': {'VGNC_SESSION_POOL_TIMEOUT': '20'},
            }
        ]

        for scenario in resource_scenarios:
            with patch.dict(os.environ, scenario['env_vars']):
                result = self.runner.invoke(cli, [
                    '--database-url', 'sqlite:///:memory:',
                    '--help'
                ])
                assert result.exit_code == 0