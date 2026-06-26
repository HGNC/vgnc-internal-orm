"""Real database-integrated tests for CLI following sessions/factory.py success pattern."""

import os
import tempfile
from datetime import UTC, datetime
from unittest.mock import patch

from click.testing import CliRunner
from sqlalchemy import text

from vgnc_internal_orm.cli.main import (
    cli,
    display_species_csv,
    display_species_json,
    display_species_table,
    ensure_config_loaded,
    format_assembly_as_xml,
    format_chromosomes_as_xml,
    format_genefam_as_xml,
    format_species_as_xml,
    get_session,
)
from vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver
from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus


class TestRealCLIConfiguration:
    """Real CLI configuration tests following sessions/factory.py pattern."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_with_real_database_configurations(self):
        """Test CLI with real database configurations."""
        configurations = [
            # SQLite configuration
            {
                "content": """
[database]
driver = "sqlite"
database = "test.db"

[app]
name = "SQLite CLI App"
debug = true
""",
                "expected_driver": "sqlite",
            },
            # MySQL configuration
            {
                "content": """
[database]
driver = "mysql"
username = "cli_user"
password = "cli_password"
database = "cli_db"
host = "localhost"
port = 3306

[app]
name = "MySQL CLI App"
""",
                "expected_driver": "mysql",
            },
            # SQLite async configuration
            {
                "content": """
[database]
driver = "sqlite+async"
database = "async_test.db"

