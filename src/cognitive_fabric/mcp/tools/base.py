"""Base MCP tool definition."""

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class McpToolParameter(BaseModel):
    """A parameter for an MCP tool."""

    name: str
    type: str
    description: str
    required: bool = False
    enum: Optional[List[str]] = None
    default: Optional[Any] = None


class McpTool(BaseModel):
    """Definition of an MCP tool."""

    name: str = Field(..., description="The tool name")
    description: str = Field(..., description="The tool description")
    parameters: Dict[str, Any] = Field(
        default_factory=dict,
        description="JSON Schema for the tool parameters",
    )

    @classmethod
    def create(
        cls,
        name: str,
        description: str,
        properties: Dict[str, Any],
        required: Optional[List[str]] = None,
    ) -> "McpTool":
        """Create an MCP tool with the given schema.

        Args:
            name: The tool name.
            description: The tool description.
            properties: JSON Schema properties for parameters.
            required: List of required parameter names.

        Returns:
            The created McpTool.
        """
        parameters = {
            "type": "object",
            "properties": properties,
        }
        if required:
            parameters["required"] = required

        return cls(
            name=name,
            description=description,
            parameters=parameters,
        )

    def to_mcp_format(self) -> Dict[str, Any]:
        """Convert to MCP protocol format.

        Returns:
            Dictionary in MCP tool format.
        """
        return {
            "name": self.name,
            "description": self.description,
            "inputSchema": self.parameters,
        }
