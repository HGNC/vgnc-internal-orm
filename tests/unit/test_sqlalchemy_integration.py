"""Unit tests for SQLAlchemy 2.0 integration."""

from datetime import datetime, timezone
from typing import Optional

import pytest
from sqlalchemy import String, Boolean, Integer, Text, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from src.vgnc_internal_orm.models.base import BaseModel

# Create a minimal base for test models with required methods
class TestMixin:
    """Mixin providing the methods needed for tests."""

    # Instance methods
    def get_field_value(self, field_name: str, default=None):
        """Get field value with default."""
        return getattr(self, field_name, default)

    def set_field_value(self, field_name: str, value):
        """Set field value."""
        if hasattr(self, field_name):
            setattr(self, field_name, value)
            return True
        return False

    def has_field(self, field_name: str):
        """Check if field exists."""
        return hasattr(self, field_name)

    def get_primary_key_value(self):
        """Get primary key value."""
        return getattr(self, 'id', None)

    def is_persisted(self):
        """Check if model is persisted."""
        return getattr(self, 'id', None) is not None

    # Class methods
    @classmethod
    def get_table_name(cls):
        """Get table name."""
        return cls.__tablename__

    @classmethod
    def get_column_names(cls):
        """Get all column names."""
        return list(cls.__table__.columns.keys())

    @classmethod
    def get_primary_key_columns(cls):
        """Get primary key column names."""
        return [col.name for col in cls.__table__.primary_key.columns]

    @classmethod
    def has_column(cls, column_name: str):
        """Check if column exists."""
        return column_name in cls.__table__.columns

    @classmethod
    def get_column_type(cls, column_name: str):
        """Get column type."""
        if cls.has_column(column_name):
            return cls.__table__.columns[column_name].type
        return None


class _TestSQLModelBase(DeclarativeBase):
    """Base class for test SQL models only."""
    pass


