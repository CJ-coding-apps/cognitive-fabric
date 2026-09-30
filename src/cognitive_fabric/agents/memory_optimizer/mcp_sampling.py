"""Memory sampling manager for the memory optimizer.

Python port of the TypeScript ``MCPSamplingManager``
(``src/agents/memory-optimizer/mcp-sampling-manager.ts``).

Unlike the MCP "sampling" protocol callback, this samples entities directly
from KuzuDB using scoped Cypher. It is used by the memory-optimizer handler to
attach a context-aware ``sample`` to analysis results. All methods are
defensive: they return empty collections when tables are empty or queries fail,
so no operation depends on a populated graph.
"""

from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

import structlog

from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)

# Entity node labels that carry repository/branch-scoped domain data.
ENTITY_TYPES: Tuple[str, ...] = (
    "Component",
    "Decision",
    "Rule",
    "File",
    "Context",
    "Tag",
)

VALID_SAMPLING_STRATEGIES: Tuple[str, ...] = (
    "representative",
    "problematic",
    "recent",
    "diverse",
)


def _sanitize_limit(value: Any, default: int = 20) -> int:
    """Sanitize a value into a safe positive integer for an inlined LIMIT.

    KuzuDB does not accept a query parameter in a LIMIT clause, so the value
    must be inlined. This guarantees the inlined text is a bounded integer and
    can never carry injection.

    Args:
        value: The candidate limit value.
        default: Fallback when the value is not a usable integer.

    Returns:
        A positive integer clamped to a sane maximum.
    """
    try:
        limit = int(value)
    except (TypeError, ValueError):
        limit = default
    if limit < 1:
        limit = 1
    # Guard against absurd inlined values.
    if limit > 10000:
        limit = 10000
    return limit


