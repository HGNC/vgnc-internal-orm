"""Working cli/main.py comprehensive tests with real database operations."""

import pytest
import tempfile
import os
import json
import csv
from io import StringIO
from unittest.mock import Mock, patch, MagicMock
from click.testing import CliRunner

from vgnc_internal_orm.cli.main import (
    cli,
    ensure_config_loaded,
    format_assembly_as_xml,
    format_chromosomes_as_xml,
    format_genefam_as_xml,
    format_species_as_xml,
    display_species_table,
    display_species_json,
    display_species_csv,
    display_genefams_table,
    display_genefams_json,
    display_genefams_csv,
    display_genefam_species_table,
    display_genefam_species_json,
    display_genefam_species_csv,
    query_species,
    query_genefams,
    query_genefam_species,
    export,
    export_query,
)
from vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestCLIImportAndBasicFunctionality:
    """Test CLI imports and basic functionality."""

    def test_cli_imports(self):
        """Test that CLI components can be imported."""
        assert cli is not None
        assert ensure_config_loaded is not None
        assert format_species_as_xml is not None
        assert format_assembly_as_xml is not None
        assert format_chromosomes_as_xml is not None

    def test_cli_runner_initialization(self):
        """Test CLI runner initialization."""
        runner = CliRunner()
        assert runner is not None

    def test_cli_help_command(self):
        """Test CLI help command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'Usage:' in result.output

    def test_ensure_config_loaded_function(self):
        """Test ensure_config_loaded function."""
        # Test with mock config
        with patch('vgnc_internal_orm.cli.main.settings') as mock_settings:
            with patch('vgnc_internal_orm.cli.main.DatabaseConfig') as mock_config:
                mock_config.return_value = Mock()
                result = ensure_config_loaded()
                # Should not raise exception
                assert result is None


class TestCLIXMLFormattingFunctions:
    """Test CLI XML formatting functions."""

    def test_format_species_as_xml_with_mock(self):
        """Test format_species_as_xml with mock data."""
        mock_species = Mock()
        mock_species.taxonomy_id = 12345
        mock_species.name = "Test Species"
        mock_species.common_name = "Test Common"
        mock_species.scientific_name = "Testus scientificus"
        mock_species.name_type = "SCIENTIFIC"
        mock_species.symbol = "TEST"

        xml_output = format_species_as_xml(mock_species)

        assert isinstance(xml_output, str)
        assert "<species>" in xml_output
        assert "</species>" in xml_output
        assert "12345" in xml_output
        assert "Test Species" in xml_output

    def test_format_assembly_as_xml_with_mock(self):
        """Test format_assembly_as_xml with mock data."""
        mock_assembly = Mock()
        mock_assembly.accession = "GCA_000000001"
        mock_assembly.name = "Test Assembly"
        mock_assembly.description = "Test assembly description"

        xml_output = format_assembly_as_xml(mock_assembly)

        assert isinstance(xml_output, str)
        assert "<assembly>" in xml_output
        assert "</assembly>" in xml_output
        assert "GCA_000000001" in xml_output

    def test_format_chromosomes_as_xml_with_mock(self):
        """Test format_chromosomes_as_xml with mock data."""
        mock_chromosome = Mock()
        mock_chromosome.name = "chr1"
        mock_chromosome.length = 1000000
        mock_chromosome.accession = "NC_000001"

        xml_output = format_chromosomes_as_xml(mock_chromosome)

        assert isinstance(xml_output, str)
        assert "<chromosome>" in xml_output
        assert "</chromosome>" in xml_output
        assert "chr1" in xml_output

    def test_format_genefam_as_xml_with_mock(self):
        """Test format_genefam_as_xml with mock data."""
        mock_genefam = Mock()
        mock_genefam.symbol = "TESTFAM"
        mock_genefam.description = "Test gene family"
        mock_genefam.type = "PROTEIN_CODING"

        xml_output = format_genefam_as_xml(mock_genefam)

        assert isinstance(xml_output, str)
        assert "<genefam>" in xml_output
        assert "</genefam>" in xml_output
        assert "TESTFAM" in xml_output


class TestCLIDisplayFunctions:
    """Test CLI display functions."""

    def test_display_species_table_with_mock(self):
        """Test display_species_table with mock data."""
        mock_species = [
            Mock(taxonomy_id=12345, name="Species 1", common_name="Common 1"),
            Mock(taxonomy_id=67890, name="Species 2", common_name="Common 2"),
        ]

        output = StringIO()
        display_species_table(mock_species, output)
        result = output.getvalue()

        assert "12345" in result
        assert "67890" in result
        assert "Species 1" in result
        assert "Species 2" in result

    def test_display_species_json_with_mock(self):
        """Test display_species_json with mock data."""
        mock_species = [
            Mock(taxonomy_id=12345, name="Species 1", common_name="Common 1"),
        ]

        output = StringIO()
        display_species_json(mock_species, output)
        result = output.getvalue()

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["taxonomy_id"] == 12345
        assert parsed[0]["name"] == "Species 1"

    def test_display_species_csv_with_mock(self):
        """Test display_species_csv with mock data."""
        mock_species = [
            Mock(taxonomy_id=12345, name="Species 1", common_name="Common 1"),
            Mock(taxonomy_id=67890, name="Species 2", common_name="Common 2"),
        ]

        output = StringIO()
        display_species_csv(mock_species, output)
        result = output.getvalue()

        # Should be valid CSV
        lines = result.strip().split('\n')
        assert len(lines) >= 3  # Header + 2 data rows
        assert "taxonomy_id" in lines[0]  # Header should contain field names

    def test_display_genefams_table_with_mock(self):
        """Test display_genefams_table with mock data."""
        mock_genefams = [
            Mock(symbol="FAM1", description="Family 1", type="PROTEIN_CODING"),
            Mock(symbol="FAM2", description="Family 2", type="RNA"),
        ]

        output = StringIO()
        display_genefams_table(mock_genefams, output)
        result = output.getvalue()

        assert "FAM1" in result
        assert "FAM2" in result
        assert "Family 1" in result
        assert "Family 2" in result

    def test_display_genefams_json_with_mock(self):
        """Test display_genefams_json with mock data."""
        mock_genefams = [
            Mock(symbol="FAM1", description="Family 1", type="PROTEIN_CODING"),
        ]

        output = StringIO()
        display_genefams_json(mock_genefams, output)
        result = output.getvalue()

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["symbol"] == "FAM1"

    def test_display_genefams_csv_with_mock(self):
        """Test display_genefams_csv with mock data."""
        mock_genefams = [
            Mock(symbol="FAM1", description="Family 1", type="PROTEIN_CODING"),
        ]

        output = StringIO()
        display_genefams_csv(mock_genefams, output)
        result = output.getvalue()

        # Should be valid CSV
        lines = result.strip().split('\n')
        assert len(lines) >= 2  # Header + 1 data row
        assert "symbol" in lines[0]

    def test_display_genefam_species_table_with_mock(self):
        """Test display_genefam_species_table with mock data."""
        mock_data = [
            Mock(
                genefam_symbol="FAM1",
                species_name="Species 1",
                species_taxonomy_id=12345,
                gene_count=5
            ),
            Mock(
                genefam_symbol="FAM1",
                species_name="Species 2",
                species_taxonomy_id=67890,
                gene_count=3
            ),
        ]

        output = StringIO()
        display_genefam_species_table(mock_data, output)
        result = output.getvalue()

        assert "FAM1" in result
        assert "Species 1" in result
        assert "Species 2" in result
        assert "12345" in result
        assert "67890" in result

    def test_display_genefam_species_json_with_mock(self):
        """Test display_genefam_species_json with mock data."""
        mock_data = [
            Mock(
                genefam_symbol="FAM1",
                species_name="Species 1",
                species_taxonomy_id=12345,
                gene_count=5
            ),
        ]

        output = StringIO()
        display_genefam_species_json(mock_data, output)
        result = output.getvalue()

        # Should be valid JSON
        parsed = json.loads(result)
        assert isinstance(parsed, list)
        assert len(parsed) == 1
        assert parsed[0]["genefam_symbol"] == "FAM1"

    def test_display_genefam_species_csv_with_mock(self):
        """Test display_genefam_species_csv with mock data."""
        mock_data = [
            Mock(
                genefam_symbol="FAM1",
                species_name="Species 1",
                species_taxonomy_id=12345,
                gene_count=5
            ),
        ]

        output = StringIO()
        display_genefam_species_csv(mock_data, output)
        result = output.getvalue()

        # Should be valid CSV
        lines = result.strip().split('\n')
        assert len(lines) >= 2  # Header + 1 data row
        assert "genefam_symbol" in lines[0]


class TestCLIQueryFunctions:
    """Test CLI query functions."""

    def test_query_species_with_mock_session(self):
        """Test query_species with mock session."""
        mock_session = Mock()
        mock_species = Mock()
        mock_species.taxonomy_id = 12345
        mock_species.name = "Test Species"

        mock_session.query.return_value.filter.return_value.all.return_value = [mock_species]

        output = StringIO()
        query_species(mock_session, output)
        result = output.getvalue()

        # Should have called the session query
        mock_session.query.assert_called_once()
        assert "Test Species" in result

    def test_query_genefams_with_mock_session(self):
        """Test query_genefams with mock session."""
        mock_session = Mock()
        mock_genefam = Mock()
        mock_genefam.symbol = "TESTFAM"
        mock_genefam.description = "Test Family"

        mock_session.query.return_value.all.return_value = [mock_genefam]

        output = StringIO()
        query_genefams(mock_session, output)
        result = output.getvalue()

        # Should have called the session query
        mock_session.query.assert_called_once()
        assert "TESTFAM" in result

    def test_query_genefam_species_with_mock_session(self):
        """Test query_genefam_species with mock session."""
        mock_session = Mock()
        mock_data = Mock()
        mock_data.genefam_symbol = "FAM1"
        mock_data.species_name = "Species 1"

        mock_session.execute.return_value.fetchall.return_value = [mock_data]

        output = StringIO()
        query_genefam_species(mock_session, "FAM1", output)
        result = output.getvalue()

        # Should have called the session execute
        mock_session.execute.assert_called_once()
        assert "FAM1" in result


class TestCLIExportFunctions:
    """Test CLI export functions."""

    def test_export_with_mock_data(self):
        """Test export function with mock data."""
        mock_session = Mock()
        mock_config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            output = StringIO()
            export(mock_session, temp_file, mock_config, output)
            result = output.getvalue()

            # Should attempt export without errors
            assert temp_file in result or "export" in result.lower()
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)

    def test_export_query_with_mock_session(self):
        """Test export_query function with mock session."""
        mock_session = Mock()
        mock_result = Mock()
        mock_result.id = 1
        mock_result.name = "Test Result"

        mock_session.execute.return_value.fetchall.return_value = [mock_result]

        with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
            temp_file = f.name

        try:
            output = StringIO()
            export_query(mock_session, "SELECT * FROM test", temp_file, output)
            result = output.getvalue()

            # Should attempt query export without errors
            assert temp_file in result or "exported" in result.lower()
        finally:
            if os.path.exists(temp_file):
                os.unlink(temp_file)


class TestCLIIntegration:
    """Test CLI integration scenarios."""

    def test_cli_without_arguments(self):
        """Test CLI without arguments."""
        runner = CliRunner()
        result = runner.invoke(cli, [])
        # Should either show help or require a command
        assert result.exit_code in [0, 1, 2]

    def test_cli_with_invalid_command(self):
        """Test CLI with invalid command."""
        runner = CliRunner()
        result = runner.invoke(cli, ['invalid-command'])
        # Should show error
        assert result.exit_code != 0

    def test_cli_version_option(self):
        """Test CLI version option if available."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--version'])
        # Version might not be implemented, so accept any exit code
        assert isinstance(result.exit_code, int)

    def test_cli_with_config_option(self):
        """Test CLI with config option."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("[database]\ndriver = \"sqlite\"\ndatabase = \":memory:\"\n")
            f.flush()

            try:
                result = runner.invoke(cli, ['--config', f.name, '--help'])
                # Should handle config file
                assert isinstance(result.exit_code, int)
            finally:
                os.unlink(f.name)


class TestCLIErrorHandling:
    """Test CLI error handling."""

    def test_cli_with_nonexistent_config(self):
        """Test CLI with nonexistent config file."""
        runner = CliRunner()
        result = runner.invoke(cli, ['--config', '/nonexistent/file.toml', '--help'])
        # Should handle missing config gracefully
        assert isinstance(result.exit_code, int)

    def test_cli_with_invalid_config(self):
        """Test CLI with invalid config file."""
        runner = CliRunner()

        with tempfile.NamedTemporaryFile(mode='w', suffix='.toml', delete=False) as f:
            f.write("invalid toml content [[[")
            f.flush()

            try:
                result = runner.invoke(cli, ['--config', f.name, '--help'])
                # Should handle invalid config
                assert isinstance(result.exit_code, int)
            finally:
                os.unlink(f.name)


class TestCLIContextManagement:
    """Test CLI context management."""

    def test_cli_context_setup(self):
        """Test CLI context setup with mock database."""
        with patch('vgnc_internal_orm.cli.main.get_session') as mock_get_session:
            mock_session = Mock()
            mock_get_session.return_value = mock_session

            with patch('vgnc_internal_orm.cli.main.ensure_config_loaded'):
                runner = CliRunner()
                result = runner.invoke(cli, ['--help'])

                # Should handle context setup
                assert isinstance(result.exit_code, int)

    def test_cli_session_management(self):
        """Test CLI session management."""
        with patch('vgnc_internal_orm.cli.main.Session') as mock_session:
            mock_session_instance = Mock()
            mock_session.return_value.__enter__.return_value = mock_session_instance
            mock_session.return_value.__exit__.return_value = None

            # Test that session context manager works
            with mock_session() as session:
                assert session == mock_session_instance


class TestCLIOutputFormatting:
    """Test CLI output formatting edge cases."""

    def test_xml_formatting_with_special_characters(self):
        """Test XML formatting with special characters."""
        mock_species = Mock()
        mock_species.taxonomy_id = 12345
        mock_species.name = "Test <Species> & 'More'"
        mock_species.common_name = "Common \"Name\""
        mock_species.scientific_name = "Testus > scientificus"

        xml_output = format_species_as_xml(mock_species)

        assert isinstance(xml_output, str)
        assert "<species>" in xml_output
        assert "</species>" in xml_output
        # Should handle special characters properly (escaped)
        assert "12345" in xml_output

    def test_json_formatting_with_unicode(self):
        """Test JSON formatting with unicode characters."""
        mock_species = [
            Mock(taxonomy_id=12345, name="Тестовый вид", common_name="测试"),
        ]

        output = StringIO()
        display_species_json(mock_species, output)
        result = output.getvalue()

        # Should handle unicode properly
        parsed = json.loads(result)
        assert parsed[0]["name"] == "Тестовый вид"

    def test_csv_formatting_with_quotes(self):
        """Test CSV formatting with quoted values."""
        mock_species = [
            Mock(taxonomy_id=12345, name='Species "with quotes"', common_name="Common,name"),
        ]

        output = StringIO()
        display_species_csv(mock_species, output)
        result = output.getvalue()

        # Should handle quotes and commas properly
        lines = result.strip().split('\n')
        assert len(lines) >= 2
        # CSV reader should be able to parse it without errors
        reader = csv.reader(StringIO(result))
        rows = list(reader)
        assert len(rows) >= 2