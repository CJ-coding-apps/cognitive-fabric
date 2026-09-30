"""Handler for search tool."""

from typing import Any, Dict, List

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


async def search_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle search tool operations.

    Args:
        params: Tool parameters.
        context: Tool handler context.
        memory_service: The memory service.

    Returns:
        Operation result.
    """
    # `mode` is the TS wire name; `searchType` kept as additive alias.
    search_type = params.get("mode") or params.get("searchType") or "fulltext"
    repository = params["repository"]
    branch = params.get("branch", "main")
    query = params.get("query", "")
    entity_types = params.get("entityTypes", ["component", "decision", "rule"])
    limit = params.get("limit", 20)

    logger.debug(
        "search handler",
        search_type=search_type,
        repository=repository,
        query=query,
    )

    kuzu_client = await memory_service.get_kuzu_client()

    try:
        if search_type == "fulltext":
            results = await _fulltext_search(
                kuzu_client, repository, branch, query, entity_types, limit
            )

            return {
                "success": True,
                "searchType": "fulltext",
                "query": query,
                "results": results,
                "count": len(results),
            }

        elif search_type == "by-name":
            results = await _search_by_name(
                kuzu_client, repository, branch, query, entity_types, limit
            )

            return {
                "success": True,
                "searchType": "by-name",
                "query": query,
                "results": results,
                "count": len(results),
            }

        elif search_type == "by-kind":
            # Search components by kind
            results = await _search_by_kind(
                kuzu_client, repository, branch, query, limit
            )

            return {
                "success": True,
                "searchType": "by-kind",
                "query": query,
                "results": results,
                "count": len(results),
            }

        elif search_type == "semantic":
            sem = await _semantic_search(
                memory_service, repository, branch, query, limit,
                params.get("threshold", 0.0),
            )
            return {
                "success": True,
                "searchType": "semantic",
                "query": query,
                "results": sem["results"],
                "count": len(sem["results"]),
                "available": sem["available"],
                "message": sem.get("message"),
            }

        elif search_type == "hybrid":
            ft = await _fulltext_search(
                kuzu_client, repository, branch, query, entity_types, limit
            )
            sem = await _semantic_search(
                memory_service, repository, branch, query, limit,
                params.get("threshold", 0.0),
            )
            merged = _merge_results(ft, sem["results"], limit)
            return {
                "success": True,
                "searchType": "hybrid",
                "query": query,
                "results": merged,
                "count": len(merged),
                "available": sem["available"],
            }

        else:
            return {
                "success": False,
                "error": f"Unknown search type: {search_type}",
            }

    except Exception as e:
        logger.error(
            "Search handler error",
            search_type=search_type,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }


async def _fulltext_search(
    kuzu_client: Any,
    repository: str,
    branch: str,
    query: str,
    entity_types: List[str],
    limit: int,
) -> List[Dict[str, Any]]:
    """Perform fulltext search across entities.

    Args:
        kuzu_client: The KuzuDB client.
        repository: The repository name.
        branch: The branch name.
        query: The search query.
        entity_types: Entity types to search.
        limit: Maximum results.

    Returns:
        List of search results.
    """
    results = []
    query_lower = query.lower()
    per_type_limit = max(1, limit // len(entity_types))

    for entity_type in entity_types:
        entity_type_lower = entity_type.lower()

        if entity_type_lower == "component":
            cypher = f"""
            MATCH (c:Component)
            WHERE c.repository = $repository AND c.branch = $branch
              AND (toLower(c.name) CONTAINS $query
                   OR toLower(c.description) CONTAINS $query
                   OR toLower(c.kind) CONTAINS $query)
            RETURN c.id AS id, c.name AS name, c.kind AS kind,
                   c.description AS description, 'component' AS type
            LIMIT {per_type_limit}
            """

        elif entity_type_lower == "decision":
            cypher = f"""
            MATCH (d:Decision)
            WHERE d.repository = $repository AND d.branch = $branch
              AND (toLower(d.name) CONTAINS $query
                   OR toLower(d.context) CONTAINS $query
                   OR toLower(d.rationale) CONTAINS $query)
            RETURN d.id AS id, d.name AS name, d.context AS context,
                   d.rationale AS description, 'decision' AS type
            LIMIT {per_type_limit}
            """

        elif entity_type_lower == "rule":
            cypher = f"""
            MATCH (r:Rule)
            WHERE r.repository = $repository AND r.branch = $branch
              AND (toLower(r.name) CONTAINS $query
                   OR toLower(r.content) CONTAINS $query
                   OR toLower(r.category) CONTAINS $query)
            RETURN r.id AS id, r.name AS name, r.category AS category,
                   r.content AS description, 'rule' AS type
            LIMIT {per_type_limit}
            """

        else:
            continue

        rows = kuzu_client.fetch_all(cypher, {
            "repository": repository,
            "branch": branch,
            "query": query_lower,
        })

        for row in rows:
            results.append({
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "description": row.get("description", ""),
                "extra": {
                    "kind": row.get("kind"),
                    "category": row.get("category"),
                    "context": row.get("context"),
                },
            })

    return results[:limit]


async def _search_by_name(
    kuzu_client: Any,
    repository: str,
    branch: str,
    query: str,
    entity_types: List[str],
    limit: int,
) -> List[Dict[str, Any]]:
    """Search entities by name.

    Args:
        kuzu_client: The KuzuDB client.
        repository: The repository name.
        branch: The branch name.
        query: The name query.
        entity_types: Entity types to search.
        limit: Maximum results.

    Returns:
        List of search results.
    """
    results = []
    query_lower = query.lower()
    per_type_limit = max(1, limit // len(entity_types))

    for entity_type in entity_types:
        entity_type_lower = entity_type.lower()

        if entity_type_lower == "component":
            cypher = f"""
            MATCH (c:Component)
            WHERE c.repository = $repository AND c.branch = $branch
              AND toLower(c.name) CONTAINS $query
            RETURN c.id AS id, c.name AS name, c.kind AS kind, 'component' AS type
            ORDER BY c.name
            LIMIT {per_type_limit}
            """

        elif entity_type_lower == "decision":
            cypher = f"""
            MATCH (d:Decision)
            WHERE d.repository = $repository AND d.branch = $branch
              AND toLower(d.name) CONTAINS $query
            RETURN d.id AS id, d.name AS name, d.status AS status, 'decision' AS type
            ORDER BY d.name
            LIMIT {per_type_limit}
            """

        elif entity_type_lower == "rule":
            cypher = f"""
            MATCH (r:Rule)
            WHERE r.repository = $repository AND r.branch = $branch
              AND toLower(r.name) CONTAINS $query
            RETURN r.id AS id, r.name AS name, r.category AS category, 'rule' AS type
            ORDER BY r.name
            LIMIT {per_type_limit}
            """

        elif entity_type_lower == "tag":
            cypher = f"""
            MATCH (t:Tag)
            WHERE t.repository = $repository AND t.branch = $branch
              AND toLower(t.name) CONTAINS $query
            RETURN t.id AS id, t.name AS name, t.category AS category, 'tag' AS type
            ORDER BY t.name
            LIMIT {per_type_limit}
            """

        else:
            continue

        rows = kuzu_client.fetch_all(cypher, {
            "repository": repository,
            "branch": branch,
            "query": query_lower,
        })

        for row in rows:
            results.append({
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
                "extra": {
                    "kind": row.get("kind"),
                    "category": row.get("category"),
                    "status": row.get("status"),
                },
            })

    return results[:limit]


async def _search_by_kind(
    kuzu_client: Any,
    repository: str,
    branch: str,
    kind: str,
    limit: int,
) -> List[Dict[str, Any]]:
    """Search components by kind.

    Args:
        kuzu_client: The KuzuDB client.
        repository: The repository name.
        branch: The branch name.
        kind: The component kind.
        limit: Maximum results.

    Returns:
        List of search results.
    """
    cypher = f"""
    MATCH (c:Component)
    WHERE c.repository = $repository AND c.branch = $branch
      AND toLower(c.kind) = $kind
    RETURN c.id AS id, c.name AS name, c.kind AS kind,
           c.status AS status, c.description AS description
    ORDER BY c.name
    LIMIT {limit}
    """

    rows = kuzu_client.fetch_all(cypher, {
        "repository": repository,
        "branch": branch,
        "kind": kind.lower(),
    })

    return [
        {
            "id": row["id"],
            "name": row["name"],
            "kind": row["kind"],
            "status": row.get("status"),
            "description": row.get("description"),
        }
        for row in rows
    ]


async def _semantic_search(
    memory_service: MemoryService,
    repository: str,
    branch: str,
    query: str,
    limit: int,
    threshold: float,
) -> Dict[str, Any]:
    """Vector search over ingested symbols via the DataFabricService.

    Degrades gracefully: returns available=False + empty results when the
    semantic layer is unavailable.
    """
    data_fabric = await memory_service.data_fabric
    resp = await data_fabric.semantic_search(
        repository, branch, query, limit, threshold
    )
    results = [
        {
            "id": r.get("symbol_id"),
            "name": r.get("name"),
            "type": "symbol",
            "score": r.get("score"),
            "extra": {"file_id": r.get("file_id"), "source": "semantic"},
        }
        for r in resp.get("results", [])
    ]
    return {
        "results": results,
        "available": resp.get("available", False),
        "message": resp.get("message"),
    }


def _merge_results(
    fulltext: List[Dict[str, Any]],
    semantic: List[Dict[str, Any]],
    limit: int,
) -> List[Dict[str, Any]]:
    """Merge full-text and semantic results, deduping by id (keep best score)."""
    by_id: Dict[Any, Dict[str, Any]] = {}
    for r in fulltext:
        entry = dict(r)
        entry.setdefault("score", 0.5)  # baseline for non-scored full-text hits
        by_id[r.get("id")] = entry
    for r in semantic:
        rid = r.get("id")
        existing = by_id.get(rid)
        if existing is None or (r.get("score") or 0) > (existing.get("score") or 0):
            by_id[rid] = r
    merged = sorted(by_id.values(), key=lambda x: x.get("score") or 0, reverse=True)
    return merged[:limit]
