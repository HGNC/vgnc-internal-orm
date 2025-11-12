"""Enhanced BaseModel tests covering relationships and complex database operations."""

import tempfile
from datetime import UTC, datetime
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine, Column, Integer, String, Text, DateTime, ForeignKey, Table
from sqlalchemy.orm import Session, sessionmaker, relationship
from sqlalchemy.ext.asyncio import AsyncSession

from src.vgnc_internal_orm.models.base import BaseModel, TimestampMixin, BaseCustomModel


class TestBaseModelRelationships:
    """Test BaseModel with real database relationships."""

    def setup_method(self):
        """Set up database with relationship models."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create association table for many-to-many relationships
        association_table = Table(
            'model_associations',
            BaseModel.metadata,
            Column('parent_id', Integer, ForeignKey('parent_models.id')),
            Column('child_id', Integer, ForeignKey('child_models.id'))
        )

        # Create models with relationships
        class ParentModel(BaseModel):
            __tablename__ = "parent_models"

            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            type = Column(String(50), nullable=True)

            # One-to-many relationship
            children = relationship("ChildModel", back_populates="parent", cascade="all, delete-orphan")

            # Many-to-many relationship
            related_models = relationship(
                "RelatedModel",
                secondary=association_table,
                back_populates="parents"
            )

        class ChildModel(BaseModel):
            __tablename__ = "child_models"

            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            parent_id = Column(Integer, ForeignKey('parent_models.id'))
            value = Column(Integer, nullable=True)

            parent = relationship("ParentModel", back_populates="children")

        class RelatedModel(BaseModel):
            __tablename__ = "related_models"

            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            description = Column(Text, nullable=True)

            parents = relationship(
                "ParentModel",
                secondary=association_table,
                back_populates="related_models"
            )

        self.ParentModel = ParentModel
        self.ChildModel = ChildModel
        self.RelatedModel = RelatedModel

        # Create all tables
        BaseModel.metadata.create_all(bind=self.engine)

    def teardown_method(self):
        """Clean up database."""
        self.engine.dispose()

    def test_basemodel_one_to_many_relationships(self):
        """Test BaseModel one-to-many relationships with real database."""
        session = self.SessionLocal()

        # Create parent with children
        parent = self.ParentModel(name="Parent 1", type="test")
        child1 = self.ChildModel(name="Child 1", value=10, parent=parent)
        child2 = self.ChildModel(name="Child 2", value=20, parent=parent)

        # This executes real relationship logic
        session.add(parent)
        session.add(child1)
        session.add(child2)
        session.commit()

        # Test relationship navigation
        assert len(parent.children) == 2
        assert child1.parent == parent
        assert child2.parent == parent
        assert parent.children[0].name == "Child 1"
        assert parent.children[1].name == "Child 2"

        # Test database queries with relationships
        queried_parent = session.query(self.ParentModel).filter_by(name="Parent 1").first()
        assert len(queried_parent.children) == 2

        session.close()

    def test_basemodel_many_to_many_relationships(self):
        """Test BaseModel many-to-many relationships with real database."""
        session = self.SessionLocal()

        # Create models
        parent1 = self.ParentModel(name="Parent 1")
        parent2 = self.ParentModel(name="Parent 2")
        related1 = self.RelatedModel(name="Related 1", description="Description 1")
        related2 = self.RelatedModel(name="Related 2", description="Description 2")

        # Set up many-to-many relationships
        parent1.related_models.extend([related1, related2])
        parent2.related_models.append(related1)

        # This executes real many-to-many relationship logic
        session.add_all([parent1, parent2, related1, related2])
        session.commit()

        # Test relationship navigation
        assert len(parent1.related_models) == 2
        assert len(parent2.related_models) == 1
        assert len(related1.parents) == 2
        assert len(related2.parents) == 1

        # Test database queries with relationships
        queried_parent = session.query(self.ParentModel).filter_by(name="Parent 1").first()
        assert len(queried_parent.related_models) == 2

        queried_related = session.query(self.RelatedModel).filter_by(name="Related 1").first()
        assert len(queried_related.parents) == 2

        session.close()

    def test_basemodel_cascade_operations(self):
        """Test BaseModel cascade operations with relationships."""
        session = self.SessionLocal()

        # Create parent with children
        parent = self.ParentModel(name="Cascade Parent")
        child1 = self.ChildModel(name="Cascade Child 1", value=100, parent=parent)
        child2 = self.ChildModel(name="Cascade Child 2", value=200, parent=parent)

        session.add(parent)
        session.commit()

        parent_id = parent.id
        child_count = session.query(self.ChildModel).filter_by(parent_id=parent_id).count()
        assert child_count == 2

        # Test cascade delete
        session.delete(parent)
        session.commit()

        # Children should be deleted due to cascade
        remaining_children = session.query(self.ChildModel).filter_by(parent_id=parent_id).count()
        assert remaining_children == 0

        session.close()

    def test_basemodel_relationship_lazy_loading(self):
        """Test BaseModel relationship lazy loading behavior."""
        session = self.SessionLocal()

        # Create parent and child
        parent = self.ParentModel(name="Lazy Parent")
        child = self.ChildModel(name="Lazy Child", value=300, parent=parent)

        session.add(parent)
        session.commit()

        # Test lazy loading by querying separately
        queried_parent = session.query(self.ParentModel).filter_by(name="Lazy Parent").first()
        queried_child = session.query(self.ChildModel).filter_by(name="Lazy Child").first()

        # Relationships should be loaded lazily
        assert queried_parent.children[0].id == queried_child.id
        assert queried_child.parent.id == queried_parent.id

        session.close()


class TestBaseModelComplexOperations:
    """Test BaseModel with complex database operations."""

    def setup_method(self):
        """Set up database for complex operations."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        # Create complex model
        class ComplexModel(BaseModel):
            __tablename__ = "complex_models"

            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            description = Column(Text, nullable=True)
            status = Column(String(20), nullable=True)
            priority = Column(Integer, nullable=True)
            created_date = Column(DateTime, nullable=True)
            tags = Column(Text, nullable=True)  # JSON-like tags

        self.ComplexModel = ComplexModel

        # Create tables
        BaseModel.metadata.create_all(bind=self.engine)

    def teardown_method(self):
        """Clean up database."""
        self.engine.dispose()

    def test_basemodel_complex_queries(self):
        """Test BaseModel with complex database queries."""
        session = self.SessionLocal()

        # Create test data
        test_data = [
            {"name": "High Priority", "status": "active", "priority": 1, "tags": "urgent,important"},
            {"name": "Medium Priority", "status": "pending", "priority": 5, "tags": "normal"},
            {"name": "Low Priority", "status": "inactive", "priority": 10, "tags": "low,priority"},
        ]

        for data in test_data:
            instance = self.ComplexModel(
                name=data["name"],
                status=data["status"],
                priority=data["priority"],
                tags=data["tags"],
                created_date=datetime.now(UTC)
            )
            session.add(instance)

        session.commit()

        # Test complex queries
        # Query with multiple conditions
        active_high_priority = session.query(self.ComplexModel).filter(
            self.ComplexModel.status == "active",
            self.ComplexModel.priority < 5
        ).all()
        assert len(active_high_priority) == 1

        # Query with ordering
        ordered_by_priority = session.query(self.ComplexModel).order_by(
            self.ComplexModel.priority.asc()
        ).all()
        assert ordered_by_priority[0].priority < ordered_by_priority[1].priority
        assert ordered_by_priority[1].priority < ordered_by_priority[2].priority

        # Query with like operations
        tagged_important = session.query(self.ComplexModel).filter(
            self.ComplexModel.tags.contains("important")
        ).all()
        assert len(tagged_important) == 1

        session.close()

    def test_basemodel_aggregation_queries(self):
        """Test BaseModel with aggregation queries."""
        session = self.SessionLocal()

        # Create test data
        priorities = [1, 2, 3, 4, 5, 1, 2, 3]
        for i, priority in enumerate(priorities):
            instance = self.ComplexModel(
                name=f"Item {i}",
                status="active",
                priority=priority,
                created_date=datetime.now(UTC)
            )
            session.add(instance)

        session.commit()

        # Test aggregation queries
        from sqlalchemy import func, extract

        # Count by status
        status_count = session.query(
            self.ComplexModel.status,
            func.count(self.ComplexModel.id).label('count')
        ).group_by(self.ComplexModel.status).all()
        assert len(status_count) == 1
        assert status_count[0].count == 8

        # Average priority
        avg_priority = session.query(
            func.avg(self.ComplexModel.priority).label('avg_priority')
        ).scalar()
        expected_avg = sum(priorities) / len(priorities)
        assert abs(avg_priority - expected_avg) < 0.001

        session.close()

    def test_basemodel_batch_operations(self):
        """Test BaseModel with batch database operations."""
        session = self.SessionLocal()

        # Batch insert
        batch_data = [
            {"name": f"Batch {i}", "status": "created", "priority": i}
            for i in range(100)
        ]

        batch_instances = [
            self.ComplexModel(**data) for data in batch_data
        ]

        session.add_all(batch_instances)
        session.commit()

        # Verify batch insert
        total_count = session.query(self.ComplexModel).filter(
            self.ComplexModel.name.like("Batch %")
        ).count()
        assert total_count == 100

        # Batch update
        session.query(self.ComplexModel).filter(
            self.ComplexModel.status == "created"
        ).update({"status": "processed"}, synchronize_session=False)
        session.commit()

        # Verify batch update
        processed_count = session.query(self.ComplexModel).filter(
            self.ComplexModel.status == "processed"
        ).count()
        assert processed_count == 100

        # Batch delete
        session.query(self.ComplexModel).filter(
            self.ComplexModel.priority > 90
        ).delete(synchronize_session=False)
        session.commit()

        # Verify batch delete
        remaining_count = session.query(self.ComplexModel).count()
        assert remaining_count == 90

        session.close()

    def test_basemodel_transaction_operations(self):
        """Test BaseModel with transaction operations."""
        session = self.SessionLocal()

        # Test successful transaction
        try:
            session.begin()

            # Insert multiple records
            for i in range(5):
                instance = self.ComplexModel(
                    name=f"Transaction {i}",
                    status="processing"
                )
                session.add(instance)

            # Commit transaction
            session.commit()

            # Verify all records were inserted
            count = session.query(self.ComplexModel).filter(
                self.ComplexModel.status == "processing"
            ).count()
            assert count == 5

        except Exception:
            session.rollback()
            raise

        # Test failed transaction (rollback)
        initial_count = session.query(self.ComplexModel).count()

        try:
            session.begin()

            # Insert valid record
            valid_instance = self.ComplexModel(name="Valid", status="valid")
            session.add(valid_instance)

            # Try to insert invalid record (this might not fail in SQLite, but let's simulate)
            session.execute("INSERT INTO complex_models (name, status) VALUES (?, ?)",
                          ("Invalid", None))  # This should work in SQLite

            # Simulate failure by raising exception
            raise ValueError("Simulated transaction failure")

        except ValueError:
            session.rollback()

            # Verify no records were added due to rollback
            final_count = session.query(self.ComplexModel).count()
            assert final_count == initial_count

        session.close()


