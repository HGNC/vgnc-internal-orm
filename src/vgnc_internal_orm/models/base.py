"""Base model definitions for VGNC ORM.

This module provides two base classes:

TimestampMixin: Common timestamp fields and helper for both id-based and
non-id-based tables.
BaseModel: Full-featured base with an auto-incrementing integer primary key
and rich utility/query helpers.
BaseCustomModel: For tables that use composite or alternative primary keys.
It supplies timestamps but intentionally omits the standard ``id`` column and
the heavy CRUD helpers that assume a single integer PK. Use this for
association tables or domain models with natural/composite keys.
"""

import json
from datetime import UTC, datetime
from typing import Any, Optional

from sqlalchemy import DateTime, Integer, String, Text
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column
from sqlalchemy.sql import func


class TimestampMixin:
    """Mixin supplying created/updated timestamp columns and touch helper."""

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Timestamp when record was created",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        comment="Timestamp when record was last updated",
    )

    def touch(self) -> None:  # Lightweight helper used by several domain models
        self.updated_at = datetime.now(UTC)


class UnifiedBase(DeclarativeBase):
    """Shared declarative base for all models.

    This unified base class is used by all models in the system, ensuring
    they all use the same metadata registry. This prevents circular import
    issues that arise from having separate metadata registries.
    """

    __abstract__ = True


