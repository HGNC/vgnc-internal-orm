"""VGNC Internal ORM Library

A comprehensive ORM library for VGNC database operations with SQLAlchemy
and Pydantic integration.
"""

__version__ = "0.2.0"
__author__ = "HGNC Development Team"
__email__ = "hgnc@genenames.org"

from .config.settings import DatabaseConfig
from .models.base import BaseModel

__all__ = [
    "DatabaseConfig",
    "BaseModel",
]
