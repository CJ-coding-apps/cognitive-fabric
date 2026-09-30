"""Handler for memory-bank tool."""

from typing import Any, Dict

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


async def memory_bank_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle memory-bank tool operations.

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
        "memory-bank handler",
        operation=operation,
        repository=repository,
        branch=branch,
    )

    if operation == "init":
        client_project_root = params.get("clientProjectRoot")
        if not client_project_root:
            return {
                "success": False,
                "error": "clientProjectRoot is required for init operation",
            }

        memory_bank_svc = await memory_service.memory_bank
        result = await memory_bank_svc.init_memory_bank(
            context, client_project_root, repository, branch
        )

        # Update context with memory bank info
        if result.get("success"):
            context.set_memory_bank(repository, branch, client_project_root)

        return result

    elif operation == "get-metadata":
        memory_bank_svc = await memory_service.memory_bank
        result = await memory_bank_svc.get_memory_bank_metadata(repository, branch)

        if result is None:
            return {
                "success": False,
                "error": f"Memory bank not found for {repository}:{branch}",
            }

        return {
            "success": True,
            **result,
        }

    elif operation == "update-metadata":
        metadata = params.get("metadata")
        if not metadata:
            return {
                "success": False,
                "error": "metadata is required for update-metadata operation",
            }

        memory_bank_svc = await memory_service.memory_bank
        return await memory_bank_svc.update_memory_bank_metadata(
            repository, branch, metadata
        )

    else:
        return {
            "success": False,
            "error": f"Unknown operation: {operation}",
        }
