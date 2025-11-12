"""Working models/base.py comprehensive tests with unique class names."""

import pytest
import tempfile
import os
from datetime import datetime, timezone
from unittest.mock import Mock, patch, MagicMock
from sqlalchemy import create_engine, text, inspect, Column, Integer, String, DateTime, Boolean, ForeignKey
from sqlalchemy.orm import sessionmaker, Session, relationship
from sqlalchemy.ext.declarative import declarative_base

from vgnc_internal_orm.models.base import (
    BaseModel,
    TimestampMixin,
    BaseCustomModel,
)
from vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


class TestBaseModelBasicFunctionality:
    """Test BaseModel basic functionality with unique class names."""

    def setup_method(self):
        """Set up test database and session for each test."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.engine = create_engine(self.config.database_url.get_secret_value())
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Use unique class names and metadata instances
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        self.TestBase = declarative_base(metadata=MetaData())

        class TestBaseModel(BaseModel, self.TestBase):
            __tablename__ = f"test_base_models_{unique_id}"

            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            description = Column(String(500))
            is_active = Column(Boolean, default=True)
            custom_field = Column(String(50))

        self.TestBaseModel = TestBaseModel
        self.TestBase.metadata.create_all(self.engine)

    def teardown_method(self):
        """Clean up after each test."""
        self.TestBase.metadata.drop_all(self.engine)

    def test_basemodel_instantiation(self):
        """Test BaseModel instantiation."""
        model = self.TestBaseModel(
            name="Test Model",
            description="Test description",
            is_active=True
        )
        assert model.name == "Test Model"
        assert model.description == "Test description"
        assert model.is_active is True
        assert model.custom_field is None

    def test_basemodel_database_operations(self):
        """Test BaseModel database operations."""
        session = self.SessionLocal()

        # Create
        test_model = self.TestBaseModel(
            name="Database Test",
            description="Testing database operations"
        )
        session.add(test_model)
        session.commit()
        session.refresh(test_model)

        assert test_model.id is not None
        assert test_model.created_at is not None
        assert test_model.updated_at is not None
        assert isinstance(test_model.created_at, datetime)

        # Read
        retrieved = session.query(self.TestBaseModel).filter_by(id=test_model.id).first()
        assert retrieved is not None
        assert retrieved.name == "Database Test"

        # Update
        retrieved.name = "Updated Name"
        session.commit()
        session.refresh(retrieved)
        assert retrieved.name == "Updated Name"
        assert retrieved.updated_at >= retrieved.created_at

        # Delete
        session.delete(retrieved)
        session.commit()
        deleted = session.query(self.TestBaseModel).filter_by(id=retrieved.id).first()
        assert deleted is None

        session.close()

    def test_basemodel_timestamp_functionality(self):
        """Test BaseModel timestamp functionality."""
        session = self.SessionLocal()

        model = self.TestBaseModel(name="Timestamp Test")
        session.add(model)
        session.commit()

        original_created = model.created_at
        original_updated = model.updated_at
        original_name = model.name

        # Wait a bit to ensure different timestamps
        import time
        time.sleep(0.01)

        # Update the model
        model.name = "Updated Timestamp Test"
        session.commit()
        session.refresh(model)

        assert model.created_at == original_created
        assert model.updated_at >= original_updated
        assert model.name != original_name

        session.close()

    def test_basemodel_field_attributes(self):
        """Test BaseModel field attributes."""
        model = self.TestBaseModel(
            name="Field Test",
            description="Testing field attributes",
            is_active=False
        )

        # Test that attributes are set correctly
        assert hasattr(model, 'id')
        assert hasattr(model, 'name')
        assert hasattr(model, 'description')
        assert hasattr(model, 'is_active')
        assert hasattr(model, 'custom_field')
        assert hasattr(model, 'created_at')
        assert hasattr(model, 'updated_at')

        # Test that timestamp fields are initially None for new instances
        assert model.created_at is None
        assert model.updated_at is None

    def test_basemodel_default_values(self):
        """Test BaseModel default values."""
        model = self.TestBaseModel(name="Defaults Test")

        # Test boolean default
        assert model.is_active is True  # Should default to True

        # Test nullable fields default to None
        assert model.description is None
        assert model.custom_field is None

    def test_basemodel_multiple_instances(self):
        """Test BaseModel with multiple instances."""
        session = self.SessionLocal()

        models = [
            self.TestBaseModel(name=f"Model {i}", description=f"Description {i}")
            for i in range(5)
        ]

        session.add_all(models)
        session.commit()

        # Verify all models were created with proper timestamps
        for i, model in enumerate(models):
            assert model.id is not None
            assert model.name == f"Model {i}"
            assert model.description == f"Description {i}"
            assert model.created_at is not None
            assert model.updated_at is not None

        # Test querying
        all_models = session.query(self.TestBaseModel).all()
        assert len(all_models) == 5

        session.close()


class TestTimestampMixinFunctionality:
    """Test TimestampMixin functionality."""

    def setup_method(self):
        """Set up test database for timestamp tests."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.engine = create_engine(self.config.database_url.get_secret_value())
        self.SessionLocal = sessionmaker(bind=self.engine)

    def test_timestamp_mixin_inheritance(self):
        """Test TimestampMixin inheritance."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        mixin_base = declarative_base()

        class TimestampedTestModel(TimestampMixin, mixin_base):
            __tablename__ = f"timestamped_models_{unique_id}"

            id = Column(Integer, primary_key=True)
            name = Column(String(100))

        mixin_base.metadata.create_all(self.engine)

        model = TimestampedTestModel(name="Timestamp Test")

        # Check that timestamp fields exist
        assert hasattr(model, 'created_at')
        assert hasattr(model, 'updated_at')

        # Test database operations
        session = self.SessionLocal()
        session.add(model)
        session.commit()
        session.refresh(model)

        # Verify timestamps were set
        assert model.created_at is not None
        assert model.updated_at is not None
        assert isinstance(model.created_at, datetime)
        assert isinstance(model.updated_at, datetime)

        session.close()

    def test_timestamp_mixin_update_behavior(self):
        """Test TimestampMixin update behavior."""
        import uuid
        unique_id = str(uuid.uuid4())[:8]

        mixin_base = declarative_base()

        class TimestampedUpdateModel(TimestampMixin, mixin_base):
            __tablename__ = f"timestamped_update_models_{unique_id}"
            id = Column(Integer, primary_key=True)
            name = Column(String(100))

        mixin_base.metadata.create_all(self.engine)
        session = self.SessionLocal()

        model = TimestampedUpdateModel(name="Original Name")
        session.add(model)
        session.commit()
        session.refresh(model)

        original_created = model.created_at
        original_updated = model.updated_at

        # Wait a bit to ensure different timestamps
        import time
        time.sleep(0.01)

        # Update the model
        model.name = "Updated Name"
        session.commit()
        session.refresh(model)

        # Created timestamp should not change
        assert model.created_at == original_created
        # Updated timestamp should be greater than or equal to original
        assert model.updated_at >= original_updated

        session.close()


class TestBaseCustomModel:
    """Test BaseCustomModel functionality."""

    def test_base_custom_model_import(self):
        """Test BaseCustomModel import and basic functionality."""
        # Test that BaseCustomModel can be imported
        assert BaseCustomModel is not None

        # Test that it can be used as a base class
        class CustomTestModel(BaseCustomModel):
            __tablename__ = "custom_test_models"
            id = Column(Integer, primary_key=True)
            name = Column(String(100))

        # Should be able to create instances
        model = CustomTestModel(name="Custom Test")
        assert model.name == "Custom Test"


class TestModelEdgeCases:
    """Test edge cases and error conditions."""

    def setup_method(self):
        """Set up test database for edge case tests."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.engine = create_engine(self.config.database_url.get_secret_value())
        self.SessionLocal = sessionmaker(bind=self.engine)

        import uuid
        unique_id = str(uuid.uuid4())[:8]

        self.TestBase = declarative_base()

        class EdgeCaseTestModel(BaseModel, self.TestBase):
            __tablename__ = f"edge_case_models_{unique_id}"
            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            description = Column(String(500))
            is_active = Column(Boolean, default=True)

        self.EdgeCaseTestModel = EdgeCaseTestModel
        self.TestBase.metadata.create_all(self.engine)

    def teardown_method(self):
        """Clean up after edge case tests."""
        self.TestBase.metadata.drop_all(self.engine)

    def test_basemodel_with_none_values(self):
        """Test BaseModel with None values."""
        model = self.EdgeCaseTestModel(name="None Test", description=None)
        assert model.description is None

        session = self.SessionLocal()
        session.add(model)
        session.commit()
        session.refresh(model)

        # Should handle None values correctly
        assert model.description is None
        session.close()

    def test_basemodel_with_empty_strings(self):
        """Test BaseModel with empty strings."""
        model = self.EdgeCaseTestModel(name="Empty Test", description="")
        assert model.description == ""

        session = self.SessionLocal()
        session.add(model)
        session.commit()
        session.refresh(model)

        # Should handle empty strings correctly
        assert model.description == ""
        session.close()

    def test_basemodel_with_unicode_characters(self):
        """Test BaseModel with unicode characters."""
        unicode_name = "Тест Юникод 🚀"
        unicode_description = "测试Unicode内容"

        model = self.EdgeCaseTestModel(name=unicode_name, description=unicode_description)
        assert model.name == unicode_name
        assert model.description == unicode_description

        session = self.SessionLocal()
        session.add(model)
        session.commit()
        session.refresh(model)

        # Should handle unicode correctly
        assert model.name == unicode_name
        assert model.description == unicode_description
        session.close()

    def test_basemodel_with_maximum_field_lengths(self):
        """Test BaseModel with maximum field lengths."""
        max_name = "x" * 100  # Maximum length for name field
        max_description = "y" * 500  # Maximum length for description field

        model = self.EdgeCaseTestModel(name=max_name, description=max_description)
        assert len(model.name) == 100
        assert len(model.description) == 500

        session = self.SessionLocal()
        session.add(model)
        session.commit()
        session.refresh(model)

        # Should handle maximum lengths correctly
        assert model.name == max_name
        assert model.description == max_description
        session.close()

    def test_basemodel_rollback_operations(self):
        """Test BaseModel with transaction rollback."""
        session = self.SessionLocal()

        # Create a model
        model = self.EdgeCaseTestModel(name="Rollback Test")
        session.add(model)
        session.commit()

        model_id = model.id
        assert model_id is not None

        # Start a new transaction and rollback
        model.name = "Updated Name"
        session.rollback()

        # Verify the change was rolled back
        session.refresh(model)
        assert model.name == "Rollback Test"

        session.close()


