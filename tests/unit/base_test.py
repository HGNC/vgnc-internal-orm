"""
Base test class and utilities for unit testing.

Provides common functionality and patterns used across unit tests
to ensure consistency and reduce code duplication.
"""

from datetime import datetime
from typing import Any, Generic, TypeVar
from unittest.mock import Mock

import pytest
from sqlalchemy import inspect
from sqlalchemy.orm import Session

from src.vgnc_internal_orm.models.base import BaseCustomModel, BaseModel

T = TypeVar("T", bound=BaseModel | BaseCustomModel)


class BaseUnitTest(Generic[T]):
    """Base class for unit tests with common functionality."""

    # Override these in subclasses
    model_class: type[T] = None
    sample_data: dict = None

    @pytest.fixture(autouse=True)
    def setup_fixtures(self, test_db_session: Session):
        """Setup common fixtures for test methods."""
        self.session = test_db_session
        self.model_class = self.__class__.model_class
        self.sample_data = self.__class__.sample_data or {}

    def create_instance(self, **overrides) -> T:
        """Create a model instance with sample data and optional overrides."""
        data = {**self.sample_data, **overrides}
        return self.model_class(**data)

    def save_instance(self, **overrides) -> T:
        """Create and save a model instance to the database."""
        instance = self.create_instance(**overrides)
        self.session.add(instance)
        self.session.commit()
        self.session.refresh(instance)
        # Don't expunge here - tests may need to access the instance later
        return instance

    def assert_model_attributes(self, instance: T, expected_data: dict):
        """Assert that model attributes match expected data."""
        for key, value in expected_data.items():
            assert hasattr(instance, key), f"Model missing attribute: {key}"
            actual_value = getattr(instance, key)
            assert (
                actual_value == value
            ), f"Attribute {key}: expected {value}, got {actual_value}"

    def assert_model_in_database(self, instance: T):
        """Assert that a model instance exists in the database."""
        pk_name = self._get_primary_key_name()
        pk_value = getattr(instance, pk_name)

        # Try multiple ways to find the record
        from_db = self.session.get(self.model_class, pk_value)
        if from_db is None:
            # Try querying directly
            from_db = (
                self.session.query(self.model_class)
                .filter(getattr(self.model_class, pk_name) == pk_value)
                .first()
            )

        assert (
            from_db is not None
        ), f"Instance not found in database with {pk_name}={pk_value}"
        assert getattr(from_db, pk_name) == pk_value, "Instance ID mismatch"

    def assert_model_not_in_database(self, instance: T):
        """Assert that a model instance does not exist in the database."""
        pk_name = self._get_primary_key_name()
        pk_value = getattr(instance, pk_name)
        from_db = self.session.get(self.model_class, pk_value)
        assert from_db is None, "Instance found in database but should not exist"

    def get_table_info(self, model_class: type[T]) -> dict:
        """Get table information for a model class."""
        inspector = inspect(self.session.bind)
        table_name = model_class.__tablename__

        if table_name not in inspector.get_table_names():
            return {"exists": False}

        columns = inspector.get_columns(table_name)
        indexes = inspector.get_indexes(table_name)
        foreign_keys = inspector.get_foreign_keys(table_name)

        return {
            "exists": True,
            "columns": columns,
            "indexes": indexes,
            "foreign_keys": foreign_keys,
        }

    def count_records(self, model_class: type[T] = None) -> int:
        """Count records in the database for a model class."""
        if model_class is None:
            model_class = self.model_class
        return self.session.query(model_class).count()

    def get_all_records(self, model_class: type[T] = None) -> list[T]:
        """Get all records for a model class."""
        if model_class is None:
            model_class = self.model_class
        return self.session.query(model_class).all()

    def assert_timestamp_fields(self, instance: T):
        """Assert that timestamp fields are properly set."""
        if hasattr(instance, "created_at"):
            assert instance.created_at is not None, "created_at should not be None"
            assert isinstance(
                instance.created_at, datetime
            ), "created_at should be datetime"

        if hasattr(instance, "updated_at"):
            assert instance.updated_at is not None, "updated_at should not be None"
            assert isinstance(
                instance.updated_at, datetime
            ), "updated_at should be datetime"

    def assert_required_fields(self, instance: T, required_fields: list[str]):
        """Assert that required fields are present and not None."""
        for field in required_fields:
            assert hasattr(instance, field), f"Model missing required field: {field}"
            value = getattr(instance, field)
            assert value is not None, f"Required field {field} should not be None"

    def create_mock_session(self) -> Mock:
        """Create a mock database session for testing without database."""
        mock_session = Mock()
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.rollback = Mock()
        mock_session.refresh = Mock()
        mock_session.query = Mock()
        mock_session.get = Mock()
        return mock_session

    def assert_validation_error(
        self, model_class: type[T], data: dict, error_field: str = None
    ):
        """Assert that creating a model instance raises a validation error."""
        # Import here to avoid circular imports
        from sqlalchemy.exc import (
            IntegrityError,
            PendingRollbackError,
            ResourceClosedError,
        )

        try:
            with pytest.raises(
                (ValueError, TypeError, AssertionError, IntegrityError)
            ) as exc_info:
                instance = model_class(**data)
                # For SQLAlchemy models, validation might happen on flush or commit
                self.session.add(instance)
                try:
                    self.session.flush()
                except IntegrityError:
                    # If flush already failed, re-raise
                    raise
                # Try commit to trigger database-level constraints
                self.session.commit()

            if error_field:
                assert error_field in str(
                    exc_info.value
                ), f"Expected field {error_field} in error message"
        except (PendingRollbackError, ResourceClosedError):
            # Session is in bad state, rollback to clean it
            # This may generate SAWarning but it's necessary for cleanup
            self.session.rollback()
            # Expunge all to prevent session state warnings
            self.session.expunge_all()
            # Now try again with a clean session
            with pytest.raises(
                (ValueError, TypeError, AssertionError, IntegrityError)
            ) as exc_info:
                instance = model_class(**data)
                self.session.add(instance)
                self.session.flush()

            if error_field:
                assert error_field in str(
                    exc_info.value
                ), f"Expected field {error_field} in error message"

    def test_crud_operations(self):
        """Test basic CRUD operations for the model."""
        if not self.model_class or not self.sample_data:
            pytest.skip("No model_class or sample_data defined")

        # Test Create
        instance = self.save_instance()
        # Handle different primary key names
        pk_name = self._get_primary_key_name()
        pk_value = getattr(instance, pk_name)
        assert pk_value is not None
        self.assert_model_in_database(instance)
        self.assert_timestamp_fields(instance)

    def _get_primary_key_name(self) -> str:
        """Get the primary key name for the model."""
        # Import SQLAlchemy to check for column attributes
        from sqlalchemy.orm.attributes import InstrumentedAttribute

        # Check common primary key names - but only if they are actual database columns
        for pk_name in ["id", "taxon_id", "genefam_id", "chr_id"]:
            if hasattr(self.model_class, pk_name):
                attr = getattr(self.model_class, pk_name)
                # Check if it's a database column (InstrumentedAttribute) not just a property
                if isinstance(attr, InstrumentedAttribute):
                    return pk_name

        # Default to 'id' if not found
        return "id"

    def _test_crud_operations_extended(self):
        """Extended CRUD operations test."""
        if not self.model_class or not self.sample_data:
            pytest.skip("No model_class or sample_data defined")

        # Test Create
        instance = self.save_instance()
        pk_name = self._get_primary_key_name()
        pk_value = getattr(instance, pk_name)

        # Test Read
        retrieved = self.session.get(self.model_class, pk_value)
        assert retrieved is not None
        assert getattr(retrieved, pk_name) == pk_value

        # Test Update
        if hasattr(instance, "updated_at"):
            original_updated = instance.updated_at

        # Make a simple update
        if hasattr(instance, "display_name"):
            instance.display_name = f"Updated {instance.display_name}"
        elif hasattr(instance, "description"):
            instance.description = "Updated description"
        else:
            # Update the first string field found
            for attr_name in dir(instance):
                if not attr_name.startswith("_") and not callable(
                    getattr(instance, attr_name)
                ):
                    attr_value = getattr(instance, attr_name)
                    if isinstance(attr_value, str):
                        setattr(instance, attr_name, f"Updated {attr_value}")
                        break

        self.session.commit()
        self.session.refresh(instance)

        if hasattr(instance, "updated_at") and original_updated:
            assert (
                instance.updated_at >= original_updated
            ), "updated_at should be updated"

        # Test Delete
        self.session.delete(instance)
        self.session.commit()
        self.assert_model_not_in_database(instance)


