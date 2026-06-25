"""Configuration management module for VGNC ORM."""

from db_common import DatabaseDriver

from .settings import DatabaseConfig

__all__ = [
    "DatabaseConfig",
    "DatabaseDriver",
]