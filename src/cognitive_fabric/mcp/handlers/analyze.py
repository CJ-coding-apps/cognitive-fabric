"""Handler for analyze tool."""

from typing import Any, Dict

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


async def analyze_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle analyze tool operations.

    Runs native KuzuDB graph algorithms over a projected graph. The projection
    tables default to Component / DEPENDS_ON but can be overridden via
    ``nodeTableNames`` / ``relationshipTableNames`` (KuzuMem-MCP wire contract).

    Args:
        params: Tool parameters.
        context: Tool handler context.
        memory_service: The memory service.

    Returns:
        Operation result.
    """
    # `type` is the TS wire name; `algorithm` is kept as an additive alias.
    algorithm = params.get("type") or params.get("algorithm")
    repository = params["repository"]
    branch = params.get("branch", "main")

    # Projection parameters (TS wire contract; optional here with defaults).
    node_tables = params.get("nodeTableNames")
    rel_tables = params.get("relationshipTableNames")

    logger.debug(
        "analyze handler",
        algorithm=algorithm,
        repository=repository,
    )

    if not algorithm:
        return {"success": False, "error": "type (algorithm) is required"}

    graph_analysis = await memory_service.graph_analysis

    def _proj(label: str) -> Dict[str, Any]:
        # `label` is only a prefix: the projection name itself is generated
        # server-side (see graph_projection.projected_graph) so a caller cannot
        # name — and therefore cannot collide with or drop — another session's
        # projection.
        return {
            "node_tables": node_tables,
            "rel_tables": rel_tables,
            "projected_graph_name": label,
        }

    try:
        if algorithm == "pagerank":
            results = await graph_analysis.run_pagerank(
                repository,
                branch,
                damping_factor=params.get("damping", 0.85),
                max_iterations=params.get("maxIterations", 20),
                **_proj("pagerank"),
            )

            return {
                "success": True,
                "algorithm": "pagerank",
                "results": results,
                "count": len(results),
            }

        elif algorithm == "k-core":
            k = params.get("k", 2)
            results = await graph_analysis.run_k_core(
                repository, k, branch, **_proj("kcore")
            )

            return {
                "success": True,
                "algorithm": "k-core",
                "k": k,
                "results": results,
                "count": len(results),
            }

        elif algorithm == "louvain":
            results = await graph_analysis.run_louvain(
                repository, branch, **_proj("louvain")
            )

            # Group by community
            communities: Dict[int, list] = {}
            for item in results:
                community_id = item.get("community_id", 0)
                if community_id not in communities:
                    communities[community_id] = []
                communities[community_id].append(item)

            return {
                "success": True,
                "algorithm": "louvain",
                "results": results,
                "communities": {
                    str(k): v for k, v in communities.items()
                },
                "num_communities": len(communities),
                "count": len(results),
            }

        elif algorithm == "shortest-path":
            # Accept TS names (startNodeId/endNodeId) and the legacy aliases.
            start_id = params.get("startNodeId") or params.get("startId")
            end_id = params.get("endNodeId") or params.get("endId")

            if not start_id or not end_id:
                return {
                    "success": False,
                    "error": (
                        "startNodeId and endNodeId are required for "
                        "shortest-path algorithm"
                    ),
                }

            result = await graph_analysis.find_shortest_path(
                repository, start_id, end_id, branch
            )

            if result is None:
                return {
                    "success": True,
                    "algorithm": "shortest-path",
                    "path_found": False,
                    "message": f"No path found between {start_id} and {end_id}",
                }

            return {
                "success": True,
                "algorithm": "shortest-path",
                **result,
            }

        else:
            return {
                "success": False,
                "error": f"Unknown algorithm: {algorithm}",
            }

    except Exception as e:
        logger.error(
            "Analyze handler error",
            algorithm=algorithm,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }
