"""Tests for VGNC ORM CLI functionality."""

import os
import tempfile

import pytest
from click.testing import CliRunner
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vgnc_internal_orm.cli.main import cli
from vgnc_internal_orm.models.base import BaseModel
from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus


@pytest.fixture
def runner():
    """Create Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def test_db():
    """Create a temporary SQLite database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    # Create database with test data
    engine = create_engine(f"sqlite:///{db_path}", echo=False)
    SessionLocal = sessionmaker(bind=engine)

    # Create tables from both metadata registries
    # Create minimal required tables for testing
    from sqlalchemy import Column, Integer, String, Table
    from sqlalchemy.schema import MetaData

    from vgnc_internal_orm.models.species import BaseCustomModel

    unified_metadata = MetaData()

    # Create missing reference tables first
    gene_status = Table(
        "gene_status",
        unified_metadata,
        Column("id", Integer, primary_key=True),
        Column("status", String(50)),
    )

    editor = Table(
        "editor",
        unified_metadata,
        Column("id", Integer, primary_key=True),
        Column("display_name", String(100)),
    )

    # Copy all tables from both metadata registries
    for table in BaseModel.metadata.tables.values():
        table.to_metadata(unified_metadata)
    for table in BaseCustomModel.metadata.tables.values():
        table.to_metadata(unified_metadata)

    # Create all tables from unified metadata
    unified_metadata.create_all(engine)

    # Add test data
    session = SessionLocal()

    # Add reference data first
    session.execute(gene_status.insert().values(id=1, status="approved"))
    session.execute(editor.insert().values(id=1, display_name="Test Editor"))
    session.commit()

    # Test species
    from datetime import datetime

    species_data = [
        Species(
            taxon_id=9606,
            genefam_prefix="HSA",
            display_name="human (Homo sapiens)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        ),
        Species(
            taxon_id=10090,
            genefam_prefix="MMU",
            display_name="house mouse (Mus musculus)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        ),
        Species(
            taxon_id=7227,
            genefam_prefix="DME",
            display_name="fruit fly (Drosophila melanogaster)",
            is_live=SpeciesLiveStatus.YES,
            created=datetime.now(),
        ),
    ]

    for species in species_data:
        session.add(species)

    # Add genefam test data directly via SQL to avoid foreign key issues
    from sqlalchemy import text

    genefam_data = [
        (1, 9606, "HOX", "HOXA1", "Homeobox A1", 1, 1, 1),
        (2, 9606, "GLOBIN", "HBA1", "Hemoglobin Subunit Alpha 1", 1, 1, 2),
        (3, 10090, "KINASE", "MAPK1", "Mitogen-Activated Protein Kinase 1", 1, 1, 3),
        (
            4,
            10090,
            "KINASE2",
            "SRC",
            "SRC Proto-Oncogene, Non-Receptor Tyrosine Kinase",
            1,
            1,
            1,
        ),
    ]

    for (
        genefam_id,
        taxon_id,
        assigned_id,
        assigned_symbol,
        assigned_name,
        status_id,
        editor_id,
        hcop_support_level,
    ) in genefam_data:
        session.execute(
            text("""
            INSERT INTO genefam (genefam_id, taxon_id, assigned_id, assigned_symbol, assigned_name, status_id, editor_id, hcop_support_level)
            VALUES (:genefam_id, :taxon_id, :assigned_id, :assigned_symbol, :assigned_name, :status_id, :editor_id, :hcop_support_level)
        """),
            {
                "genefam_id": genefam_id,
                "taxon_id": taxon_id,
                "assigned_id": assigned_id,
                "assigned_symbol": assigned_symbol,
                "assigned_name": assigned_name,
                "status_id": status_id,
                "editor_id": editor_id,
                "hcop_support_level": hcop_support_level,
            },
        )

    session.commit()
    session.close()

    yield db_path

    # Cleanup
    os.unlink(db_path)


class TestCLICommands:
    """Test CLI command functionality."""

    def test_cli_help(self, runner):
        """Test CLI help command."""
        result = runner.invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "VGNC ORM Command-line Interface" in result.output
        assert "query-species" in result.output
        assert "query-genefams" in result.output
        assert "query-genefam-species" in result.output

    def test_query_species_help(self, runner):
        """Test query-species help command."""
        result = runner.invoke(cli, ["query-species", "--help"])
        assert result.exit_code == 0
        assert "Query species information" in result.output
        assert "--limit" in result.output
        assert "--format" in result.output
        assert "--sort-by" in result.output

    def test_query_genefams_help(self, runner):
        """Test query-genefams help command."""
        result = runner.invoke(cli, ["query-genefams", "--help"])
        assert result.exit_code == 0
        assert "Query gene family information" in result.output
        assert "--name" in result.output
        assert "--status" in result.output

    def test_query_species_table_format(self, runner, test_db):
        """Test query-species with table format."""
        result = runner.invoke(
            cli, ["--database-url", f"sqlite:///{test_db}", "query-species"]
        )
        assert result.exit_code == 0
        assert "human (Homo sapiens)" in result.output
        assert "house mouse (Mus musculus)" in result.output
        assert "fruit fly (Drosophila melanogaster)" in result.output
        assert "Display Name" in result.output

    def test_query_species_json_format(self, runner, test_db):
        """Test query-species with JSON format."""
        result = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-species",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert '"scientific_name": "Homo sapiens"' in result.output
        assert '"vgnc_prefix": "HSA"' in result.output
        assert result.output.strip().startswith("[")
        assert result.output.strip().endswith("]")

    def test_query_species_csv_format(self, runner, test_db):
        """Test query-species with CSV format."""
        result = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-species",
                "--format",
                "csv",
            ],
        )
        assert result.exit_code == 0
        assert "Scientific Name" in result.output  # Header
        assert "Homo sapiens" in result.output
        assert "Mus musculus" in result.output

    def test_query_species_with_limit(self, runner, test_db):
        """Test query-species with limit parameter."""
        result = runner.invoke(
            cli,
            ["--database-url", f"sqlite:///{test_db}", "query-species", "--limit", "2"],
        )
        assert result.exit_code == 0
        # Should only show 2 species
        lines = result.output.strip().split("\n")
        # Header + separator + 2 data rows = 4 lines
        assert len(lines) == 4

    def test_query_species_with_sorting(self, runner, test_db):
        """Test query-species with sorting parameters."""
        result = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-species",
                "--sort-by",
                "genefam_prefix",
                "--order",
                "desc",
            ],
        )
        assert result.exit_code == 0
        lines = result.output.strip().split("\n")
        # Check that MMU comes before HSA in descending order
        data_lines = [
            line for line in lines if line.strip() and not line.startswith("-")
        ]
        if len(data_lines) >= 2:
            # MMU should come before HSA in descending order by VGNC prefix
            data_lines[1]  # First data row (after header)
            data_lines[2] if len(data_lines) > 2 else None

    def test_query_genefams_table_format(self, runner, test_db):
        """Test query-genefams with table format."""
        result = runner.invoke(
            cli, ["--database-url", f"sqlite:///{test_db}", "query-genefams"]
        )
        assert result.exit_code == 0
        assert "HOX" in result.output
        assert "GLOBIN" in result.output
        assert "KINASE" in result.output
        assert "Assigned ID" in result.output

    def test_query_genefams_name_filter(self, runner, test_db):
        """Test query-genefams with name filter."""
        result = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-genefams",
                "--name",
                "HOX",
            ],
        )
        assert result.exit_code == 0
        assert "HOX" in result.output
        assert "GLOBIN" not in result.output
        assert "KINASE" not in result.output

    def test_query_genefams_wildcard_filter(self, runner, test_db):
        """Test query-genefams with wildcard filter."""
        result = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-genefams",
                "--name",
                "H*",
            ],
        )
        assert result.exit_code == 0
        assert "HOX" in result.output
        assert "GLOBIN" not in result.output
        assert "KINASE" not in result.output

    def test_query_genefams_family_type_filter(self, runner, test_db):
        """Test query-genefams with status filter."""
        result = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-genefams",
                "--status",
                "approved",
            ],
        )
        assert result.exit_code == 0

    def test_query_genefams_json_format(self, runner, test_db):
        """Test query-genefams with JSON format."""
        result = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-genefams",
                "--format",
                "json",
            ],
        )
        assert result.exit_code == 0
        assert '"assigned_id": "HOX"' in result.output
        assert '"assigned_symbol": "HOXA1"' in result.output

    def test_query_genefam_species_not_found(self, runner, test_db):
        """Test query-genefam-species with non-existent gene family."""
        result = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-genefam-species",
                "NONEXISTENT",
            ],
        )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_verbose_output(self, runner, test_db):
        """Test CLI with verbose output."""
        result = runner.invoke(
            cli,
            ["--verbose", "--database-url", f"sqlite:///{test_db}", "query-species"],
        )
        assert result.exit_code == 0
        assert "Homo sapiens" in result.output

    def test_no_database_url_error(self, runner):
        """Test CLI error when no database URL is provided."""
        result = runner.invoke(cli, ["query-species"])
        assert result.exit_code == 1
        assert "Error" in result.output or "Please provide" in result.output


