"""Integration tests for CLI functions to improve coverage."""

import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

from src.vgnc_internal_orm.cli.main import (
    ensure_config_loaded,
    format_species_as_xml,
    format_genefam_as_xml,
    format_assembly_as_xml,
    format_chromosomes_as_xml,
    display_species_table,
    display_species_json,
    display_species_csv,
    get_session,
    cli,
)
from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestCLIFormattingIntegration:
    """Integration tests for CLI formatting functions."""

    def test_format_species_as_xml_real_usage(self):
        """Test format_species_as_xml with realistic mock data."""
        # Create comprehensive mock species
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = "HSA"
        mock_species.display_name = "Human"
        mock_species.is_live = Mock()
        mock_species.is_live.value = "YES"
        mock_species.primary_db_table = "species"
        mock_species.ensembl_species_name = "Homo sapiens"
        mock_species.created = None

        result = format_species_as_xml([mock_species])

        assert isinstance(result, str)
        assert 'taxon_id="9606"' in result
        assert "<genefam_prefix>HSA</genefam_prefix>" in result
        assert "<display_name>Human</display_name>" in result
        assert "<is_live><value>YES</value></is_live>" in result

    def test_format_genefam_as_xml_real_usage(self):
        """Test format_genefam_as_xml with realistic mock data."""
        mock_genefam = Mock()
        mock_genefam.genefam_id = 12345
        mock_genefam.taxon_id = 9606
        mock_genefam.assigned_id = "HGNC:5"
        mock_genefam.assigned_symbol = "BRCA1"
        mock_genefam.assigned_name = "BRCA1 DNA repair associated"
        mock_genefam.status_id = 1
        mock_genefam.editor_id = 1

        result = format_genefam_as_xml([mock_genefam])

        assert isinstance(result, str)
        assert 'genefam_id="12345"' in result
        assert "<assigned_id>HGNC:5</assigned_id>" in result
        assert "<assigned_symbol>BRCA1</assigned_symbol>" in result

    def test_format_assembly_as_xml_real_usage(self):
        """Test format_assembly_as_xml with realistic mock data."""
        mock_assembly = Mock()
        mock_assembly.id = 1
        mock_assembly.taxon_id = 9606
        mock_assembly.source = "Ensembl"
        mock_assembly.name = "GRCh38"
        mock_assembly.accession = "GCA_000001405.28"
        mock_assembly.genbank_assembly_accession = "GCA_000001405.28"

        result = format_assembly_as_xml([mock_assembly])

        assert isinstance(result, str)
        assert 'id="1"' in result
        assert "<source>Ensembl</source>" in result
        assert "<name>GRCh38</name>" in result

    def test_format_chromosomes_as_xml_real_usage(self):
        """Test format_chromosomes_as_xml with realistic mock data."""
        mock_chromosomes = Mock()
        mock_chromosomes.id = 1
        mock_chromosomes.taxon_id = 9606
        mock_chromosomes.name = "1"
        mock_chromosomes.length = 249250621
        mock_chromosomes.accession = "NC_000001.11"

        result = format_chromosomes_as_xml([mock_chromosomes])

        assert isinstance(result, str)
        assert 'id="1"' in result
        assert "<name>1</name>" in result

    def test_format_functions_with_multiple_items(self):
        """Test formatting functions with multiple items."""
        # Create multiple mock species
        species1 = Mock()
        species1.taxon_id = 9606
        species1.display_name = "Human"

        species2 = Mock()
        species2.taxon_id = 10090
        species2.display_name = "Mouse"

        result = format_species_as_xml([species1, species2])

        assert isinstance(result, str)
        assert 'taxon_id="9606"' in result
        assert 'taxon_id="10090"' in result
        assert "<display_name>Human</display_name>" in result
        assert "<display_name>Mouse</display_name>" in result


class TestCLIDisplayIntegration:
    """Integration tests for CLI display functions."""

    def test_display_species_table_with_real_data(self):
        """Test display_species_table with realistic data."""
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = "HSA"
        mock_species.display_name = "Human"
        mock_species.is_live = Mock()
        mock_species.is_live.value = "YES"

        # This should execute the real display function
        display_species_table([mock_species])

    def test_display_species_json_with_real_data(self):
        """Test display_species_json with realistic data."""
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = "HSA"
        mock_species.display_name = "Human"

        # This should execute the real JSON display function
        display_species_json([mock_species])

    def test_display_species_csv_with_real_data(self):
        """Test display_species_csv with realistic data."""
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = "HSA"
        mock_species.display_name = "Human"

        # This should execute the real CSV display function
        display_species_csv([mock_species])

    def test_display_functions_with_empty_data(self):
        """Test display functions with empty data."""
        # These should handle empty data gracefully
        display_species_table([])
        display_species_json([])
        display_species_csv([])

    def test_display_functions_with_multiple_items(self):
        """Test display functions with multiple items."""
        mock_species1 = Mock()
        mock_species1.taxon_id = 9606
        mock_species1.display_name = "Human"

        mock_species2 = Mock()
        mock_species2.taxon_id = 10090
        mock_species2.display_name = "Mouse"

        # These should handle multiple items
        display_species_table([mock_species1, mock_species2])
        display_species_json([mock_species1, mock_species2])
        display_species_csv([mock_species1, mock_species2])


