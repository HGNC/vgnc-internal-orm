"""Targeted tests for CLI functions to improve coverage."""

from datetime import datetime
from unittest.mock import Mock

from vgnc_internal_orm.cli.main import (
    display_genefam_species_csv,
    display_genefam_species_json,
    display_genefam_species_table,
    display_genefams_csv,
    display_genefams_json,
    display_genefams_table,
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
from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus


class TestCLIUtilityFunctions:
    """Test CLI utility functions."""

    def test_ensure_config_loaded_basic(self):
        """Test ensure_config_loaded function exists."""
        assert callable(ensure_config_loaded)

    def test_ensure_config_loaded_does_not_mutate_process_env(self):
        """Regression: ensure_config_loaded must not leak DB_DATABASE/DB_DRIVER
        into os.environ.

        Previously it set os.environ["DB_DATABASE"]/["DB_DRIVER"] as a side
        effect, which polluted every later DatabaseConfig() in the process and
        broke test isolation (a later in-memory test resolved to the persistent
        ``cli_database`` file). Config values are now passed as explicit kwargs.
        """
        import os

        import click

        ctx = click.Context(
            click.Command("test"),
            obj={
                "config_loaded": False,
                "database_url": "sqlite:///:memory:",
                "config_file": None,
                "verbose": False,
            },
        )

        for key in ("DB_DATABASE", "DB_DRIVER"):
            os.environ.pop(key, None)
        try:
            ensure_config_loaded(ctx)
            assert (
                "DB_DATABASE" not in os.environ
            ), "ensure_config_loaded must not leak DB_DATABASE into the process env"
            assert (
                "DB_DRIVER" not in os.environ
            ), "ensure_config_loaded must not leak DB_DRIVER into the process env"
            assert ctx.obj["config_loaded"] is True
        finally:
            for key in ("DB_DATABASE", "DB_DRIVER"):
                os.environ.pop(key, None)

    def test_format_species_as_xml_basic(self):
        """Test format_species_as_xml function exists."""
        assert callable(format_species_as_xml)

    def test_format_genefam_as_xml_basic(self):
        """Test format_genefam_as_xml function exists."""
        assert callable(format_genefam_as_xml)

    def test_format_assembly_as_xml_basic(self):
        """Test format_assembly_as_xml function exists."""
        assert callable(format_assembly_as_xml)

    def test_format_chromosomes_as_xml_basic(self):
        """Test format_chromosomes_as_xml function exists."""
        assert callable(format_chromosomes_as_xml)

    def test_display_species_table_basic(self):
        """Test display_species_table function exists."""
        assert callable(display_species_table)

    def test_display_species_json_basic(self):
        """Test display_species_json function exists."""
        assert callable(display_species_json)

    def test_display_species_csv_basic(self):
        """Test display_species_csv function exists."""
        assert callable(display_species_csv)

    def test_get_session_basic(self):
        """Test get_session function exists."""
        assert callable(get_session)


class TestCLIFormattingFunctions:
    """Test CLI XML formatting functions with simple inputs."""

    def test_format_species_as_xml_empty_list(self):
        """Test format_species_as_xml with empty list."""
        result = format_species_as_xml([])
        assert isinstance(result, str)
        assert "species" in result

    def test_format_genefam_as_xml_empty_list(self):
        """Test format_genefam_as_xml with empty list."""
        result = format_genefam_as_xml([])
        assert isinstance(result, str)
        assert "genefams" in result

    def test_format_assembly_as_xml_empty_list(self):
        """Test format_assembly_as_xml with empty list."""
        result = format_assembly_as_xml([])
        assert isinstance(result, str)
        assert "assemblies" in result

    def test_format_chromosomes_as_xml_empty_list(self):
        """Test format_chromosomes_as_xml with empty list."""
        result = format_chromosomes_as_xml([])
        assert isinstance(result, str)
        assert "chromosomes" in result

    def test_format_species_as_xml_with_mock(self):
        """Test format_species_as_xml with mock species."""
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
        assert "Human" in result

    def test_format_genefam_as_xml_with_mock(self):
        """Test format_genefam_as_xml with mock genefam."""
        mock_genefam = Mock()
        mock_genefam.genefam_id = 1
        mock_genefam.taxon_id = 9606
        mock_genefam.assigned_id = "ABC123"
        mock_genefam.assigned_symbol = "TEST"
        mock_genefam.assigned_name = "Test Gene"
        mock_genefam.status_id = 1
        mock_genefam.editor_id = 1

        result = format_genefam_as_xml([mock_genefam])
        assert isinstance(result, str)
        assert 'genefam_id="1"' in result
        assert "ABC123" in result

    def test_format_assembly_as_xml_with_mock(self):
        """Test format_assembly_as_xml with mock assembly."""
        mock_assembly = Mock()
        mock_assembly.id = 1
        mock_assembly.taxon_id = 9606
        mock_assembly.source = "Ensembl"
        mock_assembly.name = "GRCh38"
        mock_assembly.genbank_assembly_accession = "GCA_000001405.15"
        mock_assembly.refseq_assembly_accession = "GCF_000001405.26"
        mock_assembly.is_current = True
        mock_assembly.is_vgnc_default = True

        result = format_assembly_as_xml([mock_assembly])
        assert isinstance(result, str)
        assert 'id="1"' in result
        assert "Ensembl" in result

    def test_format_chromosomes_as_xml_with_mock(self):
        """Test format_chromosomes_as_xml with mock chromosomes."""
        mock_chromosomes = Mock()
        mock_chromosomes.chr_id = 1
        mock_chromosomes.taxon_id = 9606
        mock_chromosomes.display_name = "1"
        mock_chromosomes.coord_system = "GRCh38"
        mock_chromosomes.refseq_accession = "NC_000001.11"
        mock_chromosomes.genbank_accession = "CM000663.2"
        mock_chromosomes.ensembl_accession = "1"

        result = format_chromosomes_as_xml([mock_chromosomes])
        assert isinstance(result, str)
        assert 'chr_id="1"' in result


class TestCLIDisplayFunctions:
    """Test CLI display functions."""

    def test_display_species_table_empty(self):
        """Test display_species_table with empty list."""
        # This should not raise an exception
        display_species_table([])

    def test_display_species_json_empty(self):
        """Test display_species_json with empty list."""
        # This should not raise an exception
        display_species_json([])

    def test_display_species_csv_empty(self):
        """Test display_species_csv with empty list."""
        # This should not raise an exception
        display_species_csv([])

    def test_display_species_table_with_mock(self):
        """Test display_species_table with mock data."""
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = "HSA"
        mock_species.display_name = "Human"
        mock_species.is_live = Mock()
        mock_species.is_live.value = "YES"

        # This should not raise an exception
        display_species_table([mock_species])

    def test_display_species_json_with_mock(self):
        """Test display_species_json with mock data."""
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = "HSA"
        mock_species.display_name = "Human"
        mock_species.ensembl_species_name = "homo_sapiens"
        mock_species.scientific_name = "Homo sapiens"
        mock_species.vgnc_prefix = "HSA"
        mock_species.is_live = Mock()
        mock_species.is_live.value = "YES"
        mock_species.created = None
        mock_species.is_active = True

        # This should not raise an exception
        display_species_json([mock_species])

    def test_display_species_csv_with_mock(self):
        """Test display_species_csv with mock data."""
        mock_species = Mock()
        mock_species.taxon_id = 9606
        mock_species.genefam_prefix = "HSA"
        mock_species.display_name = "Human"

        # This should not raise an exception
        display_species_csv([mock_species])


class TestGetSessionFunction:
    """Test get_session function."""

    def test_get_session_with_url(self):
        """Test get_session with database URL."""
        from vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver

        db_config = DatabaseConfig(
            username="test",
            password="test",
            database="test.db",
            driver=DatabaseDriver.SQLITE,
            _env_file=None,
        )

        # This should create a session without errors
        session = get_session(db_config, "sqlite:///:memory:")
        assert session is not None

    def test_get_session_with_config(self):
        """Test get_session with database config."""
        from vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver

        db_config = DatabaseConfig(
            username="test",
            password="test",
            database="test.db",
            driver=DatabaseDriver.SQLITE,
            _env_file=None,
        )

        # This should create a session without errors
        session = get_session(db_config)
        assert session is not None


class TestCLIDisplayAndFormatExercised:
    """Exercise the CLI format/display functions with real model instances.

    These cover the full formatting branches (every field, including the
    ``created.isoformat()`` path and enum ``.value`` access) and the
    table/json/csv display paths that the existence-only tests above leave
    uncovered.
    """

    @staticmethod
    def _species(**overrides):
        defaults = {
            "taxon_id": 9606,
            "genefam_prefix": "HGNC",
            "display_name": "Homo sapiens",
            "scientific_name": "Homo sapiens",
            "ensembl_species_name": "homo_sapiens",
            "vgnc_prefix": "HSA",
            "is_live": SpeciesLiveStatus.YES,
            "created": datetime(2026, 1, 2, 3, 4, 5),
            "primary_db_table": "species_data",
        }
        defaults.update(overrides)
        return Species(**defaults)

    @staticmethod
    def _genefam(**overrides):
        defaults = {
            "genefam_id": 1,
            "taxon_id": 9606,
            "assigned_id": "GF1",
            "assigned_symbol": "SYM",
            "assigned_name": "A family",
            "status_id": 2,
            "editor_id": 3,
            "hcop_support_level": "high",
        }
        defaults.update(overrides)
        return Genefam(**defaults)

    @staticmethod
    def _assembly(**overrides):
        defaults = {
            "id": 1,
            "taxon_id": 9606,
            "source": "src",
            "name": "GRCh38",
            "genbank_assembly_accession": "GCA_000001405",
            "refseq_assembly_accession": "GCF_000001405",
            "is_current": True,
            "is_vgnc_default": False,
        }
        defaults.update(overrides)
        return Assembly(**defaults)

    @staticmethod
    def _chromosomes(**overrides):
        defaults = {
            "chr_id": 1,
            "taxon_id": 9606,
            "display_name": "1",
            "coord_system": "chromosome",
            "refseq_accession": "NC_000001",
            "genbank_accession": "CM000001",
            "ensembl_accession": "EN000001",
        }
        defaults.update(overrides)
        return Chromosomes(**defaults)

    # -- XML format functions (with real instances) ------------------------

    def test_format_species_as_xml_populated(self):
        result = format_species_as_xml([self._species()])
        assert 'taxon_id="9606"' in result
        assert "Homo sapiens" in result
        assert "<is_live>Y</is_live>" in result  # SpeciesLiveStatus.YES.value
        assert "2026-01-02T03:04:05" in result  # created.isoformat() path

    def test_format_genefam_as_xml_populated(self):
        result = format_genefam_as_xml([self._genefam()])
        assert 'genefam_id="1"' in result
        assert "GF1" in result
        assert "SYM" in result

    def test_format_assembly_as_xml_populated(self):
        result = format_assembly_as_xml([self._assembly()])
        assert 'id="1"' in result
        assert "GRCh38" in result
        assert "GCA_000001405" in result

    def test_format_chromosomes_as_xml_populated(self):
        result = format_chromosomes_as_xml([self._chromosomes()])
        assert 'chr_id="1"' in result
        assert "NC_000001" in result

    # -- species display functions (table/json/csv) ------------------------

    def test_display_species_table_populated(self, capsys):
        display_species_table([self._species()])
        out = capsys.readouterr().out
        assert "Taxon ID" in out
        assert "9606" in out
        assert "Homo sapiens" in out

    def test_display_species_table_empty(self, capsys):
        display_species_table([])
        assert "No species found." in capsys.readouterr().out

    def test_display_species_json_populated(self, capsys):
        import json

        display_species_json([self._species()])
        parsed = json.loads(capsys.readouterr().out)
        assert parsed[0]["taxon_id"] == 9606
        assert parsed[0]["is_active"] is True
        assert parsed[0]["created"] == "2026-01-02T03:04:05"

    def test_display_species_csv_populated(self, capsys):
        display_species_csv([self._species()])
        out = capsys.readouterr().out
        assert "Taxon ID" in out
        assert "9606" in out

    def test_display_species_csv_empty(self, capsys):
        display_species_csv([])
        assert capsys.readouterr().out == ""

    # -- genefam display functions -----------------------------------------

    def test_display_genefams_table_populated(self, capsys):
        display_genefams_table([self._genefam()])
        out = capsys.readouterr().out
        assert "Assigned ID" in out
        assert "GF1" in out

    def test_display_genefams_table_empty(self, capsys):
        display_genefams_table([])
        assert "No gene families found." in capsys.readouterr().out

    def test_display_genefams_json_populated(self, capsys):
        import json

        display_genefams_json([self._genefam()])
        parsed = json.loads(capsys.readouterr().out)
        assert parsed[0]["assigned_id"] == "GF1"
        assert parsed[0]["hcop_support_level"] == "high"

    def test_display_genefams_csv_populated(self, capsys):
        display_genefams_csv([self._genefam()])
        out = capsys.readouterr().out
        assert "GeneFamily ID" in out
        assert "GF1" in out

    def test_display_genefams_csv_empty(self, capsys):
        display_genefams_csv([])
        assert capsys.readouterr().out == ""

    # -- genefam-species association display functions ---------------------

    def test_display_genefam_species_table_with_species(self, capsys):
        display_genefam_species_table(self._genefam(), [self._species()])
        out = capsys.readouterr().out
        assert "Gene Family: GF1" in out
        assert "9606" in out

    def test_display_genefam_species_table_empty(self, capsys):
        display_genefam_species_table(self._genefam(), [])
        out = capsys.readouterr().out
        assert "No species associations found." in out

    def test_display_genefam_species_json_with_species(self, capsys):
        import json

        display_genefam_species_json(self._genefam(), self._species())
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["genefam"]["assigned_id"] == "GF1"
        assert parsed["species"]["taxon_id"] == 9606

    def test_display_genefam_species_json_without_species(self, capsys):
        import json

        display_genefam_species_json(self._genefam(), None)
        parsed = json.loads(capsys.readouterr().out)
        assert parsed["species"] == {}

    def test_display_genefam_species_csv_with_species(self, capsys):
        display_genefam_species_csv(self._genefam(), self._species())
        out = capsys.readouterr().out
        assert "GeneFamily ID" in out
        assert "9606" in out

    def test_display_genefam_species_csv_without_species(self, capsys):
        display_genefam_species_csv(self._genefam(), None)
        out = capsys.readouterr().out
        assert "N/A" in out
