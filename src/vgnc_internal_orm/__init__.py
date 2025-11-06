"""VGNC Internal ORM Library

A comprehensive ORM library for VGNC database operations with SQLAlchemy
and Pydantic integration.
"""

__version__ = "0.1.0"
__author__ = "VGNC Development Team"
__email__ = "dev@vgnc.com"

from .config.settings import DatabaseConfig
from .models.base import BaseModel

__all__ = [
    "DatabaseConfig",
    "BaseModel",
]