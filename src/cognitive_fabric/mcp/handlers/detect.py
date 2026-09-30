"""Handler for detect tool."""

from typing import Any, Dict

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


async def detect_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle detect tool operations.

    Args:
        params: Tool parameters.
        context: Tool handler context.
        memory_service: The memory service.

    Returns:
        Operation result.
    """
    # `type` is the TS wire name; `pattern` is kept as an additive alias.
    pattern = params.get("type") or params.get("pattern")
    repository = params["repository"]
    branch = params.get("branch", "main")

    # Projection parameters (TS wire contract; optional with defaults).
    proj = {
        "node_tables": params.get("nodeTableNames"),
        "rel_tables": params.get("relationshipTableNames"),
    }

    logger.debug(
        "detect handler",
        pattern=pattern,
        repository=repository,
    )

    if not pattern:
        return {"success": False, "error": "type (pattern) is required"}

    graph_analysis = await memory_service.graph_analysis

    try:
        if pattern == "cycles":
            cycles = await graph_analysis.detect_cycles(
                repository, branch, projected_graph_name="cycles", **proj
            )

            return {
                "success": True,
                "pattern": "cycles",
                "cycles": cycles,
                "has_cycles": len(cycles) > 0,
                "count": len(cycles),
            }

        elif pattern == "islands":
            islands = await graph_analysis.detect_islands(
                repository, branch, projected_graph_name="islands", **proj
            )

            return {
                "success": True,
                "pattern": "islands",
                "islands": islands,
                "has_islands": len(islands) > 0,
                "count": len(islands),
            }

        elif pattern == "strongly-connected":
            components = await graph_analysis.get_strongly_connected(
                repository, branch, projected_graph_name="scc", **proj
            )

            return {
                "success": True,
                "pattern": "strongly-connected",
                "components": components,
                "count": len(components),
            }

        elif pattern == "weakly-connected":
            components = await graph_analysis.get_weakly_connected(
                repository, branch, projected_graph_name="wcc", **proj
            )

            return {
                "success": True,
                "pattern": "weakly-connected",
                "components": components,
                "count": len(components),
            }

        elif pattern == "path":
            # Shortest-path detection (KuzuMem-MCP wire contract).
            start_id = params.get("startNodeId") or params.get("startId")
            end_id = params.get("endNodeId") or params.get("endId")

            if not start_id or not end_id:
                return {
                    "success": False,
                    "error": "startNodeId and endNodeId are required for path",
                }

            result = await graph_analysis.find_shortest_path(
                repository, start_id, end_id, branch
            )

            if result is None:
                return {
                    "success": True,
                    "pattern": "path",
                    "path_found": False,
                    "message": f"No path found between {start_id} and {end_id}",
                }

            return {
                "success": True,
                "pattern": "path",
                **result,
            }

        else:
            return {
                "success": False,
                "error": f"Unknown pattern: {pattern}",
            }

    except Exception as e:
        logger.error(
            "Detect handler error",
            pattern=pattern,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }
