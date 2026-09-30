"""Repository layer for Cognitive Fabric."""

from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.repositories.component_repo import ComponentRepository
from cognitive_fabric.repositories.context_repo import ContextRepository
from cognitive_fabric.repositories.decision_repo import DecisionRepository
from cognitive_fabric.repositories.file_repo import FileRepository
from cognitive_fabric.repositories.metadata_repo import MetadataRepository
from cognitive_fabric.repositories.repository_repo import RepositoryRepository
from cognitive_fabric.repositories.requirement_repo import RequirementRepository
from cognitive_fabric.repositories.rule_repo import RuleRepository
from cognitive_fabric.repositories.symbol_repo import SymbolRepository
from cognitive_fabric.repositories.tag_repo import TagRepository
from cognitive_fabric.repositories.trace_repo import TraceRepository

__all__ = [
    "BaseRepository",
    "ComponentRepository",
    "ContextRepository",
    "DecisionRepository",
    "FileRepository",
    "MetadataRepository",
    "RepositoryRepository",
    "RequirementRepository",
    "RuleRepository",
    "SymbolRepository",
    "TagRepository",
    "TraceRepository",
]
