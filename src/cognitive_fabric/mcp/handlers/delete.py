"""Handler for delete tool."""

from typing import Any, Dict, List, Optional

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


async def delete_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle delete tool operations.

    Args:
        params: Tool parameters.
        context: Tool handler context.
        memory_service: The memory service.

    Returns:
        Operation result.
    """
    # `operation` is the TS wire name; `deleteType` kept as additive alias.
    delete_type = params.get("operation") or params.get("deleteType")
    repository = params["repository"]
    branch = params.get("branch", "main")
    dry_run = params.get("dryRun", False)

    if not delete_type:
        return {"success": False, "error": "operation (deleteType) is required"}

    logger.debug(
        "delete handler",
        delete_type=delete_type,
        repository=repository,
        dry_run=dry_run,
    )

    entity_service = await memory_service.entity
    container = await memory_service.get_service_container()

    try:
        if delete_type == "single":
            entity_type = params.get("entityType")
            entity_id = params.get("entityId")

            if not entity_type or not entity_id:
                return {
                    "success": False,
                    "error": "entityType and entityId are required for single deletion",
                }

            if dry_run:
                # Check if entity exists
                entity = await entity_service.get_entity(
                    repository, entity_type, entity_id, branch
                )
                return {
                    "success": True,
                    "dryRun": True,
                    "would_delete": entity is not None,
                    "entity": {
                        "id": entity_id,
                        "type": entity_type,
                        "name": entity.name if entity else None,
                    },
                }

            deleted = await entity_service.delete_entity(
                repository, entity_type, entity_id, branch
            )

            return {
                "success": deleted,
                "deleteType": "single",
                "deleted_count": 1 if deleted else 0,
                "entity": {
                    "id": entity_id,
                    "type": entity_type,
                },
            }

        elif delete_type == "bulk-by-type":
            entity_type = params.get("entityType")

            if not entity_type:
                return {
                    "success": False,
                    "error": "entityType is required for bulk-by-type deletion",
                }

            # Get all entities of this type
            entities = await _get_entities_by_type(
                container, repository, branch, entity_type
            )

            if dry_run:
                return {
                    "success": True,
                    "dryRun": True,
                    "would_delete": len(entities),
                    "entities": [{"id": e["id"], "name": e["name"]} for e in entities],
                }

            # Delete each entity
            deleted_count = 0
            for entity in entities:
                deleted = await entity_service.delete_entity(
                    repository, entity_type, entity["id"], branch
                )
                if deleted:
                    deleted_count += 1

            return {
                "success": True,
                "deleteType": "bulk-by-type",
                "entityType": entity_type,
                "deleted_count": deleted_count,
            }

        elif delete_type == "bulk-by-tag":
            tag_id = params.get("tagId")

            if not tag_id:
                return {
                    "success": False,
                    "error": "tagId is required for bulk-by-tag deletion",
                }

            tag_repo = await container.get_tag_repository()

            # Get items with this tag
            items = await tag_repo.get_items_with_tag(repository, tag_id, branch)

            if dry_run:
                return {
                    "success": True,
                    "dryRun": True,
                    "would_delete": len(items),
                    "items": items,
                }

            # Delete each item
            deleted_count = 0
            for item in items:
                deleted = await entity_service.delete_entity(
                    repository, item["type"].lower(), item["id"], branch
                )
                if deleted:
                    deleted_count += 1

            return {
                "success": True,
                "deleteType": "bulk-by-tag",
                "tagId": tag_id,
                "deleted_count": deleted_count,
            }

        elif delete_type == "bulk-by-status":
            entity_type = params.get("entityType", "component")
            status = params.get("status")

            if not status:
                return {
                    "success": False,
                    "error": "status is required for bulk-by-status deletion",
                }

            # Get entities with this status
            entities = await _get_entities_by_status(
                container, repository, branch, entity_type, status
            )

            if dry_run:
                return {
                    "success": True,
                    "dryRun": True,
                    "would_delete": len(entities),
                    "entities": [{"id": e["id"], "name": e["name"]} for e in entities],
                }

            # Delete each entity
            deleted_count = 0
            for entity in entities:
                deleted = await entity_service.delete_entity(
                    repository, entity_type, entity["id"], branch
                )
                if deleted:
                    deleted_count += 1

            return {
                "success": True,
                "deleteType": "bulk-by-status",
                "entityType": entity_type,
                "status": status,
                "deleted_count": deleted_count,
            }

        elif delete_type == "bulk-by-branch":
            target_branch = params.get("targetBranch") or branch
            kuzu_client = await memory_service.get_kuzu_client()
            result = await _bulk_delete_cypher(
                kuzu_client,
                repository,
                target_branch,
                entity_type=None,
                dry_run=dry_run,
            )
            return {
                "success": True,
                "deleteType": "bulk-by-branch",
                "targetBranch": target_branch,
                **result,
            }

        elif delete_type == "bulk-by-repository":
            kuzu_client = await memory_service.get_kuzu_client()
            result = await _bulk_delete_cypher(
                kuzu_client,
                repository,
                branch=None,
                entity_type=None,
                dry_run=dry_run,
            )
            return {
                "success": True,
                "deleteType": "bulk-by-repository",
                "repository": repository,
                **result,
            }

        elif delete_type == "bulk-by-filter":
            entity_type = params.get("targetType") or params.get("entityType")
            kuzu_client = await memory_service.get_kuzu_client()
            result = await _bulk_delete_cypher(
                kuzu_client,
                repository,
                branch,
                entity_type=entity_type,
                dry_run=dry_run,
                name_pattern=params.get("filterNamePattern"),
                status=params.get("filterStatus"),
                created_before=params.get("filterCreatedBefore"),
                created_after=params.get("filterCreatedAfter"),
            )
            return {
                "success": True,
                "deleteType": "bulk-by-filter",
                "entityType": entity_type,
                **result,
            }

        else:
            return {
                "success": False,
                "error": f"Unknown delete type: {delete_type}",
            }

    except Exception as e:
        logger.error(
            "Delete handler error",
            delete_type=delete_type,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }


async def _get_entities_by_type(
    container: Any,
    repository: str,
    branch: str,
    entity_type: str,
) -> List[Dict[str, Any]]:
    """Get all entities of a given type.

    Args:
        container: The service container.
        repository: The repository name.
        branch: The branch name.
        entity_type: The entity type.

    Returns:
        List of entity dictionaries.
    """
    entity_type_lower = entity_type.lower()

    if entity_type_lower == "component":
        repo = await container.get_component_repository()
        entities = await repo.get_all_components(repository, branch)
    elif entity_type_lower == "decision":
        repo = await container.get_decision_repository()
        entities = await repo.get_all_decisions(repository, branch)
    elif entity_type_lower == "rule":
        repo = await container.get_rule_repository()
        entities = await repo.get_all_rules(repository, branch)
    elif entity_type_lower == "tag":
        repo = await container.get_tag_repository()
        entities = await repo.get_all_tags(repository, branch)
    else:
        return []

    return [{"id": e.id, "name": e.name} for e in entities]


_DELETABLE_LABELS = ["Component", "Decision", "Rule", "Context", "File", "Tag"]


def _label_for_entity_type(entity_type: str) -> str:
    """Map an entity type string to its node label.

    Args:
        entity_type: The entity type (any case, singular).

    Returns:
        The node label (capitalized), or the input unchanged if unknown.
    """
    return {
        "component": "Component",
        "decision": "Decision",
        "rule": "Rule",
        "context": "Context",
        "file": "File",
        "tag": "Tag",
    }.get(entity_type.lower(), entity_type)


async def _bulk_delete_cypher(
    kuzu_client: Any,
    repository: str,
    branch: Optional[str],
    entity_type: Optional[str],
    dry_run: bool,
    name_pattern: Optional[str] = None,
    status: Optional[str] = None,
    created_before: Optional[str] = None,
    created_after: Optional[str] = None,
) -> Dict[str, Any]:
    """Bulk delete (or count) nodes matching repository/branch/filters.

    Args:
        kuzu_client: The KuzuDB client.
        repository: The repository name (always scoped).
        branch: The branch name, or None to span all branches.
        entity_type: A single entity type, or None to span deletable labels.
        dry_run: If True, only count matches (no deletion).
        name_pattern: Optional case-insensitive name substring filter.
        status: Optional status filter.
        created_before: Optional ISO date; keep nodes created before it.
        created_after: Optional ISO date; keep nodes created after it.

    Returns:
        Dict with either ``would_delete`` (dry run) or ``deleted_count``.
    """
    if entity_type:
        labels = [_label_for_entity_type(entity_type)]
    else:
        labels = list(_DELETABLE_LABELS)

    # Labels are interpolated into Cypher below, so reject anything not in the
    # controlled deletable set (guards against injection via targetType).
    invalid = [lbl for lbl in labels if lbl not in _DELETABLE_LABELS]
    if invalid:
        raise ValueError(f"Invalid delete target type(s): {invalid}")

    total = 0
    per_label: Dict[str, int] = {}

    for label in labels:
        clauses = ["n.repository = $repository"]
        query_params: Dict[str, Any] = {"repository": repository}

        if branch is not None:
            clauses.append("n.branch = $branch")
            query_params["branch"] = branch
        if name_pattern:
            clauses.append("toLower(n.name) CONTAINS $name_pattern")
            query_params["name_pattern"] = name_pattern.lower()
        if status:
            clauses.append("n.status = $status")
            query_params["status"] = status
        if created_before:
            clauses.append("n.created_at < $created_before")
            query_params["created_before"] = created_before
        if created_after:
            clauses.append("n.created_at > $created_after")
            query_params["created_after"] = created_after

        where = " AND ".join(clauses)

        # Count first so the reported deleted_count is accurate.
        count_cypher = (
            f"MATCH (n:{label}) WHERE {where} RETURN count(n) AS count"
        )
        row = kuzu_client.fetch_one(count_cypher, query_params)
        count = row.get("count", 0) if row else 0

        if not dry_run and count:
            delete_cypher = (
                f"MATCH (n:{label}) WHERE {where} DETACH DELETE n"
            )
            kuzu_client.execute_query(delete_cypher, query_params)

        if count:
            per_label[label] = count
        total += count

    if dry_run:
        return {"dryRun": True, "would_delete": total, "by_label": per_label}
    return {"deleted_count": total, "by_label": per_label}


async def _get_entities_by_status(
    container: Any,
    repository: str,
    branch: str,
    entity_type: str,
    status: str,
) -> List[Dict[str, Any]]:
    """Get entities with a given status.

    Args:
        container: The service container.
        repository: The repository name.
        branch: The branch name.
        entity_type: The entity type.
        status: The status to filter by.

    Returns:
        List of entity dictionaries.
    """
    entity_type_lower = entity_type.lower()

    if entity_type_lower == "component":
        from cognitive_fabric.types.entities import ComponentStatus
        try:
            status_enum = ComponentStatus(status)
        except ValueError:
            return []

        repo = await container.get_component_repository()
        # Get all and filter by status
        all_components = await repo.get_all_components(repository, branch)
        entities = [c for c in all_components if c.status == status_enum]

    elif entity_type_lower == "decision":
        from cognitive_fabric.types.entities import DecisionStatus
        try:
            status_enum = DecisionStatus(status)
        except ValueError:
            return []

        repo = await container.get_decision_repository()
        entities = await repo.get_decisions_by_status(repository, status_enum, branch)

    elif entity_type_lower == "rule":
        from cognitive_fabric.types.entities import RuleStatus
        try:
            status_enum = RuleStatus(status)
        except ValueError:
            return []

        repo = await container.get_rule_repository()
        all_rules = await repo.get_all_rules(repository, branch)
        entities = [r for r in all_rules if r.status == status_enum]

    else:
        return []

    return [{"id": e.id, "name": e.name} for e in entities]
