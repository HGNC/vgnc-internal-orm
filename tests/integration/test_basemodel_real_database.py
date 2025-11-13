"""Real database-integrated tests for BaseModel following sessions/factory.py success pattern."""

import tempfile
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, Column, Integer, String, DateTime, Text
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine, async_sessionmaker

from src.vgnc_internal_orm.models.base import BaseModel, TimestampMixin, BaseCustomModel


class TestRealBaseModelInstance:
    """Real BaseModel instance tests with actual database operations."""

    def setup_method(self):
        """Set up real database for testing."""
        # Use in-memory SQLite database
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create a real test model that inherits from BaseModel
        class TestModel(BaseModel):
            __tablename__ = "test_model"
            __table_args__ = {'extend_existing': True}

            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            description = Column(Text, nullable=True)
            custom_field = Column(String(50), nullable=True)

        self.TestModel = TestModel

        # Create tables
        BaseModel.metadata.create_all(bind=self.engine)

    def teardown_method(self):
        """Clean up database."""
        self.engine.dispose()

    def test_basemodel_real_instance_creation(self):
        """Test BaseModel real instance creation with database."""
        session = self.SessionLocal()

        # Create real model instance
        test_instance = self.TestModel(
            name="Test Name",
            description="Test Description",
            custom_field="Custom Value"
        )

        # Test instance attributes exist
        assert hasattr(test_instance, 'id')
        assert hasattr(test_instance, 'name')
        assert hasattr(test_instance, 'description')
        assert hasattr(test_instance, 'custom_field')
        assert hasattr(test_instance, 'created_at')
        assert hasattr(test_instance, 'updated_at')

        # Test touch method from TimestampMixin
        test_instance.touch()
        assert isinstance(test_instance.updated_at, datetime)
        assert test_instance.updated_at.tzinfo == UTC

        session.close()

    def test_basemodel_real_database_operations(self):
        """Test BaseModel with real database operations."""
        session = self.SessionLocal()

        # Create and save real instance
        test_instance = self.TestModel(
            name="Database Test",
            description="Testing database operations"
        )

        # Test save method (execute real logic)
        session.add(test_instance)
        session.commit()

        # Test that the instance was saved
        assert test_instance.id is not None
        assert test_instance.created_at is not None
        assert test_instance.updated_at is not None

        # Test refresh method
        session.refresh(test_instance)

        # Test query methods
        queried = session.query(self.TestModel).filter_by(name="Database Test").first()
        assert queried is not None
        assert queried.id == test_instance.id
        assert queried.name == "Database Test"

        session.close()

    def test_basemodel_field_utilities_real_usage(self):
        """Test BaseModel field utilities with real instances."""
        session = self.SessionLocal()

        # Create real instance
        test_instance = self.TestModel(
            name="Field Test",
            description="Testing field utilities",
            custom_field="Custom Value"
        )

        # Test get_field_value method (execute real logic)
        assert test_instance.get_field_value('name') == "Field Test"
        assert test_instance.get_field_value('description') == "Testing field utilities"
        assert test_instance.get_field_value('nonexistent', 'default') == "default"

        # Test set_field_value method (execute real logic)
        result = test_instance.set_field_value('name', 'Updated Name')
        assert result is True
        assert test_instance.name == "Updated Name"

        result = test_instance.set_field_value('new_field', 'New Value')
        assert result is True
        assert hasattr(test_instance, 'new_field')
        assert test_instance.new_field == "New Value"

        # Test has_field method (execute real logic)
        assert test_instance.has_field('name') is True
        assert test_instance.has_field('description') is True
        assert test_instance.has_field('nonexistent') is False

        session.close()

    def test_basemodel_timestamp_functionality(self):
        """Test BaseModel timestamp functionality with real database."""
        session = self.SessionLocal()

        # Create instance and initialize timestamps by touching
        test_instance = self.TestModel(name="Timestamp Test")
        test_instance.touch()  # Initialize updated_at
        initial_updated = test_instance.updated_at

        # Test touch method
        import time
        time.sleep(0.001)  # Small delay
        test_instance.touch()
        assert test_instance.updated_at > initial_updated

        # Test refresh_timestamps method (execute real logic)
        # Need to add to session first for refresh to work
        session.add(test_instance)
        session.commit()
        test_instance.refresh_timestamps(session)
        assert test_instance.updated_at >= test_instance.created_at

        session.close()

    def test_basemodel_repr_methods(self):
        """Test BaseModel __repr__ and __str__ methods with real instances."""
        test_instance = self.TestModel(
            id=123,
            name="Repr Test",
            description="Testing representation methods"
        )

        # Test __repr__ method (execute real logic)
        repr_str = repr(test_instance)
        assert "TestModel" in repr_str
        assert "123" in repr_str

        # Test __str__ method (execute real logic)
        str_str = str(test_instance)
        assert "TestModel" in str_str
        assert "123" in str_str


