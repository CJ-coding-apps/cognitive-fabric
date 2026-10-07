"""Main entry point for Cognitive Fabric MCP server."""

import asyncio
import sys

import structlog

from cognitive_fabric.config import settings
from cognitive_fabric.utils.logger import configure_logging


def main() -> None:
    """Main entry point."""
    # Configure logging first, from the settings the docs describe rather than
    # from this function's own defaults: COGNITIVE_FABRIC_LOG_LEVEL and
    # COGNITIVE_FABRIC_LOG_JSON reached nothing here before, so the container's
    # configured level and format were not the ones it ran with.
    configure_logging(json_output=settings.log_json, log_level=settings.log_level)

    logger = structlog.get_logger(__name__)
    logger.info("Cognitive Fabric MCP Server starting")

    try:
        from cognitive_fabric.mcp.server import run_server
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
        sys.exit(0)
    except Exception as e:
        logger.error("Server error", error=str(e))
        sys.exit(1)


if __name__ == "__main__":
    main()