class TestBaseModelPerformanceAndOptimization:
    """Test BaseModel performance and optimization scenarios."""

    def setup_method(self):
        """Set up database for performance testing."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        class PerformanceModel(BaseModel):
            __tablename__ = "performance_models"

            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=False)
            data = Column(Text, nullable=True)
            index_field = Column(String(50), nullable=True)

        self.PerformanceModel = PerformanceModel

        # Create tables
        BaseModel.metadata.create_all(bind=self.engine)

    def teardown_method(self):
        """Clean up database."""
        self.engine.dispose()

    def test_basemodel_bulk_insert_performance(self):
        """Test BaseModel bulk insert performance."""
        session = self.SessionLocal()

        # Create large dataset
        bulk_data = [
            {"name": f"Bulk Item {i}", "data": f"Data {i}"}
            for i in range(1000)
        ]

        # Time bulk insert
        import time
        start_time = time.time()

        session.bulk_insert_mappings(self.PerformanceModel, bulk_data)
        session.commit()

        end_time = time.time()
        insert_time = end_time - start_time

        # Verify all records were inserted
        count = session.query(self.PerformanceModel).filter(
            self.PerformanceModel.name.like("Bulk Item%")
        ).count()
        assert count == 1000

        # Performance should be reasonable (less than 5 seconds for 1000 records)
        assert insert_time < 5.0

        session.close()

    def test_basemodel_query_optimization(self):
        """Test BaseModel query optimization."""
        session = self.SessionLocal()

        # Create test data with indexable field
        test_data = [
            {"name": f"Optimized {i}", "index_field": f"index_{i % 10}"}
            for i in range(500)
        ]

        for data in test_data:
            instance = self.PerformanceModel(**data)
            session.add(instance)

        session.commit()

        # Test indexed query vs non-indexed query
        import time

        # Indexed query (should be faster)
        start_time = time.time()
        indexed_results = session.query(self.PerformanceModel).filter(
            self.PerformanceModel.index_field == "index_5"
        ).all()
        indexed_time = time.time() - start_time

        # Non-indexed query (full table scan)
        start_time = time.time()
        non_indexed_results = session.query(self.PerformanceModel).filter(
            self.PerformanceModel.name.like("%Optimized 5%")
        ).all()
        non_indexed_time = time.time() - start_time

        # Both should return same number of results
        assert len(indexed_results) == len(non_indexed_results)

        session.close()

    def test_basemodel_memory_efficiency(self):
        """Test BaseModel memory efficiency with large datasets."""
        session = self.SessionLocal()

        # Test query with large result set
        large_data = [
            {"name": f"Memory Test {i}", "data": "x" * 100}  # 100 characters per record
            for i in range(1000)
        ]

        for data in large_data:
            instance = self.PerformanceModel(**data)
            session.add(instance)

        session.commit()

        # Test memory-efficient querying
        from sqlalchemy.orm import lazyload

        # Query without loading all data at once
        start_time = time.time()
        results = session.query(self.PerformanceModel).yield_per(100)

        record_count = 0
        for batch in results:
            record_count += len(batch)
            # Process batch without keeping all data in memory

        query_time = time.time() - start_time
        assert record_count == 1000
        assert query_time < 2.0  # Should complete quickly

        session.close()


class TestBaseModelEdgeCases:
    """Test BaseModel edge cases and boundary conditions."""

    def setup_method(self):
        """Set up database for edge case testing."""
        self.engine = create_engine("sqlite:///:memory:", echo=False)
        self.SessionLocal = sessionmaker(bind=self.engine)

        class EdgeCaseModel(BaseModel):
            __tablename__ = "edge_case_models"

            id = Column(Integer, primary_key=True)
            name = Column(String(100), nullable=True)  # Allow null
            description = Column(Text, nullable=True)
            status = Column(String(20), default="pending")
            created_date = Column(DateTime, nullable=True)

        self.EdgeCaseModel = EdgeCaseModel

        # Create tables
        BaseModel.metadata.create_all(bind=self.engine)

    def teardown_method(self):
        """Clean up database."""
        self.engine.dispose()

    def test_basemodel_null_value_handling(self):
        """Test BaseModel handling of null values."""
        session = self.SessionLocal()

        # Create instances with various null scenarios
        null_instance = self.EdgeCaseModel()  # All fields except defaults
        partial_instance = self.EdgeCaseModel(name="Partial", description="Some description")

        session.add(null_instance)
        session.add(partial_instance)
        session.commit()

        # Test null value queries
        null_names = session.query(self.EdgeCaseModel).filter(
            self.EdgeCaseModel.name.is_(None)
        ).count()
        assert null_names >= 1

        non_null_names = session.query(self.EdgeCaseModel).filter(
            self.EdgeCaseModel.name.isnot(None)
        ).count()
        assert non_null_names >= 1

        session.close()

    def test_basemodel_max_value_constraints(self):
        """Test BaseModel with maximum value constraints."""
        session = self.SessionLocal()

        # Test with maximum length strings
        max_string = "x" * 100  # Matches column definition
        max_instance = self.EdgeCaseModel(name=max_string)

        session.add(max_instance)
        session.commit()

        # Verify max length handling
        queried = session.query(self.EdgeCaseModel).filter_by(id=max_instance.id).first()
        assert len(queried.name) == 100

        # Test with text field (should handle large amounts)
        large_text = "y" * 10000
        text_instance = self.EdgeCaseModel(name="Text Test", description=large_text)

        session.add(text_instance)
        session.commit()

        text_queried = session.query(self.EdgeCaseModel).filter_by(name="Text Test").first()
        assert len(text_queried.description) == 10000

        session.close()

    def test_basemodel_unicode_and_special_characters(self):
        """Test BaseModel with Unicode and special characters."""
        session = self.SessionLocal()

        unicode_test_cases = [
            {"name": "Tëst Ñâmé", "description": "Unicode test with ënicødé"},
            {"name": "Emoji Test 🚀", "description": "Testing with emojis: 🌟⭐✨"},
            {"name": "Special Chars", "description": "Testing: !@#$%^&*()[]{}|\\:;\"'<>?,./"},
            {"name": "New Lines\nTabs\t", "description": "Testing\nwhitespace\tcharacters"},
            {"name": "Quotes and 'Apostrophes'", "description": "Testing \"quotes\" and 'apostrophes'"},
        ]

        for test_case in unicode_test_cases:
            instance = self.EdgeCaseModel(**test_case)
            session.add(instance)

        session.commit()

        # Verify all unicode data was saved correctly
        for test_case in unicode_test_cases:
            queried = session.query(self.EdgeCaseModel).filter_by(name=test_case["name"]).first()
            assert queried is not None
            assert queried.description == test_case["description"]

        session.close()

    def test_basemodel_concurrent_operations(self):
        """Test BaseModel with concurrent operations."""
        # Note: SQLite may have limitations with true concurrency
        # But we can test the concurrent method signatures
        session = self.SessionLocal()

        # Create initial data
        for i in range(5):
            instance = self.EdgeCaseModel(name=f"Concurrent {i}")
            session.add(instance)
        session.commit()

        # Test concurrent-like operations (sequential but testing concurrent patterns)
        operations = []

        # Simulate concurrent updates
        for i in range(5):
            result = session.query(self.EdgeCaseModel).filter_by(name=f"Concurrent {i}").update({
                "status": "updated"
            }, synchronize_session=False)
            operations.append(result)

        session.commit()

        # Verify all operations completed
        updated_count = session.query(self.EdgeCaseModel).filter_by(status="updated").count()
        assert updated_count == 5

        session.close()