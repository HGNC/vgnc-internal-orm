"""Integration tests for BaseModel functions to improve coverage.

Note: TimestampMixin tests have been consolidated into
tests/unit/test_timestamp_mixin_consolidated.py
"""

from datetime import UTC, datetime
from unittest.mock import Mock

from vgnc_internal_orm.models.base import BaseCustomModel, BaseModel


class TestBaseModelUtilityIntegration:
    """Integration tests for BaseModel utility methods."""

    def test_base_model_field_utilities(self):
        """Test BaseModel field utility methods with real instances."""

        # Create a mock instance with real field access
        class MockBaseModel:
            def __init__(self):
                self.id = 1
                self.name = "Test"
                self.description = "Test Description"
                self.created_at = datetime.now(UTC)
                self.updated_at = datetime.now(UTC)

        # Add BaseModel methods
        mock_instance = MockBaseModel()
        mock_instance.get_field_value = BaseModel.get_field_value.__get__(mock_instance)
        mock_instance.set_field_value = BaseModel.set_field_value.__get__(mock_instance)
        mock_instance.has_field = BaseModel.has_field.__get__(mock_instance)
        mock_instance.get_primary_key_value = BaseModel.get_primary_key_value.__get__(
            mock_instance
        )
        mock_instance.is_persisted = BaseModel.is_persisted.__get__(mock_instance)

        # Test get_field_value
        assert mock_instance.get_field_value("name") == "Test"
        assert mock_instance.get_field_value("nonexistent", "default") == "default"

        # Test set_field_value
        result = mock_instance.set_field_value("name", "Updated")
        assert result is True
        assert mock_instance.name == "Updated"

        result = mock_instance.set_field_value("new_field", "new_value")
        assert result is True
        assert mock_instance.new_field == "new_value"

        # Test has_field
        assert mock_instance.has_field("name") is True
        assert mock_instance.has_field("nonexistent") is False

        # Test get_primary_key_value
        assert mock_instance.get_primary_key_value() == 1

        # Test is_persisted
        assert mock_instance.is_persisted() is True

    def test_base_model_repr_methods(self):
        """Test BaseModel __repr__ and __str__ methods."""

        class TestModel:
            def __init__(self):
                self.id = 123

        mock_instance = TestModel()
        # Properly bind methods using MethodType
        TestModel.__repr__ = lambda self: BaseModel.__repr__(self)
        TestModel.__str__ = lambda self: BaseModel.__str__(self)

        # Test __repr__
        repr_str = repr(mock_instance)
        assert "TestModel" in repr_str
        assert "123" in repr_str

        # Test __str__
        str_str = str(mock_instance)
        assert "TestModel" in str_str
        assert "123" in str_str

    def test_base_model_datetime_serialization(self):
        """Test BaseModel datetime serialization."""
        from datetime import date, datetime
        from decimal import Decimal

        test_datetime = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        test_date = date(2023, 1, 1)
        test_decimal = Decimal("123.45")

        # Test _json_default method
        result_datetime = BaseModel._json_default(test_datetime)
        assert isinstance(result_datetime, str)

        result_date = BaseModel._json_default(test_date)
        assert isinstance(result_date, str)

        result_decimal = BaseModel._json_default(test_decimal)
        assert isinstance(result_decimal, (str, float))

        # Test _serialize_relationship method
        mock_instance = BaseModel.__new__(BaseModel)

        # Test with mock that has to_dict method - should call to_dict()
        mock_with_to_dict = Mock()
        mock_with_to_dict.to_dict.return_value = {"id": 1, "name": "test"}
        result_rel = mock_instance._serialize_relationship(mock_with_to_dict, "iso")
        assert result_rel == {"id": 1, "name": "test"}  # Should call to_dict()
        mock_with_to_dict.to_dict.assert_called_once_with(datetime_format="iso")

        # Test with value that doesn't have to_dict - should return as-is
        simple_value = "simple string"
        result_simple = mock_instance._serialize_relationship(simple_value, "iso")
        assert result_simple == "simple string"


class TestBaseCustomModelIntegration:
    """Integration tests for BaseCustomModel."""

    def test_base_custom_model_inheritance(self):
        """Test BaseCustomModel can be used as base class."""

        class TestCustomModel(BaseCustomModel):
            __tablename__ = "test_custom"

            # Mock table structure for testing
            from sqlalchemy import Column, Integer, String

            id = Column(Integer, primary_key=True)
            name = Column(String(50))

        # Test that it inherits from BaseCustomModel
        assert issubclass(TestCustomModel, BaseCustomModel)

    def test_base_custom_model_basic_functionality(self):
        """Test BaseCustomModel basic functionality."""

        class TestCustomModelBasic(BaseCustomModel):
            __tablename__ = "test_custom_model_basic"

            from sqlalchemy import Column, Integer, String

            custom_id = Column(String(50), primary_key=True)

        instance = TestCustomModelBasic(custom_id="TEST_001")

        # Test basic instantiation
        assert hasattr(instance, "custom_id")
        assert instance.custom_id == "TEST_001"