class TestRealBaseCustomModel:
    """Real BaseCustomModel tests with actual database operations."""

    def setup_method(self):
        """Set up database for custom model testing."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create a real custom model
        class TestCustomModel(BaseCustomModel):
            __tablename__ = "test_custom_model"
            __table_args__ = {'extend_existing': True}

            # Custom primary key
            custom_id = Column(String(50), primary_key=True)
            name = Column(String(100), nullable=False)
            category = Column(String(50), nullable=False)

        self.TestCustomModel = TestCustomModel

        # Create only the test table, not all metadata tables
        # This avoids issues with Genefam's foreign keys to editor
        TestCustomModel.__table__.create(bind=self.engine, checkfirst=True)

    def teardown_method(self):
        """Clean up database."""
        self.engine.dispose()

    def test_basecustommodel_real_instance_creation(self):
        """Test BaseCustomModel real instance creation."""
        session = self.SessionLocal()

        # Create real custom model instance
        custom_instance = self.TestCustomModel(
            custom_id="CUSTOM_001",
            name="Custom Test",
            category="Test Category"
        )

        # Test instance has correct attributes
        assert hasattr(custom_instance, 'custom_id')
        assert hasattr(custom_instance, 'name')
        assert hasattr(custom_instance, 'category')
        assert hasattr(custom_instance, 'created_at')
        assert hasattr(custom_instance, 'updated_at')
        assert not hasattr(custom_instance, 'id')  # Should not have default id

        # Test touch method from TimestampMixin
        custom_instance.touch()
        assert isinstance(custom_instance.updated_at, datetime)

        session.close()

    def test_basecustommodel_database_operations(self):
        """Test BaseCustomModel with real database operations."""
        session = self.SessionLocal()

        # Create and save custom instance
        custom_instance = self.TestCustomModel(
            custom_id="CUSTOM_002",
            name="Database Custom Test",
            category="Testing"
        )

        # Test database operations
        session.add(custom_instance)
        session.commit()

        # Verify saved
        assert custom_instance.custom_id == "CUSTOM_002"
        assert custom_instance.created_at is not None

        # Test query
        queried = session.query(self.TestCustomModel).filter_by(
            custom_id="CUSTOM_002"
        ).first()
        assert queried is not None
        assert queried.name == "Database Custom Test"

        session.close()


class TestRealBaseModelClassMethods:
    """Real BaseModel class method tests."""

    def setup_method(self):
        """Set up database for class method testing."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create test model with table
        class TestClassModel(BaseModel):
            __tablename__ = "test_class_model"
            __table_args__ = {'extend_existing': True}

            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            value = Column(Integer, nullable=True)

        self.TestClassModel = TestClassModel

        # Create tables
        BaseModel.metadata.create_all(bind=self.engine)

    def teardown_method(self):
        """Clean up database."""
        self.engine.dispose()

    def test_basemodel_class_methods_exist_and_callable(self):
        """Test that BaseModel class methods exist and are callable."""
        class_methods = [
            'get_table_name',
            'get_column_names',
            'get_primary_key_columns',
            'has_column',
            'get_column_type'
        ]

        for method_name in class_methods:
            assert hasattr(self.TestClassModel, method_name)
            method = getattr(self.TestClassModel, method_name)
            assert callable(method)

    def test_basemodel_get_table_name(self):
        """Test get_table_name method execution."""
        # This executes real get_table_name logic
        table_name = self.TestClassModel.get_table_name()
        assert table_name == "test_class_model"

    def test_basemodel_get_column_names(self):
        """Test get_column_names method execution."""
        # This executes real get_column_names logic
        column_names = self.TestClassModel.get_column_names()
        assert isinstance(column_names, list)
        assert 'id' in column_names
        assert 'name' in column_names
        assert 'value' in column_names

    def test_basemodel_get_primary_key_columns(self):
        """Test get_primary_key_columns method execution."""
        # This executes real get_primary_key_columns logic
        pk_columns = self.TestClassModel.get_primary_key_columns()
        assert isinstance(pk_columns, list)
        assert 'id' in pk_columns

    def test_basemodel_has_column(self):
        """Test has_column method execution."""
        # This executes real has_column logic
        assert self.TestClassModel.has_column('id') is True
        assert self.TestClassModel.has_column('name') is True
        assert self.TestClassModel.has_column('nonexistent') is False

    def test_basemodel_get_column_type(self):
        """Test get_column_type method execution."""
        # This executes real get_column_type logic
        from sqlalchemy import Integer, String

        id_type = self.TestClassModel.get_column_type('id')
        name_type = self.TestClassModel.get_column_type('name')
        nonexistent_type = self.TestClassModel.get_column_type('nonexistent')

        # Types should be SQLAlchemy column types
        assert id_type is not None
        assert name_type is not None
        assert nonexistent_type is None


