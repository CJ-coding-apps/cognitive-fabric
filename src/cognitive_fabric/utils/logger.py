"""Logging configuration using structlog."""

import sys
from typing import Any

import structlog


def configure_logging(json_output: bool = True, log_level: str = "INFO") -> None:
    """Configure structlog for the application.

    Args:
        json_output: If True, output JSON format. If False, use console format.
        log_level: The logging level (DEBUG, INFO, WARNING, ERROR).
    """
    # NOTE: structlog.stdlib.add_logger_name requires a stdlib logger with a
    # `.name`; it is incompatible with PrintLoggerFactory (used below) and is
    # therefore omitted.
    processors: list[Any] = [
        structlog.stdlib.add_log_level,
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.UnicodeDecoder(),
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer())

    structlog.configure(
        processors=processors,
        wrapper_class=structlog.stdlib.BoundLogger,
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(file=sys.stderr),
        cache_logger_on_first_use=True,
    )


def get_logger(name: str) -> structlog.stdlib.BoundLogger:
    """Get a logger instance with the given name.

    Args:
        name: The logger name (typically module name).

    Returns:
        A bound logger instance.
    """
    return structlog.get_logger(name)


# Pre-configured loggers for specific components
def get_kuzu_logger() -> structlog.stdlib.BoundLogger:
    """Get logger for KuzuDB operations."""
    return get_logger("KuzuDB")


def get_memory_service_logger() -> structlog.stdlib.BoundLogger:
    """Get logger for MemoryService."""
    return get_logger("MemoryService")


def get_mcp_logger() -> structlog.stdlib.BoundLogger:
    """Get logger for MCP server."""
    return get_logger("MCP")


def get_repository_logger() -> structlog.stdlib.BoundLogger:
    """Get logger for repository operations."""
    return get_logger("Repository")


def get_optimizer_logger() -> structlog.stdlib.BoundLogger:
    """Get logger for memory optimizer agent."""
    return get_logger("MemoryOptimizer")
