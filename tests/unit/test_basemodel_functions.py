"""Targeted tests for BaseModel functions to improve coverage.

Note: TimestampMixin tests have been consolidated into
tests/unit/test_timestamp_mixin_consolidated.py
"""

from unittest.mock import Mock

from vgnc_internal_orm.models.base import BaseModel


class TestBaseModelClassMethods:
    """Test BaseModel class methods."""

    def test_get_table_name_method_exists(self):
        """Test get_table_name method exists."""
        assert hasattr(BaseModel, "get_table_name")
        assert callable(BaseModel.get_table_name)

    def test_get_column_names_method_exists(self):
        """Test get_column_names method exists."""
        assert hasattr(BaseModel, "get_column_names")
        assert callable(BaseModel.get_column_names)

    def test_get_primary_key_columns_method_exists(self):
        """Test get_primary_key_columns method exists."""
        assert hasattr(BaseModel, "get_primary_key_columns")
        assert callable(BaseModel.get_primary_key_columns)

    def test_has_column_method_exists(self):
        """Test has_column method exists."""
        assert hasattr(BaseModel, "has_column")
        assert callable(BaseModel.has_column)

    def test_get_column_type_method_exists(self):
        """Test get_column_type method exists."""
        assert hasattr(BaseModel, "get_column_type")
        assert callable(BaseModel.get_column_type)


class TestBaseModelInstanceMethods:
    """Test BaseModel instance methods."""

    def test_to_dict_method_exists(self):
        """Test to_dict method exists."""
        assert hasattr(BaseModel, "to_dict")
        assert callable(BaseModel.to_dict)

    def test_to_json_method_exists(self):
        """Test to_json method exists."""
        assert hasattr(BaseModel, "to_json")
        assert callable(BaseModel.to_json)

    def test_update_from_dict_method_exists(self):
        """Test update_from_dict method exists."""
        assert hasattr(BaseModel, "update_from_dict")
        assert callable(BaseModel.update_from_dict)

    def test_refresh_timestamps_method_exists(self):
        """Test refresh_timestamps method exists."""
        assert hasattr(BaseModel, "refresh_timestamps")
        assert callable(BaseModel.refresh_timestamps)


class TestBaseModelUtilityMethods:
    """Test BaseModel utility methods."""

    def test_get_field_value_method_exists(self):
        """Test get_field_value method exists."""
        assert hasattr(BaseModel, "get_field_value")
        assert callable(BaseModel.get_field_value)

    def test_set_field_value_method_exists(self):
        """Test set_field_value method exists."""
        assert hasattr(BaseModel, "set_field_value")
        assert callable(BaseModel.set_field_value)

    def test_has_field_method_exists(self):
        """Test has_field method exists."""
        assert hasattr(BaseModel, "has_field")
        assert callable(BaseModel.has_field)

    def test_get_primary_key_value_method_exists(self):
        """Test get_primary_key_value method exists."""
        assert hasattr(BaseModel, "get_primary_key_value")
        assert callable(BaseModel.get_primary_key_value)

    def test_is_persisted_method_exists(self):
        """Test is_persisted method exists."""
        assert hasattr(BaseModel, "is_persisted")
        assert callable(BaseModel.is_persisted)

    def test___repr___method_exists(self):
        """Test __repr__ method exists."""
        assert hasattr(BaseModel, "__repr__")
        assert callable(BaseModel.__repr__)

    def test___str___method_exists(self):
        """Test __str__ method exists."""
        assert hasattr(BaseModel, "__str__")
        assert callable(BaseModel.__str__)


class TestBaseModelCRUDMethods:
    """Test BaseModel CRUD methods."""

    def test_save_method_exists(self):
        """Test save method exists."""
        assert hasattr(BaseModel, "save")
        assert callable(BaseModel.save)

    def test_delete_method_exists(self):
        """Test delete method exists."""
        assert hasattr(BaseModel, "delete")
        assert callable(BaseModel.delete)

    def test_refresh_method_exists(self):
        """Test refresh method exists."""
        assert hasattr(BaseModel, "refresh")
        assert callable(BaseModel.refresh)

    def test_expire_method_exists(self):
        """Test expire method exists."""
        assert hasattr(BaseModel, "expire")
        assert callable(BaseModel.expire)