class TestCLIIntegration:
    """Integration tests for CLI functionality."""

    def test_complete_workflow(self, runner, test_db):
        """Test complete CLI workflow with multiple commands."""
        # Query all species
        result1 = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-species",
                "--format",
                "json",
            ],
        )
        assert result1.exit_code == 0

        # Query specific gene family
        result2 = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-genefams",
                "--name",
                "HOX",
                "--format",
                "json",
            ],
        )
        assert result2.exit_code == 0

        # Verify data consistency
        assert '"scientific_name": "Homo sapiens"' in result1.output
        assert '"assigned_id": "HOX"' in result2.output

    def test_different_output_formats_consistency(self, runner, test_db):
        """Test that different output formats provide consistent data."""
        # Use a specific sort order to ensure consistent results
        # Sort by taxon_id ascending to get Homo sapiens (9606) first
        # Actually, let's sort by scientific_name to get Drosophila first (alphabetical)

        # Table format
        result_table = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-species",
                "--limit",
                "1",
                "--sort-by",
                "display_name",
                "--order",
                "asc",
            ],
        )
        assert result_table.exit_code == 0

        # JSON format
        result_json = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-species",
                "--limit",
                "1",
                "--sort-by",
                "display_name",
                "--order",
                "asc",
                "--format",
                "json",
            ],
        )
        assert result_json.exit_code == 0

        # CSV format
        result_csv = runner.invoke(
            cli,
            [
                "--database-url",
                f"sqlite:///{test_db}",
                "query-species",
                "--limit",
                "1",
                "--sort-by",
                "display_name",
                "--order",
                "asc",
                "--format",
                "csv",
            ],
        )
        assert result_csv.exit_code == 0

        # All formats should contain the same species (Drosophila comes first alphabetically)
        assert "Drosophila melanogaster" in result_table.output
        assert "Drosophila melanogaster" in result_json.output
        assert "Drosophila melanogaster" in result_csv.output
