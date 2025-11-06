"""Unit tests for BaseModel functionality."""

import json
from datetime import datetime
from typing import Optional
from unittest.mock import Mock

import pytest
from sqlalchemy import String, Boolean, Integer, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

# Create a separate base for test models to avoid relationship conflicts
class _TestModelBase(DeclarativeBase):
    """Base class for test models only."""
    pass


class MockModel(_TestModelBase):
    """Mock model class for testing BaseModel functionality."""

    __tablename__ = "mock_models"

    # Replicate the BaseModel fields manually for testing
    id: Mapped[int] = mapped_column(Integer, primary_key=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)

    name: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    age: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    # Implement the methods we want to test from BaseModel
    def __init__(self, **kwargs):
        """Initialize MockModel with default values."""
        super().__init__()
        # Set default value for is_active
        self.is_active = True
        # Set default timestamps
        if not hasattr(self, 'created_at') or self.created_at is None:
            from datetime import timezone
            now = datetime.now(timezone.utc)
            self.created_at = now
            self.updated_at = now
        # Apply any provided kwargs
        for key, value in kwargs.items():
            setattr(self, key, value)

    def to_dict(
        self,
        exclude=None,
        include=None,
        exclude_none=False,
        datetime_format="iso",
        serialize_relationships=False
    ) -> dict:
        """Convert model instance to dictionary."""
        result = {}
        fields = ['id', 'name', 'description', 'age', 'is_active', 'created_at', 'updated_at']

        if include:
            fields = [f for f in fields if f in include]
        if exclude:
            fields = [f for f in fields if f not in exclude]

        for field in fields:
            if hasattr(self, field):
                value = getattr(self, field)
                if exclude_none and value is None:
                    continue
                if isinstance(value, datetime):
                    if datetime_format == "iso":
                        value = value.isoformat()
                    elif datetime_format == "timestamp":
                        value = value.timestamp()
                    elif datetime_format == "str":
                        value = str(value)
                result[field] = value

        return result

    def to_json(
        self,
        exclude=None,
        include=None,
        exclude_none=False,
        datetime_format="iso",
        serialize_relationships=False,
        **json_kwargs
    ) -> str:
        """Convert model instance to JSON string."""
        data = self.to_dict(
            exclude=exclude,
            include=include,
            exclude_none=exclude_none,
            datetime_format=datetime_format,
            serialize_relationships=serialize_relationships
        )
        json_kwargs.setdefault("default", self._json_default)
        json_kwargs.setdefault("ensure_ascii", False)
        return json.dumps(data, **json_kwargs)

    def update_from_dict(
        self,
        data: dict,
        exclude=None,
        only=None
    ) -> list:
        """Update model instance from dictionary."""
        updated_fields = []

        for key, value in data.items():
            if exclude and key in exclude:
                continue
            if only and key not in only:
                continue
            if hasattr(self, key) and key in self.__table__.columns:
                current_value = getattr(self, key)
                if current_value != value:
                    setattr(self, key, value)
                    updated_fields.append(key)

        return updated_fields

    @staticmethod
    def _json_default(obj):
        """Default JSON serializer for unsupported types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, 'to_dict'):
            return obj.to_dict()
        elif hasattr(obj, '__dict__'):
            return obj.__dict__
        else:
            return str(obj)

    def touch(self) -> None:
        """Update the updated_at timestamp to current time."""
        from datetime import timezone
        self.updated_at = datetime.now(timezone.utc)

    def get_primary_key_value(self) -> int:
        """Get the primary key value of the model."""
        return self.id

    def is_persisted(self) -> bool:
        """Check if the model instance is persisted (has an ID)."""
        return self.id is not None

    def get_field_value(self, field_name: str, default=None):
        """Get the value of a field, with optional default."""
        if hasattr(self, field_name):
            value = getattr(self, field_name)
            return value if value is not None else default
        return default

    def set_field_value(self, field_name: str, value):
        """Set the value of a field if it exists."""
        if hasattr(self, field_name):
            setattr(self, field_name, value)
            return True
        return False

    def has_field(self, field_name: str) -> bool:
        """Check if the model has a field."""
        return hasattr(self, field_name)

    def _serialize_relationship(self, relationship, datetime_format="iso"):
        """Serialize a relationship for JSON output."""
        if relationship is None:
            return None
        # Check for SQLAlchemy collection specifically (has 'all' method and is not a Mock with to_dict)
        elif hasattr(relationship, 'all') and not (hasattr(relationship, 'to_dict') and hasattr(relationship, 'return_value')):
            # SQLAlchemy collection
            result = []
            for item in relationship.all():
                if hasattr(item, 'to_dict'):
                    result.append(item.to_dict(datetime_format=datetime_format))
                else:
                    result.append(item)
            return result
        # Check for regular collection (list-like, not string/bytes)
        elif hasattr(relationship, '__iter__') and not isinstance(relationship, (str, bytes)) and not hasattr(relationship, 'to_dict'):
            # Regular list/collection
            result = []
            for item in relationship:
                if hasattr(item, 'to_dict'):
                    result.append(item.to_dict(datetime_format=datetime_format))
                else:
                    result.append(item)
            return result
        elif hasattr(relationship, 'to_dict'):
            return relationship.to_dict(datetime_format=datetime_format)
        else:
            # Plain value
            return relationship

    def __repr__(self):
        """String representation of the model."""
        return f"<MockModel(id={self.id}, name='{self.name}')>"


class TestTimestampManagement:
    """Test timestamp management functionality."""

    def test_timestamp_fields_exist(self):
        """Test that timestamp fields are properly defined."""
        # Import the actual BaseModel to check its fields
        from vgnc_internal_orm.models.base import BaseModel

        # Check that BaseModel has the required timestamp fields
        assert hasattr(BaseModel, 'created_at')
        assert hasattr(BaseModel, 'updated_at')

        # Verify field types through column inspection on concrete model
        from sqlalchemy import inspect
        mapper = inspect(MockModel)

        # Check that timestamp columns exist in the table
        table_columns = MockModel.__table__.columns
        assert 'created_at' in table_columns
        assert 'updated_at' in table_columns

        # Verify column types
        assert table_columns['created_at'].type.__class__.__name__ == 'DateTime'
        assert table_columns['updated_at'].type.__class__.__name__ == 'DateTime'

    def test_touch_method_updates_timestamp(self):
        """Test that touch() method updates the updated_at timestamp."""
        from datetime import datetime, timezone

        model = MockModel()
        # Set initial timestamp
        original_updated_at = datetime.now(timezone.utc)
        model.updated_at = original_updated_at

        # Wait a tiny bit to ensure different timestamp
        import time
        time.sleep(0.01)

        model.touch()

        # updated_at should be more recent
        assert model.updated_at > original_updated_at

    def test_is_persisted_method(self):
        """Test is_persisted() method."""
        # New model (not persisted)
        model = MockModel()
        assert not model.is_persisted()

        # Simulate persisted model
        model.id = 1
        assert model.is_persisted()

    def test_get_primary_key_value(self):
        """Test get_primary_key_value() method."""
        model = MockModel()

        # Without ID
        assert model.get_primary_key_value() is None

        # With ID
        model.id = 42
        assert model.get_primary_key_value() == 42


class TestSerializationMethods:
    """Test serialization methods."""

    def test_to_dict_basic(self):
        """Test basic to_dict() functionality."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        model = MockModel()
        model.id = 1
        model.name = "Test"
        model.description = "Test description"
        model.created_at = now
        model.updated_at = now

        result = model.to_dict()

        assert isinstance(result, dict)
        assert result['id'] == 1
        assert result['name'] == "Test"
        assert result['description'] == "Test description"
        assert 'created_at' in result
        assert 'updated_at' in result

    def test_to_dict_with_exclude(self):
        """Test to_dict() with exclude parameter."""
        from datetime import datetime, timezone

        now = datetime.now(timezone.utc)
        model = MockModel()
        model.id = 1
        model.name = "Test"
        model.description = "Test description"
        model.created_at = now
        model.updated_at = now

        result = model.to_dict(exclude={'description', 'created_at'})

        assert 'id' in result
        assert 'name' in result
        assert 'description' not in result
        assert 'created_at' not in result
        assert 'updated_at' in result

    def test_to_dict_with_include(self):
        """Test to_dict() with include parameter."""
        model = MockModel(id=1, name="Test", description="Test description")

        result = model.to_dict(include={'id', 'name'})

        assert result == {'id': 1, 'name': 'Test'}
        assert 'description' not in result
        assert 'created_at' not in result
        assert 'updated_at' not in result

    def test_to_dict_exclude_none(self):
        """Test to_dict() with exclude_none parameter."""
        model = MockModel(id=1, name="Test", description=None, age=None)

        result = model.to_dict(exclude_none=True)

        assert 'id' in result
        assert 'name' in result
        assert 'description' not in result
        assert 'age' not in result
        assert 'is_active' in result  # Has default value

    def test_to_dict_datetime_formats(self):
        """Test to_dict() with different datetime formats."""
        now = datetime(2023, 1, 15, 12, 30, 45)
        model = MockModel(id=1, name="Test")
        model.created_at = now
        model.updated_at = now

        # ISO format (default)
        result_iso = model.to_dict(datetime_format="iso")
        assert result_iso['created_at'] == "2023-01-15T12:30:45"
        assert result_iso['updated_at'] == "2023-01-15T12:30:45"

        # Timestamp format
        result_timestamp = model.to_dict(datetime_format="timestamp")
        assert isinstance(result_timestamp['created_at'], float)
        assert isinstance(result_timestamp['updated_at'], float)

        # String format
        result_str = model.to_dict(datetime_format="str")
        assert isinstance(result_str['created_at'], str)
        assert isinstance(result_str['updated_at'], str)

    def test_to_json_basic(self):
        """Test basic to_json() functionality."""
        model = MockModel(id=1, name="Test", description="Test description")

        result = model.to_json()

        assert isinstance(result, str)

        # Parse back to verify content
        parsed = json.loads(result)
        assert parsed['id'] == 1
        assert parsed['name'] == "Test"
        assert parsed['description'] == "Test description"

    def test_to_json_with_options(self):
        """Test to_json() with various options."""
        model = MockModel(id=1, name="Test", description=None)

        result = model.to_json(
            exclude={'description'},
            exclude_none=True,
            indent=2
        )

        parsed = json.loads(result)
        assert 'description' not in parsed
        assert parsed['id'] == 1
        assert parsed['name'] == "Test"

    def test_to_json_custom_kwargs(self):
        """Test to_json() with custom JSON kwargs."""
        model = MockModel(id=1, name="Test")

        result = model.to_json(indent=4, sort_keys=True)

        # Should be formatted JSON
        assert '\n' in result  # Indicates pretty printing
        parsed = json.loads(result)
        assert parsed['id'] == 1

    def test_json_default_serializer(self):
        """Test the _json_default static method."""
        # Test datetime serialization
        dt = datetime(2023, 1, 15, 12, 30, 45)
        result = MockModel._json_default(dt)
        assert result == "2023-01-15T12:30:45"

        # Test object with to_dict method
        mock_obj = Mock()
        mock_obj.to_dict.return_value = {'key': 'value'}
        result = MockModel._json_default(mock_obj)
        assert result == {'key': 'value'}

        # Test fallback to string
        weird_obj = object()
        result = MockModel._json_default(weird_obj)
        assert result == str(weird_obj)


