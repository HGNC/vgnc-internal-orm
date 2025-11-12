"""Comprehensive database-integrated tests for BaseModel functionality."""

import pytest
import json
from datetime import datetime, timezone
from decimal import Decimal
from sqlalchemy import create_engine, text, Column, Integer, String, DateTime, Boolean, DECIMAL
from sqlalchemy.orm import sessionmaker, Session, DeclarativeBase
from sqlalchemy.ext.hybrid import hybrid_property

from src.vgnc_internal_orm.models.base import BaseModel, TimestampMixin
from src.vgnc_internal_orm.sessions.factory import DatabaseFactory
from src.vgnc_internal_orm.config.settings import DatabaseConfig, DatabaseDriver


# Test model definitions
class TestBasicModel(BaseModel):
    """Basic test model for BaseModel functionality."""
    __tablename__ = "test_basic_model"

    id = Column(Integer, primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(String(500))
    active = Column(Boolean, default=True)
    price = Column(DECIMAL(10, 2))
    category = Column(String(50))


class TestTimestampModel(TimestampMixin, BaseModel):
    """Test model with timestamp functionality."""
    __tablename__ = "test_timestamp_model"

    id = Column(Integer, primary_key=True)
    title = Column(String(200), nullable=False)
    content = Column(String(1000))


class TestHybridModel(BaseModel):
    """Test model with hybrid properties."""
    __tablename__ = "test_hybrid_model"

    id = Column(Integer, primary_key=True)
    first_name = Column(String(100))
    last_name = Column(String(100))
    age = Column(Integer)

    @hybrid_property
    def full_name(self):
        return f"{self.first_name} {self.last_name}"

    @full_name.expression
    def full_name(cls):
        return text("first_name || ' ' || last_name")


class TestBaseModelComprehensive:
    """Comprehensive database-integrated tests for BaseModel."""

    def setup_method(self):
        """Set up test database and session."""
        self.config = DatabaseConfig(
            driver=DatabaseDriver.SQLITE,
            database=":memory:",
            _env_file=None
        )
        self.factory = DatabaseFactory(self.config)
        self.engine = self.factory.create_engine()
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create tables
        BaseModel.metadata.create_all(bind=self.engine)

        self.session = self.SessionLocal()

    def teardown_method(self):
        """Clean up test database."""
        self.session.close()
        self.engine.dispose()

    def test_basemodel_crud_operations_complete(self):
        """Test complete CRUD operations with BaseModel."""
        # Create
        test_model = TestBasicModel(
            name="Test Product",
            description="A test product for coverage",
            active=True,
            price=Decimal("29.99"),
            category="electronics"
        )

        self.session.add(test_model)
        self.session.commit()

        assert test_model.id is not None
        assert test_model.created is not None
        assert test_model.modified is not None

        # Read
        retrieved = self.session.query(TestBasicModel).filter_by(id=test_model.id).first()
        assert retrieved is not None
        assert retrieved.name == "Test Product"
        assert retrieved.price == Decimal("29.99")

        # Update
        retrieved.name = "Updated Product"
        retrieved.price = Decimal("39.99")
        self.session.commit()

        # Verify update
        updated = self.session.query(TestBasicModel).filter_by(id=test_model.id).first()
        assert updated.name == "Updated Product"
        assert updated.price == Decimal("39.99")
        assert updated.modified > updated.created

        # Delete
        self.session.delete(updated)
        self.session.commit()

        # Verify deletion
        deleted = self.session.query(TestBasicModel).filter_by(id=test_model.id).first()
        assert deleted is None

    def test_basemodel_field_utilities_comprehensive(self):
        """Test BaseModel field utility methods."""
        test_model = TestBasicModel(
            name="Field Test",
            description="Testing field utilities",
            category="testing"
        )

        # Test get_field_value
        assert test_model.get_field_value("name") == "Field Test"
        assert test_model.get_field_value("description") == "Testing field utilities"
        assert test_model.get_field_value("nonexistent") is None
        assert test_model.get_field_value("nonexistent", "default") == "default"

        # Test set_field_value
        test_model.set_field_value("name", "Updated Name")
        assert test_model.name == "Updated Name"

        test_model.set_field_value("new_field", "new_value")
        assert hasattr(test_model, "new_field")
        assert getattr(test_model, "new_field") == "new_value"

        # Test has_field
        assert test_model.has_field("name") is True
        assert test_model.has_field("description") is True
        assert test_model.has_field("nonexistent") is False

        # Test get_field_type
        assert test_model.get_field_type("name") == str
        assert test_model.get_field_type("price") == Decimal
        assert test_model.get_field_type("active") == bool
        assert test_model.get_field_type("nonexistent") is None

    def test_basemodel_dict_conversion_comprehensive(self):
        """Test BaseModel dictionary conversion methods."""
        now = datetime.now(timezone.utc)

        test_model = TestBasicModel(
            name="Dict Test",
            description="Testing dict conversion",
            active=True,
            price=Decimal("19.99"),
            category="conversion"
        )
        test_model.created = now
        test_model.modified = now

        # Test to_dict basic
        result = test_model.to_dict()
        assert isinstance(result, dict)
        assert result["name"] == "Dict Test"
        assert result["active"] is True
        assert str(result["price"]) == "19.99"

        # Test to_dict with exclude
        result_exclude = test_model.to_dict(exclude=["description", "category"])
        assert "description" not in result_exclude
        assert "category" not in result_exclude
        assert "name" in result_exclude

        # Test to_dict with include
        result_include = test_model.to_dict(include=["name", "price"])
        assert len(result_include) == 2
        assert "name" in result_include
        assert "price" in result_include
        assert "description" not in result_include

        # Test to_dict exclude_none
        test_model_partial = TestBasicModel(name="Partial Test")
        result_exclude_none = test_model_partial.to_dict(exclude_none=True)
        assert "name" in result_exclude_none
        assert "description" not in result_exclude_none
        assert "price" not in result_exclude_none
        assert "category" not in result_exclude_none

        # Test to_dict with datetime formatting
        result_datetime = test_model.to_dict(datetime_format="%Y-%m-%d %H:%M:%S")
        assert "created" in result_datetime
        assert "modified" in result_datetime

    def test_basemodel_json_conversion_comprehensive(self):
        """Test BaseModel JSON conversion methods."""
        test_model = TestBasicModel(
            name="JSON Test",
            description="Testing JSON conversion",
            active=False,
            price=Decimal("99.99"),
            category="json"
        )

        # Test to_json basic
        json_str = test_model.to_json()
        assert isinstance(json_str, str)

        parsed = json.loads(json_str)
        assert parsed["name"] == "JSON Test"
        assert parsed["active"] is False
        assert parsed["price"] == "99.99"
        assert parsed["category"] == "json"

        # Test to_json with custom parameters
        json_filtered = test_model.to_json(exclude=["description"], indent=2)
        parsed_filtered = json.loads(json_filtered)
        assert "description" not in parsed_filtered
        assert "name" in parsed_filtered

    def test_basemodel_update_from_dict_comprehensive(self):
        """Test BaseModel update_from_dict method."""
        test_model = TestBasicModel(
            name="Original",
            description="Original description",
            active=True,
            price=Decimal("10.00")
        )

        # Basic update
        update_data = {
            "name": "Updated Name",
            "description": "Updated description",
            "price": "25.50"  # String that should convert to Decimal
        }

        test_model.update_from_dict(update_data)

        assert test_model.name == "Updated Name"
        assert test_model.description == "Updated description"
        assert test_model.price == Decimal("25.50")
        assert test_model.active is True  # Should remain unchanged

        # Update with exclude
        update_data2 = {
            "name": "Should Not Change",
            "description": "New Description",
            "active": False
        }

        test_model.update_from_dict(update_data2, exclude=["name"])

        assert test_model.name == "Updated Name"  # Should not change
        assert test_model.description == "New Description"
        assert test_model.active is False

    def test_basemodel_timestamp_mixin_comprehensive(self):
        """Test TimestampMixin functionality."""
        timestamp_model = TestTimestampModel(
            title="Timestamp Test",
            content="Testing timestamp functionality"
        )

        # Initially timestamps should be None
        assert timestamp_model.created is None
        assert timestamp_model.modified is None

        # Save to database
        self.session.add(timestamp_model)
        self.session.commit()

        # Timestamps should be set
        assert timestamp_model.created is not None
        assert timestamp_model.modified is not None
        assert isinstance(timestamp_model.created, datetime)
        assert isinstance(timestamp_model.modified, datetime)

        # Test touch functionality
        original_modified = timestamp_model.modified
        timestamp_model.touch()

        assert timestamp_model.modified > original_modified

        # Save the touch
        self.session.commit()

    def test_basemodel_class_methods_comprehensive(self):
        """Test BaseModel class methods."""
        # Test get_table_name
        assert TestBasicModel.get_table_name() == "test_basic_model"
        assert TestTimestampModel.get_table_name() == "test_timestamp_model"

        # Test get_column_names
        basic_columns = TestBasicModel.get_column_names()
        assert "id" in basic_columns
        assert "name" in basic_columns
        assert "description" in basic_columns
        assert "created" in basic_columns
        assert "modified" in basic_columns

        # Test get_primary_key_columns
        pk_columns = TestBasicModel.get_primary_key_columns()
        assert pk_columns == ["id"]

        # Test has_column
        assert TestBasicModel.has_column("id") is True
        assert TestBasicModel.has_column("name") is True
        assert TestBasicModel.has_column("nonexistent") is False

        # Test get_column_type
        assert TestBasicModel.get_column_type("id") == int
        assert TestBasicModel.get_column_type("name") == str
        assert TestBasicModel.get_column_type("active") == bool
        assert TestBasicModel.get_column_type("price") == Decimal
        assert TestBasicModel.get_column_type("nonexistent") is None

    def test_basemodel_repr_methods_comprehensive(self):
        """Test BaseModel representation methods."""
        test_model = TestBasicModel(
            name="Repr Test",
            description="Testing repr methods",
            category="representation"
        )

        # Test __repr__ with ID (after save)
        self.session.add(test_model)
        self.session.commit()

        repr_str = repr(test_model)
        assert "TestBasicModel" in repr_str
        assert str(test_model.id) in repr_str

        # Test __str__
        str_str = str(test_model)
        assert "TestBasicModel" in str_str

    def test_basemodel_hybrid_properties(self):
        """Test BaseModel with hybrid properties."""
        hybrid_model = TestHybridModel(
            first_name="John",
            last_name="Doe",
            age=30
        )

        # Test hybrid property
        assert hybrid_model.full_name == "John Doe"

        # Save and test database-level hybrid property
        self.session.add(hybrid_model)
        self.session.commit()

        # Query using hybrid property
        result = self.session.query(TestHybridModel).filter(
            TestHybridModel.full_name == "John Doe"
        ).first()

        assert result is not None
        assert result.full_name == "John Doe"

    def test_basemodel_query_utilities(self):
        """Test BaseModel query utility methods."""
        # Create test data
        models = [
            TestBasicModel(name="Active 1", active=True, category="A"),
            TestBasicModel(name="Active 2", active=True, category="B"),
            TestBasicModel(name="Inactive 1", active=False, category="A"),
            TestBasicModel(name="Inactive 2", active=False, category="B"),
        ]

        for model in models:
            self.session.add(model)
        self.session.commit()

        # Test querying with different conditions
        active_models = self.session.query(TestBasicModel).filter_by(active=True).all()
        assert len(active_models) == 2

        category_a_models = self.session.query(TestBasicModel).filter_by(category="A").all()
        assert len(category_a_models) == 2

        # Test ordering
        ordered_models = self.session.query(TestBasicModel).order_by(TestBasicModel.name).all()
        assert ordered_models[0].name == "Active 1"
        assert ordered_models[-1].name == "Inactive 2"

    def test_basemodel_edge_cases_comprehensive(self):
        """Test BaseModel edge cases and error conditions."""
        # Test model with all optional fields
        minimal_model = TestBasicModel(name="Minimal")
        self.session.add(minimal_model)
        self.session.commit()

        assert minimal_model.id is not None
        assert minimal_model.description is None
        assert minimal_model.price is None
        assert minimal_model.category is None

        # Test model with maximum length strings
        max_name = "x" * 100
        max_description = "y" * 500

        max_model = TestBasicModel(
            name=max_name,
            description=max_description,
            category="max"
        )
        self.session.add(max_model)
        self.session.commit()

        assert max_model.name == max_name
        assert max_model.description == max_description

        # Test model with special characters
        special_model = TestBasicModel(
            name="Special & Chars <test>",
            description="Unicode: αβγδε Russian: абвгд Chinese: 中文",
            category="special"
        )
        self.session.add(special_model)
        self.session.commit()

        assert special_model.name == "Special & Chars <test>"
        assert "αβγδε" in special_model.description

    def test_basemodel_bulk_operations(self):
        """Test BaseModel bulk operations."""
        # Create multiple models for bulk testing
        bulk_models = [
            TestBasicModel(name=f"Bulk {i}", category="bulk_test")
            for i in range(100)
        ]

        # Bulk insert
        self.session.add_all(bulk_models)
        self.session.commit()

        # Verify bulk insert
        count = self.session.query(TestBasicModel).filter_by(category="bulk_test").count()
        assert count == 100

        # Bulk update
        self.session.query(TestBasicModel).filter_by(category="bulk_test").update(
            {"description": "Bulk updated"}
        )
        self.session.commit()

        # Verify bulk update
        updated_count = self.session.query(TestBasicModel).filter(
            TestBasicModel.category == "bulk_test",
            TestBasicModel.description == "Bulk updated"
        ).count()
        assert updated_count == 100

        # Bulk delete
        self.session.query(TestBasicModel).filter_by(category="bulk_test").delete()
        self.session.commit()

        # Verify bulk delete
        remaining_count = self.session.query(TestBasicModel).filter_by(category="bulk_test").count()
        assert remaining_count == 0

    def test_basemodel_transaction_handling(self):
        """Test BaseModel transaction handling."""
        # Start a transaction
        test_model = TestBasicModel(name="Transaction Test")
        self.session.add(test_model)

        # Save before rollback
        self.session.flush()
        model_id = test_model.id

        # Rollback transaction
        self.session.rollback()

        # Verify rollback
        rolled_back = self.session.query(TestBasicModel).filter_by(id=model_id).first()
        assert rolled_back is None

        # Try again with commit
        test_model2 = TestBasicModel(name="Committed Test")
        self.session.add(test_model2)
        self.session.commit()

        # Verify commit
        committed = self.session.query(TestBasicModel).filter_by(name="Committed Test").first()
        assert committed is not None
        assert committed.name == "Committed Test"

    def test_basemodel_validation_and_constraints(self):
        """Test BaseModel validation and database constraints."""
        # Test NOT NULL constraint
        with pytest.raises(Exception):  # Should raise IntegrityError or similar
            invalid_model = TestBasicModel()  # Missing required 'name' field
            self.session.add(invalid_model)
            self.session.commit()

        # Rollback any failed transaction
        self.session.rollback()

        # Test length constraints (if applicable)
        try:
            long_name = "x" * 200  # Exceeds VARCHAR(100)
            long_model = TestBasicModel(name=long_name, category="test")
            self.session.add(long_model)
            self.session.commit()
        except Exception:
            # Expected to fail due to length constraint
            self.session.rollback()

        # Verify valid model still works
        valid_model = TestBasicModel(name="Valid", category="validation")
        self.session.add(valid_model)
        self.session.commit()

        assert valid_model.id is not None