class BaseModel(TimestampMixin, UnifiedBase):
    """Base model class with integer ``id`` primary key and rich helpers."""

    __abstract__ = True

    id: Mapped[int] = mapped_column(
        Integer, primary_key=True, autoincrement=True, comment="Primary key identifier"
    )

    @classmethod
    def get_table_name(cls) -> str:
        """Get the table name for this model."""
        if hasattr(cls, "__tablename__"):
            return str(getattr(cls, "__tablename__", ""))
        return cls.__name__.lower()

    @classmethod
    def get_column_names(cls) -> list[str]:
        """Get list of column names for this model."""
        return [str(column.name) for column in cls.__table__.columns]

    @classmethod
    def get_primary_key_columns(cls) -> list[str]:
        """Get list of primary key column names."""
        pk_columns = []
        for column in cls.__table__.primary_key.columns:  # type: ignore[attr-defined]
            pk_columns.append(str(column.name))
        return pk_columns

    @classmethod
    def has_column(cls, column_name: str) -> bool:
        """Check if model has a specific column."""
        return column_name in cls.__table__.columns

    @classmethod
    def get_column_type(cls, column_name: str) -> type | None:
        """Get the SQLAlchemy type for a specific column."""
        if column_name in cls.__table__.columns:
            return type(cls.__table__.columns[column_name].type)
        return None

    def to_dict(
        self,
        exclude: set[str] | None = None,
        include: set[str] | None = None,
        exclude_none: bool = False,
        datetime_format: str = "iso",
        serialize_relationships: bool = False,
    ) -> dict[str, Any]:
        """
        Convert model instance to dictionary with various options.

        Args:
            exclude: Set of field names to exclude from the result
            include: Set of field names to include (exclusive with exclude)
            exclude_none: Whether to exclude fields with None values
            datetime_format: Format for datetime fields ('iso', 'timestamp', or 'str')
            serialize_relationships: Whether to serialize loaded relationships

        Returns:
            Dictionary representation of the model
        """
        result = {}

        # Determine which fields to process
        if include is not None:
            fields_to_process = include
        else:
            fields_to_process = {column.name for column in self.__table__.columns}
            if exclude:
                fields_to_process -= exclude

        # Process each field
        for field_name in fields_to_process:
            if hasattr(self, field_name):
                value = getattr(self, field_name)

                # Skip None values if requested
                if exclude_none and value is None:
                    continue

                # Format datetime values
                if isinstance(value, datetime):
                    if datetime_format == "iso":
                        value = value.isoformat()
                    elif datetime_format == "timestamp":
                        value = value.timestamp()
                    elif datetime_format == "str":
                        value = str(value)

                # Handle relationships if requested
                if serialize_relationships and hasattr(self, field_name):
                    value = self._serialize_relationship(value, datetime_format)

                result[field_name] = value

        return result

    def to_json(
        self,
        exclude: set[str] | None = None,
        include: set[str] | None = None,
        exclude_none: bool = False,
        datetime_format: str = "iso",
        serialize_relationships: bool = False,
        **json_kwargs: Any,
    ) -> str:
        """
        Convert model instance to JSON string.

        Args:
            exclude: Set of field names to exclude from the result
            include: Set of field names to include (exclusive with exclude)
            exclude_none: Whether to exclude fields with None values
            datetime_format: Format for datetime fields ('iso', 'timestamp', or 'str')
            serialize_relationships: Whether to serialize loaded relationships
            **json_kwargs: Additional arguments passed to json.dumps()

        Returns:
            JSON string representation of the model
        """
        data = self.to_dict(
            exclude=exclude,
            include=include,
            exclude_none=exclude_none,
            datetime_format=datetime_format,
            serialize_relationships=serialize_relationships,
        )

        # Default JSON encoder settings
        json_kwargs.setdefault("default", self._json_default)
        json_kwargs.setdefault("ensure_ascii", False)

        return json.dumps(data, **json_kwargs)

    def update_from_dict(
        self,
        data: dict[str, Any],
        exclude: set[str] | None = None,
        only: set[str] | None = None,
    ) -> list[str]:
        """
        Update model instance from dictionary.

        Args:
            data: Dictionary of field values to update
            exclude: Set of field names to exclude from updating
            only: Set of field names to exclusively update

        Returns:
            List of field names that were actually updated
        """
        updated_fields = []

        for key, value in data.items():
            # Skip excluded fields
            if exclude and key in exclude:
                continue

            # Only update specified fields if 'only' is provided
            if only and key not in only:
                continue

            # Only update if the attribute exists and is a mapped column
            if hasattr(self, key) and key in self.__table__.columns:
                current_value = getattr(self, key)
                # Only update if the value is actually different
                if current_value != value:
                    setattr(self, key, value)
                    updated_fields.append(key)

        return updated_fields

    # touch provided by TimestampMixin

    def _serialize_relationship(self, value: Any, datetime_format: str) -> Any:
        """Helper method to serialize relationship values."""
        if value is None:
            return None
        elif hasattr(value, "to_dict"):  # Single related object
            return value.to_dict(datetime_format=datetime_format)
        elif hasattr(value, "__iter__") and not isinstance(
            value, (str, bytes, bytearray)
        ):  # Collection of related objects
            if hasattr(value, "all"):  # SQLAlchemy relationship collection
                value = value.all()
            return [
                (
                    item.to_dict(datetime_format=datetime_format)
                    if hasattr(item, "to_dict")
                    else item
                )
                for item in value
            ]
        else:
            return value

    @staticmethod
    def _json_default(obj: Any) -> Any:
        """Default JSON serializer for unsupported types."""
        if isinstance(obj, datetime):
            return obj.isoformat()
        elif hasattr(obj, "to_dict"):
            return obj.to_dict()
        elif hasattr(obj, "__dict__"):
            return obj.__dict__
        else:
            return str(obj)

    def refresh_timestamps(self, session: Session) -> None:
        """Force refresh of timestamp fields from database."""
        session.refresh(self)
        # Refresh specifically the timestamp fields
        session.refresh(self, ["created_at", "updated_at"])

    async def arefresh_timestamps(self, session: AsyncSession) -> None:
        """Force refresh of timestamp fields from database asynchronously."""
        await session.refresh(self)
        # Refresh specifically the timestamp fields
        await session.refresh(self, ["created_at", "updated_at"])

    def save(self, session: Session) -> None:
        """Save the model instance to the database."""
        session.add(self)
        session.commit()
        session.refresh(self)

    async def asave(self, session: AsyncSession) -> None:
        """Save the model instance to the database asynchronously."""
        session.add(self)
        await session.commit()
        await session.refresh(self)

    def delete(self, session: Session) -> None:
        """Delete the model instance from the database."""
        session.delete(self)
        session.commit()

    async def adelete(self, session: AsyncSession) -> None:
        """Delete the model instance from the database asynchronously."""
        await session.delete(self)
        await session.commit()

    def refresh(
        self, session: Session, attribute_names: list[str] | None = None
    ) -> None:
        """Refresh the model instance from the database."""
        session.refresh(self, attribute_names)

    async def arefresh(
        self, session: AsyncSession, attribute_names: list[str] | None = None
    ) -> None:
        """Refresh the model instance from the database asynchronously."""
        await session.refresh(self, attribute_names)

    def expire(
        self, session: Session, attribute_names: list[str] | None = None
    ) -> None:
        """Expire the model instance attributes."""
        session.expire(self, attribute_names)

    async def aexpire(
        self, session: AsyncSession, attribute_names: list[str] | None = None
    ) -> None:
        """Expire the model instance attributes asynchronously."""
        session.expire(self, attribute_names)  # expire returns None

    def get_dirty_fields(self, session: Session) -> set[str]:
        """Get set of dirty field names."""
        from sqlalchemy.orm.attributes import get_history

        dirty_fields = set()

        for column in self.__table__.columns:
            history = get_history(self, column.name)
            if history.has_changes():
                dirty_fields.add(column.name)

        return dirty_fields

    # Query helper methods (class methods)
    @classmethod
    def find_by_id(cls, session: Session, record_id: Any) -> Optional["BaseModel"]:
        """Find a record by its primary key ID."""
        return session.query(cls).filter(cls.id == record_id).first()

    @classmethod
    async def afind_by_id(
        cls, session: AsyncSession, record_id: Any
    ) -> Optional["BaseModel"]:
        """Find a record by its primary key ID asynchronously."""
        from sqlalchemy import select

        result = await session.execute(select(cls).filter(cls.id == record_id))
        return result.scalar_one_or_none()

    @classmethod
    def find_all(cls, session: Session, **filters: Any) -> list["BaseModel"]:
        """Find all records matching the given filters."""
        query = session.query(cls)
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        return query.all()

    @classmethod
    async def afind_all(
        cls, session: AsyncSession, **filters: Any
    ) -> list["BaseModel"]:
        """Find all records matching the given filters asynchronously."""
        from sqlalchemy import select

        stmt = select(cls)
        for key, value in filters.items():
            if hasattr(cls, key):
                stmt = stmt.filter(getattr(cls, key) == value)
        result = await session.execute(stmt)
        return list(result.scalars().all())

    @classmethod
    def find_one(cls, session: Session, **filters: Any) -> Optional["BaseModel"]:
        """Find one record matching the given filters."""
        query = session.query(cls)
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        return query.first()

    @classmethod
    async def afind_one(
        cls, session: AsyncSession, **filters: Any
    ) -> Optional["BaseModel"]:
        """Find one record matching the given filters asynchronously."""
        from sqlalchemy import select

        stmt = select(cls)
        for key, value in filters.items():
            if hasattr(cls, key):
                stmt = stmt.filter(getattr(cls, key) == value)
        result = await session.execute(stmt)
        return result.scalar_one_or_none()

    @classmethod
    def create(cls, session: Session, **kwargs: Any) -> "BaseModel":
        """Create a new record with the given attributes."""
        instance = cls(**kwargs)
        session.add(instance)
        session.commit()
        session.refresh(instance)
        return instance

    @classmethod
    async def acreate(cls, session: AsyncSession, **kwargs: Any) -> "BaseModel":
        """Create a new record with the given attributes asynchronously."""
        instance = cls(**kwargs)
        session.add(instance)
        await session.commit()
        await session.refresh(instance)
        return instance

    @classmethod
    def get_or_create(
        cls, session: Session, defaults: dict[str, Any] | None = None, **kwargs: Any
    ) -> tuple["BaseModel", bool]:
        """Get a record or create it if it doesn't exist."""
        instance = cls.find_one(session, **kwargs)
        if instance:
            return instance, False

        merge_data = {**kwargs}
        if defaults:
            merge_data.update(defaults)

        instance = cls.create(session, **merge_data)
        return instance, True

    @classmethod
    async def aget_or_create(
        cls,
        session: AsyncSession,
        defaults: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> tuple["BaseModel", bool]:
        """Get a record or create it if it doesn't exist asynchronously."""
        instance = await cls.afind_one(session, **kwargs)
        if instance:
            return instance, False

        merge_data = {**kwargs}
        if defaults:
            merge_data.update(defaults)

        instance = await cls.acreate(session, **merge_data)
        return instance, True

    @classmethod
    def update_by_id(
        cls, session: Session, record_id: Any, **kwargs: Any
    ) -> Optional["BaseModel"]:
        """Update a record by ID with the given attributes."""
        instance = cls.find_by_id(session, record_id)
        if instance:
            updated_fields = instance.update_from_dict(kwargs)
            if updated_fields:
                session.commit()
                session.refresh(instance)
        return instance

    @classmethod
    async def aupdate_by_id(
        cls, session: AsyncSession, record_id: Any, **kwargs: Any
    ) -> Optional["BaseModel"]:
        """Update a record by ID with the given attributes asynchronously."""
        instance = await cls.afind_by_id(session, record_id)
        if instance:
            updated_fields = instance.update_from_dict(kwargs)
            if updated_fields:
                await session.commit()
                await session.refresh(instance)
        return instance

    @classmethod
    def delete_by_id(cls, session: Session, record_id: Any) -> bool:
        """Delete a record by ID. Returns True if deleted, False if not found."""
        instance = cls.find_by_id(session, record_id)
        if instance:
            session.delete(instance)
            session.commit()
            return True
        return False

    @classmethod
    async def adelete_by_id(cls, session: AsyncSession, record_id: Any) -> bool:
        """Delete a record by ID asynchronously. Returns True if deleted, False if not found."""
        instance = await cls.afind_by_id(session, record_id)
        if instance:
            await session.delete(instance)
            await session.commit()
            return True
        return False

    @classmethod
    def count(cls, session: Session, **filters: Any) -> int:
        """Count records matching the given filters."""
        query = session.query(cls)
        for key, value in filters.items():
            if hasattr(cls, key):
                query = query.filter(getattr(cls, key) == value)
        return query.count()

    @classmethod
    async def acount(cls, session: AsyncSession, **filters: Any) -> int:
        """Count records matching the given filters asynchronously."""
        from sqlalchemy import func, select

        stmt = select(func.count(cls.id))
        for key, value in filters.items():
            if hasattr(cls, key):
                stmt = stmt.filter(getattr(cls, key) == value)
        result = await session.execute(stmt)
        count = result.scalar()
        return count or 0  # Ensure int return type

    @classmethod
    def exists(cls, session: Session, **filters: Any) -> bool:
        """Check if any record exists matching the given filters."""
        return cls.count(session, **filters) > 0

    @classmethod
    async def aexists(cls, session: AsyncSession, **filters: Any) -> bool:
        """Check if any record exists matching the given filters asynchronously."""
        return await cls.acount(session, **filters) > 0

    def get_field_value(self, field_name: str, default: Any = None) -> Any:
        """Get field value with optional default."""
        value = getattr(self, field_name, None)
        return default if value is None else value

    def set_field_value(self, field_name: str, value: Any) -> bool:
        """Set field value. Creates field if it doesn't exist."""
        # For SQLAlchemy models, prefer mapped columns
        if hasattr(self, "__table__") and field_name in self.__table__.columns:
            setattr(self, field_name, value)
            return True
        # Allow setting any attribute (for flexibility with non-mapped attributes)
        setattr(self, field_name, value)
        return True

    def has_field(self, field_name: str) -> bool:
        """Check if model has a specific field."""
        if not hasattr(self, field_name):
            return False
        if hasattr(self, "__table__"):
            return field_name in self.__table__.columns
        # For non-SQLAlchemy models, just check attribute existence
        return True

    def get_primary_key_value(self) -> Any:
        """Get the primary key value of the model."""
        return self.id

    def is_persisted(self) -> bool:
        """Check if the model instance is persisted (has an ID)."""
        return self.id is not None

    def __repr__(self) -> str:
        """String representation of the model."""
        class_name = self.__class__.__name__
        return f"<{class_name}(id={self.id})>"

    def __str__(self) -> str:
        """String representation of the model."""
        return f"{self.__class__.__name__}(id={self.id})"

    # UTF8MB4 charset validation methods
    def validate_utf8mb4_fields(self, *field_names: str) -> dict[str, Any]:
        """
        Validate that specified text fields can handle UTF8MB4 characters.

        Args:
            *field_names: Names of text fields to validate

        Returns:
            Dictionary with validation results for each field
        """
        from ..utils.mysql_features import CharsetValidator

        results = {}
        for field_name in field_names:
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                if isinstance(value, str):
                    results[field_name] = CharsetValidator.validate_text_encoding(value)
                else:
                    results[field_name] = {
                        "valid": True,
                        "encoding": "not_text",
                        "message": "Field is not a text field",
                    }
            else:
                results[field_name] = {
                    "valid": False,
                    "error": f"Field '{field_name}' does not exist",
                }

        return results

    def requires_utf8mb4(self, *field_names: str) -> dict[str, bool]:
        """
        Check if specified text fields contain characters requiring UTF8MB4.

        Args:
            *field_names: Names of text fields to check

        Returns:
            Dictionary mapping field names to boolean indicating UTF8MB4 requirement
        """
        from ..utils.mysql_features import UTF8MB4Handler

        results = {}
        for field_name in field_names:
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                if isinstance(value, str):
                    results[field_name] = UTF8MB4Handler.requires_utf8mb4(value)
                else:
                    results[field_name] = False
            else:
                results[field_name] = False

        return results

    def sanitize_for_basic_utf8(
        self, *field_names: str, replacement: str = "?"
    ) -> dict[str, str]:
        """
        Sanitize specified text fields by replacing UTF8MB4-only characters.

        Args:
            *field_names: Names of text fields to sanitize
            replacement: Character to use as replacement

        Returns:
            Dictionary mapping field names to sanitized values
        """
        from ..utils.mysql_features import UTF8MB4Handler

        results = {}
        for field_name in field_names:
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                if isinstance(value, str):
                    results[field_name] = UTF8MB4Handler.sanitize_for_basic_utf8(
                        value, replacement
                    )
                else:
                    results[field_name] = value
            else:
                results[field_name] = (
                    ""  # Empty string instead of None for str return type
                )

        return results

    def get_utf8mb4_summary(self) -> dict[str, Any]:
        """
        Get a summary of UTF8MB4 requirements for all text fields in the model.

        Returns:
            Summary with UTF8MB4 analysis for all text fields
        """
        from ..utils.mysql_features import UTF8MB4Handler

        summary: dict[str, Any] = {
            "model": self.__class__.__name__,
            "total_text_fields": 0,
            "utf8mb4_required_fields": 0,
            "fields_requiring_utf8mb4": [],
            "all_fields_support_utf8mb4": True,
            "emoji_count": 0,
            "total_characters": 0,
        }

        # Check all text columns
        for column in self.__table__.columns:
            if isinstance(column.type, (String, Text)):
                summary["total_text_fields"] = summary["total_text_fields"] + 1

                field_name = column.name
                if hasattr(self, field_name):
                    value = getattr(self, field_name)
                    if isinstance(value, str):
                        summary["total_characters"] = summary["total_characters"] + len(
                            value
                        )

                        if UTF8MB4Handler.requires_utf8mb4(value):
                            summary["utf8mb4_required_fields"] = (
                                summary["utf8mb4_required_fields"] + 1
                            )
                            summary["fields_requiring_utf8mb4"].append(field_name)
                            summary["all_fields_support_utf8mb4"] = False

                        # Count emoji characters
                        for char in value:
                            char_code = ord(char)
                            for start, end in UTF8MB4Handler.EMOJI_RANGES:
                                if start <= char_code <= end:
                                    summary["emoji_count"] = summary["emoji_count"] + 1
                                    break

        return summary

    @classmethod
    def search_with_charset_support(
        cls,
        session: Session,
        search_term: str,
        *field_names: str,
        case_sensitive: bool = False,
        exact_match: bool = False,
    ) -> list["BaseCustomModel"]:
        """Search records with proper charset and collation support.

        This method provides charset-aware searching for UTF8MB4 fields,
        ensuring proper handling of international characters and emoji.
        It automatically applies the appropriate MySQL COLLATE clauses
        for optimal search results with UTF8MB4 encoded data.

        Args:
            session: SQLAlchemy session object
            search_term: Search term to look for
            *field_names: Field names to search in
            case_sensitive: Whether to perform case-sensitive search
            exact_match: Whether to require exact match (vs contains)

        Returns:
            List of matching records

        Raises:
            ValueError: If no field names provided
            ImportError: If SQLAlchemy is not available
        """
        # Lazy imports to avoid circular dependencies
        try:
            from sqlalchemy import or_, text
        except ImportError as e:
            raise ImportError("SQLAlchemy is required for charset-aware search") from e

        if not field_names:
            raise ValueError("At least one field name must be provided")

        if not hasattr(cls, "__tablename__"):
            raise ValueError("Model must have a __tablename__ attribute")

        table_name = cls.__tablename__
        conditions = []

        for field_name in field_names:
            if not hasattr(cls, field_name):
                continue

            if exact_match:
                if case_sensitive:
                    # Use COLLATE utf8mb4_bin for case-sensitive exact match
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_bin = :search_term"
                    )
                else:
                    # Use COLLATE utf8mb4_general_ci for case-insensitive exact match
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_general_ci = :search_term"
                    )
            else:
                if case_sensitive:
                    # Use COLLATE utf8mb4_bin for case-sensitive contains search
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_bin LIKE CONCAT('%', :search_term, '%')"
                    )
                else:
                    # Use COLLATE utf8mb4_general_ci for case-insensitive contains search
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_general_ci LIKE CONCAT('%', :search_term, '%')"
                    )

            conditions.append(condition)

        if not conditions:
            return []

        # Combine conditions with OR and bind parameters
        query = (
            session.query(cls).filter(or_(*conditions)).params(search_term=search_term)
        )

        return query.all()  # type: ignore[return-value]

    @classmethod
    async def asearch_with_charset_support(
        cls,
        session: "AsyncSession",
        search_term: str,
        *field_names: str,
        case_sensitive: bool = False,
        exact_match: bool = False,
    ) -> list["BaseCustomModel"]:
        """Async version of search_with_charset_support.

        This method provides charset-aware searching for UTF8MB4 fields,
        ensuring proper handling of international characters and emoji.
        It automatically applies the appropriate MySQL COLLATE clauses
        for optimal search results with UTF8MB4 encoded data.

        Args:
            session: SQLAlchemy async session object
            search_term: Search term to look for
            *field_names: Field names to search in
            case_sensitive: Whether to perform case-sensitive search
            exact_match: Whether to require exact match (vs contains)

        Returns:
            List of matching records

        Raises:
            ValueError: If no field names provided
            ImportError: If SQLAlchemy is not available
        """
        # Lazy imports to avoid circular dependencies
        try:
            from sqlalchemy import or_, text
        except ImportError as e:
            raise ImportError("SQLAlchemy is required for charset-aware search") from e

        if not field_names:
            raise ValueError("At least one field name must be provided")

        if not hasattr(cls, "__tablename__"):
            raise ValueError("Model must have a __tablename__ attribute")

        table_name = cls.__tablename__
        conditions = []

        for field_name in field_names:
            if not hasattr(cls, field_name):
                continue

            if exact_match:
                if case_sensitive:
                    # Use COLLATE utf8mb4_bin for case-sensitive exact match
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_bin = :search_term"
                    )
                else:
                    # Use COLLATE utf8mb4_general_ci for case-insensitive exact match
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_general_ci = :search_term"
                    )
            else:
                if case_sensitive:
                    # Use COLLATE utf8mb4_bin for case-sensitive contains search
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_bin LIKE CONCAT('%', :search_term, '%')"
                    )
                else:
                    # Use COLLATE utf8mb4_general_ci for case-insensitive contains search
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_general_ci LIKE CONCAT('%', :search_term, '%')"
                    )

            conditions.append(condition)

        if not conditions:
            return []

        # Combine conditions with OR and execute
        from sqlalchemy import select

        stmt = select(cls).where(or_(*conditions)).params(search_term=search_term)
        result = await session.execute(stmt)

        return result.scalars().all()  # type: ignore[return-value]