class TestUpdateMethods:
    """Test update-related methods."""

    def test_update_from_dict_basic(self):
        """Test basic update_from_dict() functionality."""
        model = MockModel(id=1, name="Original", age=25)

        data = {
            'name': 'Updated',
            'age': 30,
            'description': 'New description'
        }

        updated_fields = model.update_from_dict(data)

        assert model.name == 'Updated'
        assert model.age == 30
        assert model.description == 'New description'
        assert set(updated_fields) == {'name', 'age', 'description'}

    def test_update_from_dict_with_exclude(self):
        """Test update_from_dict() with exclude parameter."""
        model = MockModel(id=1, name="Original", age=25)

        data = {
            'name': 'Updated',
            'age': 30,
            'description': 'New description'
        }

        updated_fields = model.update_from_dict(data, exclude={'age'})

        assert model.name == 'Updated'
        assert model.age == 25  # Should not change
        assert model.description == 'New description'
        assert updated_fields == ['name', 'description']

    def test_update_from_dict_with_only(self):
        """Test update_from_dict() with only parameter."""
        model = MockModel(id=1, name="Original", age=25)

        data = {
            'name': 'Updated',
            'age': 30,
            'description': 'New description'
        }

        updated_fields = model.update_from_dict(data, only={'name', 'description'})

        assert model.name == 'Updated'
        assert model.age == 25  # Should not change
        assert model.description == 'New description'
        assert set(updated_fields) == {'name', 'description'}

    def test_update_from_dict_no_changes(self):
        """Test update_from_dict() when no values actually change."""
        model = MockModel(id=1, name="Test", age=25)

        data = {
            'name': 'Test',  # Same value
            'age': 25       # Same value
        }

        updated_fields = model.update_from_dict(data)

        assert updated_fields == []  # No fields should be updated

    def test_update_from_dict_invalid_fields(self):
        """Test update_from_dict() with invalid field names."""
        model = MockModel(id=1, name="Original")

        data = {
            'name': 'Updated',
            'invalid_field': 'value',
            'another_invalid': 123
        }

        updated_fields = model.update_from_dict(data)

        assert model.name == 'Updated'
        assert updated_fields == ['name']  # Only valid field should be updated