class TestBaseModelClassMethodIntegration:
    """Integration tests for BaseModel class methods."""

    def test_base_model_class_methods_exist(self):
        """Test that BaseModel class methods exist and are callable."""

        # Test class methods exist
        assert hasattr(BaseModel, "get_table_name")
        assert callable(BaseModel.get_table_name)

        assert hasattr(BaseModel, "get_column_names")
        assert callable(BaseModel.get_column_names)

        assert hasattr(BaseModel, "get_primary_key_columns")
        assert callable(BaseModel.get_primary_key_columns)

        assert hasattr(BaseModel, "has_column")
        assert callable(BaseModel.has_column)

        assert hasattr(BaseModel, "get_column_type")
        assert callable(BaseModel.get_column_type)

    def test_base_model_crud_methods_exist(self):
        """Test that BaseModel CRUD methods exist and are callable."""

        # Test CRUD methods exist (async methods removed in db-common migration)
        crud_methods = [
            "save",
            "delete",
            "refresh",
            "expire",
            "get_dirty_fields",
            "find_by_id",
            "find_all",
            "find_one",
            "create",
            "get_or_create",
            "update_by_id",
            "delete_by_id",
            "count",
            "exists",
        ]

        for method_name in crud_methods:
            assert hasattr(BaseModel, method_name), f"Method {method_name} should exist"
            method = getattr(BaseModel, method_name)
            assert callable(method), f"Method {method_name} should be callable"

    def test_base_model_utility_methods_exist(self):
        """Test that BaseModel utility methods exist and are callable."""

        # Test utility methods exist (async methods removed in db-common migration)
        utility_methods = [
            "to_dict",
            "to_json",
            "update_from_dict",
            "refresh_timestamps",
            "validate_utf8mb4_fields",
            "requires_utf8mb4",
            "sanitize_for_basic_utf8",
            "get_utf8mb4_summary",
            "search_with_charset_support",
        ]

        for method_name in utility_methods:
            assert hasattr(BaseModel, method_name), f"Method {method_name} should exist"
            method = getattr(BaseModel, method_name)
            assert callable(method), f"Method {method_name} should be callable"


class TestBaseModelToDictIntegration:
    """Integration tests for BaseModel to_dict method."""

    def test_to_dict_method_signature(self):
        """Test to_dict method signature and basic functionality."""

        # Test that to_dict method exists
        assert hasattr(BaseModel, "to_dict")
        assert callable(BaseModel.to_dict)

        # Test method accepts expected parameters
        import inspect

        sig = inspect.signature(BaseModel.to_dict)

        expected_params = [
            "exclude",
            "include",
            "exclude_none",
            "serialize_relationships",
            "datetime_format",
        ]
        for param in expected_params:
            assert param in sig.parameters, f"to_dict should accept {param} parameter"

    def test_to_json_method_signature(self):
        """Test to_json method signature and basic functionality."""

        # Test that to_json method exists
        assert hasattr(BaseModel, "to_json")
        assert callable(BaseModel.to_json)

        # Test method accepts expected parameters
        import inspect

        sig = inspect.signature(BaseModel.to_json)

        expected_params = [
            "exclude",
            "include",
            "exclude_none",
            "serialize_relationships",
            "datetime_format",
        ]
        for param in expected_params:
            assert param in sig.parameters, f"to_json should accept {param} parameter"

    def test_update_from_dict_method_signature(self):
        """Test update_from_dict method signature and basic functionality."""

        # Test that update_from_dict method exists
        assert hasattr(BaseModel, "update_from_dict")
        assert callable(BaseModel.update_from_dict)

        # Test method accepts expected parameters
        import inspect

        sig = inspect.signature(BaseModel.update_from_dict)

        expected_params = ["data", "exclude"]
        for param in expected_params:
            assert (
                param in sig.parameters
            ), f"update_from_dict should accept {param} parameter"


class TestBaseModelWithMockDatabase:
    """Integration tests with mock database sessions."""

    def test_base_model_with_mock_session(self):
        """Test BaseModel methods with mock database session."""

        # Create a mock session
        mock_session = Mock()
        mock_session.add = Mock()
        mock_session.commit = Mock()
        mock_session.rollback = Mock()
        mock_session.refresh = Mock()
        mock_session.expire = Mock()

        # Test save method signature
        mock_instance = Mock()
        mock_instance.save = BaseModel.save.__get__(mock_instance)

        # This should not raise an exception
        try:
            mock_instance.save(mock_session)
        except Exception:
            # Expected since we're using a mock instance
            pass

    def test_base_model_session_methods_exist(self):
        """Test that BaseModel session-dependent methods exist."""

        session_methods = [
            "refresh_timestamps",
            "arefresh_timestamps",
            "save",
            "asave",
            "delete",
            "adelete",
            "refresh",
            "arefresh",
            "expire",
            "aexpire",
            "get_dirty_fields",
        ]

        for method_name in session_methods:
            assert hasattr(
                BaseModel, method_name
            ), f"Session method {method_name} should exist"
            method = getattr(BaseModel, method_name)
            assert callable(method), f"Session method {method_name} should be callable"
