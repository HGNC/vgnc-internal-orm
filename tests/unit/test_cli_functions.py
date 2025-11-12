"""Targeted tests for CLI functions to improve coverage."""

from unittest.mock import Mock

import pytest

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
)


class TestCLIUtilityFunctions:
    """Test CLI utility functions."""

    def test_ensure_config_loaded_basic(self):
        """Test ensure_config_loaded function exists."""
        assert callable(ensure_config_loaded)

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
        from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver

        db_config = DatabaseConfig(
            username="test",
            password="test",
            database="test.db",
            driver=DatabaseDriver.SQLITE,
            _env_file=None
        )

        # This should create a session without errors
        session = get_session(db_config, "sqlite:///:memory:")
        assert session is not None

    def test_get_session_with_config(self):
        """Test get_session with database config."""
        from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver

        db_config = DatabaseConfig(
            username="test",
            password="test",
            database="test.db",
            driver=DatabaseDriver.SQLITE,
            _env_file=None
        )

        # This should create a session without errors
        session = get_session(db_config)
        assert session is not None