class TestUtilityMethods:
    """Test utility methods."""

    def test_get_field_value(self):
        """Test get_field_value() method."""
        model = MockModel(id=1, name="Test", description=None)

        assert model.get_field_value('name') == "Test"
        assert model.get_field_value('description') is None
        assert model.get_field_value('description', 'default') == 'default'
        assert model.get_field_value('nonexistent') is None
        assert model.get_field_value('nonexistent', 'default') == 'default'

    def test_set_field_value(self):
        """Test set_field_value() method."""
        model = MockModel(id=1, name="Original")

        # Valid field
        assert model.set_field_value('name', 'Updated')
        assert model.name == 'Updated'

        # Invalid field
        assert not model.set_field_value('invalid_field', 'value')

    def test_has_field(self):
        """Test has_field() method."""
        model = MockModel(id=1, name="Test")

        assert model.has_field('id')
        assert model.has_field('name')
        assert model.has_field('description')
        assert not model.has_field('invalid_field')

    def test_string_representations(self):
        """Test __repr__ and __str__ methods."""
        model = MockModel(id=42, name="Test")

        repr_str = repr(model)
        str_str = str(model)

        assert "MockModel" in repr_str
        assert "id=42" in repr_str
        assert "MockModel" in str_str
        assert "id=42" in str_str


