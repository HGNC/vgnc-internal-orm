"""Comprehensive tests for TimestampMixin functionality.

This file consolidates all TimestampMixin tests from multiple files to avoid
duplication and provide better organization.
"""

from datetime import UTC, datetime
from time import sleep
from unittest.mock import Mock

import pytest

from vgnc_internal_orm.models.base import BaseCustomModel, BaseModel, TimestampMixin


class TestTimestampMixinUnit:
    """Unit tests for TimestampMixin functions."""

    def test_touch_method_timestamp_update(self):
        """Test touch method updates timestamp correctly."""
        mock_instance = Mock()

        # Record time before touching
        before_time = datetime.now(UTC)

        # Apply touch method
        TimestampMixin.touch(mock_instance)

        # Check timestamp was updated
        assert hasattr(mock_instance, "updated_at")
        assert isinstance(mock_instance.updated_at, datetime)
        assert mock_instance.updated_at.tzinfo == UTC
        assert mock_instance.updated_at >= before_time

    def test_touch_method_multiple_calls(self):
        """Test touch method can be called multiple times."""
        mock_instance = Mock()

        # First touch
        TimestampMixin.touch(mock_instance)
        first_time = mock_instance.updated_at

        # Small delay to ensure different timestamp
        sleep(0.001)

        # Second touch
        TimestampMixin.touch(mock_instance)
        second_time = mock_instance.updated_at

        # Should be different times
        assert second_time >= first_time

    def test_touch_method_with_existing_timestamp(self):
        """Test touch method with existing timestamp."""
        mock_instance = Mock()
        existing_time = datetime(2023, 1, 1, 12, 0, 0, tzinfo=UTC)
        mock_instance.updated_at = existing_time

        # Apply touch method
        TimestampMixin.touch(mock_instance)

        # Should have updated the timestamp
        assert mock_instance.updated_at != existing_time
        assert mock_instance.updated_at > existing_time

    def test_touch_method_timezone_handling(self):
        """Test touch method handles timezone correctly."""
        mock_instance = Mock()

        # Apply touch method
        TimestampMixin.touch(mock_instance)

        # Should always use UTC
        assert mock_instance.updated_at.tzinfo == UTC


class TestTimestampMixinIntegration:
    """Integration tests for TimestampMixin."""

    def test_timestamp_mixin_with_real_instance(self):
        """Test TimestampMixin with a real instance."""

        class TestModel:
            pass

        # Add TimestampMixin to the model
        TestModel.touch = TimestampMixin.touch

        instance = TestModel()

        # Test touch functionality
        before_time = datetime.now(UTC)
        instance.touch()
        after_time = datetime.now(UTC)

        assert hasattr(instance, "updated_at")
        assert isinstance(instance.updated_at, datetime)
        assert instance.updated_at.tzinfo == UTC
        assert before_time <= instance.updated_at <= after_time

    def test_timestamp_mixin_multiple_touches(self):
        """Test TimestampMixin with multiple touches."""

        class TestModel:
            pass

        TestModel.touch = TimestampMixin.touch
        instance = TestModel()

        # First touch
        instance.touch()
        first_time = instance.updated_at

        # Small delay
        sleep(0.001)

        # Second touch
        instance.touch()
        second_time = instance.updated_at

        assert second_time >= first_time

    def test_timestamp_mixin_multiple_calls_sequence(self):
        """Test TimestampMixin with multiple calls in sequence."""

        class TestModel:
            pass

        TestModel.touch = TimestampMixin.touch
        instance = TestModel()

        # Test that touch can be called multiple times in sequence
        instance.touch()  # First call
        first_time = instance.updated_at

        instance.touch()  # Second call
        second_time = instance.updated_at

        # Verify the timestamp was updated
        assert hasattr(instance, "updated_at")
        assert isinstance(instance.updated_at, datetime)
        assert second_time >= first_time

    def test_timestamp_mixin_with_inheritance(self):
        """Test TimestampMixin behavior with class inheritance."""

        class TestModel(TimestampMixin):
            pass

        instance = TestModel()

        # Should inherit the touch method
        assert hasattr(instance, "touch")
        assert callable(instance.touch)

        # Test touch functionality
        instance.touch()
        assert hasattr(instance, "updated_at")
        assert isinstance(instance.updated_at, datetime)