class MemorySamplingManager:
    """Samples memory graph entities directly from KuzuDB.

    Mirrors the behavior of the TypeScript ``MCPSamplingManager`` but operates
    over the in-process :class:`KuzuDBClient` rather than an MCP callback.
    """

    def __init__(self, memory_service: MemoryService) -> None:
        """Initialize the sampling manager.

        Args:
            memory_service: The memory service used to obtain a KuzuDB client.
        """
        self._memory_service = memory_service
        self._logger = logger.bind(service="MemorySamplingManager")

    async def sample_memory_context(
        self,
        repository: str,
        branch: str = "main",
        strategy: str = "representative",
        sample_size: int = 20,
    ) -> Dict[str, Any]:
        """Sample memory context based on a strategy.

        Args:
            repository: The repository name to scope the sample to.
            branch: The branch name to scope the sample to.
            strategy: One of ``representative``, ``problematic``, ``recent``,
                ``diverse``. Unknown strategies fall back to
                ``representative``.
            sample_size: Target number of entities to sample.

        Returns:
            A dict with ``entities``, ``relationships`` and ``metadata`` keys.
        """
        if strategy not in VALID_SAMPLING_STRATEGIES:
            self._logger.warning(
                "Unknown sampling strategy; using representative",
                strategy=strategy,
            )
            strategy = "representative"

        size = _sanitize_limit(sample_size)

        try:
            client = await self._memory_service.get_kuzu_client()
        except Exception as exc:  # pragma: no cover - defensive
            self._logger.warning("Failed to obtain KuzuDB client", error=str(exc))
            return self._empty_sample(repository, branch, strategy, size)

        total_counts = self._get_total_counts(client, repository, branch)

        if strategy == "representative":
            entities, relationships = self._sample_representative(
                client, repository, branch, size
            )
        elif strategy == "problematic":
            entities, relationships = self._sample_problematic(
                client, repository, branch, size
            )
        elif strategy == "recent":
            entities, relationships = self._sample_recent(
                client, repository, branch, size
            )
        else:  # diverse
            entities, relationships = self._sample_diverse(
                client, repository, branch, size
            )

        total_entities = total_counts["entities"]
        sampling_ratio = (
            len(entities) / total_entities if total_entities else 0.0
        )

        return {
            "entities": entities,
            "relationships": relationships,
            "metadata": {
                "samplingStrategy": strategy,
                "sampleSize": len(entities),
                "requestedSampleSize": size,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "repository": repository,
                "branch": branch,
                "totalEntities": total_entities,
                "totalRelationships": total_counts["relationships"],
                "samplingRatio": sampling_ratio,
            },
        }

    def _empty_sample(
        self,
        repository: str,
        branch: str,
        strategy: str,
        size: int,
    ) -> Dict[str, Any]:
        """Build an empty sample payload (used on failure)."""
        return {
            "entities": [],
            "relationships": [],
            "metadata": {
                "samplingStrategy": strategy,
                "sampleSize": 0,
                "requestedSampleSize": size,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "repository": repository,
                "branch": branch,
                "totalEntities": 0,
                "totalRelationships": 0,
                "samplingRatio": 0.0,
            },
        }

    def _get_total_counts(
        self,
        client: Any,
        repository: str,
        branch: str,
    ) -> Dict[str, int]:
        """Get total entity and relationship counts for metadata."""
        entities = 0
        relationships = 0
        params = {"repository": repository, "branch": branch}

        try:
            entity_query = """
            MATCH (n)
            WHERE n.repository = $repository AND n.branch = $branch
              AND n.id IS NOT NULL
            RETURN count(n) AS entityCount
            """
            row = client.fetch_one(entity_query, params)
            if row and row.get("entityCount") is not None:
                entities = int(row["entityCount"])
        except Exception as exc:
            self._logger.warning("Failed to count entities", error=str(exc))

        try:
            rel_query = """
            MATCH (a)-[r]->(b)
            WHERE a.repository = $repository AND a.branch = $branch
              AND b.repository = $repository AND b.branch = $branch
            RETURN count(r) AS relationshipCount
            """
            row = client.fetch_one(rel_query, params)
            if row and row.get("relationshipCount") is not None:
                relationships = int(row["relationshipCount"])
        except Exception as exc:
            self._logger.warning("Failed to count relationships", error=str(exc))

        return {"entities": entities, "relationships": relationships}

    def _sample_representative(
        self,
        client: Any,
        repository: str,
        branch: str,
        sample_size: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Stratified representative sample across all entity types."""
        limit = _sanitize_limit(sample_size)
        try:
            query = f"""
            MATCH (n)
            WHERE n.repository = $repository AND n.branch = $branch
              AND n.id IS NOT NULL
            WITH n
            ORDER BY n.id
            LIMIT {limit}
            RETURN n.id AS id, n.name AS name,
                   n.created_at AS created_at,
                   n.description AS description, n.status AS status
            """
            entities = client.fetch_all(
                query, {"repository": repository, "branch": branch}
            )
        except Exception as exc:
            self._logger.warning(
                "Failed to sample representative entities", error=str(exc)
            )
            return [], []

        relationships = self._get_sample_relationships(
            client, [e.get("id") for e in entities], repository, branch
        )
        return entities, relationships

    def _sample_problematic(
        self,
        client: Any,
        repository: str,
        branch: str,
        sample_size: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Sample entities with no relationships or deprecated status."""
        limit = _sanitize_limit(sample_size)
        try:
            query = f"""
            MATCH (n)
            WHERE n.repository = $repository AND n.branch = $branch
              AND n.id IS NOT NULL
            OPTIONAL MATCH (n)-[r]-()
            WITH n, count(r) AS relationshipCount
            WHERE relationshipCount = 0 OR n.status = 'deprecated'
            ORDER BY relationshipCount ASC
            LIMIT {limit}
            RETURN n.id AS id, n.name AS name,
                   n.created_at AS created_at,
                   n.description AS description, n.status AS status,
                   relationshipCount
            """
            entities = client.fetch_all(
                query, {"repository": repository, "branch": branch}
            )
        except Exception as exc:
            self._logger.warning(
                "Failed to sample problematic entities", error=str(exc)
            )
            return [], []

        relationships = self._get_sample_relationships(
            client, [e.get("id") for e in entities], repository, branch
        )
        return entities, relationships

    def _sample_recent(
        self,
        client: Any,
        repository: str,
        branch: str,
        sample_size: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Sample the most recently created entities (newest first)."""
        limit = _sanitize_limit(sample_size)
        try:
            query = f"""
            MATCH (n)
            WHERE n.repository = $repository AND n.branch = $branch
              AND n.id IS NOT NULL
              AND n.created_at IS NOT NULL
            ORDER BY n.created_at DESC
            LIMIT {limit}
            RETURN n.id AS id, n.name AS name,
                   n.created_at AS created_at,
                   n.description AS description, n.status AS status
            """
            entities = client.fetch_all(
                query, {"repository": repository, "branch": branch}
            )
        except Exception as exc:
            self._logger.warning(
                "Failed to sample recent entities", error=str(exc)
            )
            return [], []

        relationships = self._get_sample_relationships(
            client, [e.get("id") for e in entities], repository, branch
        )
        return entities, relationships

    def _sample_diverse(
        self,
        client: Any,
        repository: str,
        branch: str,
        sample_size: int,
    ) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
        """Sample an even distribution across all entity types."""
        per_type = _sanitize_limit(max(1, sample_size // len(ENTITY_TYPES)))
        all_entities: List[Dict[str, Any]] = []

        for entity_type in ENTITY_TYPES:
            # entity_type is a fixed whitelist constant, never user input.
            try:
                query = f"""
                MATCH (n:{entity_type})
                WHERE n.repository = $repository AND n.branch = $branch
                WITH n
                ORDER BY n.id
                LIMIT {per_type}
                RETURN n.id AS id, n.name AS name,
                       n.created_at AS created_at,
                       n.description AS description, n.status AS status
                """
                rows = client.fetch_all(
                    query, {"repository": repository, "branch": branch}
                )
                for row in rows:
                    row["nodeLabel"] = entity_type
                all_entities.extend(rows)
            except Exception as exc:
                self._logger.warning(
                    "Failed to sample diverse entities",
                    entity_type=entity_type,
                    error=str(exc),
                )

        if len(all_entities) > sample_size:
            all_entities = all_entities[:sample_size]

        relationships = self._get_sample_relationships(
            client, [e.get("id") for e in all_entities], repository, branch
        )
        return all_entities, relationships

    def _get_sample_relationships(
        self,
        client: Any,
        entity_ids: List[Any],
        repository: str,
        branch: str,
    ) -> List[Dict[str, Any]]:
        """Get relationships touching any of the sampled entities."""
        ids = [i for i in entity_ids if i is not None]
        if not ids:
            return []

        try:
            query = """
            MATCH (a)-[r]->(b)
            WHERE a.repository = $repository AND a.branch = $branch
              AND b.repository = $repository AND b.branch = $branch
              AND (a.id IN $entityIds OR b.id IN $entityIds)
            RETURN a.id AS fromId, b.id AS toId,
                   'RELATIONSHIP' AS relationshipType
            LIMIT 100
            """
            return client.fetch_all(
                query,
                {
                    "repository": repository,
                    "branch": branch,
                    "entityIds": ids,
                },
            )
        except Exception as exc:
            self._logger.warning(
                "Failed to get sample relationships", error=str(exc)
            )
            return []
