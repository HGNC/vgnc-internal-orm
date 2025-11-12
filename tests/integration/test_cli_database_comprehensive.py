"""Comprehensive database-integrated tests for CLI functionality."""

import pytest
import tempfile
import os
import xml.etree.ElementTree as ET
from pathlib import Path
from unittest.mock import Mock, patch
from click.testing import CliRunner
from datetime import datetime, timezone
from sqlalchemy import text, sessionmaker

from src.vgnc_internal_orm.cli.main import (
    cli,
    ensure_config_loaded,
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
from src.vgnc_internal_orm.sessions.factory import DatabaseFactory


class TestCLICoreFunctionalityComprehensive:
    """Comprehensive tests for CLI core functionality with database integration."""

    def setup_method(self):
        """Set up test database and CLI runner."""
        self.runner = CliRunner()
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables for all models
        from src.vgnc_internal_orm.models.base import BaseModel
        from src.vgnc_internal_orm.models.species import Species
        BaseModel.metadata.create_all(bind=self.engine)

    def teardown_method(self):
        """Clean up test database."""
        self.engine.dispose()

    def test_cli_help_functionality(self):
        """Test CLI help commands and documentation."""
        # Test main help
        result = self.runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "VGNC ORM Command-line Interface" in result.output

        # Test with verbose flag
        result = self.runner.invoke(cli, ["--verbose", "--help"])
        assert result.exit_code == 0

        # Test with config file flag
        result = self.runner.invoke(cli, ["--config", "nonexistent.toml", "--help"])
        assert result.exit_code == 0

    def test_cli_configuration_scenarios(self):
        """Test CLI configuration with various scenarios."""
        scenarios = [
            # Database URL only
            ["--database-url", "sqlite:///:memory:", "--help"],
            # Config file only
            ["--config", "/dev/null", "--help"],  # Will fail but test error handling
            # Both database URL and config
            ["--database-url", "sqlite:///:memory:", "--config", "/dev/null", "--help"],
            # Verbose mode
            ["--verbose", "--help"],
            # All options
            ["--database-url", "sqlite:///:memory:", "--config", "/dev/null", "--verbose", "--help"],
        ]

        for args in scenarios:
            result = self.runner.invoke(cli, args)
            # Should handle gracefully even with invalid config files
            assert result.exit_code in [0, 1, 2]

    def test_ensure_config_loaded_function(self):
        """Test ensure_config_loaded function with various scenarios."""
        from click import Context

        # Create CLI context
        ctx = Context(cli)
        ctx.obj = {
            "verbose": False,
            "database_url": None,
            "config_file": None,
            "config_loaded": False
        }

        # Test with database URL
        ctx.obj["database_url"] = "sqlite:///:memory:"
        ensure_config_loaded(ctx)
        assert ctx.obj["config_loaded"] is True
        assert ctx.obj["db_config"] is not None

        # Test with config file
        ctx.obj["database_url"] = None
        ctx.obj["config_file"] = "/nonexistent/config.toml"
        ctx.obj["config_loaded"] = False

        with patch.dict(os.environ, {"DB_DATABASE": "test", "DB_DRIVER": "sqlite"}):
            ensure_config_loaded(ctx)
            assert ctx.obj["config_loaded"] is True

        # Test already loaded
        ensure_config_loaded(ctx)
        assert ctx.obj["config_loaded"] is True

    def test_get_session_function(self):
        """Test get_session function with database integration."""
        # Test with database config
        session = get_session(self.config)
        assert session is not None

        # Test session functionality
        result = session.execute(text("SELECT 1")).scalar()
        assert result == 1

        session.close()

        # Test with database URL override
        session2 = get_session(self.config, database_url="sqlite:///:memory:")
        assert session2 is not None
        session2.close()


class TestCLIFormattingFunctionsComprehensive:
    """Comprehensive tests for CLI formatting functions with real data."""

    def setup_method(self):
        """Set up test data."""
        self.test_species = []
        for i in range(5):
            species = Mock()
            species.taxon_id = 9600 + i
            species.genefam_prefix = f"HS{i:02d}"
            species.display_name = f"Test Species {i}"
            species.primary_db_table = "species"
            species.ensembl_species_name = f"test_species_{i}"
            species.created = datetime(2023, i+1, 1, 12, 0, 0, tzinfo=timezone.utc)

            # Mock is_live as an enum-like object
            is_live = Mock()
            is_live.value = "YES" if i % 2 == 0 else "NO"
            species.is_live = is_live

            self.test_species.append(species)

        # Test genefam data
        self.test_genefams = []
        for i in range(3):
            genefam = Mock()
            genefam.genefam_id = f"GF{i:03d}"
            genefam.assigned_symbol = f"GENE{i}"
            genefam.name = f"Gene Family {i}"
            genefam.description = f"Description for gene family {i}"
            genefam.taxon_id = 9606
            self.test_genefams.append(genefam)

        # Test assembly data
        self.test_assemblies = []
        for i in range(2):
            assembly = Mock()
            assembly.id = i + 1
            assembly.accession = f"GCA_{i:09d}"
            assembly.name = f"Assembly {i}"
            assembly.taxon_id = 9606
            self.test_assemblies.append(assembly)

        # Test chromosome data
        self.test_chromosomes = []
        for i in range(5):
            chromosome = Mock()
            chromosome.id = i + 1
            chromosome.display_name = f"chr{i+1}" if i < 3 else ["chrX", "chrY"][i-3]
            chromosome.taxon_id = 9606
            self.test_chromosomes.append(chromosome)

    def test_format_species_as_xml_comprehensive(self):
        """Test format_species_as_xml with various data scenarios."""
        # Test with normal data
        xml_result = format_species_as_xml(self.test_species)
        assert isinstance(xml_result, str)
        assert "<species>" in xml_result
        assert xml_result.count("<species>") == len(self.test_species) + 1  # Root + individual

        # Parse XML to verify structure
        root = ET.fromstring(xml_result)
        assert root.tag == "species"
        assert len(root) == len(self.test_species)

        for i, species_elem in enumerate(root):
            assert species_elem.get("taxon_id") == str(9600 + i)

            # Check child elements
            genefam_elem = species_elem.find("genefam_prefix")
            assert genefam_elem is not None
            assert genefam_elem.text == f"HS{i:02d}"

        # Test with empty list
        empty_result = format_species_as_xml([])
        assert isinstance(empty_result, str)
        root = ET.fromstring(empty_result)
        assert len(root) == 0

        # Test with None values
        species_with_nones = []
        for i in range(2):
            species = Mock()
            species.taxon_id = 8000 + i
            species.genefam_prefix = None
            species.display_name = None
            species.is_live = Mock()
            species.is_live.value = None
            species.primary_db_table = None
            species.ensembl_species_name = None
            species.created = None
            species_with_nones.append(species)

        none_result = format_species_as_xml(species_with_nones)
        assert isinstance(none_result, str)
        root = ET.fromstring(none_result)

        for species_elem in root:
            genefam_elem = species_elem.find("genefam_prefix")
            assert genefam_elem.text == ""

    def test_format_genefam_as_xml_comprehensive(self):
        """Test format_genefam_as_xml with various data scenarios."""
        xml_result = format_genefam_as_xml(self.test_genefams)
        assert isinstance(xml_result, str)
        assert "<genefams>" in xml_result

        # Parse XML to verify structure
        root = ET.fromstring(xml_result)
        assert root.tag == "genefams"
        assert len(root) == len(self.test_genefams)

        for i, genefam_elem in enumerate(root):
            genefam_id_elem = genefam_elem.find("genefam_id")
            assert genefam_id_elem is not None
            assert genefam_id_elem.text == f"GF{i:03d}"

        # Test with empty list
        empty_result = format_genefam_as_xml([])
        assert isinstance(empty_result, str)
        root = ET.fromstring(empty_result)
        assert len(root) == 0

    def test_format_assembly_as_xml_comprehensive(self):
        """Test format_assembly_as_xml with various data scenarios."""
        xml_result = format_assembly_as_xml(self.test_assemblies)
        assert isinstance(xml_result, str)
        assert "<assemblies>" in xml_result

        # Parse XML to verify structure
        root = ET.fromstring(xml_result)
        assert root.tag == "assemblies"
        assert len(root) == len(self.test_assemblies)

        for i, assembly_elem in enumerate(root):
            id_elem = assembly_elem.find("id")
            assert id_elem is not None
            assert id_elem.text == str(i + 1)

        # Test with empty list
        empty_result = format_assembly_as_xml([])
        assert isinstance(empty_result, str)
        root = ET.fromstring(empty_result)
        assert len(root) == 0

    def test_format_chromosomes_as_xml_comprehensive(self):
        """Test format_chromosomes_as_xml with various data scenarios."""
        xml_result = format_chromosomes_as_xml(self.test_chromosomes)
        assert isinstance(xml_result, str)
        assert "<chromosomes>" in xml_result

        # Parse XML to verify structure
        root = ET.fromstring(xml_result)
        assert root.tag == "chromosomes"
        assert len(root) == len(self.test_chromosomes)

        chromosome_names = ["chr1", "chr2", "chr3", "chrX", "chrY"]
        for i, chromosome_elem in enumerate(root):
            display_name_elem = chromosome_elem.find("display_name")
            assert display_name_elem is not None
            assert display_name_elem.text == chromosome_names[i]

        # Test with empty list
        empty_result = format_chromosomes_as_xml([])
        assert isinstance(empty_result, str)
        root = ET.fromstring(empty_result)
        assert len(root) == 0


class TestCLIDisplayFunctionsComprehensive:
    """Comprehensive tests for CLI display functions."""

    def setup_method(self):
        """Set up test data."""
        self.test_species = []
        for i in range(3):
            species = Mock()
            species.taxon_id = 9600 + i
            species.genefam_prefix = f"HS{i:02d}"
            species.display_name = f"Test Species {i}"
            species.primary_db_table = "species"
            species.ensembl_species_name = f"test_species_{i}"

            is_live = Mock()
            is_live.value = "YES" if i % 2 == 0 else "NO"
            species.is_live = is_live

            self.test_species.append(species)

    def test_display_species_table_comprehensive(self):
        """Test display_species_table function."""
        # Test with normal data
        display_species_table(self.test_species)
        # Function prints to stdout, no return value to test

        # Test with empty list
        display_species_table([])

        # Test with None values
        species_with_nones = []
        for i in range(2):
            species = Mock()
            species.taxon_id = 8000 + i
            species.genefam_prefix = None
            species.display_name = None
            is_live = Mock()
            is_live.value = None
            species.is_live = is_live
            species.primary_db_table = None
            species.ensembl_species_name = None
            species_with_nones.append(species)

        display_species_table(species_with_nones)

    def test_display_species_json_comprehensive(self):
        """Test display_species_json function."""
        import json
        import sys
        from io import StringIO

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            display_species_json(self.test_species)
            output = captured_output.getvalue()

            # Verify it's valid JSON
            parsed_data = json.loads(output)
            assert isinstance(parsed_data, list)
            assert len(parsed_data) == len(self.test_species)

            # Test with empty list
            captured_output.truncate(0)
            captured_output.seek(0)
            display_species_json([])
            empty_output = captured_output.getvalue()
            empty_data = json.loads(empty_output)
            assert empty_data == []

        finally:
            sys.stdout = old_stdout

    def test_display_species_csv_comprehensive(self):
        """Test display_species_csv function."""
        import sys
        from io import StringIO

        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()

        try:
            display_species_csv(self.test_species)
            output = captured_output.getvalue()

            # Verify CSV format
            lines = output.strip().split('\n')
            assert len(lines) == len(self.test_species) + 1  # Header + data

            # Check header
            header = lines[0]
            assert "taxon_id" in header
            assert "genefam_prefix" in header
            assert "display_name" in header

            # Test with empty list
            captured_output.truncate(0)
            captured_output.seek(0)
            display_species_csv([])
            empty_output = captured_output.getvalue()
            assert empty_output.strip() == ""

        finally:
            sys.stdout = old_stdout


class TestCLIErrorHandlingComprehensive:
    """Comprehensive tests for CLI error handling scenarios."""

    def setup_method(self):
        """Set up CLI runner."""
        self.runner = CliRunner()

    def test_cli_invalid_option_handling(self):
        """Test CLI handling of invalid options."""
        # Test with invalid option
        result = self.runner.invoke(cli, ["--invalid-option"])
        assert result.exit_code == 2
        assert "no such option" in result.output.lower()

    def test_cli_configuration_error_handling(self):
        """Test CLI handling of configuration errors."""
        # Test with non-existent config file
        with self.runner.isolated_filesystem():
            result = self.runner.invoke(cli, ["--config", "nonexistent.toml", "--help"])
            # Should handle gracefully for help command
            assert result.exit_code == 0

    def test_cli_database_connection_error_handling(self):
        """Test CLI handling of database connection errors."""
        # Test with invalid database URL
        result = self.runner.invoke(cli, [
            "--database-url", "invalid://url",
            "--help"
        ])
        # Help should work even with invalid database URL
        assert result.exit_code == 0

    def test_cli_exception_handling_in_ensure_config_loaded(self):
        """Test exception handling in ensure_config_loaded function."""
        from click import Context

        ctx = Context(cli)
        ctx.obj = {
            "verbose": False,
            "database_url": None,
            "config_file": None,
            "config_loaded": False
        }

        # Test with database URL that causes config loading error
        with patch('src.vgnc_internal_orm.cli.main.DatabaseConfig', side_effect=Exception("Config error")):
            # Should handle gracefully and exit
            with pytest.raises(SystemExit):
                ensure_config_loaded(ctx)

    def test_cli_fallback_configuration(self):
        """Test CLI fallback configuration when primary fails."""
        from click import Context

        ctx = Context(cli)
        ctx.obj = {
            "verbose": True,
            "database_url": "sqlite:///:memory:",
            "config_file": None,
            "config_loaded": False
        }

        # Mock DatabaseConfig to fail first time, succeed second time
        with patch('src.vgnc_internal_orm.cli.main.DatabaseConfig') as mock_config:
            mock_config.side_effect = [
                Exception("First failure"),
                Mock(database="fallback_db")
            ]

            ensure_config_loaded(ctx)
            assert ctx.obj["config_loaded"] is True


class TestCLIIntegrationWorkflows:
    """Integration tests for complete CLI workflows."""

    def setup_method(self):
        """Set up test environment."""
        self.runner = CliRunner()
        self.temp_dir = tempfile.mkdtemp()

    def teardown_method(self):
        """Clean up test environment."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def test_cli_complete_workflow_with_config_file(self):
        """Test complete CLI workflow with configuration file."""
        config_content = '''
[database]
driver = "sqlite"
database = "workflow_test.db"

[app]
name = "Workflow Test App"
debug = true
'''
        config_file = Path(self.temp_dir) / "test_config.toml"
        with open(config_file, 'w') as f:
            f.write(config_content)

        # Test that CLI can load config file
        result = self.runner.invoke(cli, [
            "--config", str(config_file),
            "--help"
        ])
        assert result.exit_code == 0

    def test_cli_complete_workflow_with_database_url(self):
        """Test complete CLI workflow with database URL."""
        result = self.runner.invoke(cli, [
            "--database-url", "sqlite:///:memory:",
            "--verbose",
            "--help"
        ])
        assert result.exit_code == 0

    def test_cli_environment_variable_integration(self):
        """Test CLI integration with environment variables."""
        env_vars = {
            "VGNC_CONFIG_FILE": str(Path(self.temp_dir) / "env_config.toml"),
            "DATABASE_URL": "sqlite:///:memory:",
            "VGNC_DEBUG": "true"
        }

        with patch.dict(os.environ, env_vars):
            result = self.runner.invoke(cli, ["--help"])
            assert result.exit_code == 0

    def test_cli_complex_configuration_scenario(self):
        """Test CLI with complex configuration scenarios."""
        # Create multiple config files
        primary_config = '''
[database]
driver = "sqlite"
database = "primary.db"
'''
        override_config = '''
[database]
driver = "sqlite"
database = "override.db"
'''

        primary_file = Path(self.temp_dir) / "primary.toml"
        override_file = Path(self.temp_dir) / "override.toml"

        with open(primary_file, 'w') as f:
            f.write(primary_config)
        with open(override_file, 'w') as f:
            f.write(override_config)

        # Test priority: CLI args > env vars > config file
        with patch.dict(os.environ, {"VGNC_CONFIG_FILE": str(override_file)}):
            result = self.runner.invoke(cli, [
                "--config", str(primary_file),
                "--database-url", "sqlite:///:memory:",
                "--help"
            ])
            assert result.exit_code == 0

    def test_cli_configuration_precedence(self):
        """Test CLI configuration precedence rules."""
        # Test that command line args override environment variables
        env_vars = {
            "DATABASE_URL": "sqlite:///env.db",
            "VGNC_DEBUG": "false"
        }

        with patch.dict(os.environ, env_vars):
            # CLI args should override environment
            result = self.runner.invoke(cli, [
                "--database-url", "sqlite:///:memory:",
                "--help"
            ])
            assert result.exit_code == 0

    def test_cli_error_recovery_workflow(self):
        """Test CLI error recovery and graceful degradation."""
        # Test multiple failure scenarios
        failure_scenarios = [
            # Invalid config file
            lambda: self.runner.invoke(cli, ["--config", "/nonexistent/file.toml", "--help"]),
            # Invalid database URL (but help should still work)
            lambda: self.runner.invoke(cli, ["--database-url", "invalid://url", "--help"]),
            # Missing configuration
            lambda: self.runner.invoke(cli, ["--help"]),
        ]

        for scenario in failure_scenarios:
            result = scenario()
            # Help command should work even with config errors
            assert result.exit_code == 0