class TestTimestampMixinWithBaseModels:
    """Test TimestampMixin integration with BaseModel classes."""

    def test_basemodel_timestamp_mixin_integration(self):
        """Test BaseModel includes TimestampMixin functionality."""
        # Test that BaseModel has timestamp attributes
        assert hasattr(BaseModel, "created_at")
        assert hasattr(BaseModel, "updated_at")
        assert hasattr(BaseModel, "touch")

        # Test that BaseModel is a subclass of TimestampMixin
        assert issubclass(BaseModel, TimestampMixin)

    def test_basecustommodel_timestamp_mixin_integration(self):
        """Test BaseCustomModel includes TimestampMixin functionality."""
        # Test that BaseCustomModel has timestamp attributes
        assert hasattr(BaseCustomModel, "created_at")
        assert hasattr(BaseCustomModel, "updated_at")
        assert hasattr(BaseCustomModel, "touch")

        # Test that BaseCustomModel is a subclass of TimestampMixin
        assert issubclass(BaseCustomModel, TimestampMixin)

    def test_basecustommodel_touch_functionality(self):
        """Test BaseCustomModel touch functionality."""

        class TestCustomModel(BaseCustomModel):
            __tablename__ = "test_custom_model"

            from sqlalchemy import Column, Integer, String

            id = Column(Integer, primary_key=True)

            def __init__(self, **kwargs):
                # Initialize without calling super() to avoid SQLAlchemy setup
                for key, value in kwargs.items():
                    setattr(self, key, value)

        instance = TestCustomModel(id=1)

        # Test touch functionality
        before_time = datetime.now(UTC)
        instance.touch()
        after_time = datetime.now(UTC)

        assert hasattr(instance, "updated_at")
        assert isinstance(instance.updated_at, datetime)
        assert instance.updated_at.tzinfo == UTC
        assert before_time <= instance.updated_at <= after_time


class TestTimestampMixinEdgeCases:
    """Test edge cases and error conditions for TimestampMixin."""

    def test_touch_method_with_none_instance(self):
        """Test touch method behavior with None input."""
        # This should raise an AttributeError when trying to set attribute on None
        with pytest.raises(AttributeError):
            TimestampMixin.touch(None)

    def test_touch_method_with_custom_object(self):
        """Test touch method with custom object that has existing attributes."""

        class CustomObject:
            def __init__(self):
                self.updated_at = datetime(2020, 1, 1, tzinfo=UTC)
                self.some_other_field = "test"

        obj = CustomObject()
        original_time = obj.updated_at

        # Apply touch
        TimestampMixin.touch(obj)

        # Should update timestamp but preserve other fields
        assert obj.updated_at != original_time
        assert obj.updated_at > original_time
        assert obj.some_other_field == "test"

    def test_touch_method_thread_safety(self):
        """Test that touch method is thread-safe (basic test)."""
        import threading

        results = []

        def worker():
            mock_instance = Mock()
            TimestampMixin.touch(mock_instance)
            results.append(mock_instance.updated_at)

        # Create multiple threads
        threads = []
        for _ in range(5):
            thread = threading.Thread(target=worker)
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join()

        # All timestamps should be valid
        assert len(results) == 5
        for timestamp in results:
            assert isinstance(timestamp, datetime)
            assert timestamp.tzinfo == UTC

    def test_touch_method_performance(self):
        """Test touch method performance (basic sanity check)."""
        mock_instance = Mock()

        # Test multiple calls don't cause significant slowdown
        start_time = datetime.now(UTC)

        for _ in range(100):
            TimestampMixin.touch(mock_instance)

        end_time = datetime.now(UTC)
        duration = (end_time - start_time).total_seconds()

        # Should complete 100 calls in under 1 second (very generous threshold)
        assert duration < 1.0