class TestModelStringRepresentation:
    """Test model string representation methods."""

    def setup_method(self):
        """Set up test database for string representation tests."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.engine = create_engine(self.config.database_url.get_secret_value())
        self.SessionLocal = sessionmaker(bind=self.engine)

        import uuid
        unique_id = str(uuid.uuid4())[:8]

        self.TestBase = declarative_base()

        class StringTestModel(BaseModel, self.TestBase):
            __tablename__ = f"string_test_models_{unique_id}"
            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            description = Column(String(500))

        self.StringTestModel = StringTestModel

    def test_basemodel_string_representation(self):
        """Test BaseModel string representation."""
        model = self.StringTestModel(name="String Test", id=123)

        # Test __str__ method
        str_repr = str(model)
        assert isinstance(str_repr, str)

        # Test __repr__ method
        repr_str = repr(model)
        assert isinstance(repr_str, str)
        assert "String Test" in repr_str

    def test_basemodel_comparison(self):
        """Test BaseModel comparison operations."""
        model1 = self.StringTestModel(name="Test Model 1")
        model2 = self.StringTestModel(name="Test Model 2")

        # Models with different IDs should not be equal
        assert model1 != model2

        # Same model should be equal to itself
        assert model1 == model1


# Need to import MetaData for unique metadata instances
from sqlalchemy.schema import MetaData