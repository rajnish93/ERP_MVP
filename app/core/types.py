"""
Custom SQLAlchemy types for enum handling.
Converts between Python enum instances and string storage in the database.
"""
import logging
from sqlalchemy import TypeDecorator, String
from typing import Type, TypeVar, Generic
import enum

T = TypeVar('T', bound=enum.Enum)

logger = logging.getLogger(__name__)


class EnumType(TypeDecorator, Generic[T]):
    """
    Stores Python enum values as strings in the database.
    Automatically converts between enum instances and string values.
    """
    impl = String
    cache_ok = True
    
    def __init__(self, enum_class: Type[T], length: int = 50, strict_mode: bool = True, *args, **kwargs):
        super().__init__(length=length, *args, **kwargs)
        self.enum_class = enum_class
        self.strict_mode = strict_mode
    
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
            # Handle invalid enum values based on strict_mode setting
            if self.strict_mode:
                # Fail-fast: raise descriptive exception for data integrity
                valid_values = [e.value for e in self.enum_class]
                raise ValueError(
                    f"Invalid enum value '{value}' for {self.enum_class.__name__}. "
                    f"Valid values: {valid_values}"
                ) from None
            else:
                # Legacy behavior: warn and return None for backward compatibility
                logger.warning(
                    f"Invalid enum value '{value}' for {self.enum_class.__name__}. "
                    f"Returning None. Valid values: {[e.value for e in self.enum_class]}"
                )
                return None


