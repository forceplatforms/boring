"""
Base model with common fields and functionality for all database models.
"""

import uuid
from datetime import datetime
from typing import Any, Dict, Optional, Type, TypeVar

from sqlalchemy import Column, DateTime, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import Session

from complianceguard.database import Base

T = TypeVar("T", bound="BaseModel")


class BaseModel(Base):
    """
    Abstract base model with common fields and methods.

    All models should inherit from this class to get:
    - UUID primary key
    - created_at and updated_at timestamps
    - Common CRUD operations
    - JSON serialization
    """

    __abstract__ = True

    # Common columns for all models
    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        nullable=False,
        index=True,
    )

    created_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        index=True,
    )

    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
        index=True,
    )

    @declared_attr
    def __tablename__(cls) -> str:
        """Generate table name from class name."""
        # Convert CamelCase to snake_case
        name = cls.__name__
        # Handle acronyms and multiple capitals
        result = []
        for i, char in enumerate(name):
            if char.isupper():
                if i > 0 and (
                    i + 1 < len(name)
                    and name[i + 1].islower()
                    or name[i - 1].islower()
                ):
                    result.append("_")
                result.append(char.lower())
            else:
                result.append(char)
        table_name = "".join(result).lstrip("_")
        # Pluralize common patterns
        if table_name.endswith("y"):
            return f"{table_name[:-1]}ies"
        elif table_name.endswith("s"):
            return f"{table_name}es"
        else:
            return f"{table_name}s"

    def __repr__(self) -> str:
        """String representation of the model."""
        return f"<{self.__class__.__name__}(id={self.id})>"

    def __str__(self) -> str:
        """Human-readable string representation."""
        return f"{self.__class__.__name__} {self.id}"

    def to_dict(
        self,
        exclude: Optional[set] = None,
        include_relationships: bool = False,
    ) -> Dict[str, Any]:
        """
        Convert model to dictionary.

        Args:
            exclude: Set of field names to exclude.
            include_relationships: Whether to include relationship fields.

        Returns:
            Dictionary representation of the model.
        """
        exclude = exclude or set()
        result = {}

        # Include all column attributes
        for column in self.__table__.columns:
            if column.name not in exclude:
                value = getattr(self, column.name)
                # Handle special types
                if isinstance(value, datetime):
                    value = value.isoformat()
                elif isinstance(value, uuid.UUID):
                    value = str(value)
                result[column.name] = value

        # Optionally include relationships
        if include_relationships:
            for relationship in self.__mapper__.relationships:
                if relationship.key not in exclude:
                    value = getattr(self, relationship.key)
                    if value is not None:
                        if hasattr(value, "to_dict"):
                            result[relationship.key] = value.to_dict()
                        elif hasattr(value, "__iter__"):
                            result[relationship.key] = [
                                item.to_dict() if hasattr(item, "to_dict") else str(item)
                                for item in value
                            ]
                        else:
                            result[relationship.key] = str(value)

        return result

    @classmethod
    def create(
        cls: Type[T],
        db: Session,
        commit: bool = True,
        **kwargs: Any,
    ) -> T:
        """
        Create a new instance and save to database.

        Args:
            db: Database session.
            commit: Whether to commit the transaction.
            **kwargs: Field values for the new instance.

        Returns:
            Created instance.
        """
        instance = cls(**kwargs)
        db.add(instance)
        if commit:
            db.commit()
            db.refresh(instance)
        return instance

    @classmethod
    def get_by_id(
        cls: Type[T],
        db: Session,
        id: uuid.UUID,
    ) -> Optional[T]:
        """
        Get instance by ID.

        Args:
            db: Database session.
            id: Instance ID.

        Returns:
            Instance if found, None otherwise.
        """
        return db.query(cls).filter(cls.id == id).first()

    @classmethod
    def get_all(
        cls: Type[T],
        db: Session,
        skip: int = 0,
        limit: int = 100,
    ) -> list[T]:
        """
        Get all instances with pagination.

        Args:
            db: Database session.
            skip: Number of records to skip.
            limit: Maximum number of records to return.

        Returns:
            List of instances.
        """
        return db.query(cls).offset(skip).limit(limit).all()

    @classmethod
    def count(cls: Type[T], db: Session) -> int:
        """
        Count total number of instances.

        Args:
            db: Database session.

        Returns:
            Total count.
        """
        return db.query(cls).count()

    def update(
        self,
        db: Session,
        commit: bool = True,
        **kwargs: Any,
    ) -> None:
        """
        Update instance fields.

        Args:
            db: Database session.
            commit: Whether to commit the transaction.
            **kwargs: Field values to update.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
        if commit:
            db.commit()
            db.refresh(self)

    def delete(self, db: Session, commit: bool = True) -> None:
        """
        Delete instance from database.

        Args:
            db: Database session.
            commit: Whether to commit the transaction.
        """
        db.delete(self)
        if commit:
            db.commit()

    @classmethod
    def bulk_create(
        cls: Type[T],
        db: Session,
        instances: list[dict],
        commit: bool = True,
    ) -> list[T]:
        """
        Bulk create multiple instances.

        Args:
            db: Database session.
            instances: List of dictionaries with field values.
            commit: Whether to commit the transaction.

        Returns:
            List of created instances.
        """
        objects = [cls(**data) for data in instances]
        db.bulk_save_objects(objects, return_defaults=True)
        if commit:
            db.commit()
        return objects