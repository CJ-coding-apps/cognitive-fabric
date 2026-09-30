"""Handler for query tool."""

from typing import Any, Dict

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


async def query_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle query tool operations.

    Args:
        params: Tool parameters.
        context: Tool handler context.
        memory_service: The memory service.

    Returns:
        Operation result.
    """
    # `type` is the TS wire name; `queryType` kept as additive alias.
    query_type = params.get("type") or params.get("queryType")
    repository = params["repository"]
    branch = params.get("branch", "main")

    if not query_type:
        return {"success": False, "error": "type (queryType) is required"}

    logger.debug(
        "query handler",
        query_type=query_type,
        repository=repository,
    )

    graph_query = await memory_service.graph_query

    try:
        if query_type == "context":
            result = await graph_query.query_context(repository, branch)
            return {"success": True, **result}

        elif query_type == "entities":
            # TS wire: `label` is an alias for entityType.
            entity_type = params.get("entityType") or params.get("label")
            if not entity_type:
                return {
                    "success": False,
                    "error": "entityType is required for entities query",
                }

            filters = params.get("filters")
            entities = await graph_query.query_entities(
                repository, entity_type, branch, filters
            )

            return {
                "success": True,
                "entities": entities,
                "count": len(entities),
                "entityType": entity_type,
            }

        elif query_type == "relationships":
            relationship_type = params.get("relationshipType")
            if not relationship_type:
                return {
                    "success": False,
                    "error": "relationshipType is required for relationships query",
                }

            relationships = await graph_query.query_relationships(
                repository, relationship_type, branch
            )

            return {
                "success": True,
                "relationships": relationships,
                "count": len(relationships),
                "relationshipType": relationship_type,
            }

        elif query_type == "dependencies":
            component_id = params.get("componentId")
            if not component_id:
                return {
                    "success": False,
                    "error": "componentId is required for dependencies query",
                }

            direction = params.get("direction", "both")
            depth = params.get("depth", 1)

            result = await graph_query.query_dependencies(
                repository, component_id, branch, direction, depth
            )

            return {"success": True, **result}

        elif query_type == "governance":
            component_id = params.get("componentId")
            if not component_id:
                return {
                    "success": False,
                    "error": "componentId is required for governance query",
                }

            result = await graph_query.query_governance(
                repository, component_id, branch
            )

            return {"success": True, **result}

        elif query_type == "history":
            # TS wire: `itemId` is an alias for componentId.
            component_id = (
                params.get("componentId") or params.get("itemId")
            )
            if not component_id:
                return {
                    "success": False,
                    "error": "componentId is required for history query",
                }

            result = await graph_query.query_history(
                repository, component_id, branch
            )

            return {"success": True, **result}

        elif query_type == "tags":
            tag_id = params.get("tagId")

            result = await graph_query.query_tags(repository, tag_id, branch)

            return {"success": True, **result}

        else:
            return {
                "success": False,
                "error": f"Unknown query type: {query_type}",
            }

    except Exception as e:
        logger.error(
            "Query handler error",
            query_type=query_type,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }
