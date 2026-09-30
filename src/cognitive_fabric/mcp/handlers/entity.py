"""Handler for entity tool."""

from typing import Any, Dict

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.entities import (
    ComponentInput,
    DecisionInput,
    FileInput,
    RuleInput,
    TagInput,
)

logger = structlog.get_logger(__name__)


async def entity_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle entity tool operations.

    Args:
        params: Tool parameters.
        context: Tool handler context.
        memory_service: The memory service.

    Returns:
        Operation result.
    """
    operation = params["operation"]
    entity_type = params["entityType"]
    repository = params["repository"]
    branch = params.get("branch", "main")
    entity_id = params.get("id")
    data = params.get("data", {})

    logger.debug(
        "entity handler",
        operation=operation,
        entity_type=entity_type,
        repository=repository,
    )

    # TS wire field aliases: normalize into Python field names when the
    # Python key is absent (additive; never clobbers an explicit Python key).
    if isinstance(data, dict):
        alias_map = {
            "decisionStatus": "status",
            "ruleStatus": "status",
            "size_bytes": "size",
            "content_hash": "checksum",
        }
        for ts_key, py_key in alias_map.items():
            if ts_key in data and py_key not in data:
                data[py_key] = data[ts_key]

    entity_service = await memory_service.entity

    try:
        if operation == "create" or operation == "update":
            return await _handle_create_update(
                entity_service, entity_type, repository, branch, data, entity_id
            )

        elif operation == "get":
            if not entity_id:
                return {
                    "success": False,
                    "error": "id is required for get operation",
                }

            entity = await entity_service.get_entity(
                repository, entity_type, entity_id, branch
            )

            if entity is None:
                return {
                    "success": False,
                    "error": f"{entity_type} not found: {entity_id}",
                }

            return {
                "success": True,
                "entity": entity.model_dump(mode="json"),
            }

        elif operation == "delete":
            if not entity_id:
                return {
                    "success": False,
                    "error": "id is required for delete operation",
                }

            deleted = await entity_service.delete_entity(
                repository, entity_type, entity_id, branch
            )

            return {
                "success": deleted,
                "message": (
                    f"Deleted {entity_type}: {entity_id}"
                    if deleted
                    else f"{entity_type} not found: {entity_id}"
                ),
            }

        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
            }

    except Exception as e:
        logger.error(
            "Entity handler error",
            operation=operation,
            entity_type=entity_type,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }


async def _handle_create_update(
    entity_service: Any,
    entity_type: str,
    repository: str,
    branch: str,
    data: Dict[str, Any],
    entity_id: str = None,
) -> Dict[str, Any]:
    """Handle create/update operations.

    Args:
        entity_service: The entity service.
        entity_type: The entity type.
        repository: The repository name.
        branch: The branch name.
        data: The entity data.
        entity_id: Optional entity ID.

    Returns:
        Operation result.
    """
    # Ensure id is set
    if entity_id:
        data["id"] = entity_id
    elif "id" not in data:
        return {
            "success": False,
            "error": "id is required for create/update operation",
        }

    # Set branch
    data["branch"] = branch

    entity_type_lower = entity_type.lower()

    if entity_type_lower == "component":
        input_data = ComponentInput(**data)
        entity = await entity_service.create_component(repository, input_data)

    elif entity_type_lower == "decision":
        input_data = DecisionInput(**data)
        entity = await entity_service.create_decision(repository, input_data)

    elif entity_type_lower == "rule":
        input_data = RuleInput(**data)
        entity = await entity_service.create_rule(repository, input_data)

    elif entity_type_lower == "file":
        input_data = FileInput(**data)
        entity = await entity_service.create_file(repository, input_data)

    elif entity_type_lower == "tag":
        input_data = TagInput(**data)
        entity = await entity_service.create_tag(repository, input_data)

    else:
        return {
            "success": False,
            "error": f"Unknown entity type: {entity_type}",
        }

    return {
        "success": True,
        "entity": entity.model_dump(mode="json"),
    }
