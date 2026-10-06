"""MCP server implementation using stdio transport."""

import asyncio
import ipaddress
import json
from typing import Optional

import structlog
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from cognitive_fabric import __app_name__, __version__
from cognitive_fabric.config import Settings
from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.mcp.tool_registry import ToolRegistry
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)

# Global state
_memory_service: Optional[MemoryService] = None
_tool_registry: Optional[ToolRegistry] = None
_context: Optional[ToolHandlerContext] = None


def build_mcp_tools(registry: ToolRegistry) -> list[Tool]:
    """Build the MCP wire tool list from a registry.

    Single source of truth for what the server advertises: both the
    ``list_tools`` handler and the tool-surface snapshot test build through
    this function, so the snapshot cannot drift from the wire.

    Args:
        registry: The tool registry to project.

    Returns:
        The MCP ``Tool`` objects, annotations included.
    """
    return [Tool(**tool.to_mcp_format()) for tool in registry.list_tools()]


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
        db_path = settings.db_path

    logger.info("Creating MCP server", db_path=db_path)

    # Initialize memory service
    _memory_service = await MemoryService.get_instance(db_path)

    # Initialize tool registry
    _tool_registry = ToolRegistry()

    # Initialize context
    _context = ToolHandlerContext()

    # Create server. `version` is passed explicitly: without it the MCP SDK
    # falls back to the *mcp* package's version (`server_version = self.version
    # if self.version else pkg_version("mcp")`), so a client checking the
    # server's version on connect would be reading the SDK's version instead.
    server = Server(__app_name__, version=__version__)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available tools."""
        return build_mcp_tools(_tool_registry)


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


# ─── HTTP transport: who is allowed to reach it ───────────────────────────────


def loopback_hosts(host: str, port: int) -> list[str]:
    """Every Host header this bind may legitimately be addressed by.

    ``localhost`` and ``127.0.0.1`` are the same server to a client but different
    strings on the wire, and a browser sends whichever the page used.
    """
    spellings = {host}
    if host in ("127.0.0.1", "localhost"):
        spellings |= {"127.0.0.1", "localhost"}
    return sorted(f"{name}:{port}" for name in spellings)


def loopback_origins(host: str, port: int) -> list[str]:
    """The ``Origin`` values a page served from this machine may carry."""
    return sorted(f"http://{name}" for name in loopback_hosts(host, port))


def require_loopback(host: str) -> None:
    """Refuse to serve HTTP on anything but this machine.

    Binding loopback is not on its own a control. A page in a browser can reach
    ``127.0.0.1``, and DNS rebinding lets a name the attacker controls resolve
    there — at which point the page's requests arrive with the attacker's ``Host``
    and reach every tool this server registers. The SDK's middleware is what
    actually refuses those requests (see ``create_http_app``); this is the second
    half, refusing to publish the port at all.

    Args:
        host: The address the HTTP transport was asked to bind.

    Raises:
        ValueError: If ``host`` is not a loopback address or ``localhost``.
    """
    if host == "localhost":
        return
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        raise ValueError(
            f"--host {host!r} is not an IP address or 'localhost', so this server "
            "cannot tell whether binding it would expose the port. The HTTP transport "
            "has no authentication: binding a routable address would let anyone who "
            "can reach it call every tool this server registers. Serve stdio, or put "
            "a reverse proxy with authentication in front."
        ) from None
    if not address.is_loopback:
        raise ValueError(
            f"--host {host!r} is not a loopback address. The HTTP transport has no "
            "authentication: binding a routable address would let anyone who can "
            "reach it call every tool this server registers. Serve stdio, or put a "
            "reverse proxy with authentication in front."
        )


def create_http_app(server: Server, host: str, port: int) -> object:
    """Build the ASGI app the HTTP transport serves: ``/mcp``, behind a header check.

    The guard is the whole reason this is a function rather than three lines inline,
    because it is easy to get wrong in a way that looks fine. The SDK's
    ``TransportSecurityMiddleware`` checks the ``Host`` and ``Origin`` headers and
    refuses anything outside the allowlists — but its own default, when handed no
    settings, is to leave that check **off** for backwards compatibility
    (``mcp/server/transport_security.py``). Passing no ``security_settings`` therefore
    reads as "the default" and means "no protection at all", which is how a server on
    ``127.0.0.1`` came to be reachable from any web page the operator visited.

    Args:
        server: The low-level MCP server to mount.
        host: The loopback address actually being bound.
        port: The port actually being bound.

    Returns:
        A Starlette application routing ``/mcp`` to the session manager.
    """
    import contextlib

    from mcp.server.streamable_http_manager import StreamableHTTPSessionManager
    from mcp.server.transport_security import TransportSecuritySettings
    from starlette.applications import Starlette
    from starlette.routing import Mount

    security = TransportSecuritySettings(
        enable_dns_rebinding_protection=True,
        allowed_hosts=loopback_hosts(host, port),
        allowed_origins=loopback_origins(host, port),
    )
    session_manager = StreamableHTTPSessionManager(
        app=server, security_settings=security
    )

    async def handle_mcp(scope, receive, send) -> None:
        await session_manager.handle_request(scope, receive, send)

    @contextlib.asynccontextmanager
    async def lifespan(app: Starlette):
        async with session_manager.run():
            logger.info("MCP HTTP transport ready", host=host, port=port)
            yield

    return Starlette(routes=[Mount("/mcp", app=handle_mcp)], lifespan=lifespan)


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
        host: Bind host (defaults to settings.http_host). Must be loopback.
        port: Bind port (defaults to settings.http_port).

    Raises:
        ValueError: If ``host`` is not a loopback address or ``localhost``.
    """
    import uvicorn

    if settings is None:
        settings = Settings()
    host = host or settings.http_host
    port = port or settings.http_port

    require_loopback(host)

    server = await create_server(db_path, settings)
    app = create_http_app(server, host, port)

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
