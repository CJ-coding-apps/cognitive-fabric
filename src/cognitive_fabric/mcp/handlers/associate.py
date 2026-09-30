"""Handler for associate tool."""

from typing import Any, Dict

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


async def associate_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle associate tool operations.

    Args:
        params: Tool parameters.
        context: Tool handler context.
        memory_service: The memory service.

    Returns:
        Operation result.
    """
    # `type` is the TS wire name; `associationType` kept as additive alias.
    association_type = params.get("type") or params.get("associationType")
    repository = params["repository"]
    branch = params.get("branch", "main")

    if not association_type:
        return {
            "success": False,
            "error": "type (associationType) is required",
        }

    # Default id resolution (Python wire names); per-branch overrides below.
    source_id = params.get("sourceId")
    target_id = params.get("targetId")

    logger.debug(
        "associate handler",
        association_type=association_type,
        repository=repository,
        source_id=source_id,
        target_id=target_id,
    )

    container = await memory_service.get_service_container()

    try:
        if association_type == "file-component":
            # TS wire: fileId (source) / componentId (target); Py fallback.
            source_id = params.get("fileId") or source_id
            target_id = params.get("componentId") or target_id
            # Create IMPLEMENTS relationship: Component -> File
            file_repo = await container.get_file_repository()
            created = await file_repo.create_implements_relationship(
                repository, source_id, target_id, branch
            )

            return {
                "success": created,
                "message": (
                    f"Created IMPLEMENTS relationship: {source_id} -> {target_id}"
                    if created
                    else "Failed to create relationship"
                ),
                "relationship": "IMPLEMENTS",
            }

        elif association_type == "tag-item":
            # TS wire: itemId (source) / tagId (target); Py fallback.
            source_id = params.get("itemId") or source_id
            target_id = params.get("tagId") or target_id
            # Create TAGGED_WITH relationship: Item -> Tag
            # TS wire: `entityType` is the item label (Component/Decision/...).
            item_type = (
                params.get("entityType")
                or params.get("itemType")
                or "Component"
            )
            tag_repo = await container.get_tag_repository()
            created = await tag_repo.create_tagged_with_relationship(
                repository, source_id, item_type, target_id, branch
            )

            return {
                "success": created,
                "message": (
                    f"Created TAGGED_WITH relationship: {source_id} -> {target_id}"
                    if created
                    else "Failed to create relationship"
                ),
                "relationship": "TAGGED_WITH",
            }

        elif association_type == "decision-component":
            # Create AFFECTS relationship: Decision -> Component
            decision_repo = await container.get_decision_repository()
            created = await decision_repo.create_affects_relationship(
                repository, source_id, target_id, branch
            )

            return {
                "success": created,
                "message": (
                    f"Created AFFECTS relationship: {source_id} -> {target_id}"
                    if created
                    else "Failed to create relationship"
                ),
                "relationship": "AFFECTS",
            }

        elif association_type == "rule-component":
            # Create GOVERNS relationship: Rule -> Component
            rule_repo = await container.get_rule_repository()
            created = await rule_repo.create_governs_relationship(
                repository, source_id, target_id, branch
            )

            return {
                "success": created,
                "message": (
                    f"Created GOVERNS relationship: {source_id} -> {target_id}"
                    if created
                    else "Failed to create relationship"
                ),
                "relationship": "GOVERNS",
            }

        elif association_type == "context-component":
            # Create CONTEXT_OF relationship: Context -> Component/Decision/Rule
            target_type = params.get("itemType") or params.get(
                "targetType", "Component"
            )
            context_repo = await container.get_context_repository()
            created = await context_repo.create_context_of_relationship(
                repository, source_id, target_id, branch, target_type
            )

            return {
                "success": created,
                "message": (
                    f"Created CONTEXT_OF relationship: {source_id} -> {target_id}"
                    if created
                    else "Failed to create relationship"
                ),
                "relationship": "CONTEXT_OF",
            }

        else:
            return {
                "success": False,
                "error": f"Unknown association type: {association_type}",
            }

    except Exception as e:
        logger.error(
            "Associate handler error",
            association_type=association_type,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }
