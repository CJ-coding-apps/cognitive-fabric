"""Handler for bulk-import tool."""

from typing import Any, Dict

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.entities import ComponentInput, DecisionInput, RuleInput

logger = structlog.get_logger(__name__)


async def bulk_import_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle bulk-import tool operations.

    Args:
        params: Tool parameters.
        context: Tool handler context.
        memory_service: The memory service.

    Returns:
        Operation result.
    """
    # `type` is the TS wire name (plural); `entityType` kept as additive alias.
    raw_type = params.get("type") or params.get("entityType")
    repository = params["repository"]
    branch = params.get("branch", "main")

    if not raw_type:
        return {"success": False, "error": "type (entityType) is required"}

    # Normalize TS plural -> Python singular.
    plural_to_singular = {
        "components": "component",
        "decisions": "decision",
        "rules": "rule",
    }
    entity_type = plural_to_singular.get(raw_type, raw_type)

    # Gather items: prefer a TS typed array, else the generic `items` array.
    typed_arrays = {
        "component": "components",
        "decision": "decisions",
        "rule": "rules",
    }
    typed_key = typed_arrays.get(entity_type)
    items = None
    if typed_key and params.get(typed_key) is not None:
        items = params.get(typed_key)
    if items is None:
        items = params.get("items")
    if items is None:
        return {"success": False, "error": "items (or a typed array) is required"}

    logger.debug(
        "bulk-import handler",
        entity_type=entity_type,
        repository=repository,
        item_count=len(items),
    )

    entity_service = await memory_service.entity

    try:
        imported = []
        errors = []

        for i, item in enumerate(items):
            try:
                # Set branch if not specified
                item["branch"] = item.get("branch", branch)

                if entity_type == "component":
                    input_data = ComponentInput(**item)
                    entity = await entity_service.create_component(
                        repository, input_data
                    )
                    imported.append({
                        "id": entity.id,
                        "name": entity.name,
                    })

                elif entity_type == "decision":
                    input_data = DecisionInput(**item)
                    entity = await entity_service.create_decision(
                        repository, input_data
                    )
                    imported.append({
                        "id": entity.id,
                        "name": entity.name,
                    })

                elif entity_type == "rule":
                    input_data = RuleInput(**item)
                    entity = await entity_service.create_rule(repository, input_data)
                    imported.append({
                        "id": entity.id,
                        "name": entity.name,
                    })

                else:
                    errors.append({
                        "index": i,
                        "error": f"Unknown entity type: {entity_type}",
                    })

            except Exception as e:
                errors.append({
                    "index": i,
                    "id": item.get("id"),
                    "error": str(e),
                })

        return {
            "success": len(errors) == 0,
            "entityType": entity_type,
            "imported_count": len(imported),
            "error_count": len(errors),
            "imported": imported,
            "errors": errors if errors else None,
        }

    except Exception as e:
        logger.error(
            "Bulk import handler error",
            entity_type=entity_type,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }
