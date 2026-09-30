"""Handler for introspect tool."""

from typing import Any, Dict

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


async def introspect_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle introspect tool operations.

    Args:
        params: Tool parameters.
        context: Tool handler context.
        memory_service: The memory service.

    Returns:
        Operation result.
    """
    # `query` is the TS wire name; `operation` kept as additive alias.
    operation = params.get("query") or params.get("operation")
    repository = params["repository"]
    branch = params.get("branch", "main")

    if not operation:
        return {"success": False, "error": "query (operation) is required"}

    logger.debug(
        "introspect handler",
        operation=operation,
        repository=repository,
    )

    kuzu_client = await memory_service.get_kuzu_client()

    try:
        if operation == "labels":
            # Get all node and relationship labels
            node_labels = [
                "Repository", "Component", "Decision", "Rule",
                "Context", "File", "Tag", "Metadata"
            ]
            rel_labels = [
                "DEPENDS_ON", "IMPLEMENTS", "TAGGED_WITH", "GOVERNS",
                "AFFECTS", "CONTEXT_OF", "PART_OF", "HAS_METADATA"
            ]

            return {
                "success": True,
                "operation": "labels",
                "node_labels": node_labels,
                "relationship_labels": rel_labels,
            }

        elif operation == "count":
            # Count entities in the repository
            counts = {}

            entity_types = ["Component", "Decision", "Rule", "Context", "File", "Tag"]

            for entity_type in entity_types:
                query = f"""
                MATCH (n:{entity_type})
                WHERE n.repository = $repository AND n.branch = $branch
                RETURN count(n) AS count
                """
                result = kuzu_client.fetch_one(query, {
                    "repository": repository,
                    "branch": branch,
                })
                counts[entity_type.lower()] = result.get("count", 0) if result else 0

            # Count Repository (different structure)
            repo_query = """
            MATCH (r:Repository)
            WHERE r.name = $repository AND r.branch = $branch
            RETURN count(r) AS count
            """
            repo_result = kuzu_client.fetch_one(repo_query, {
                "repository": repository,
                "branch": branch,
            })
            counts["repository"] = repo_result.get("count", 0) if repo_result else 0

            return {
                "success": True,
                "operation": "count",
                "counts": counts,
                "total": sum(counts.values()),
            }

        elif operation == "properties":
            # TS wire: `target` is an alias for label.
            label = params.get("target") or params.get("label")
            if not label:
                return {
                    "success": False,
                    "error": "label is required for properties operation",
                }

            # Define properties for each label
            properties_map = {
                "Repository": [
                    "id", "name", "branch", "tech_stack", "architecture",
                    "created_at", "updated_at",
                ],
                "Component": [
                    "graph_unique_id", "id", "name", "kind", "status",
                    "depends_on", "description", "metadata", "repository",
                    "branch", "created_at", "updated_at",
                ],
                "Decision": [
                    "graph_unique_id", "id", "name", "context", "date",
                    "status", "rationale", "alternatives", "consequences",
                    "related_decisions", "repository", "branch",
                    "created_at", "updated_at",
                ],
                "Rule": [
                    "graph_unique_id", "id", "name", "created", "triggers",
                    "content", "status", "category", "priority", "examples",
                    "repository", "branch", "created_at", "updated_at",
                ],
                "Context": [
                    "graph_unique_id", "id", "name", "iso_date", "agent",
                    "summary", "observation", "key_findings", "repository",
                    "branch", "created_at", "updated_at",
                ],
                "File": [
                    "id", "name", "path", "size", "mime_type", "metadata",
                    "checksum", "repository", "branch", "created_at",
                    "updated_at",
                ],
                "Tag": [
                    "id", "name", "color", "description", "category",
                    "repository", "branch", "created_at", "updated_at",
                ],
                "Metadata": [
                    "graph_unique_id", "id", "name", "content", "branch",
                    "created_at", "updated_at",
                ],
            }

            properties = properties_map.get(label, [])

            return {
                "success": True,
                "operation": "properties",
                "label": label,
                "properties": properties,
            }

        elif operation == "indexes":
            # List indexes (KuzuDB uses primary keys as indexes)
            indexes = [
                {"label": "Repository", "property": "id", "type": "primary_key"},
                {
                    "label": "Component",
                    "property": "graph_unique_id",
                    "type": "primary_key",
                },
                {
                    "label": "Decision",
                    "property": "graph_unique_id",
                    "type": "primary_key",
                },
                {
                    "label": "Rule",
                    "property": "graph_unique_id",
                    "type": "primary_key",
                },
                {
                    "label": "Context",
                    "property": "graph_unique_id",
                    "type": "primary_key",
                },
                {"label": "File", "property": "id", "type": "primary_key"},
                {"label": "Tag", "property": "id", "type": "primary_key"},
                {
                    "label": "Metadata",
                    "property": "graph_unique_id",
                    "type": "primary_key",
                },
            ]

            return {
                "success": True,
                "operation": "indexes",
                "indexes": indexes,
            }

        elif operation == "statistics":
            # Get comprehensive statistics
            stats = await memory_service.get_statistics(repository, branch)

            return {
                "success": True,
                "operation": "statistics",
                **stats,
            }

        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
            }

    except Exception as e:
        logger.error(
            "Introspect handler error",
            operation=operation,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }
