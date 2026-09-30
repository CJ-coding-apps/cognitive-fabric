"""MCP server implementation using stdio transport."""

import asyncio
import json
from typing import Optional

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from cognitive_fabric.config import Settings
from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.mcp.tool_registry import ToolRegistry
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)

# Global state
_memory_service: Optional[MemoryService] = None
_tool_registry: Optional[ToolRegistry] = None
_context: Optional[ToolHandlerContext] = None


async def create_server(
    db_path: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> Server:
    """Create and configure the MCP server.

    Args:
        db_path: Optional path to the database.
        settings: Optional settings object.

    Returns:
        The configured MCP server.
    """
    global _memory_service, _tool_registry, _context

    # Load settings if not provided
    if settings is None:
        settings = Settings()

    # Use provided db_path or default from settings
    if db_path is None:
        db_path = settings.db_path_override

    logger.info("Creating MCP server", db_path=db_path)

    # Initialize memory service
    _memory_service = await MemoryService.get_instance(db_path)

    # Initialize tool registry
    _tool_registry = ToolRegistry()

    # Initialize context
    _context = ToolHandlerContext()

    # Create server
    server = Server("cognitive_fabric-mcp")

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        tools = _tool_registry.list_tools()
        return [
            Tool(
                name=tool.name,
                description=tool.description,
                inputSchema=tool.parameters,
            )
            for tool in tools
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict) -> list[TextContent]:
        """Call a tool by name.

        Args:
            name: The tool name.
            arguments: The tool arguments.

        Returns:
            List of text content with the result.
        """
        logger.debug(f"Tool call: {name}", arguments=arguments)

        try:
            result = await _tool_registry.call_tool(
                name,
                arguments,
                _context,
                _memory_service,
            )

            # Convert result to JSON string
            result_json = json.dumps(result, indent=2, default=str)

            return [TextContent(type="text", text=result_json)]

        except Exception as e:
            logger.error(f"Tool call error: {name}", error=str(e))
            error_result = {
                "success": False,
                "error": str(e),
            }
            return [TextContent(type="text", text=json.dumps(error_result))]

    logger.info("MCP server created successfully")
    return server


async def run_server(
    db_path: Optional[str] = None,
    settings: Optional[Settings] = None,
) -> None:
    """Run the MCP server with stdio transport.

    Args:
        db_path: Optional path to the database.
        settings: Optional settings object.
    """
    server = await create_server(db_path, settings)

    logger.info("Starting MCP server with stdio transport")

    async with stdio_server() as (read_stream, write_stream):
        await server.run(
            read_stream,
            write_stream,
            server.create_initialization_options(),
        )


async def run_http_server(
    db_path: Optional[str] = None,
    settings: Optional[Settings] = None,
    host: Optional[str] = None,
    port: Optional[int] = None,
) -> None:
    """Run the MCP server over the streamable-HTTP transport.

    Mounts the same low-level ``Server`` (and therefore the identical
    ToolRegistry dispatch used by stdio) behind a Starlette ASGI app served by
    uvicorn. The MCP endpoint is exposed at ``/mcp``.

    Args:
        db_path: Optional path to the database.
        settings: Optional settings object.
        host: Bind host (defaults to settings.http_host).
        port: Bind port (defaults to settings.http_port).
    """
    import contextlib

    import uvicorn
    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from starlette.applications import Starlette
    from starlette.routing import Mount

    if settings is None:
        settings = Settings()
    host = host or settings.http_host
    port = port or settings.http_port

    server = await create_server(db_path, settings)

    # Stateful session manager wrapping the low-level server.
    session_manager = StreamableHTTPSessionManager(app=server)

    async def handle_mcp(scope, receive, send) -> None:
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with session_manager.run():
            logger.info("MCP HTTP transport ready", host=host, port=port)
            yield

    app = Starlette(
        routes=[Mount("/mcp", app=handle_mcp)],
        lifespan=lifespan,
    )

    logger.info("Starting MCP server with HTTP transport", host=host, port=port)
    config = uvicorn.Config(app, host=host, port=port, log_level="info")
    await uvicorn.Server(config).serve()


def main() -> None:
    """Main entry point for the MCP server."""
    # Configure logging
    from cognitive_fabric.utils.logger import configure_logging
    configure_logging()

    logger.info("Cognitive Fabric MCP Server starting")

    try:
        asyncio.run(run_server())
    except KeyboardInterrupt:
        logger.info("Server stopped by user")
    except Exception as e:
        logger.error("Server error", error=str(e))
        raise


if __name__ == "__main__":
    main()
