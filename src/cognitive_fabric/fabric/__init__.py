"""Cognitive Fabric layer: in-process symbolic ingestion + semantic layer."""

from cognitive_fabric.fabric.ingestor import SymbolicIngestor
from cognitive_fabric.fabric.vector_store import VectorStore

__all__ = ["SymbolicIngestor", "VectorStore"]