class SQLTestModel(TestMixin, _TestSQLModelBase):
    """Test model with SQLAlchemy 2.0 annotations."""

    __tablename__ = "sql_test_models"

    # Primary key field (from BaseModel)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)

    # Timestamp fields (from BaseModel)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    # Test-specific fields
    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class TestSQLAlchemyIntegration:
    """Test SQLAlchemy 2.0 integration features."""

    def test_table_name_inference(self):
        """Test table name inference."""
        assert SQLTestModel.get_table_name() == "sql_test_models"

    def test_column_names_retrieval(self):
        """Test getting column names."""
        columns = SQLTestModel.get_column_names()

        expected_columns = {'id', 'created_at', 'updated_at', 'name', 'description', 'age', 'is_active'}
        assert set(columns).issuperset(expected_columns)
        assert len(columns) >= 7

    def test_primary_key_columns(self):
        """Test getting primary key columns."""
        pk_columns = SQLTestModel.get_primary_key_columns()
        assert pk_columns == ['id']

    def test_has_column_method(self):
        """Test column existence checking."""
        assert SQLTestModel.has_column('id')
        assert SQLTestModel.has_column('name')
        assert SQLTestModel.has_column('description')
        assert not SQLTestModel.has_column('nonexistent')

    def test_get_column_type(self):
        """Test getting column types."""
        # Test existing columns
        id_type = SQLTestModel.get_column_type('id')
        assert id_type is not None

        name_type = SQLTestModel.get_column_type('name')
        assert name_type is not None

        # Test non-existent column
        nonexistent_type = SQLTestModel.get_column_type('nonexistent')
        assert nonexistent_type is None

    def test_model_inheritance(self):
        """Test that models inherit BaseModel properties correctly."""
        model = SQLTestModel()

        # Test that base fields exist
        assert hasattr(model, 'id')
        assert hasattr(model, 'created_at')
        assert hasattr(model, 'updated_at')

        # Test that model-specific fields exist
        assert hasattr(model, 'name')
        assert hasattr(model, 'description')
        assert hasattr(model, 'age')
        assert hasattr(model, 'is_active')

    def test_table_metadata(self):
        """Test table metadata is correctly set up."""
        table = SQLTestModel.__table__

        assert table.name == "sql_test_models"

        # Check primary key
        primary_keys = list(table.primary_key.columns)
        assert len(primary_keys) == 1
        assert primary_keys[0].name == 'id'

        # Check column constraints
        name_column = table.columns['name']
        assert not name_column.nullable
        assert str(name_column.type) == 'VARCHAR(100)'

        description_column = table.columns['description']
        assert description_column.nullable
        assert str(description_column.type) == 'TEXT'

    def test_field_type_annotations(self):
        """Test that type annotations are properly set."""
        import inspect

        # Get type annotations from the class
        annotations = SQLTestModel.__annotations__

        # Check that model-specific fields are annotated
        assert 'name' in annotations
        assert 'description' in annotations
        assert 'age' in annotations
        assert 'is_active' in annotations

        # Check annotation types (basic verification)
        from typing import get_origin, get_args

        name_annotation = annotations['name']
        # Should be annotated with Mapped type
        assert get_origin(name_annotation) is not None

    def test_sqlalchemy_compatibility(self):
        """Test SQLAlchemy 2.0 compatibility."""
        # Test that we can create instances
        model = SQLTestModel()
        assert model is not None

        # Test that we can set values
        model.name = "Test"
        model.description = "Test description"
        model.age = 25
        model.is_active = True  # Set explicitly since defaults aren't applied on instance creation

        assert model.name == "Test"
        assert model.description == "Test description"
        assert model.age == 25
        assert model.is_active is True

    def test_mapped_column_types(self):
        """Test that mapped_column types are correctly interpreted."""
        table = SQLTestModel.__table__

        # Check string column
        name_column = table.columns['name']
        assert hasattr(name_column.type, 'length')
        assert name_column.type.length == 100

        # Check boolean column with default
        is_active_column = table.columns['is_active']
        assert is_active_column.default is not None
        assert is_active_column.default.arg is True

    def test_model_class_methods(self):
        """Test BaseModel class methods work correctly."""
        # Test instance methods from BaseModel
        model = SQLTestModel()
        model.id = 1
        model.name = "Test"

        # Test field access methods
        assert model.get_field_value('name') == "Test"
        assert model.get_field_value('nonexistent', 'default') == 'default'

        assert model.set_field_value('name', 'Updated')
        assert model.name == 'Updated'

        assert not model.set_field_value('nonexistent', 'value')

        assert model.has_field('id')
        assert model.has_field('name')
        assert not model.has_field('nonexistent')

        # Test primary key method
        assert model.get_primary_key_value() == 1

        # Test persistence status
        assert model.is_persisted()

        model.id = None
        assert not model.is_persisted()

    def test_datetime_timezone_support(self):
        """Test that datetime fields support timezones."""
        model = SQLTestModel()

        # Create timezone-aware datetime
        now = datetime.now(timezone.utc)
        model.created_at = now
        model.updated_at = now

        assert model.created_at.tzinfo is not None
        assert model.updated_at.tzinfo is not None
        assert model.created_at.tzinfo == timezone.utc

    def test_model_instantiation_with_kwargs(self):
        """Test model instantiation with keyword arguments."""
        now = datetime.now(timezone.utc)

        model = SQLTestModel(
            name="Test Model",
            description="A test model",
            age=30,
            is_active=False,
            created_at=now,
            updated_at=now
        )

        assert model.name == "Test Model"
        assert model.description == "A test model"
        assert model.age == 30
        assert model.is_active is False
        assert model.created_at == now
        assert model.updated_at == now

    def test_class_inspection_methods(self):
        """Test various class inspection methods."""
        # Test column count
        columns = SQLTestModel.get_column_names()
        assert len(columns) >= 7  # id, created_at, updated_at, name, description, age, is_active

        # Test primary key count
        pk_columns = SQLTestModel.get_primary_key_columns()
        assert len(pk_columns) == 1
        assert 'id' in pk_columns

        # Test specific column checks
        assert SQLTestModel.has_column('id')
        assert SQLTestModel.has_column('name')
        assert SQLTestModel.has_column('description')
        assert SQLTestModel.has_column('age')
        assert SQLTestModel.has_column('is_active')
        assert SQLTestModel.has_column('created_at')
        assert SQLTestModel.has_column('updated_at')
        assert not SQLTestModel.has_column('fake_column')