class BaseCustomModel(TimestampMixin, UnifiedBase):
    """Base class for tables with composite/natural primary keys.

    Provides timestamps and ``touch`` but intentionally omits the auto
    integer ``id`` and the CRUD helpers that assume it.

    Note: BaseCustomModel now uses the same metadata registry as BaseModel
    (UnifiedBase) to eliminate circular import issues.
    """

    __abstract__ = True

    def requires_utf8mb4(self, *field_names: str) -> dict[str, bool]:
        """
        Check if specified text fields contain characters requiring UTF8MB4.

        Args:
            *field_names: Names of text fields to check

        Returns:
            Dictionary mapping field names to boolean indicating UTF8MB4 requirement
        """
        from ..utils.mysql_features import UTF8MB4Handler

        results = {}
        for field_name in field_names:
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                if isinstance(value, str):
                    results[field_name] = UTF8MB4Handler.requires_utf8mb4(value)
                else:
                    results[field_name] = False
            else:
                results[field_name] = False

        return results

    def sanitize_for_basic_utf8(
        self, *field_names: str, replacement: str = "?"
    ) -> dict[str, str]:
        """
        Sanitize specified text fields by replacing UTF8MB4-only characters.

        Args:
            *field_names: Names of text fields to sanitize
            replacement: Character to use as replacement

        Returns:
            Dictionary mapping field names to sanitized values
        """
        from ..utils.mysql_features import UTF8MB4Handler

        results = {}
        for field_name in field_names:
            if hasattr(self, field_name):
                value = getattr(self, field_name)
                if isinstance(value, str):
                    results[field_name] = UTF8MB4Handler.sanitize_for_basic_utf8(
                        value, replacement
                    )
                else:
                    results[field_name] = value
            else:
                results[field_name] = (
                    ""  # Empty string instead of None for str return type
                )

        return results

    def get_utf8mb4_summary(self) -> dict[str, Any]:
        """
        Get a summary of UTF8MB4 requirements for all text fields in the model.

        Returns:
            Summary with UTF8MB4 analysis for all text fields
        """
        from ..utils.mysql_features import UTF8MB4Handler

        summary: dict[str, Any] = {
            "model": self.__class__.__name__,
            "total_text_fields": 0,
            "utf8mb4_required_fields": 0,
            "fields_requiring_utf8mb4": [],
            "all_fields_support_utf8mb4": True,
            "emoji_count": 0,
            "total_characters": 0,
        }

        # Check all text columns
        for column in self.__table__.columns:
            if isinstance(column.type, (String, Text)):
                summary["total_text_fields"] = summary["total_text_fields"] + 1

                field_name = column.name
                if hasattr(self, field_name):
                    value = getattr(self, field_name)
                    if isinstance(value, str):
                        summary["total_characters"] = summary["total_characters"] + len(
                            value
                        )

                        if UTF8MB4Handler.requires_utf8mb4(value):
                            summary["utf8mb4_required_fields"] = (
                                summary["utf8mb4_required_fields"] + 1
                            )
                            summary["fields_requiring_utf8mb4"].append(field_name)
                            summary["all_fields_support_utf8mb4"] = False

                        # Count emoji characters
                        for char in value:
                            char_code = ord(char)
                            for start, end in UTF8MB4Handler.EMOJI_RANGES:
                                if start <= char_code <= end:
                                    summary["emoji_count"] = summary["emoji_count"] + 1
                                    break

        return summary

    @classmethod
    def search_with_charset_support(
        cls,
        session: Session,
        search_term: str,
        *field_names: str,
        case_sensitive: bool = False,
        exact_match: bool = False,
    ) -> list["BaseCustomModel"]:
        """Search records with proper charset and collation support.

        This method provides charset-aware searching for UTF8MB4 fields,
        ensuring proper handling of international characters and emoji.
        It automatically applies the appropriate MySQL COLLATE clauses
        for optimal search results with UTF8MB4 encoded data.

        Args:
            session: SQLAlchemy session object
            search_term: Search term to look for
            *field_names: Field names to search in
            case_sensitive: Whether to perform case-sensitive search
            exact_match: Whether to require exact match (vs contains)

        Returns:
            List of matching records

        Raises:
            ValueError: If no field names provided
            ImportError: If SQLAlchemy is not available
        """
        # Lazy imports to avoid circular dependencies
        try:
            from sqlalchemy import or_, text
        except ImportError as e:
            raise ImportError("SQLAlchemy is required for charset-aware search") from e

        if not field_names:
            raise ValueError("At least one field name must be provided")

        if not hasattr(cls, "__tablename__"):
            raise ValueError("Model must have a __tablename__ attribute")

        table_name = cls.__tablename__
        conditions = []

        for field_name in field_names:
            if not hasattr(cls, field_name):
                continue

            if exact_match:
                if case_sensitive:
                    # Use COLLATE utf8mb4_bin for case-sensitive exact match
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_bin = :search_term"
                    )
                else:
                    # Use COLLATE utf8mb4_general_ci for case-insensitive exact match
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_general_ci = :search_term"
                    )
            else:
                if case_sensitive:
                    # Use COLLATE utf8mb4_bin for case-sensitive contains search
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_bin LIKE CONCAT('%', :search_term, '%')"
                    )
                else:
                    # Use COLLATE utf8mb4_general_ci for case-insensitive contains search
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_general_ci LIKE CONCAT('%', :search_term, '%')"
                    )

            conditions.append(condition)

        if not conditions:
            return []

        # Combine conditions with OR and bind parameters
        query = (
            session.query(cls).filter(or_(*conditions)).params(search_term=search_term)
        )

        return query.all()

    @classmethod
    async def asearch_with_charset_support(
        cls,
        session: "AsyncSession",
        search_term: str,
        *field_names: str,
        case_sensitive: bool = False,
        exact_match: bool = False,
    ) -> list["BaseCustomModel"]:
        """Async version of search_with_charset_support.

        This method provides charset-aware searching for UTF8MB4 fields,
        ensuring proper handling of international characters and emoji.
        It automatically applies the appropriate MySQL COLLATE clauses
        for optimal search results with UTF8MB4 encoded data.

        Args:
            session: SQLAlchemy async session object
            search_term: Search term to look for
            *field_names: Field names to search in
            case_sensitive: Whether to perform case-sensitive search
            exact_match: Whether to require exact match (vs contains)

        Returns:
            List of matching records

        Raises:
            ValueError: If no field names provided
            ImportError: If SQLAlchemy is not available
        """
        # Lazy imports to avoid circular dependencies
        try:
            from sqlalchemy import or_, text
        except ImportError as e:
            raise ImportError("SQLAlchemy is required for charset-aware search") from e

        if not field_names:
            raise ValueError("At least one field name must be provided")

        if not hasattr(cls, "__tablename__"):
            raise ValueError("Model must have a __tablename__ attribute")

        table_name = cls.__tablename__
        conditions = []

        for field_name in field_names:
            if not hasattr(cls, field_name):
                continue

            if exact_match:
                if case_sensitive:
                    # Use COLLATE utf8mb4_bin for case-sensitive exact match
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_bin = :search_term"
                    )
                else:
                    # Use COLLATE utf8mb4_general_ci for case-insensitive exact match
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_general_ci = :search_term"
                    )
            else:
                if case_sensitive:
                    # Use COLLATE utf8mb4_bin for case-sensitive contains search
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_bin LIKE CONCAT('%', :search_term, '%')"
                    )
                else:
                    # Use COLLATE utf8mb4_general_ci for case-insensitive contains search
                    condition = text(
                        f"CAST({table_name}.{field_name} AS CHAR) COLLATE utf8mb4_general_ci LIKE CONCAT('%', :search_term, '%')"
                    )

            conditions.append(condition)

        if not conditions:
            return []

        # Combine conditions with OR and execute
        from sqlalchemy import select

        stmt = select(cls).where(or_(*conditions)).params(search_term=search_term)
        result = await session.execute(stmt)

        return result.scalars().all()  # type: ignore[return-value]