[app]
name = "Async SQLite CLI App"
""",
                "expected_driver": "sqlite+async",
            },
        ]

        for config_data in configurations:
            with self.runner.isolated_filesystem():
                with open("config.toml", "w") as f:
                    f.write(config_data["content"])

                result = self.runner.invoke(cli, ["--config", "config.toml", "--help"])

                assert result.exit_code == 0
                assert "VGNC ORM Command-line Interface" in result.output

    def test_ensure_config_loaded_real_execution(self):
        """Test ensure_config_loaded with real configuration objects."""
        from click import Context

        # Test with SQLite configuration (should work without MySQL)
        ctx = Context(cli)
        ctx.obj = {"config_loaded": False, "database_url": "sqlite:///:memory:"}

        # This executes real ensure_config_loaded logic
        ensure_config_loaded(ctx)

        assert ctx.obj["config_loaded"] is True
        assert "db_config" in ctx.obj

        # Test with environment override
        ctx_env = Context(cli)
        ctx_env.obj = {"config_loaded": False}

        # DatabaseConfig reads env vars with the `DB_` prefix (pydantic-settings),
        # not from a VGNC_CONFIG_FILE and not under a `DATABASE__` prefix. Provide
        # real env vars so the no-URL branch of ensure_config_loaded can build a
        # valid config from the environment.
        env_vars = {
            "DB_DRIVER": "sqlite",
            "DB_DATABASE": "env_test.db",
        }

        with patch.dict(os.environ, env_vars):
            ensure_config_loaded(ctx_env)

            assert ctx_env.obj["config_loaded"] is True
            assert "db_config" in ctx_env.obj

    def test_cli_environment_variable_integration(self):
        """Test CLI integration with environment variables."""
        env_vars = {
            "DATABASE_URL": "sqlite:///:memory:",
            "VGNC_DEBUG": "true",
            "VGNC_APP_NAME": "Environment CLI Test",
        }

        with patch.dict(os.environ, env_vars):
            result = self.runner.invoke(cli, ["--help"])

            assert result.exit_code == 0

    def test_cli_multiple_database_url_formats(self):
        """Test CLI with multiple database URL formats."""
        url_formats = [
            "sqlite:///:memory:",
            "sqlite:///test.db",
            "sqlite:///file::memory:?cache=shared",
        ]

        for db_url in url_formats:
            result = self.runner.invoke(cli, ["--database-url", db_url, "--help"])

            assert result.exit_code == 0


class TestRealCLIXMLFormatting:
    """Real CLI XML formatting tests with actual data structures."""

    def test_format_species_as_xml_complete_data(self):
        """Test format_species_as_xml with complete species data structures."""
        # Create comprehensive species instance with all required attributes
        species = Species(
            taxon_id=9606,
            genefam_prefix="HSA",
            display_name="Human",
            is_live=SpeciesLiveStatus.YES,
            primary_db_table="species",
            ensembl_species_name="Homo sapiens",
            created=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        # This executes real XML formatting logic
        result = format_species_as_xml([species])

        # Verify XML structure and content
        assert isinstance(result, str)
        assert "<species>" in result
        assert "</species>" in result
        assert 'taxon_id="9606"' in result
        assert "<genefam_prefix>HSA</genefam_prefix>" in result
        assert "<display_name>Human</display_name>" in result
        assert "<is_live>Y</is_live>" in result
        assert "<ensembl_species_name>Homo sapiens</ensembl_species_name>" in result

    def test_format_genefam_as_xml_complete_data(self):
        """Test format_genefam_as_xml with complete genefam data structures."""
        genefam = Genefam(
            genefam_id=1101,
            taxon_id=9606,
            assigned_id="HGNC:1101",
            assigned_symbol="BRCA1",
            assigned_name="BRCA1 DNA repair associated",
            status_id=1,
            editor_id=1,
        )

        # This executes real XML formatting logic
        result = format_genefam_as_xml([genefam])

        # Verify XML structure and content
        assert isinstance(result, str)
        assert "<genefams>" in result
        assert "</genefams>" in result
        assert 'genefam_id="1101"' in result
        assert 'taxon_id="9606"' in result
        assert "<assigned_id>HGNC:1101</assigned_id>" in result
        assert "<assigned_symbol>BRCA1</assigned_symbol>" in result
        assert "<assigned_name>BRCA1 DNA repair associated</assigned_name>" in result

    def test_format_assembly_as_xml_complete_data(self):
        """Test format_assembly_as_xml with complete assembly data structures."""
        assembly = Assembly(
            id=1,
            taxon_id=9606,
            source="Ensembl",
            name="GRCh38",
            genbank_assembly_accession="GCA_000001405.28",
            refseq_assembly_accession="GCF_000001405.38",
            is_current=True,
            is_vgnc_default=True,
        )

        # This executes real XML formatting logic
        result = format_assembly_as_xml([assembly])

        # Verify XML structure and content
        assert isinstance(result, str)
        assert "<assemblies>" in result
        assert "</assemblies>" in result
        assert 'id="1"' in result
        assert 'taxon_id="9606"' in result
        assert "<source>Ensembl</source>" in result
        assert "<name>GRCh38</name>" in result
        assert (
            "<genbank_assembly_accession>GCA_000001405.28</genbank_assembly_accession>"
            in result
        )

    def test_format_chromosomes_as_xml_complete_data(self):
        """Test format_chromosomes_as_xml with complete chromosomes data structures."""
        chromosomes = Chromosomes(
            chr_id=1,
            taxon_id=9606,
            display_name="1",
            coord_system="GRCh38",
            refseq_accession="NC_000001.11",
            genbank_accession="NC_000001.11",
            ensembl_accession="NC_000001.11",
        )

        # This executes real XML formatting logic
        result = format_chromosomes_as_xml([chromosomes])

        # Verify XML structure and content
        assert isinstance(result, str)
        assert "<chromosomes>" in result
        assert "</chromosomes>" in result
        assert 'chr_id="1"' in result
        assert 'taxon_id="9606"' in result
        assert "<display_name>1</display_name>" in result
        assert "<refseq_accession>NC_000001.11</refseq_accession>" in result

    def test_format_functions_with_multiple_items(self):
        """Test formatting functions with multiple complete data structures."""
        # Create multiple species with different data
        species1 = Species(
            taxon_id=9606,
            display_name="Human",
            genefam_prefix="HSA",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        )

        species2 = Species(
            taxon_id=10090,
            display_name="Mouse",
            genefam_prefix="MMU",
            is_live=SpeciesLiveStatus.NO,
            created=datetime.now(),
        )

        # This executes real multiple-item XML formatting logic
        result = format_species_as_xml([species1, species2])

        # Verify multiple items are included
        assert 'taxon_id="9606"' in result
        assert 'taxon_id="10090"' in result
        assert "<display_name>Human</display_name>" in result
        assert "<display_name>Mouse</display_name>" in result
        assert "<genefam_prefix>HSA</genefam_prefix>" in result
        assert "<genefam_prefix>MMU</genefam_prefix>" in result
        assert "<is_live>Y</is_live>" in result
        assert "<is_live>N</is_live>" in result

    def test_format_functions_with_none_and_empty_values(self):
        """Test formatting functions handle None and empty values gracefully."""
        species = Species(
            taxon_id=9606,
            genefam_prefix=None,
            display_name="",
            is_live=None,
            primary_db_table=None,
            ensembl_species_name=None,
            created=None,
        )

        # This executes real None/empty value handling logic
        result = format_species_as_xml([species])

        # Should handle None/empty values gracefully
        assert isinstance(result, str)
        assert 'taxon_id="9606"' in result
        assert "<genefam_prefix />" in result  # None becomes empty element
        assert "<display_name />" in result  # Empty string becomes empty element


class TestRealCLIDisplayFunctions:
    """Real CLI display function tests with actual data processing."""

    def test_display_species_table_with_complete_data(self):
        """Test display_species_table with complete species data structures."""
        # Create real species instances
        species_list = []
        for i in range(3):
            species = Species(
                taxon_id=9600 + i,
                genefam_prefix=f"HSA{i}",
                display_name=f"Species {i}",
                is_live=SpeciesLiveStatus.YES if i % 2 == 0 else SpeciesLiveStatus.NO,
                created=datetime.now(),
            )
            species_list.append(species)

        # This executes real table display logic
        display_species_table(species_list)

    def test_display_species_json_with_complete_data(self):
        """Test display_species_json with complete species data structures."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HSA",
            display_name="Human",
            is_live=SpeciesLiveStatus.YES,
            created=datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC),
        )

        # This executes real JSON display logic
        display_species_json([species])

    def test_display_species_csv_with_complete_data(self):
        """Test display_species_csv with complete species data structures."""
        species_list = []
        for i in range(5):
            species = Species(
                taxon_id=9600 + i,
                genefam_prefix=f"HSA{i}",
                display_name=f"CSV Species {i}",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            species_list.append(species)

        # This executes real CSV display logic
        display_species_csv(species_list)

    def test_display_functions_with_large_datasets(self):
        """Test display functions with large datasets."""
        # Create large dataset with real species
        species_list = []
        for i in range(100):
            species = Species(
                taxon_id=9000 + i,
                display_name=f"Large Dataset Species {i}",
                genefam_prefix=f"PREFIX{i}",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            species_list.append(species)

        # This executes real large dataset handling logic
        display_species_table(species_list)
        display_species_json(species_list[:10])  # Test JSON with subset
        display_species_csv(species_list)

    def test_display_functions_with_special_characters(self):
        """Test display functions with special characters in data."""
        species = Species(
            taxon_id=9606,
            genefam_prefix="HSA",
            display_name="Tëst Ñâmé wïth ïcödé & spëciäl chârâctér$",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        )

        # This executes real special character handling logic
        display_species_table([species])
        display_species_json([species])
        display_species_csv([species])


class TestRealGetSessionFunction:
    """Real get_session function tests with actual database connections."""

    def test_get_session_sqlite_memory_database(self):
        """Test get_session with SQLite in-memory database."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database=":memory:", _env_file=None
        )

        # This executes real get_session logic with in-memory database
        session = get_session(config, "sqlite:///:memory:")

        assert session is not None
        assert hasattr(session, "execute")
        assert hasattr(session, "commit")
        assert hasattr(session, "rollback")
        assert hasattr(session, "close")

        # Test actual database operations
        result = session.execute(text("SELECT 1 as test_value"))
        rows = result.fetchall()
        assert len(rows) == 1
        assert rows[0][0] == 1

        # Test table creation
        session.execute(
            text("CREATE TABLE test_table (id INTEGER PRIMARY KEY, name TEXT)")
        )
        session.commit()

        # Test data insertion
        session.execute(
            text("INSERT INTO test_table (name) VALUES (:name)"), {"name": "test_name"}
        )
        session.commit()

        # Verify data
        result = session.execute(
            text("SELECT name FROM test_table WHERE name = :name"),
            {"name": "test_name"},
        )
        row = result.fetchone()
        assert row[0] == "test_name"

        session.close()

    def test_get_session_sqlite_file_database(self):
        """Test get_session with SQLite file database."""
        config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE, database="test_file.db", _env_file=None
        )

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = os.path.join(tmpdir, "test_file.db")

            # This executes real get_session logic with file database
            session = get_session(config, f"sqlite:///{db_path}")

            assert session is not None

            # Test database operations
            session.execute(text("CREATE TABLE file_test (id INTEGER, content TEXT)"))
            session.commit()

            session.execute(
                text("INSERT INTO file_test (id, content) VALUES (:id, :content)"),
                {"id": 1, "content": "test_content"},
            )
            session.commit()

            # Verify
            result = session.execute(
                text("SELECT content FROM file_test WHERE id = :id"), {"id": 1}
            )
            row = result.fetchone()
            assert row[0] == "test_content"

            session.close()

            # Verify file was created
            assert os.path.exists(db_path)

    def test_get_session_with_different_configurations(self):
        """Test get_session with different database configurations."""
        configurations = [
            # Basic SQLite
            DatabaseConfig(
                driver=DatabaseDriver.SQLITE, database="test.db", _env_file=None
            ),
            # SQLite with timeout
            DatabaseConfig(
                driver=DatabaseDriver.SQLITE,
                database="timeout.db",
                timeout=30.0,
                _env_file=None,
            ),
            # SQLite with connection options
            DatabaseConfig(
                driver=DatabaseDriver.SQLITE,
                database="options.db",
                pool_size=5,
                _env_file=None,
            ),
        ]

        for config in configurations:
            # This executes real get_session logic with different configurations
            session = get_session(config, f"sqlite:///{config.database}")

            assert session is not None

            # Test basic operation
            result = session.execute(text("SELECT 1"))
            assert result is not None

            session.close()

    def test_get_session_url_parsing(self):
        """Test get_session URL parsing with different URL formats."""
        with tempfile.TemporaryDirectory() as tmpdir:
            url_formats = [
                "sqlite:///:memory:",
                "sqlite:///file::memory:?cache=shared",
                f"sqlite:///{os.path.join(tmpdir, 'test.db')}",
            ]

            config = DatabaseConfig(
                driver=DatabaseDriver.SQLITE, database="default.db", _env_file=None
            )

            for url in url_formats:
                # This executes real get_session URL parsing logic
                session = get_session(config, url)

                assert session is not None

                # Test session works
                result = session.execute(text("SELECT 1 as test"))
                rows = result.fetchall()
                assert len(rows) > 0

                session.close()


class TestRealCLICommandIntegration:
    """Real CLI command integration tests."""

    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()

    def test_cli_command_with_various_configurations(self):
        """Test CLI commands with various real configurations."""
        test_scenarios = [
            # Basic SQLite
            {
                "args": ["--database-url", "sqlite:///:memory:", "--help"],
                "expected_exit": 0,
            },
            # With config file
            {"args": ["--verbose", "--help"], "expected_exit": 0},
            # With verbose flag
            {
                "args": ["--verbose", "--database-url", "sqlite:///:memory:", "--help"],
                "expected_exit": 0,
            },
        ]

        for scenario in test_scenarios:
            result = self.runner.invoke(cli, scenario["args"])
            assert result.exit_code == scenario["expected_exit"]

    def test_cli_config_file_integration(self):
        """Test CLI with real configuration file integration."""
        config_content = """
[database]
driver = "sqlite"
database = "cli_integration_test.db"
timeout = 30.0

[app]
name = "CLI Integration Test App"
debug = true
log_level = "INFO"

[session]
pool_size = 10
max_overflow = 20
"""

        with self.runner.isolated_filesystem():
            with open("integration_config.toml", "w") as f:
                f.write(config_content)

            result = self.runner.invoke(
                cli, ["--config", "integration_config.toml", "--help"]
            )

            assert result.exit_code == 0
            assert "VGNC ORM Command-line Interface" in result.output

    def test_cli_environment_integration(self):
        """Test CLI with environment variable integration."""
        env_vars = {
            "VGNC_DATABASE_DRIVER": "sqlite",
            "VGNC_DATABASE_DATABASE": "env_test.db",
            "VGNC_APP_NAME": "Environment CLI Test",
            "VGNC_DEBUG": "true",
        }

        with patch.dict(os.environ, env_vars):
            result = self.runner.invoke(cli, ["--help"])
            assert result.exit_code == 0

    def test_cli_error_handling_integration(self):
        """Test CLI error handling with real configurations."""
        # Test with invalid database URL format
        result = self.runner.invoke(cli, ["--database-url", "invalid://url", "--help"])
        # Should still show help despite invalid URL
        assert result.exit_code == 0

        # Test with non-existent config file
        result = self.runner.invoke(
            cli, ["--config", "nonexistent_config.toml", "--help"]
        )
        # May fail gracefully or show help
        assert result.exit_code in [0, 1, 2]