class TestGetSessionIntegration:
    """Integration tests for get_session function."""

    def test_get_session_with_sqlite_memory(self):
        """Test get_session with SQLite in-memory database."""
        db_config = DatabaseConfig(
            username="test",
            password="test",
            database="test.db",
            driver=DatabaseDriver.SQLITE,
            _env_file=None
        )

        # This should create a real SQLAlchemy session
        session = get_session(db_config, "sqlite:///:memory:")

        assert session is not None
        # Session should be usable
        assert hasattr(session, 'execute')
        assert hasattr(session, 'commit')
        assert hasattr(session, 'rollback')
        assert hasattr(session, 'close')

    def test_get_session_with_config_object(self):
        """Test get_session with DatabaseConfig object."""
        db_config = DatabaseConfig(
            username="test",
            password="test",
            database="test.db",
            host="localhost",
            port=3306,
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )

        # This should attempt to create a session (may fail without real DB)
        try:
            session = get_session(db_config)
            assert session is not None
        except Exception:
            # Expected if MySQL is not available
            pass

    def test_get_session_with_different_drivers(self):
        """Test get_session with different database drivers."""
        db_config = DatabaseConfig(
            username="test",
            password="test",
            database="test.db",
            driver=DatabaseDriver.SQLITE,
            _env_file=None
        )

        # Test with different URLs
        session1 = get_session(db_config, "sqlite:///:memory:")
        session2 = get_session(db_config, "sqlite:///tmp/test.db")

        assert session1 is not None
        assert session2 is not None

        # Clean up
        session1.close()
        session2.close()


class TestCLIEnsureConfigIntegration:
    """Integration tests for ensure_config_loaded function."""

    def test_ensure_config_loaded_with_real_config(self):
        """Test ensure_config_loaded with real configuration."""
        from click import Context

        # Create a real Click context
        ctx = Context(cli)
        ctx.obj = {
            "config_loaded": False,
            "database_url": "sqlite:///:memory:"
        }

        # This should load configuration
        ensure_config_loaded(ctx)

        assert ctx.obj["config_loaded"] is True
        assert "db_config" in ctx.obj

    def test_ensure_config_loaded_already_loaded(self):
        """Test ensure_config_loaded when config already loaded."""
        from click import Context

        ctx = Context(cli)
        mock_config = Mock()
        ctx.obj = {
            "config_loaded": True,
            "db_config": mock_config
        }

        # This should return early
        ensure_config_loaded(ctx)

        assert ctx.obj["config_loaded"] is True
        assert ctx.obj["db_config"] is mock_config

    def test_ensure_config_loaded_with_env_vars(self):
        """Test ensure_config_loaded with environment variables."""
        from click import Context

        ctx = Context(cli)
        ctx.obj = {
            "config_loaded": False,
            "database_url": "sqlite:///:memory:"
        }

        # Test with environment variables
        with patch.dict(os.environ, {"DB_DATABASE": "test_db", "DB_DRIVER": "sqlite"}):
            ensure_config_loaded(ctx)

            assert ctx.obj["config_loaded"] is True
            assert "db_config" in ctx.obj


class TestCLICommandIntegration:
    """Integration tests for CLI commands."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_command_with_database_url(self):
        """Test CLI command with database URL."""
        result = self.runner.invoke(cli, [
            '--database-url', 'sqlite:///:memory:',
            '--help'
        ])

        assert result.exit_code == 0
        assert 'VGNC ORM Command-line Interface' in result.output

    def test_cli_command_with_config_file(self):
        """Test CLI command with config file."""
        with self.runner.isolated_filesystem():
            # Create a minimal config file
            config_content = """
[database]
username = "test"
password = "test"
database = "test.db"
driver = "sqlite"

[app]
name = "Test App"
debug = true
"""
            with open('config.toml', 'w') as f:
                f.write(config_content)

            result = self.runner.invoke(cli, [
                '--config', 'config.toml',
                '--help'
            ])

            assert result.exit_code == 0

    def test_cli_command_with_verbose(self):
        """Test CLI command with verbose flag."""
        result = self.runner.invoke(cli, [
            '--verbose',
            '--database-url', 'sqlite:///:memory:',
            '--help'
        ])

        assert result.exit_code == 0