class TestBaseModelQueryMethods:
    """Test BaseModel query methods."""

    def test_get_dirty_fields_method_exists(self):
        """Test get_dirty_fields method exists."""
        assert hasattr(BaseModel, "get_dirty_fields")
        assert callable(BaseModel.get_dirty_fields)

    def test_find_by_id_method_exists(self):
        """Test find_by_id method exists."""
        assert hasattr(BaseModel, "find_by_id")
        assert callable(BaseModel.find_by_id)

    def test_find_all_method_exists(self):
        """Test find_all method exists."""
        assert hasattr(BaseModel, "find_all")
        assert callable(BaseModel.find_all)

    def test_find_one_method_exists(self):
        """Test find_one method exists."""
        assert hasattr(BaseModel, "find_one")
        assert callable(BaseModel.find_one)

    def test_create_method_exists(self):
        """Test create method exists."""
        assert hasattr(BaseModel, "create")
        assert callable(BaseModel.create)

    def test_get_or_create_method_exists(self):
        """Test get_or_create method exists."""
        assert hasattr(BaseModel, "get_or_create")
        assert callable(BaseModel.get_or_create)

    def test_update_by_id_method_exists(self):
        """Test update_by_id method exists."""
        assert hasattr(BaseModel, "update_by_id")
        assert callable(BaseModel.update_by_id)

    def test_delete_by_id_method_exists(self):
        """Test delete_by_id method exists."""
        assert hasattr(BaseModel, "delete_by_id")
        assert callable(BaseModel.delete_by_id)

    def test_count_method_exists(self):
        """Test count method exists."""
        assert hasattr(BaseModel, "count")
        assert callable(BaseModel.count)

    def test_exists_method_exists(self):
        """Test exists method exists."""
        assert hasattr(BaseModel, "exists")
        assert callable(BaseModel.exists)


class TestBaseModelUtilityFunctionTests:
    """Test BaseModel utility function behaviors."""

    def test_get_field_value_with_mock_instance(self):
        """Test get_field_value with mock instance."""
        mock_instance = Mock()
        mock_instance.test_field = "test_value"

        # Add the method to the mock instance
        mock_instance.get_field_value = BaseModel.get_field_value.__get__(mock_instance)

        result = mock_instance.get_field_value("test_field")
        assert result == "test_value"

    def test_set_field_value_with_mock_instance(self):
        """Test set_field_value with mock instance."""
        mock_instance = Mock()
        mock_instance.test_field = None  # Pre-existing field

        # Mock __table__ with columns
        mock_column = Mock()
        mock_column.name = "test_field"
        mock_table = Mock()
        mock_table.columns = {"test_field": mock_column}
        mock_instance.__table__ = mock_table

        # Add the method to the mock instance
        mock_instance.set_field_value = BaseModel.set_field_value.__get__(mock_instance)

        result = mock_instance.set_field_value("test_field", "test_value")
        assert result is True
        assert mock_instance.test_field == "test_value"

    def test_has_field_with_mock_instance(self):
        """Test has_field with mock instance."""
        mock_instance = Mock()
        mock_instance.existing_field = "value"

        # Mock __table__ with columns
        mock_column = Mock()
        mock_column.name = "existing_field"
        mock_table = Mock()
        mock_table.columns = {"existing_field": mock_column}
        mock_instance.__table__ = mock_table

        # Add the method to the mock instance
        mock_instance.has_field = BaseModel.has_field.__get__(mock_instance)

        assert mock_instance.has_field("existing_field") is True
        assert mock_instance.has_field("nonexistent_field") is False