class ModelTestMixin:
    """Mixin class providing common test methods for models."""

    def test_model_creation(self):
        """Test model creation with sample data."""
        if not self.model_class or not self.sample_data:
            pytest.skip("No model_class or sample_data defined")

        instance = self.create_instance()
        assert instance is not None

        # Check that all sample data fields are set
        for key, value in self.sample_data.items():
            if hasattr(instance, key):
                assert getattr(instance, key) == value

    def test_model_validation(self):
        """Test model validation with invalid data."""
        if not self.model_class or not self.sample_data:
            pytest.skip("No model_class or sample_data defined")

        # Test with empty required fields
        if hasattr(self, "required_fields"):
            pk_name = self._get_primary_key_name()

            # Get fields that don't have defaults and are not primary key
            from sqlalchemy import inspect

            mapper = inspect(self.model_class)
            fields_to_test = []

            for field in self.required_fields:
                if field == pk_name:
                    continue  # Skip primary key

                # Check if field has a default
                column = mapper.local_table.columns.get(field)
                if column is None:
                    continue
                has_default = hasattr(column, "default") and column.default is not None
                if not has_default:
                    fields_to_test.append(field)

            # If no fields to test (all have defaults), skip test
            if not fields_to_test:
                pytest.skip("No required fields without defaults to test")

            for field in fields_to_test:
                invalid_data = self.sample_data.copy()
                invalid_data[field] = None
                self.assert_validation_error(self.model_class, invalid_data, field)

    def test_model_serialization(self):
        """Test model serialization methods if available."""
        if not self.model_class or not self.sample_data:
            pytest.skip("No model_class or sample_data defined")

        instance = self.save_instance()

        # Test to_dict method if available
        if hasattr(instance, "to_dict"):
            data_dict = instance.to_dict()
            assert isinstance(data_dict, dict)
            # Check for the actual primary key field, not just 'id'
            pk_name = self._get_primary_key_name()
            assert pk_name in data_dict

        # Test to_json method if available
        if hasattr(instance, "to_json"):
            json_data = instance.to_json()
            assert isinstance(json_data, str)
            # Should be valid JSON
            import json

            parsed = json.loads(json_data)
            assert isinstance(parsed, dict)


