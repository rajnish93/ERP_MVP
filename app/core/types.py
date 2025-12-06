"""
Custom SQLAlchemy types for enum handling.
Converts between Python enum instances and string storage in the database.
"""
from sqlalchemy import TypeDecorator, String
from typing import Type, TypeVar, Generic
import enum

T = TypeVar('T', bound=enum.Enum)


class EnumType(TypeDecorator, Generic[T]):
    """
    Stores Python enum values as strings in the database.
    Automatically converts between enum instances and string values.
    """
    impl = String
    cache_ok = True
    
    def __init__(self, enum_class: Type[T], length: int = 50, *args, **kwargs):
        super().__init__(length=length, *args, **kwargs)
        self.enum_class = enum_class
    
    def process_bind_param(self, value: T | str | None, dialect):
        """Convert enum to string when saving to database"""
        if value is None:
            return None
        if isinstance(value, str):
            return value
        if isinstance(value, self.enum_class):
            return value.value
        raise ValueError(f"Invalid value for {self.enum_class.__name__}: {value}")
    
    def process_result_value(self, value: str | None, dialect):
        """Convert string to enum when loading from database"""
        if value is None:
            return None
        # If value is already an enum instance (shouldn't happen from DB, but handle gracefully)
        if isinstance(value, self.enum_class):
            return value
        try:
            return self.enum_class(value)
        except ValueError:
            # If value doesn't match any enum member, log warning and return None
            # This handles migration scenarios gracefully but prevents type errors
            import logging
            logger = logging.getLogger(__name__)
            logger.warning(
                f"Invalid enum value '{value}' for {self.enum_class.__name__}. "
                f"Returning None. Valid values: {[e.value for e in self.enum_class]}"
            )
            return None


