"""MCP-specific type definitions."""

from typing import Any, Callable, Coroutine, Literal, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Tool Handler Context
# =============================================================================


class SessionData(BaseModel):
    """Session data stored across tool calls."""

    client_project_root: Optional[str] = None
    repository: Optional[str] = None
    branch: str = "main"


class ProgressNotification(BaseModel):
    """Progress notification for long-running operations."""

    status: Literal[
        "initializing", "in_progress", "complete", "error", "cancelled"
    ]
    message: Optional[str] = None
    percent: Optional[int] = Field(default=None, ge=0, le=100)
    is_final: bool = False
    tool_name: Optional[str] = None
    data: Optional[dict[str, Any]] = None
    error: Optional[dict[str, Any]] = None


class ToolHandlerContext(BaseModel):
    """Context passed to tool handlers."""

    model_config = {"arbitrary_types_allowed": True}

    logger: Any  # structlog.BoundLogger
    session: SessionData = Field(default_factory=SessionData)
    request_id: Optional[str] = None

    async def send_progress(self, progress: dict[str, Any]) -> None:
        """Send a progress notification.

        Note: This is a stub for stdio transport.
        HTTP transport would implement actual streaming.
        """
        notification = ProgressNotification(**progress)
        self.logger.debug(
            "Progress",
            status=notification.status,
            percent=notification.percent,
            message=notification.message,
        )


# Type alias for tool handlers
ToolHandler = Callable[
    [dict[str, Any], ToolHandlerContext, Any],
    Coroutine[Any, Any, dict[str, Any]],
]


# =============================================================================
# Tool Definition Types
# =============================================================================


class ToolParameter(BaseModel):
    """Individual tool parameter definition."""

    type: str
    description: str
    title: Optional[str] = None
    enum: Optional[list[str]] = None
    items: Optional[dict[str, Any]] = None
    default: Optional[Any] = None


class ToolParameters(BaseModel):
    """Tool parameters schema (JSON Schema object)."""

    type: Literal["object"] = "object"
    properties: dict[str, ToolParameter]
    required: list[str] = Field(default_factory=list)


class ToolReturns(BaseModel):
    """Tool return value schema."""

    type: str
    properties: dict[str, ToolParameter]


class ToolAnnotations(BaseModel):
    """Tool annotations for hints and metadata."""

    title: str
    read_only_hint: bool = Field(default=False, alias="readOnlyHint")
    destructive_hint: bool = Field(default=False, alias="destructiveHint")
    idempotent_hint: bool = Field(default=True, alias="idempotentHint")
    open_world_hint: bool = Field(default=False, alias="openWorldHint")

    model_config = {"populate_by_name": True}


class McpTool(BaseModel):
    """MCP Tool definition matching the TypeScript interface."""

    name: str
    description: str
    parameters: ToolParameters
    returns: Optional[ToolReturns] = None
    annotations: Optional[ToolAnnotations] = None


# =============================================================================
# Tool Result Types
# =============================================================================


class ToolSuccess(BaseModel):
    """Successful tool result."""

    success: Literal[True] = True
    message: Optional[str] = None
    data: Optional[dict[str, Any]] = None


class ToolError(BaseModel):
    """Error tool result."""

    success: Literal[False] = False
    error: str
    code: Optional[str] = None
    details: Optional[dict[str, Any]] = None


ToolResult = ToolSuccess | ToolError


# =============================================================================
# Query Types
# =============================================================================


class QueryType(str):
    """Query types for the query tool."""

    CONTEXT = "context"
    ENTITIES = "entities"
    RELATIONSHIPS = "relationships"
    DEPENDENCIES = "dependencies"
    GOVERNANCE = "governance"
    HISTORY = "history"
    TAGS = "tags"


class AssociationType(str):
    """Association types for the associate tool."""

    FILE_COMPONENT = "file-component"
    TAG_ITEM = "tag-item"


class AnalyzeType(str):
    """Analysis types for the analyze tool."""

    PAGERANK = "pagerank"
    K_CORE = "k-core"
    LOUVAIN = "louvain"
    SHORTEST_PATH = "shortest-path"


class DetectType(str):
    """Detection types for the detect tool."""

    CYCLES = "cycles"
    ISLANDS = "islands"
    PATH = "path"
    STRONGLY_CONNECTED = "strongly-connected"
    WEAKLY_CONNECTED = "weakly-connected"


class SearchMode(str):
    """Search modes for the search tool."""

    FULLTEXT = "fulltext"
    SEMANTIC = "semantic"
    HYBRID = "hybrid"


class DeleteOperation(str):
    """Delete operations for the delete tool."""

    SINGLE = "single"
    BULK_BY_TYPE = "bulk-by-type"
    BULK_BY_TAG = "bulk-by-tag"
    BULK_BY_BRANCH = "bulk-by-branch"
    BULK_BY_REPOSITORY = "bulk-by-repository"
    BULK_BY_FILTER = "bulk-by-filter"
