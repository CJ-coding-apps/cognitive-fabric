"""Tool registry for MCP server."""

from typing import Any, Callable, Dict, Optional

import structlog

from cognitive_fabric.mcp.handlers import TOOL_HANDLERS
from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.mcp.tools import MEMORY_BANK_MCP_TOOLS, McpTool
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)

# Type alias for handler function
HandlerFunc = Callable[
    [Dict[str, Any], ToolHandlerContext, MemoryService],
    Any,
]


class ToolRegistry:
    """Registry for MCP tools and their handlers."""

    def __init__(self) -> None:
        """Initialize the tool registry."""
        self._tools: Dict[str, McpTool] = {}
        self._handlers: Dict[str, HandlerFunc] = {}

        # Register all default tools
        self._register_default_tools()

    def _register_default_tools(self) -> None:
        """Register all default memory bank tools."""
        for tool in MEMORY_BANK_MCP_TOOLS:
            self._tools[tool.name] = tool

            handler = TOOL_HANDLERS.get(tool.name)
            if handler:
                self._handlers[tool.name] = handler
            else:
                logger.warning(f"No handler found for tool: {tool.name}")

    def register_tool(
        self,
        tool: McpTool,
        handler: HandlerFunc,
    ) -> None:
        """Register a custom tool.

        Args:
            tool: The tool definition.
            handler: The tool handler function.
        """
        self._tools[tool.name] = tool
        self._handlers[tool.name] = handler
        logger.debug(f"Registered tool: {tool.name}")

    def get_tool(self, name: str) -> Optional[McpTool]:
        """Get a tool by name.

        Args:
            name: The tool name.

        Returns:
            The tool if found, None otherwise.
        """
        return self._tools.get(name)

    def get_handler(self, name: str) -> Optional[HandlerFunc]:
        """Get a tool handler by name.

        Args:
            name: The tool name.

        Returns:
            The handler if found, None otherwise.
        """
        return self._handlers.get(name)

    def list_tools(self) -> list[McpTool]:
        """List all registered tools.

        Returns:
            List of all tools.
        """
        return list(self._tools.values())

    def list_tool_names(self) -> list[str]:
        """List all registered tool names.

        Returns:
            List of tool names.
        """
        return list(self._tools.keys())

    async def call_tool(
        self,
        name: str,
        params: Dict[str, Any],
        context: ToolHandlerContext,
        memory_service: MemoryService,
    ) -> Dict[str, Any]:
        """Call a tool by name.

        Args:
            name: The tool name.
            params: The tool parameters.
            context: The tool handler context.
            memory_service: The memory service.

        Returns:
            The tool result.

        Raises:
            ValueError: If the tool is not found.
        """
        handler = self.get_handler(name)
        if not handler:
            raise ValueError(f"Tool not found: {name}")

        logger.debug(f"Calling tool: {name}", params=params)

        try:
            result = await handler(params, context, memory_service)
            return result
        except Exception as e:
            logger.error(f"Tool error: {name}", error=str(e))
            return {
                "success": False,
                "error": str(e),
            }
