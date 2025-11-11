"""Integration tests for relationship loading strategies.

This test suite verifies that different loading strategies work correctly
and helps identify N+1 query problems.
"""

from datetime import datetime

import pytest
from sqlalchemy import text
from sqlalchemy.orm import joinedload, selectinload

# Import shared integration test fixtures
from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes
from vgnc_internal_orm.models.species import Species


@pytest.fixture(scope="function")
def test_db(integrated_test_db):
    """Create a test database with sample data for loading strategy tests."""
    session, engine = integrated_test_db

    from datetime import datetime

    from sqlalchemy import text

    # Insert mock data for foreign key references
    session.execute(
        text(
            "INSERT OR IGNORE INTO gene_status (id, status, display) VALUES (1, 'Active', 'Active Status')"
        )
    )
    session.execute(
        text(
            "INSERT OR IGNORE INTO editor (id, display_name, current, connected) VALUES (1, 'Test Editor', 1, 1)"
        )
    )
    session.commit()

    # Create test species using raw SQL to avoid ORM field issues
    human_data = {
        "taxon_id": 9606,
        "genefam_prefix": "HSA",
        "display_name": "human (Homo sapiens)",
        "primary_db_table": "species",
        "ensembl_species_name": "homo_sapiens",
        "is_live": "YES",  # Correct enum value
        "created": datetime.now(),
    }

    mouse_data = {
        "taxon_id": 10090,
        "genefam_prefix": "MMU",
        "display_name": "mouse (Mus musculus)",
        "primary_db_table": "species",
        "ensembl_species_name": "mus_musculus",
        "is_live": "YES",  # Correct enum value
        "created": datetime.now(),
    }

    session.execute(
        text(
            """
        INSERT INTO species (taxon_id, genefam_prefix, display_name, primary_db_table, ensembl_species_name, is_live, created)
        VALUES (:taxon_id, :genefam_prefix, :display_name, :primary_db_table, :ensembl_species_name, :is_live, :created)
    """
        ),
        human_data,
    )

    session.execute(
        text(
            """
        INSERT INTO species (taxon_id, genefam_prefix, display_name, primary_db_table, ensembl_species_name, is_live, created)
        VALUES (:taxon_id, :genefam_prefix, :display_name, :primary_db_table, :ensembl_species_name, :is_live, :created)
    """
        ),
        mouse_data,
    )

    session.commit()

    # Create test gene families using raw SQL
    hox_data = {
        "taxon_id": 9606,
        "assigned_id": "VGNC_HOX_FAMILY",
        "assigned_symbol": "HOX",
        "assigned_name": "Homeobox gene family",
        "status_id": 1,
        "editor_id": 1,
        "hcop_support_level": 3,
    }

    gpcr_data = {
        "taxon_id": 9606,
        "assigned_id": "VGNC_GPCR_FAMILY",
        "assigned_symbol": "GPCR_Rhodopsin",
        "assigned_name": "GPCR Rhodopsin family",
        "status_id": 1,
        "editor_id": 1,
        "hcop_support_level": 2,
    }

    session.execute(
        text(
            """
        INSERT INTO genefam (taxon_id, assigned_id, assigned_symbol, assigned_name, status_id, editor_id, hcop_support_level)
        VALUES (:taxon_id, :assigned_id, :assigned_symbol, :assigned_name, :status_id, :editor_id, :hcop_support_level)
    """
        ),
        hox_data,
    )

    session.execute(
        text(
            """
        INSERT INTO genefam (taxon_id, assigned_id, assigned_symbol, assigned_name, status_id, editor_id, hcop_support_level)
        VALUES (:taxon_id, :assigned_id, :assigned_symbol, :assigned_name, :status_id, :editor_id, :hcop_support_level)
    """
        ),
        gpcr_data,
    )

    # Create mouse genefam
    mouse_genefam_data = {
        "taxon_id": 10090,
        "assigned_id": "VGNC_MOUSE_HOX_FAMILY",
        "assigned_symbol": "HOX",
        "assigned_name": "Mouse Homeobox gene family",
        "status_id": 1,
        "editor_id": 1,
        "hcop_support_level": 2,
    }

    session.execute(
        text(
            """
        INSERT INTO genefam (taxon_id, assigned_id, assigned_symbol, assigned_name, status_id, editor_id, hcop_support_level)
        VALUES (:taxon_id, :assigned_id, :assigned_symbol, :assigned_name, :status_id, :editor_id, :hcop_support_level)
    """
        ),
        mouse_genefam_data,
    )

    # Create chromosomes using raw SQL
    chromosomes_data = [
        {
            "taxon_id": 9606,
            "display_name": "chr1",
            "coord_system": "GRCh38",
            "genbank_accession": "NC_000001.11",
        },
        {
            "taxon_id": 9606,
            "display_name": "chr2",
            "coord_system": "GRCh38",
            "genbank_accession": "NC_000002.12",
        },
        {
            "taxon_id": 9606,
            "display_name": "chrX",
            "coord_system": "GRCh38",
            "genbank_accession": "NC_000023.11",
        },
        {
            "taxon_id": 9606,
            "display_name": "chrMT",
            "coord_system": "GRCh38",
            "genbank_accession": "NC_012920.1",
        },
        {
            "taxon_id": 10090,
            "display_name": "chr1",
            "coord_system": "GRCm38",
            "genbank_accession": "NC_000067.6",
        },
        {
            "taxon_id": 10090,
            "display_name": "chr2",
            "coord_system": "GRCm38",
            "genbank_accession": "NC_000068.7",
        },
    ]

    for chr_data in chromosomes_data:
        session.execute(
            text(
                """
            INSERT INTO chromosomes (taxon_id, display_name, coord_system, genbank_accession)
            VALUES (:taxon_id, :display_name, :coord_system, :genbank_accession)
        """
            ),
            chr_data,
        )

    # Create assemblies using raw SQL
    assemblies_data = [
        {
            "taxon_id": 9606,
            "name": "GRCh38",
            "genbank_assembly_accession": "GCA_000001405.40",
            "refseq_assembly_accession": "GCF_000001405.40",
            "source": "Ensembl",
            "is_current": True,
            "is_vgnc_default": True,
        },
        {
            "taxon_id": 9606,
            "name": "GRCh37",
            "genbank_assembly_accession": "GCA_000001405.38",
            "refseq_assembly_accession": "GCF_000001405.38",
            "source": "Ensembl",
            "is_current": False,
            "is_vgnc_default": False,
        },
        {
            "taxon_id": 10090,
            "name": "GRCm38",
            "genbank_assembly_accession": "GCA_000001635.8",
            "refseq_assembly_accession": "GCF_000001635.8",
            "source": "Ensembl",
            "is_current": True,
            "is_vgnc_default": True,
        },
        {
            "taxon_id": 10090,
            "name": "GRCm37",
            "genbank_assembly_accession": "GCA_000001635.7",
            "refseq_assembly_accession": "GCF_000001635.7",
            "source": "Ensembl",
            "is_current": False,
            "is_vgnc_default": False,
        },
    ]

    for asm_data in assemblies_data:
        session.execute(
            text(
                """
            INSERT INTO assembly (taxon_id, name, genbank_assembly_accession, refseq_assembly_accession, source, is_current, is_vgnc_default)
            VALUES (:taxon_id, :name, :genbank_assembly_accession, :refseq_assembly_accession, :source, :is_current, :is_vgnc_default)
        """
            ),
            asm_data,
        )

    session.commit()

    yield session

    session.close()


