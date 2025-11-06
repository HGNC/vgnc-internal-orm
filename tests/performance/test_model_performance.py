"""Performance benchmarks for ORM model operations.

This module benchmarks model creation, validation, and ORM operations
to ensure they meet performance requirements.
"""

import pytest
from datetime import datetime

from vgnc_internal_orm.models.species import Species, SpeciesLiveStatus
from vgnc_internal_orm.models.genefam import Genefam
from vgnc_internal_orm.models.assembly import Assembly
from vgnc_internal_orm.models.chromosomes import Chromosomes

from tests.performance.conftest import (
    benchmark_db, benchmark_data_factory,
    performance_thresholds, assert_performance_threshold,
    assert_performance_regression
)


class TestModelCreationPerformance:
    """Benchmarks for model creation and instantiation."""

    def test_species_creation_performance(self, benchmark, performance_thresholds):
        """Benchmark Species model creation."""
        def create_species():
            return Species(
                taxon_id=12345,
                genefam_prefix="TST",
                display_name="Test Species",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )

        species = benchmark(create_species)
        assert species.taxon_id == 12345

    def test_genefam_creation_performance(self, benchmark, performance_thresholds):
        """Benchmark Genefam model creation."""
        def create_genefam():
            return Genefam(
                taxon_id=9606,
                assigned_id="TST001",
                assigned_symbol="TST001",
                assigned_name="Test Gene Family",
                status_id=1,
                editor_id=1,
                hcop_support_level=3,
            )

        genefam = benchmark(create_genefam)
        assert genefam.assigned_id == "TST001"

    def test_assembly_creation_performance(self, benchmark, performance_thresholds):
        """Benchmark Assembly model creation."""
        def create_assembly():
            return Assembly(
                name="TEST_ASSEMBLY",
                taxon_id=9606,
                source="Test",
                genbank_assembly_accession="TEST001",
                refseq_assembly_accession="TEST_REF001",
                is_current=True,
                is_vgnc_default=True,
            )

        assembly = benchmark(create_assembly)
        assert assembly.name == "TEST_ASSEMBLY"

    def test_chromosomes_creation_performance(self, benchmark, performance_thresholds):
        """Benchmark Chromosomes model creation."""
        def create_chromosome():
            return Chromosomes(
                display_name="chrTEST",
                taxon_id=9606,
                coord_system="TEST_COORD",
            )

        chromosome = benchmark(create_chromosome)
        assert chromosome.display_name == "chrTEST"

    def test_batch_model_creation(self, benchmark, performance_thresholds):
        """Benchmark batch model creation."""
        def create_models_batch():
            models = []
            for i in range(100):
                model = Species(
                    taxon_id=20000 + i,
                    genefam_prefix=f"BAT{i:03d}",
                    display_name=f"Batch Species {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                models.append(model)
            return models

        models = benchmark(create_models_batch)
        assert len(models) == 100


class TestORMOperationPerformance:
    """Benchmarks for ORM operations (add, update, delete, etc.)."""

    def test_add_single_object(self, benchmark, benchmark_session, performance_thresholds):
        """Benchmark adding a single object to the database."""
        session = benchmark_session

        # Use a counter to generate unique taxon_ids for each benchmark run
        counter = [30000]

        def add_object():
            species = Species(
                taxon_id=counter[0],
                genefam_prefix="ADD",
                display_name="Add Test",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species)
            session.commit()
            session.refresh(species)
            # Increment counter for next run
            counter[0] += 1
            return species

        result = benchmark(add_object)
        # Just verify the result structure, not the specific taxon_id since it changes
        assert result.taxon_id >= 30000

    def test_add_multiple_objects(self, benchmark, benchmark_session, performance_thresholds):
        """Benchmark adding multiple objects to the database."""
        session = benchmark_session

        # Use a counter to generate unique taxon_ids for each benchmark run
        counter = [31000]

        def add_objects():
            objects = []
            for i in range(50):
                obj = Species(
                    taxon_id=counter[0] + i,
                    genefam_prefix=f"ADD{i:03d}",
                    display_name=f"Add Test {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                objects.append(obj)

            session.add_all(objects)
            session.commit()

            # Refresh all objects
            for obj in objects:
                session.refresh(obj)

            # Increment counter for next run
            counter[0] += 50
            return len(objects)

        result = benchmark(add_objects)
        assert_performance_threshold(benchmark, performance_thresholds["bulk_insert"], "add multiple objects")
        assert result == 50

    def test_update_single_object(self, benchmark, benchmark_db, performance_thresholds):
        """Benchmark updating a single object."""
        session = benchmark_db

        def update_object(session):
            # First create an object
            species = Species(
                taxon_id=40000,
                genefam_prefix="UPD",
                display_name="Original Name",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species)
            session.commit()

            # Update the object
            species.display_name = "Updated Name"
            session.commit()
            session.refresh(species)

            return species

        result = benchmark(update_object, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "update single object")
        assert result.display_name == "Updated Name"

    def test_update_multiple_objects(self, benchmark, benchmark_db, performance_thresholds):
        """Benchmark updating multiple objects."""
        session = benchmark_db

        def update_objects(session):
            # First create objects
            objects = []
            for i in range(25):
                obj = Species(
                    taxon_id=41000 + i,
                    genefam_prefix=f"UPD{i:03d}",
                    display_name=f"Original {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                objects.append(obj)

            session.add_all(objects)
            session.commit()

            # Update all objects
            count = session.query(Species).filter(
                Species.taxon_id >= 41000,
                Species.taxon_id < 41025
            ).update({"display_name": "Updated Name"})

            session.commit()

            return count

        result = benchmark(update_objects, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "update multiple objects")
        assert result == 25

    def test_delete_single_object(self, benchmark, benchmark_db, performance_thresholds):
        """Benchmark deleting a single object."""
        session = benchmark_db

        def delete_object(session):
            # First create an object
            species = Species(
                taxon_id=50000,
                genefam_prefix="DEL",
                display_name="Delete Test",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species)
            session.commit()
            session.refresh(species)

            # Delete the object
            session.delete(species)
            session.commit()

            # Verify deletion
            deleted = session.get(Species, 50000)
            return deleted is None

        result = benchmark(delete_object, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "delete single object")
        assert result is True

    def test_delete_multiple_objects(self, benchmark, benchmark_db, performance_thresholds):
        """Benchmark deleting multiple objects."""
        session = benchmark_db

        def delete_objects(session):
            # First create objects
            objects = []
            for i in range(30):
                obj = Species(
                    taxon_id=51000 + i,
                    genefam_prefix=f"DEL{i:03d}",
                    display_name=f"Delete Test {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                objects.append(obj)

            session.add_all(objects)
            session.commit()

            # Delete all objects
            count = session.query(Species).filter(
                Species.taxon_id >= 51000,
                Species.taxon_id < 51030
            ).delete()

            session.commit()

            return count

        result = benchmark(delete_objects, session)
        assert_performance_threshold(benchmark, performance_thresholds["bulk_insert"], "delete multiple objects")
        assert result == 30


class TestSessionOperationPerformance:
    """Benchmarks for SQLAlchemy session operations."""

    def test_session_commit_performance(self, benchmark, benchmark_db, performance_thresholds):
        """Benchmark session commit performance."""
        session = benchmark_db

        def commit_operation(session):
            # Create multiple objects
            for i in range(20):
                species = Species(
                    taxon_id=60000 + i,
                    genefam_prefix=f"COM{i:03d}",
                    display_name=f"Commit Test {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                session.add(species)

            # Commit
            session.commit()

            return True

        result = benchmark(commit_operation, session)
        assert_performance_threshold(benchmark, performance_thresholds["bulk_insert"], "session commit")
        assert result is True

    def test_session_rollback_performance(self, benchmark, benchmark_db, performance_thresholds):
        """Benchmark session rollback performance."""
        session = benchmark_db

        def rollback_operation(session):
            # Create multiple objects
            for i in range(15):
                species = Species(
                    taxon_id=61000 + i,
                    genefam_prefix=f"ROL{i:03d}",
                    display_name=f"Rollback Test {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                session.add(species)

            # Rollback
            session.rollback()

            return True

        result = benchmark(rollback_operation, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "session rollback")
        assert result is True

    def test_session_flush_performance(self, benchmark, benchmark_db, performance_thresholds):
        """Benchmark session flush performance."""
        session = benchmark_db

        def flush_operation(session):
            # Create multiple objects and flush
            for i in range(10):
                species = Species(
                    taxon_id=62000 + i,
                    genefam_prefix=f"FLU{i:03d}",
                    display_name=f"Flush Test {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                session.add(species)

            # Flush (but don't commit)
            session.flush()

            # Rollback at the end
            session.rollback()

            return True

        result = benchmark(flush_operation, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "session flush")
        assert result is True

    def test_session_refresh_performance(self, benchmark, benchmark_db, performance_thresholds):
        """Benchmark session refresh performance."""
        session = benchmark_db

        def refresh_operation(session):
            # Create an object
            species = Species(
                taxon_id=70000,
                genefam_prefix="REF",
                display_name="Refresh Test",
                is_live=SpeciesLiveStatus.YES,
                created=datetime.now(),
            )
            session.add(species)
            session.commit()

            # Refresh multiple times
            for _ in range(10):
                session.refresh(species)

            return species

        result = benchmark(refresh_operation, session)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "session refresh")
        assert result.taxon_id == 70000


class TestValidationPerformance:
    """Benchmarks for model validation operations."""

    def test_enum_validation_performance(self, benchmark, performance_thresholds):
        """Benchmark enum field validation."""
        def validate_enum():
            for i in range(100):
                # Create species with different enum values
                species = Species(
                    taxon_id=80000 + i,
                    genefam_prefix=f"VAL{i:03d}",
                    display_name=f"Validation Test {i}",
                    is_live=SpeciesLiveStatus.YES,  # Enum validation
                    created=datetime.now(),
                )
                # Just creating the object validates the enum

            return 100

        result = benchmark(validate_enum)
        assert_performance_threshold(benchmark, performance_thresholds["bulk_insert"], "enum validation")
        assert result == 100

    def test_string_validation_performance(self, benchmark, performance_thresholds):
        """Benchmark string field validation."""
        def validate_strings():
            for i in range(50):
                # Test with different string lengths
                long_string = "A" * (100 + i)  # Strings from 100 to 150 chars
                species = Species(
                    taxon_id=81000 + i,
                    genefam_prefix="VAL",
                    display_name=long_string,
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                # Just creating the object validates string constraints

            return 50

        result = benchmark(validate_strings)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "string validation")
        assert result == 50

    def test_datetime_validation_performance(self, benchmark, performance_thresholds):
        """Benchmark datetime field validation."""
        def validate_datetimes():
            for i in range(75):
                # Test with different datetime values
                dt = datetime(2024, 1, 1, i % 24, i % 60, i % 60)
                species = Species(
                    taxon_id=82000 + i,
                    genefam_prefix="VAL",
                    display_name="Datetime Test",
                    is_live=SpeciesLiveStatus.YES,
                    created=dt,  # Datetime validation
                )
                # Just creating the object validates the datetime

            return 75

        result = benchmark(validate_datetimes)
        assert_performance_threshold(benchmark, performance_thresholds["simple_query"], "datetime validation")
        assert result == 75


class TestSerializationPerformance:
    """Benchmarks for model serialization operations."""

    def test_model_dict_serialization(self, benchmark, benchmark_session, performance_thresholds):
        """Benchmark model to_dict serialization performance."""
        session = benchmark_session

        # Use a counter to generate unique taxon_ids for each benchmark run
        counter = [90000]

        def serialize_models():
            # Create models
            models = []
            for i in range(25):
                species = Species(
                    taxon_id=counter[0] + i,
                    genefam_prefix=f"SER{i:03d}",
                    display_name=f"Serialization Test {i}",
                    is_live=SpeciesLiveStatus.YES,
                    created=datetime.now(),
                )
                session.add(species)
                models.append(species)

            session.commit()
            # Increment counter for next run
            counter[0] += 25

            # Serialize models to dict
            dict_data = []
            for model in models:
                if hasattr(model, 'to_dict'):
                    dict_data.append(model.to_dict())
                else:
                    # Fallback serialization
                    dict_data.append({
                        'taxon_id': model.taxon_id,
                        'genefam_prefix': model.genefam_prefix,
                        'display_name': model.display_name,
                        'is_live': model.is_live,
                        'created': model.created,
                    })

            return len(dict_data)

        result = benchmark(serialize_models)
        assert_performance_threshold(benchmark, performance_thresholds["bulk_insert"], "model serialization")
        assert result == 25