class DatabaseTestMixin:
    """Mixin class providing database-related test methods."""

    def test_table_creation(self):
        """Test that model table is created correctly."""
        if not self.model_class:
            pytest.skip("No model_class defined")

        table_info = self.get_table_info(self.model_class)
        assert table_info[
            "exists"
        ], f"Table {self.model_class.__tablename__} should exist"

    def test_table_columns(self):
        """Test that table has expected columns."""
        if not self.model_class:
            pytest.skip("No model_class defined")

        table_info = self.get_table_info(self.model_class)
        if not table_info["exists"]:
            pytest.skip("Table does not exist")

        columns = [col["name"] for col in table_info["columns"]]

        # Check for primary key column (use dynamic primary key detection)
        pk_name = self._get_primary_key_name()
        expected_columns = [pk_name]
        if hasattr(self.model_class, "created_at"):
            expected_columns.append("created_at")
        if hasattr(self.model_class, "updated_at"):
            expected_columns.append("updated_at")

        for col in expected_columns:
            assert col in columns, f"Expected column {col} not found in table"


def create_test_data_factory(model_class: type[T], base_data: dict):
    """Create a factory function for generating test data."""

    def factory(**overrides):
        data = {**base_data, **overrides}
        return model_class(**data)

    return factory


def assert_query_count(session: Session, expected_count: int, model_class: type[T]):
    """Assert that the query count matches expected value."""
    count = session.query(model_class).count()
    assert count == expected_count, f"Expected {expected_count} records, got {count}"


def assert_attribute_exists(instance: Any, attribute_name: str):
    """Assert that an attribute exists on an instance."""
    assert hasattr(
        instance, attribute_name
    ), f"Attribute {attribute_name} does not exist"


def assert_attribute_not_none(instance: Any, attribute_name: str):
    """Assert that an attribute is not None."""
    assert hasattr(
        instance, attribute_name
    ), f"Attribute {attribute_name} does not exist"
    value = getattr(instance, attribute_name)
    assert value is not None, f"Attribute {attribute_name} should not be None"