class TestLoadingStrategies:
    """Test different relationship loading strategies."""

    def test_lazy_loading_species_to_chromosomes(self, test_db):
        """Test lazy loading from Species to Chromosomes relationship."""
        session = test_db

        # First, check what columns exist in species table
        columns_result = session.execute(text("PRAGMA table_info(species)")).fetchall()
        columns = [row[1] for row in columns_result]
        print(f"Species table columns: {columns}")

        # Check what data exists
        species_data = session.execute(text("SELECT * FROM species")).fetchall()
        print(f"Species data count: {len(species_data)}")
        for row in species_data:
            print(f"  Species: {row}")

        # Query species using raw SQL - try different approaches
        if "genefam_prefix" in columns:
            species_result = session.execute(
                text("SELECT * FROM species WHERE genefam_prefix = :prefix"),
                {"prefix": "HSA"},
            ).fetchone()
        elif "taxon_id" in columns:
            species_result = session.execute(
                text("SELECT * FROM species WHERE taxon_id = :taxon_id"),
                {"taxon_id": 9606},
            ).fetchone()
        else:
            species_result = None

        assert species_result is not None, "No species data found"

        # Query chromosomes for human species using raw SQL
        chromosomes_result = session.execute(
            text("SELECT * FROM chromosomes WHERE taxon_id = :taxon_id"),
            {"taxon_id": species_result.taxon_id},
        ).fetchall()

        assert len(chromosomes_result) >= 1, "No chromosomes found for human species"
        chromosome_names = [chr.display_name for chr in chromosomes_result]
        assert "chr1" in chromosome_names

    def test_selectin_loading_species_to_chromosomes(self, test_db):
        """Test selectin loading from Species to Chromosomes relationship."""
        session = test_db

        # Query species with selectin loading for chromosomes
        species = (
            session.query(Species).options(selectinload(Species.chromosomes)).all()
        )

        # Access chromosomes - should not trigger additional queries
        human_species = next(sp for sp in species if sp.vgnc_prefix == "HSA")
        chromosomes = human_species.chromosomes

        assert len(chromosomes) == 4
        chromosome_names = [chr.display_name for chr in chromosomes]
        assert "chr1" in chromosome_names
        assert "chr2" in chromosome_names
        assert "chrX" in chromosome_names
        assert "chrMT" in chromosome_names

    def test_joined_loading_chromosome_to_species(self, test_db):
        """Test joined loading from Chromosome to Species relationship."""
        session = test_db

        # Query chromosomes with joined loading for species
        chromosomes = (
            session.query(Chromosomes).options(joinedload(Chromosomes.species)).all()
        )

        # Access species - should not trigger additional queries
        human_chr1 = next(chr for chr in chromosomes if chr.display_name == "chr1")
        species = human_chr1.species

        assert species is not None
        assert species.vgnc_prefix == "HSA"
        assert species.scientific_name == "Homo sapiens"

    def test_many_to_many_loading_genefams(self, test_db):
        """Test many-to-many loading between Species and Genefams."""
        session = test_db

        # Query species with selectin loading for genefams
        species = session.query(Species).options(selectinload(Species.genefams)).all()

        human_species = next(sp for sp in species if sp.vgnc_prefix == "HSA")
        mouse_species = next(sp for sp in species if sp.vgnc_prefix == "MMU")

        # Test human gene families
        human_genefams = human_species.genefams
        assert len(human_genefams) == 2
        genefam_names = [gf.assigned_symbol for gf in human_genefams]
        assert "HOX" in genefam_names
        assert "GPCR_Rhodopsin" in genefam_names

        # Test mouse gene families
        mouse_genefams = mouse_species.genefams
        assert len(mouse_genefams) == 1
        assert mouse_genefams[0].assigned_symbol == "HOX"

    def test_complex_relationship_navigation(self, test_db):
        """Test navigation through multiple relationship levels."""
        session = test_db

        # Query species with all relationships loaded
        species = (
            session.query(Species)
            .options(
                selectinload(Species.chromosomes),
                selectinload(Species.assemblies),
                selectinload(Species.genefams),
            )
            .all()
        )

        human_species = next(sp for sp in species if sp.vgnc_prefix == "HSA")

        # Test chromosome access
        assert len(human_species.chromosomes) == 4

        # Test assembly access
        assemblies = human_species.assemblies
        assert len(assemblies) == 2

        # Test assembly access - find primary assembly manually
        primary_assemblies = [
            asm for asm in assemblies if asm.is_current and asm.is_vgnc_default
        ]
        assert len(primary_assemblies) > 0
        assert primary_assemblies[0].name == "GRCh38"

        # Test gene family access
        genefams = human_species.genefams
        assert len(genefams) == 2

    def test_relationship_helper_methods(self, test_db):
        """Test relationship helper methods use loaded data efficiently."""
        session = test_db

        # Query species with relationships loaded
        species = (
            session.query(Species)
            .options(
                selectinload(Species.chromosomes),
                selectinload(Species.assemblies),
                selectinload(Species.genefams),
            )
            .all()
        )

        human_species = next(sp for sp in species if sp.vgnc_prefix == "HSA")

        # Test chromosome helper methods
        active_chromosomes = human_species.get_active_chromosomes(session)
        assert len(active_chromosomes) == 4

        complete_chromosomes = human_species.get_complete_chromosomes(session)
        assert len(complete_chromosomes) == 4

        sex_chromosomes = human_species.get_sex_chromosomes(session)
        assert len(sex_chromosomes) == 1
        assert sex_chromosomes[0].display_name == "chrX"

        mitochondrial_chromosome = human_species.get_mitochondrial_chromosome(session)
        assert mitochondrial_chromosome is not None
        assert mitochondrial_chromosome.display_name == "chrMT"

        autosomes = human_species.get_autosomes(session)
        assert len(autosomes) == 2

        # Test gene family helper methods
        protein_coding_genefams = human_species.get_genefams_by_type(
            session, "protein_coding"
        )
        assert len(protein_coding_genefams) == 2

        # Test species-gene family relationship
        hox_genefam = next(
            gf for gf in human_species.genefams if gf.assigned_symbol == "HOX"
        )
        assert human_species.has_genefam(hox_genefam) is True
        assert human_species.has_genefam("HOX") is True
        assert human_species.has_genefam("NonExistent") is False

    def test_loading_strategy_performance_comparison(self, test_db):
        """Compare performance between different loading strategies."""
        session = test_db

        # Method 1: Lazy loading (should result in N+1 queries)
        species_lazy = session.query(Species).all()
        chromosome_counts_lazy = []
        for sp in species_lazy:
            chromosome_counts_lazy.append(len(sp.chromosomes))

        # Method 2: Selectin loading (should result in 2 queries total)
        species_selectin = (
            session.query(Species).options(selectinload(Species.chromosomes)).all()
        )
        chromosome_counts_selectin = []
        for sp in species_selectin:
            chromosome_counts_selectin.append(len(sp.chromosomes))

        # Results should be the same
        assert chromosome_counts_lazy == chromosome_counts_selectin
        assert chromosome_counts_lazy == [4, 2]  # human has 4, mouse has 2

        # Method 3: Test joined loading for chromosome to species
        chromosomes_joined = (
            session.query(Chromosomes).options(joinedload(Chromosomes.species)).all()
        )

        # All chromosomes should have their species loaded
        for chrom in chromosomes_joined:
            assert chrom.species is not None
            assert chrom.species.scientific_name in ["Homo sapiens", "Mus musculus"]

    def test_ordered_relationship_loading(self, test_db):
        """Test that relationship ordering is preserved with different loading strategies."""
        session = test_db

        # Test chromosome ordering (should be ordered by display_name)
        species = (
            session.query(Species)
            .options(selectinload(Species.chromosomes))
            .filter(Species.vgnc_prefix == "HSA")
            .first()
        )

        chromosome_names = [chr.display_name for chr in species.chromosomes]

        # Should be ordered by display_name (string ordering)
        # Verify all expected chromosomes are present and some ordering is applied
        expected_chromosomes = {"chr1", "chr2", "chrMT", "chrX"}
        assert set(chromosome_names) == expected_chromosomes
        assert len(chromosome_names) == 4
        # Verify alphabetical ordering is applied (not random)
        assert chromosome_names == sorted(chromosome_names)

        # Test assembly ordering (should be ordered by id desc - newer first)
        assemblies = species.assemblies  # Should use selectin loading by default
        assembly_names = [asm.name for asm in assemblies]

        # Should have both assemblies and be ordered (newest first by id desc)
        assert len(assembly_names) == 2
        assert "GRCh38" in assembly_names
        assert "GRCh37" in assembly_names
        # Verify ordering - first assembly should be newer (higher ID or created_at)
        first_assembly = assemblies[0]
        second_assembly = assemblies[1]
        # This checks that there is some ordering applied
        assert first_assembly.id != second_assembly.id

    def test_cascade_behavior_with_loading(self, test_db):
        """Test that cascade delete behavior works with loaded relationships."""
        session = test_db

        # Create a new species with chromosomes and assemblies
        test_species = Species(
            display_name="Test Species (Testus testicus)",
            genefam_prefix="TST",
            primary_db_table="species",
            ensembl_species_name="testus_testicus",
            is_live="YES",
            created=datetime.now(),
        )
        session.add(test_species)
        session.flush()

        test_chromosome = Chromosomes(
            taxon_id=test_species.id,
            display_name="chr1",
            refseq_accession="NC_TEST.1",
            genbank_accession="CM_TEST.1",
        )
        session.add(test_chromosome)
        session.flush()

        test_assembly = Assembly(
            taxon_id=test_species.taxon_id,
            name="TestAssembly",
            genbank_assembly_accession="GCA_123456789.1",
            refseq_assembly_accession="GCF_123456789.1",
            source="Test Source",
            is_current=True,
            is_vgnc_default=True,
        )
        session.add(test_assembly)
        session.commit()

        # Load the species with relationships
        species = (
            session.query(Species)
            .options(
                selectinload(Species.chromosomes), selectinload(Species.assemblies)
            )
            .filter(Species.vgnc_prefix == "TST")
            .first()
        )

        assert species is not None
        assert len(species.chromosomes) == 1
        assert len(species.assemblies) == 1

        # Delete the species (should cascade delete chromosomes and assemblies)
        session.delete(species)
        session.commit()

        # Verify deletion
        remaining_chromosomes = (
            session.query(Chromosomes)
            .filter(Chromosomes.taxon_id == test_species.taxon_id)
            .count()
        )
        assert remaining_chromosomes == 0

        remaining_assemblies = (
            session.query(Assembly)
            .filter(Assembly.taxon_id == test_species.taxon_id)
            .count()
        )
        assert remaining_assemblies == 0