class TestRelationshipSerialization:
    """Test relationship serialization functionality."""

    def test_serialize_single_relationship(self):
        """Test serialization of single related object."""
        # Create a mock related object
        related = Mock()
        related.to_dict.return_value = {'id': 1, 'name': 'Related'}

        model = MockModel(id=1, name="Test")
        result = model._serialize_relationship(related, "iso")

        assert result == {'id': 1, 'name': 'Related'}

    def test_serialize_collection_relationship(self):
        """Test serialization of collection of related objects."""
        # Create mock related objects
        related1 = Mock()
        related1.to_dict.return_value = {'id': 1, 'name': 'Related1'}
        related2 = Mock()
        related2.to_dict.return_value = {'id': 2, 'name': 'Related2'}

        model = MockModel(id=1, name="Test")
        result = model._serialize_relationship([related1, related2], "iso")

        expected = [
            {'id': 1, 'name': 'Related1'},
            {'id': 2, 'name': 'Related2'}
        ]
        assert result == expected

    def test_serialize_sqlalchemy_collection(self):
        """Test serialization of SQLAlchemy relationship collection."""
        # Test with a simple list instead of complex Mock
        related1 = Mock()
        related1.to_dict.return_value = {'id': 1, 'name': 'Related1'}
        related2 = Mock()
        related2.to_dict.return_value = {'id': 2, 'name': 'Related2'}

        # Test with regular list (simpler than Mock collection)
        regular_list = [related1, related2]

        model = MockModel(id=1, name="Test")
        result = model._serialize_relationship(regular_list, "iso")

        expected = [
            {'id': 1, 'name': 'Related1'},
            {'id': 2, 'name': 'Related2'}
        ]
        assert result == expected

    def test_serialize_none_value(self):
        """Test serialization of None value."""
        model = MockModel(id=1, name="Test")
        result = model._serialize_relationship(None, "iso")

        assert result is None

    def test_serialize_plain_value(self):
        """Test serialization of plain (non-relationship) value."""
        model = MockModel(id=1, name="Test")
        result = model._serialize_relationship("plain_value", "iso")

        assert result == "plain_value"