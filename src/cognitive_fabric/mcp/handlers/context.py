"""Handler for context tool."""

from typing import Any, Dict

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.entities import ContextInput

logger = structlog.get_logger(__name__)


async def context_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle context tool operations.

    Args:
        params: Tool parameters.
        context: Tool handler context.
        memory_service: The memory service.

    Returns:
        Operation result.
    """
    operation = params["operation"]
    repository = params["repository"]
    branch = params.get("branch", "main")

    logger.debug(
        "context handler",
        operation=operation,
        repository=repository,
    )

    context_service = await memory_service.context

    try:
        if operation == "update":
            # TS wire: flat fields at top level when `data` is absent.
            data = params.get("data")
            if not data:
                data = {
                    k: params[k]
                    for k in ("id", "name", "agent", "summary", "observation")
                    if k in params
                }
            if not data:
                return {
                    "success": False,
                    "error": "data is required for update operation",
                }

            if "id" not in data:
                return {
                    "success": False,
                    "error": "data.id is required for update operation",
                }

            data["branch"] = branch
            input_data = ContextInput(**data)

            ctx = await context_service.update_context(repository, input_data)

            return {
                "success": True,
                "context": ctx.model_dump(mode="json"),
            }

        elif operation == "get-recent":
            limit = params.get("limit", 10)

            contexts = await context_service.get_recent_contexts(
                repository, branch, limit
            )

            return {
                "success": True,
                "contexts": [c.model_dump(mode="json") for c in contexts],
                "count": len(contexts),
            }

        elif operation == "get-summary":
            limit = params.get("limit", 5)

            summary = await context_service.get_context_summary(
                repository, branch, limit
            )

            return {
                "success": True,
                **summary,
            }

        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
            }

    except Exception as e:
        logger.error(
            "Context handler error",
            operation=operation,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }
