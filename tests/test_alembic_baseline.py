"""Tests for Alembic baseline migration validation."""

import os
import tempfile

import pytest
from alembic import command
from alembic.config import Config
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def test_database():
    """Create a temporary database for testing."""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as tmp:
        db_path = tmp.name

    engine = create_engine(f"sqlite:///{db_path}")

    yield db_path, engine

    # Cleanup
    engine.dispose()
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def alembic_config(test_database):
    """Create Alembic configuration for testing."""
    db_path, _ = test_database

    # Create alembic config
    alembic_cfg = Config("alembic.ini")
    alembic_cfg.set_main_option("sqlalchemy.url", f"sqlite:///{db_path}")

    return alembic_cfg


class TestBaselineMigration:
    """Test baseline migration functionality."""

    def test_baseline_migration_creates_all_tables(self, alembic_config, test_database):
        """Test that baseline migration creates all expected tables."""
        db_path, engine = test_database

        # Run the baseline migration
        command.upgrade(alembic_config, "head")

        # Check that all expected tables exist
        inspector = inspect(engine)
        tables = inspector.get_table_names()

        expected_tables = {
            "species",
            "genefam",
            "assembly",
            "chromosomes",  # Main entities
            "assembly_has_chr",
            "gene_alt_name",
            "gene_alt_symbol",  # Associations
            "gene_has_comment",
            "gene_has_family",
            "gene_has_flag",
            "alt_name",
            "alt_symbol",
            "comment",
            "editor",
            "family_new",
            "flag_class",
            "gene_flag",
            "gene_status",
            "nomenclature_type",
            "alembic_version",  # Alembic tracking table
        }

        # Check that all expected tables are present
        for table in expected_tables:
            assert table in tables, f"Expected table '{table}' not found"

        # Check no unexpected tables exist
        unexpected_tables = set(tables) - expected_tables
        assert not unexpected_tables, f"Unexpected tables found: {unexpected_tables}"

    def test_species_table_schema_is_correct(self, alembic_config, test_database):
        """Test that species table schema matches model definition."""
        db_path, engine = test_database

        # Run migration
        command.upgrade(alembic_config, "head")

        # Check species table schema
        inspector = inspect(engine)
        columns = inspector.get_columns("species")

        expected_columns = {
            "taxon_id": {"nullable": False, "primary_key": True},
            "genefam_prefix": {"nullable": False},
            "primary_db_table": {"nullable": True},
            "display_name": {"nullable": False},
            "ensembl_species_name": {"nullable": True},
            "is_live": {"nullable": False},
            "created": {"nullable": False},
            "_scientific_name": {"nullable": True},
            "_common_name": {"nullable": True},
            "created_at": {"nullable": False},
            "updated_at": {"nullable": False},
        }

        for column in columns:
            col_name = column["name"]
            assert col_name in expected_columns, f"Unexpected column '{col_name}'"

            expected = expected_columns[col_name]
            assert (
                column["nullable"] == expected["nullable"]
            ), f"Column '{col_name}' nullable mismatch"

            if "primary_key" in expected:
                assert column[
                    "primary_key"
                ], f"Column '{col_name}' should be primary key"

    def test_genefam_table_schema_is_correct(self, alembic_config, test_database):
        """Test that genefam table schema matches model definition."""
        db_path, engine = test_database

        # Run migration
        command.upgrade(alembic_config, "head")

        # Check genefam table schema
        inspector = inspect(engine)
        columns = inspector.get_columns("genefam")

        expected_columns = {
            "genefam_id": {"nullable": False, "primary_key": True},
            "taxon_id": {"nullable": False},
            "assigned_id": {"nullable": False},
            "assigned_symbol": {"nullable": True},
            "assigned_name": {"nullable": True},
            "status_id": {"nullable": False},
            "editor_id": {"nullable": False},
            "hcop_support_level": {"nullable": True},
            "created_at": {"nullable": False},
            "updated_at": {"nullable": False},
        }

        for column in columns:
            col_name = column["name"]
            assert col_name in expected_columns, f"Unexpected column '{col_name}'"

            expected = expected_columns[col_name]
            assert (
                column["nullable"] == expected["nullable"]
            ), f"Column '{col_name}' nullable mismatch"

    def test_foreign_key_constraints_exist(self, alembic_config, test_database):
        """Test that foreign key constraints are properly created."""
        db_path, engine = test_database

        # Run migration
        command.upgrade(alembic_config, "head")

        # Check foreign key constraints
        inspector = inspect(engine)

        # Check genefam table has foreign key to gene_status
        fks = inspector.get_foreign_keys("genefam")
        status_fk = [fk for fk in fks if "gene_status" in str(fk["referred_table"])]
        assert len(status_fk) > 0, "genefam should have foreign key to gene_status"

        # Check alt_name has foreign key to nomenclature_type
        fks = inspector.get_foreign_keys("alt_name")
        nomen_fk = [
            fk for fk in fks if "nomenclature_type" in str(fk["referred_table"])
        ]
        assert (
            len(nomen_fk) > 0
        ), "alt_name should have foreign key to nomenclature_type"

    def test_indexes_are_created(self, alembic_config, test_database):
        """Test that indexes are properly created."""
        db_path, engine = test_database

        # Run migration
        command.upgrade(alembic_config, "head")

        # Check indexes exist
        inspector = inspect(engine)

        # Check association table indexes
        gene_alt_name_indexes = inspector.get_indexes("gene_alt_name")
        index_names = [idx["name"] for idx in gene_alt_name_indexes]

        assert (
            "idx_gene_alt_name_genefam" in index_names
        ), "Missing index idx_gene_alt_name_genefam"
        assert (
            "idx_gene_alt_name_name_id" in index_names
        ), "Missing index idx_gene_alt_name_name_id"

    def test_models_work_with_migrated_database(self, alembic_config, test_database):
        """Test that our models can work with the database created by migration."""
        db_path, engine = test_database

        # Run migration
        command.upgrade(alembic_config, "head")

        # Test model operations
        from datetime import datetime

        from vgnc_internal_orm.models.assembly import Assembly
        from vgnc_internal_orm.models.chromosomes import Chromosomes
        from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus

        SessionLocal = sessionmaker(bind=engine)
        session = SessionLocal()

        try:
            # Create a species
            species = Species(
                taxon_id=9606,
                genefam_prefix="HSA",
                display_name="human (Homo sapiens)",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species)
            session.commit()

            # Query it back
            saved_species = (
                session.query(Species).filter(Species.taxon_id == 9606).first()
            )

            assert saved_species is not None
            assert saved_species.display_name == "human (Homo sapiens)"
            assert saved_species.genefam_prefix == "HSA"

            # Test assembly creation
            assembly = Assembly(
                id=1,
                taxon_id=9606,
                source="Ensembl",
                name="GRCh38",
                genbank_assembly_accession="GCA_000001405.15",
                refseq_assembly_accession="GCF_000001405.26",
                is_current=True,
                is_vgnc_default=True,
            )
            session.add(assembly)
            session.commit()

            # Query assembly
            saved_assembly = session.query(Assembly).filter(Assembly.id == 1).first()

            assert saved_assembly is not None
            assert saved_assembly.taxon_id == 9606

            # Test chromosome creation
            chromosome = Chromosomes(
                chr_id=1,
                taxon_id=9606,
                display_name="Chromosome 1",
                genbank_accession="CM000663.2",
            )
            session.add(chromosome)
            session.commit()

            # Query chromosome
            saved_chrom = (
                session.query(Chromosomes).filter(Chromosomes.chr_id == 1).first()
            )

            assert saved_chrom is not None
            assert saved_chrom.taxon_id == 9606

        finally:
            session.close()

    def test_alembic_version_tracking(self, alembic_config, test_database):
        """Test that Alembic version tracking works correctly."""
        db_path, engine = test_database

        # Run migration
        command.upgrade(alembic_config, "head")

        # Check alembic version table
        with engine.connect() as conn:
            result = conn.execute(text("SELECT version_num FROM alembic_version"))
            version = result.scalar()

        assert version is not None, "Alembic version should be set"
        assert len(version) == 12, "Version should be a valid revision hash"
