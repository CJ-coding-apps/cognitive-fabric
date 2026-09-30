"""MCP tool handlers."""

from cognitive_fabric.mcp.handlers.analyze import analyze_handler
from cognitive_fabric.mcp.handlers.associate import associate_handler
from cognitive_fabric.mcp.handlers.bulk_import import bulk_import_handler
from cognitive_fabric.mcp.handlers.context import context_handler
from cognitive_fabric.mcp.handlers.delete import delete_handler
from cognitive_fabric.mcp.handlers.detect import detect_handler
from cognitive_fabric.mcp.handlers.entity import entity_handler
from cognitive_fabric.mcp.handlers.fabric import fabric_handler
from cognitive_fabric.mcp.handlers.introspect import introspect_handler
from cognitive_fabric.mcp.handlers.memory_bank import memory_bank_handler
from cognitive_fabric.mcp.handlers.memory_optimizer import memory_optimizer_handler
from cognitive_fabric.mcp.handlers.query import query_handler
from cognitive_fabric.mcp.handlers.search import search_handler

TOOL_HANDLERS = {
    "memory-bank": memory_bank_handler,
    "entity": entity_handler,
    "context": context_handler,
    "query": query_handler,
    "associate": associate_handler,
    "analyze": analyze_handler,
    "detect": detect_handler,
    "introspect": introspect_handler,
    "bulk-import": bulk_import_handler,
    "search": search_handler,
    "delete": delete_handler,
    "memory-optimizer": memory_optimizer_handler,
    "fabric": fabric_handler,
}

__all__ = [
    "TOOL_HANDLERS",
    "analyze_handler",
    "associate_handler",
    "bulk_import_handler",
    "context_handler",
    "delete_handler",
    "detect_handler",
    "entity_handler",
    "fabric_handler",
    "introspect_handler",
    "memory_bank_handler",
    "memory_optimizer_handler",
    "query_handler",
    "search_handler",
]
