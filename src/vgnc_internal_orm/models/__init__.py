"""Models module for VGNC ORM."""

from .assembly import Assembly
from .base import BaseModel
from .chromosomes import Chromosomes
from .genefam import Genefam
from .species import BaseCustomModel, Species
from .supporting import (
    AltName,
    AltSymbol,
    Comment,
    Editor,
    FamilyNew,
    FlagClass,
    GeneFlag,
    GeneStatus,
    NomenclatureType,
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
