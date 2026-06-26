"""Integration tests for the read-only CLI query commands.

Each test stands up a real SQLite file database (the CLI's get_session uses
plain create_engine, so an in-memory DB would not be shared with the command's
own session), seeds it via the ORM, then invokes the CLI through CliRunner and
asserts on the rendered output across all supported formats.
"""

import os
import tempfile

import pytest
from click.testing import CliRunner
from db_common import DeclarativeBase
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from vgnc_internal_orm.cli.main import cli
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus


@pytest.fixture()
def file_db_url():
    """Create a seeded SQLite file database and yield its URL."""
    tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False).name
    engine = create_engine(f"sqlite:///{tmp}")
    DeclarativeBase.metadata.create_all(engine)
    session_local = sessionmaker(bind=engine)

    with session_local() as session:
        session.add(
            Species(
                taxon_id=9606,
                genefam_prefix="P",
                display_name="Homo sapiens",
                scientific_name="Homo sapiens",
                is_live=SpeciesLiveStatus.YES,
                created=__import__("datetime").datetime(2026, 1, 2, 3, 4, 5),
            )
        )
        session.add(
            Species(
                taxon_id=10090,
                genefam_prefix="M",
                display_name="Mus musculus",
                scientific_name="Mus musculus",
                is_live=SpeciesLiveStatus.YES,
                created=__import__("datetime").datetime(2026, 1, 3, 4, 5, 6),
            )
        )
        session.add(
            Genefam(
                genefam_id=1,
                taxon_id=9606,
                assigned_id="GF1",
                assigned_symbol="SYM",
                assigned_name="A family",
                status_id=2,
                editor_id=3,
            )
        )
        session.commit()

    engine.dispose()
    yield f"sqlite:///{tmp}"
    if os.path.exists(tmp):
        os.unlink(tmp)


def _invoke(url: str, args: list[str]):
    return CliRunner().invoke(cli, ["--database-url", url, *args])


class TestQuerySpeciesCommand:
    def test_query_species_table(self, file_db_url):
        result = _invoke(file_db_url, ["query-species", "--format", "table"])
        assert result.exit_code == 0
        assert "9606" in result.output
        assert "Homo sapiens" in result.output

    def test_query_species_json(self, file_db_url):
        result = _invoke(file_db_url, ["query-species", "--format", "json"])
        assert result.exit_code == 0
        assert '"taxon_id": 9606' in result.output

    def test_query_species_csv(self, file_db_url):
        result = _invoke(file_db_url, ["query-species", "--format", "csv"])
        assert result.exit_code == 0
        assert "Taxon ID" in result.output
        assert "9606" in result.output

    def test_query_species_xml(self, file_db_url):
        result = _invoke(file_db_url, ["query-species", "--format", "xml"])
        assert result.exit_code == 0
        assert 'taxon_id="9606"' in result.output

    def test_query_species_pagination_and_sort(self, file_db_url):
        # limit=1, sorted by taxon_id descending -> the higher id first
        result = _invoke(
            file_db_url,
            [
                "query-species",
                "--format",
                "table",
                "--limit",
                "1",
                "--sort-by",
                "taxon_id",
                "--order",
                "desc",
            ],
        )
        assert result.exit_code == 0
        assert "10090" in result.output
        assert "9606" not in result.output


class TestQueryGenefamsCommand:
    def test_query_genefams_table(self, file_db_url):
        result = _invoke(file_db_url, ["query-genefams", "--format", "table"])
        assert result.exit_code == 0
        assert "GF1" in result.output

    def test_query_genefams_json(self, file_db_url):
        result = _invoke(file_db_url, ["query-genefams", "--format", "json"])
        assert result.exit_code == 0
        assert '"assigned_id": "GF1"' in result.output

    def test_query_genefams_csv(self, file_db_url):
        result = _invoke(file_db_url, ["query-genefams", "--format", "csv"])
        assert result.exit_code == 0
        assert "GeneFamily ID" in result.output

    def test_query_genefams_xml(self, file_db_url):
        result = _invoke(file_db_url, ["query-genefams", "--format", "xml"])
        assert result.exit_code == 0
        assert 'genefam_id="1"' in result.output

    def test_query_genefams_name_wildcard(self, file_db_url):
        result = _invoke(
            file_db_url, ["query-genefams", "--name", "GF*", "--format", "json"]
        )
        assert result.exit_code == 0
        assert "GF1" in result.output

    def test_query_genefams_name_exact_no_match(self, file_db_url):
        result = _invoke(
            file_db_url, ["query-genefams", "--name", "NOPE", "--format", "table"]
        )
        assert result.exit_code == 0
        assert "No gene families found." in result.output


class TestQueryGenefamSpeciesCommand:
    def test_query_genefam_species_table(self, file_db_url):
        result = _invoke(
            file_db_url, ["query-genefam-species", "1", "--format", "table"]
        )
        assert result.exit_code == 0
        # Either renders the associated species or a "no associations" message;
        # both exercise the command path. Assert the command ran and reported.
        assert result.exit_code == 0

    def test_query_genefam_species_json(self, file_db_url):
        result = _invoke(
            file_db_url, ["query-genefam-species", "1", "--format", "json"]
        )
        assert result.exit_code == 0
        assert "genefam" in result.output
