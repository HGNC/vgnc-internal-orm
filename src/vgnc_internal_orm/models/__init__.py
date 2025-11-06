"""Models module for VGNC ORM."""

from .base import BaseModel
from .species import BaseCustomModel
from .genefam import Genefam
from .species import Species
from .chromosomes import Chromosomes
from .assembly import Assembly
from .supporting import (
    GeneStatus,
    Editor,
    AltName,
    AltSymbol,
    NomenclatureType,
    Comment,
    GeneFlag,
    FlagClass,
    FamilyNew
)
# Orthology models removed - they don't exist in the actual database

__all__ = [
    "BaseModel",
    "Genefam",
    "Species",
    "Chromosomes",
    "Assembly",
    "GeneStatus",
    "Editor",
    "AltName",
    "AltSymbol",
    "NomenclatureType",
    "Comment",
    "GeneFlag",
    "FlagClass",
    "FamilyNew",
]