class TestRealBaseModelCRUDMethods:
    """Real BaseModel CRUD method tests."""

    def setup_method(self):
        """Set up database for CRUD testing."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create test model for CRUD operations
        class TestCRUDModel(BaseModel):
            __tablename__ = "test_crud_model"
            __table_args__ = {'extend_existing': True}

            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            status = Column(String(20), nullable=True)
            value = Column(Integer, nullable=True)

        self.TestCRUDModel = TestCRUDModel

        # Create tables
        BaseModel.metadata.create_all(bind=self.engine)

    def teardown_method(self):
        """Clean up database."""
        self.engine.dispose()

    def test_basemodel_crud_methods_exist_and_callable(self):
        """Test that BaseModel CRUD methods exist and are callable."""
        crud_methods = [
            'save', 'asave', 'delete', 'adelete', 'refresh', 'arefresh',
            'expire', 'aexpire', 'get_dirty_fields', 'find_by_id', 'afind_by_id',
            'find_all', 'afind_all', 'find_one', 'afind_one', 'create', 'acreate',
            'get_or_create', 'aget_or_create', 'update_by_id', 'aupdate_by_id',
            'delete_by_id', 'adelete_by_id', 'count', 'acount', 'exists', 'aexists'
        ]

        for method_name in crud_methods:
            assert hasattr(self.TestCRUDModel, method_name)
            method = getattr(self.TestCRUDModel, method_name)
            assert callable(method)

    def test_basemodel_find_by_id(self):
        """Test find_by_id method with real database."""
        session = self.SessionLocal()

        # Create test data
        test_instance = self.TestCRUDModel(
            name="Find Test",
            status="active",
            value=42
        )
        session.add(test_instance)
        session.commit()
        test_id = test_instance.id

        # Test find_by_id method execution
        found = self.TestCRUDModel.find_by_id(session, test_id)
        assert found is not None
        assert found.name == "Find Test"
        assert found.status == "active"
        assert found.value == 42

        # Test not found
        not_found = self.TestCRUDModel.find_by_id(session, 99999)
        assert not_found is None

        session.close()

    def test_basemodel_find_all(self):
        """Test find_all method with real database."""
        session = self.SessionLocal()

        # Create test data
        instances = [
            self.TestCRUDModel(name="Test 1", status="active"),
            self.TestCRUDModel(name="Test 2", status="inactive"),
            self.TestCRUDModel(name="Test 3", status="active")
        ]

        for instance in instances:
            session.add(instance)
        session.commit()

        # Test find_all method execution
        all_instances = self.TestCRUDModel.find_all(session)
        assert len(all_instances) >= 3

        # Test find_all with filters
        active_instances = self.TestCRUDModel.find_all(session, status="active")
        assert len(active_instances) >= 2

        session.close()

    def test_basemodel_find_one(self):
        """Test find_one method with real database."""
        session = self.SessionLocal()

        # Create test data
        test_instance = self.TestCRUDModel(
            name="Find One Test",
            status="unique"
        )
        session.add(test_instance)
        session.commit()

        # Test find_one method execution
        found = self.TestCRUDModel.find_one(session, name="Find One Test")
        assert found is not None
        assert found.status == "unique"

        # Test not found
        not_found = self.TestCRUDModel.find_one(session, name="Nonexistent")
        assert not_found is None

        session.close()

    def test_basemodel_create(self):
        """Test create method with real database."""
        session = self.SessionLocal()

        # Test create method execution
        created = self.TestCRUDModel.create(
            session,
            name="Created Test",
            status="created",
            value=100
        )

        assert created is not None
        assert created.id is not None
        assert created.name == "Created Test"
        assert created.status == "created"
        assert created.value == 100

        # Verify in database
        queried = session.query(self.TestCRUDModel).filter_by(name="Created Test").first()
        assert queried is not None
        assert queried.id == created.id

        session.close()

    def test_basemodel_count(self):
        """Test count method with real database."""
        session = self.SessionLocal()

        # Create test data
        for i in range(5):
            instance = self.TestCRUDModel(name=f"Count Test {i}", status="count")
            session.add(instance)
        session.commit()

        # Test count method execution
        total_count = self.TestCRUDModel.count(session)
        assert total_count >= 5

        # Test count with filters
        count_filtered = self.TestCRUDModel.count(session, status="count")
        assert count_filtered >= 5

        session.close()

    def test_basemodel_exists(self):
        """Test exists method with real database."""
        session = self.SessionLocal()

        # Create test data
        test_instance = self.TestCRUDModel(name="Exists Test", status="exists")
        session.add(test_instance)
        session.commit()

        # Test exists method execution
        assert self.TestCRUDModel.exists(session, name="Exists Test") is True
        assert self.TestCRUDModel.exists(session, status="exists") is True
        assert self.TestCRUDModel.exists(session, name="Nonexistent") is False

        session.close()


class TestRealBaseModelUtilityMethods:
    """Real BaseModel utility method tests."""

    def setup_method(self):
        """Set up database for utility method testing."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create test model
        class TestUtilityModel(BaseModel):
            __tablename__ = "test_utility_model"
            __table_args__ = {'extend_existing': True}

            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            json_field = Column(Text, nullable=True)

        self.TestUtilityModel = TestUtilityModel

        # Create tables
        BaseModel.metadata.create_all(bind=self.engine)

    def teardown_method(self):
        """Clean up database."""
        self.engine.dispose()

    def test_basemodel_utility_methods_exist_and_callable(self):
        """Test that BaseModel utility methods exist and are callable."""
        utility_methods = [
            'to_dict', 'to_json', 'update_from_dict', 'validate_utf8mb4_fields',
            'requires_utf8mb4', 'sanitize_for_basic_utf8', 'get_utf8mb4_summary'
        ]

        for method_name in utility_methods:
            assert hasattr(self.TestUtilityModel, method_name)
            method = getattr(self.TestUtilityModel, method_name)
            assert callable(method)

    def test_basemodel_to_dict_method_signature(self):
        """Test to_dict method signature and basic execution."""
        session = self.SessionLocal()

        # Create test instance
        test_instance = self.TestUtilityModel(
            name="Dict Test",
            json_field='{"key": "value"}'
        )

        # Test to_dict method execution
        result_dict = test_instance.to_dict()
        assert isinstance(result_dict, dict)
        assert 'id' in result_dict
        assert 'name' in result_dict
        assert 'json_field' in result_dict

        # Test with parameters
        result_exclude = test_instance.to_dict(exclude={'json_field'})
        assert 'json_field' not in result_exclude
        assert 'name' in result_exclude

        result_include = test_instance.to_dict(include={'name'})
        assert 'name' in result_include
        assert 'json_field' not in result_include

        session.close()

    def test_basemodel_to_json_method(self):
        """Test to_json method execution."""
        session = self.SessionLocal()

        # Create test instance
        test_instance = self.TestUtilityModel(
            name="JSON Test",
            json_field='{"test": "data"}'
        )

        # Test to_json method execution
        json_result = test_instance.to_json()
        assert isinstance(json_result, str)

        # Should be valid JSON
        import json
        parsed = json.loads(json_result)
        assert isinstance(parsed, dict)
        assert parsed['name'] == "JSON Test"

        session.close()

    def test_basemodel_update_from_dict(self):
        """Test update_from_dict method execution."""
        session = self.SessionLocal()

        # Create test instance
        test_instance = self.TestUtilityModel(name="Original")

        # Test update_from_dict method execution - only mapped columns are updated
        update_data = {
            'name': 'Updated Name',
            'json_field': '{"updated": true}'
        }

        updated_fields = test_instance.update_from_dict(update_data)
        assert isinstance(updated_fields, list)

        # Verify updates for mapped columns
        assert test_instance.name == 'Updated Name'
        assert test_instance.json_field == '{"updated": true}'
        
        # Test with exclude
        test_instance2 = self.TestUtilityModel(name="Test 2")
        updated_fields2 = test_instance2.update_from_dict(
            {'name': 'New Name', 'json_field': 'New JSON'},
            exclude={'json_field'}
        )
        assert test_instance2.name == 'New Name'
        # json_field should not be set since it was excluded
        assert test_instance2.json_field is None

        session.close()