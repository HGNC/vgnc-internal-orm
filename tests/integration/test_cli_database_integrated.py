"""Database-integrated tests for CLI following sessions/factory.py success pattern."""

import tempfile
import os
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from click.testing import CliRunner

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


class TestCLIRealConfigIntegration:
    """Database-integrated tests for CLI with real configuration."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_with_real_sqlite_config(self):
        """Test CLI with real SQLite configuration."""
        config_content = """
[database]
driver = "sqlite"
database = "test.db"

[app]
name = "Test CLI App"
debug = true
"""
        with self.runner.isolated_filesystem():
            with open('config.toml', 'w') as f:
                f.write(config_content)

            result = self.runner.invoke(cli, [
                '--config', 'config.toml',
                '--help'
            ])

            assert result.exit_code == 0
            assert 'VGNC ORM Command-line Interface' in result.output

    def test_cli_with_real_mysql_config(self):
        """Test CLI with real MySQL configuration."""
        config_content = """
[database]
driver = "mysql"
username = "test_user"
password = "test_password"
database = "test_db"
host = "localhost"
port = 3306

[app]
name = "MySQL CLI App"
"""
        with self.runner.isolated_filesystem():
            with open('config.toml', 'w') as f:
                f.write(config_content)

            result = self.runner.invoke(cli, [
                '--config', 'config.toml',
                '--help'
            ])

            assert result.exit_code == 0

    def test_ensure_config_loaded_with_real_objects(self):
        """Test ensure_config_loaded with real database configuration objects."""
        from click import Context

        # Create real DatabaseConfig objects
        sqlite_config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )

        mysql_config = DatabaseConfig(
            username="test_user",
            password="test_password",
            database="test_db",
            driver=DatabaseDriver.MYSQL,
            _env_file=None
        )

        # Test with SQLite configuration
        ctx = Context(cli)
        ctx.obj = {
            "config_loaded": False,
            "database_url": "sqlite:///:memory:"
        }

        # This should create a real configuration
        ensure_config_loaded(ctx)
        assert ctx.obj["config_loaded"] is True
        assert "db_config" in ctx.obj

        # Test with MySQL configuration
        ctx_mysql = Context(cli)
        ctx_mysql.obj = {
            "config_loaded": False,
            "database_url": None
        }

        # Mock environment variables for MySQL
        with patch.dict(os.environ, {
            "DB_DATABASE": "test_db",
            "DB_USERNAME": "test_user",
            "DB_PASSWORD": "test_password",
            "DB_DRIVER": "mysql"
        }):
            ensure_config_loaded(ctx_mysql)
            assert ctx_mysql.obj["config_loaded"] is True
            assert "db_config" in ctx_mysql.obj


class TestCLIXMLFormattingWithRealData:
    """Test CLI XML formatting functions with realistic data structures."""

    def test_format_species_with_complete_data(self):
        """Test format_species_as_xml with complete species data."""
        # Create realistic mock species
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = "HSA"
        mock_species.display_name = "Human"
        mock_species.is_live = Mock()
        mock_species.is_live.value = "YES"
        mock_species.primary_db_table = "species"
        mock_species.ensembl_species_name = "Homo sapiens"
        mock_species.created = None
        mock_species.updated = None

        result = format_species_as_xml([mock_species])

        # Verify XML structure and content
        assert isinstance(result, str)
        assert '<species>' in result
        assert '</species>' in result
        assert 'taxon_id="9606"' in result
        assert '<genefam_prefix>HSA</genefam_prefix>' in result
        assert '<display_name>Human</display_name>' in result
        assert '<is_live><value>YES</value></is_live>' in result

    def test_format_genefam_with_complete_data(self):
        """Test format_genefam_as_xml with complete genefam data."""
        mock_genefam = Mock()
        mock_genefam.genefam_id = 1101
        mock_genefam.taxon_id = 9606
        mock_genefam.assigned_id = "HGNC:1101"
        mock_genefam.assigned_symbol = "BRCA1"
        mock_genefam.assigned_name = "BRCA1 DNA repair associated"
        mock_genefam.assigned_locus = "17q21.31"
        mock_genefam.assigned_type = "protein coding"
        mock_genefam.status_id = 1
        mock_genefam.editor_id = 1

        result = format_genefam_as_xml([mock_genefam])

        # Verify XML structure and content
        assert isinstance(result, str)
        assert '<genefams>' in result
        assert '</genefams>' in result
        assert 'genefam_id="1101"' in result
        assert 'taxon_id="9606"' in result
        assert '<assigned_id>HGNC:1101</assigned_id>' in result
        assert '<assigned_symbol>BRCA1</assigned_symbol>' in result

    def test_format_assembly_with_complete_data(self):
        """Test format_assembly_as_xml with complete assembly data."""
        mock_assembly = Mock()
        mock_assembly.id = 1
        mock_assembly.taxon_id = 9606
        mock_assembly.source = "Ensembl"
        mock_assembly.name = "GRCh38"
        mock_assembly.accession = "GCA_000001405.28"
        mock_assembly.genbank_assembly_accession = "GCA_000001405.28"
        mock_assembly.refseq_assembly_accession = "GCF_000001405.38"
        mock_assembly.ensembl_version = 109

        result = format_assembly_as_xml([mock_assembly])

        # Verify XML structure and content
        assert isinstance(result, str)
        assert '<assemblies>' in result
        assert '</assemblies>' in result
        assert 'id="1"' in result
        assert 'taxon_id="9606"' in result
        assert '<source>Ensembl</source>' in result
        assert '<name>GRCh38</name>' in result

    def test_format_chromosomes_with_complete_data(self):
        """Test format_chromosomes_as_xml with complete chromosomes data."""
        mock_chromosomes = Mock()
        mock_chromosomes.id = 1
        mock_chromosomes.taxon_id = 9606
        mock_chromosomes.name = "1"
        mock_chromosomes.length = 249250621
        mock_chromosomes.accession = "NC_000001.11"
        mock_chromosomes.refseq_accession = "NC_000001.11"
        mock_chromosomes.ensembl_name = "1"
        mock_chromosomes.ucsc_name = "chr1"

        result = format_chromosomes_as_xml([mock_chromosomes])

        # Verify XML structure and content
        assert isinstance(result, str)
        assert '<chromosomes>' in result
        assert '</chromosomes>' in result
        assert 'id="1"' in result
        assert 'taxon_id="9606"' in result
        assert '<name>1</name>' in result

    def test_format_functions_with_multiple_species(self):
        """Test formatting functions with multiple species."""
        species1 = Mock()
        species1.taxon_id = 9606
        species1.display_name = "Human"
        species1.genefam_prefix = "HSA"

        species2 = Mock()
        species2.taxon_id = 10090
        species2.display_name = "Mouse"
        species2.genefam_prefix = "MMU"

        result = format_species_as_xml([species1, species2])

        assert 'taxon_id="9606"' in result
        assert 'taxon_id="10090"' in result
        assert "<display_name>Human</display_name>" in result
        assert "<display_name>Mouse</display_name>" in result
        assert "<genefam_prefix>HSA</genefam_prefix>" in result
        assert "<genefam_prefix>MMU</genefam_prefix>" in result

    def test_format_functions_with_none_values(self):
        """Test formatting functions handle None values gracefully."""
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = None
        mock_species.display_name = None
        mock_species.is_live = None
        mock_species.primary_db_table = None
        mock_species.ensembl_species_name = None
        mock_species.created = None

        result = format_species_as_xml([mock_species])

        # Should handle None values gracefully
        assert isinstance(result, str)
        assert 'taxon_id="9606"' in result
        assert '<genefam_prefix></genefam_prefix>' in result  # None becomes empty element


class TestCLIDisplayWithRealData:
    """Test CLI display functions with realistic data structures."""

    def test_display_species_table_with_complete_data(self):
        """Test display_species_table with complete species data."""
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = "HSA"
        mock_species.display_name = "Human"
        mock_species.is_live = Mock()
        mock_species.is_live.value = "YES"
        mock_species.primary_db_table = "species"
        mock_species.ensembl_species_name = "Homo sapiens"

        # This should execute the real display function without errors
        display_species_table([mock_species])

    def test_display_species_json_with_complete_data(self):
        """Test display_species_json with complete species data."""
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = "HSA"
        mock_species.display_name = "Human"
        mock_species.ensembl_species_name = "Homo sapiens"

        # This should execute the real JSON display function
        display_species_json([mock_species])

    def test_display_species_csv_with_complete_data(self):
        """Test display_species_csv with complete species data."""
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = "HSA"
        mock_species.display_name = "Human"
        mock_species.primary_db_table = "species"

        # This should execute the real CSV display function
        display_species_csv([mock_species])

    def test_display_functions_with_multiple_items(self):
        """Test display functions with multiple items."""
        species1 = Mock()
        species1.taxon_id = 9606
        species1.display_name = "Human"
        species1.genefam_prefix = "HSA"

        species2 = Mock()
        species2.taxon_id = 10090
        species2.display_name = "Mouse"
        species2.genefam_prefix = "MMU"

        # These should handle multiple items
        display_species_table([species1, species2])
        display_species_json([species1, species2])
        display_species_csv([species1, species2])


class TestGetSessionWithRealConfig:
    """Test get_session function with real configuration objects."""

    def test_get_session_sqlite_memory(self):
        """Test get_session with SQLite in-memory database."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )

        # This should create a real SQLAlchemy session
        session = get_session(config, "sqlite:///:memory:")

        assert session is not None
        assert hasattr(session, 'execute')
        assert hasattr(session, 'commit')
        assert hasattr(session, 'rollback')
        assert hasattr(session, 'close')

        # Test session methods work
        result = session.execute("SELECT 1")
        assert result is not None

        session.close()

    def test_get_session_sqlite_file(self):
        """Test get_session with SQLite file database."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test.db")
            session = get_session(config, f"sqlite:///{db_path}")

            assert session is not None

            # Test basic database operations
            session.execute("CREATE TABLE test (id INTEGER)")
            session.commit()

            result = session.execute("SELECT name FROM sqlite_master WHERE type='table'")
            tables = result.fetchall()
            assert len(tables) > 0

            session.close()

    def test_get_session_with_different_database_urls(self):
        """Test get_session with different database URLs."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database="test.db",
            _env_file=None
        )

        # Test with different URL formats
        session1 = get_session(config, "sqlite:///:memory:")
        session2 = get_session(config, "sqlite:///tmp/test.db")
        session3 = get_session(config, "sqlite:///file::memory:?cache=shared")

        assert session1 is not None
        assert session2 is not None
        assert session3 is not None

        # Clean up
        session1.close()
        session2.close()
        session3.close()


class TestCLIEnvironmentVariableIntegration:
    """Test CLI integration with environment variables."""

    def test_cli_with_environment_database_url(self):
        """Test CLI with database URL from environment."""
        with patch.dict(os.environ, {
            "DATABASE_URL": "sqlite:///:memory:"
        }):
            result = self.runner.invoke(cli, [
                '--help'
            ])

            assert result.exit_code == 0

    def test_cli_with_environment_config_file(self):
        """Test CLI with config file path from environment."""
        config_content = """
[database]
driver = "sqlite"
database = "test.db"

[app]
name = "Environment Test App"
"""
        with self.runner.isolated_filesystem():
            with open('env_config.toml', 'w') as f:
                f.write(config_content)

            with patch.dict(os.environ, {
                "VGNC_CONFIG_FILE": "env_config.toml"
            }):
                result = self.runner.invoke(cli, [
                    '--help'
                ])

                assert result.exit_code == 0

    def test_cli_verbose_flag_integration(self):
        """Test CLI verbose flag with real configuration."""
        result = self.runner.invoke(cli, [
            '--verbose',
            '--database-url', 'sqlite:///:memory:',
            '--help'
        ])

        assert result.exit_code == 0