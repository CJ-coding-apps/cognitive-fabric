"""Graph query service for structured graph queries."""

from typing import TYPE_CHECKING, Any, Optional

import structlog

if TYPE_CHECKING:
    from cognitive_fabric.services.service_container import ServiceContainer

logger = structlog.get_logger(__name__)


class GraphQueryService:
    """Service for graph query operations."""

    def __init__(self, container: "ServiceContainer") -> None:
        """Initialize the graph query service.

        Args:
            container: The service container for dependency injection.
        """
        self._container = container

    async def query_context(
        self,
        repository: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Query context information for a repository.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            Context information including recent activity and summary.
        """
        context_repo = await self._container.get_context_repository()
        component_repo = await self._container.get_component_repository()

        # Get recent contexts
        recent_contexts = await context_repo.get_recent_contexts(repository, branch, 5)

        # Get component count
        components = await component_repo.get_all_components(repository, branch)

        # Get latest context
        latest = await context_repo.get_latest_context(repository, branch)

        return {
            "repository": repository,
            "branch": branch,
            "total_components": len(components),
            "recent_contexts": [
                {
                    "id": ctx.id,
                    "name": ctx.name,
                    "date": ctx.iso_date,
                    "agent": ctx.agent,
                    "summary": ctx.summary,
                }
                for ctx in recent_contexts
            ],
            "latest_context": {
                "id": latest.id,
                "name": latest.name,
                "date": latest.iso_date,
                "summary": latest.summary,
            } if latest else None,
        }

    async def query_entities(
        self,
        repository: str,
        entity_type: str,
        branch: str = "main",
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Query entities with optional filters.

        Args:
            repository: The repository name.
            entity_type: The entity type to query.
            branch: The branch name.
            filters: Optional filters to apply.

        Returns:
            List of matching entities.
        """
        entity_type_lower = entity_type.lower()
        filters = filters or {}

        if entity_type_lower == "component":
            component_repo = await self._container.get_component_repository()

            if filters.get("status") == "active":
                components = await component_repo.get_active_components(
                    repository, branch
                )
            else:
                components = await component_repo.get_all_components(repository, branch)

            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "kind": c.kind,
                    "status": c.status.value if c.status else None,
                    "depends_on": c.depends_on,
                    "description": c.description,
                }
                for c in components
            ]

        elif entity_type_lower == "decision":
            decision_repo = await self._container.get_decision_repository()
            decisions = await decision_repo.get_all_decisions(repository, branch)

            return [
                {
                    "id": d.id,
                    "name": d.name,
                    "context": d.context,
                    "date": d.date,
                    "status": d.status.value if d.status else None,
                    "rationale": d.rationale,
                }
                for d in decisions
            ]

        elif entity_type_lower == "rule":
            rule_repo = await self._container.get_rule_repository()

            if filters.get("status") == "active":
                rules = await rule_repo.get_active_rules(repository, branch)
            elif filters.get("category"):
                rules = await rule_repo.get_rules_by_category(
                    repository, filters["category"], branch
                )
            else:
                rules = await rule_repo.get_all_rules(repository, branch)

            return [
                {
                    "id": r.id,
                    "name": r.name,
                    "triggers": r.triggers,
                    "content": r.content,
                    "status": r.status.value if r.status else None,
                    "category": r.category,
                    "priority": r.priority,
                }
                for r in rules
            ]

        elif entity_type_lower == "file":
            file_repo = await self._container.get_file_repository()
            files = await file_repo.get_all_files(repository, branch)

            return [
                {
                    "id": f.id,
                    "name": f.name,
                    "path": f.path,
                    "size": f.size,
                    "mime_type": f.mime_type,
                }
                for f in files
            ]

        elif entity_type_lower == "tag":
            tag_repo = await self._container.get_tag_repository()

            if filters.get("category"):
                tags = await tag_repo.get_tags_by_category(
                    repository, filters["category"], branch
                )
            else:
                tags = await tag_repo.get_all_tags(repository, branch)

            return [
                {
                    "id": t.id,
                    "name": t.name,
                    "color": t.color,
                    "description": t.description,
                    "category": t.category,
                }
                for t in tags
            ]

        elif entity_type_lower == "context":
            context_repo = await self._container.get_context_repository()
            contexts = await context_repo.get_all_contexts(repository, branch)

            return [
                {
                    "id": c.id,
                    "name": c.name,
                    "iso_date": c.iso_date,
                    "agent": c.agent,
                    "summary": c.summary,
                }
                for c in contexts
            ]

        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

    async def query_relationships(
        self,
        repository: str,
        relationship_type: str,
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Query relationships by type.

        Args:
            repository: The repository name.
            relationship_type: The relationship type to query.
            branch: The branch name.

        Returns:
            List of relationships.
        """
        client = await self._container.get_kuzu_client()

        relationship_type_upper = relationship_type.upper().replace("-", "_")

        # Build query based on relationship type
        if relationship_type_upper == "DEPENDS_ON":
            query = """
            MATCH (a:Component)-[r:DEPENDS_ON]->(b:Component)
            WHERE a.repository = $repository AND a.branch = $branch
            RETURN a.id AS from_id, a.name AS from_name,
                   b.id AS to_id, b.name AS to_name,
                   'DEPENDS_ON' AS relationship_type
            """
        elif relationship_type_upper == "IMPLEMENTS":
            query = """
            MATCH (c:Component)-[r:IMPLEMENTS]->(f:File)
            WHERE c.repository = $repository AND c.branch = $branch
            RETURN c.id AS from_id, c.name AS from_name,
                   f.id AS to_id, f.name AS to_name,
                   'IMPLEMENTS' AS relationship_type
            """
        elif relationship_type_upper == "TAGGED_WITH":
            query = """
            MATCH (item)-[r:TAGGED_WITH]->(t:Tag)
            WHERE t.repository = $repository AND t.branch = $branch
            RETURN item.id AS from_id, item.name AS from_name,
                   t.id AS to_id, t.name AS to_name,
                   'TAGGED_WITH' AS relationship_type
            """
        elif relationship_type_upper == "GOVERNS":
            query = """
            MATCH (r:Rule)-[rel:GOVERNS]->(c:Component)
            WHERE r.repository = $repository AND r.branch = $branch
            RETURN r.id AS from_id, r.name AS from_name,
                   c.id AS to_id, c.name AS to_name,
                   'GOVERNS' AS relationship_type
            """
        elif relationship_type_upper == "AFFECTS":
            query = """
            MATCH (d:Decision)-[r:AFFECTS]->(c:Component)
            WHERE d.repository = $repository AND d.branch = $branch
            RETURN d.id AS from_id, d.name AS from_name,
                   c.id AS to_id, c.name AS to_name,
                   'AFFECTS' AS relationship_type
            """
        elif relationship_type_upper == "CONTEXT_OF":
            query = """
            MATCH (ctx:Context)-[r:CONTEXT_OF]->(c:Component)
            WHERE ctx.repository = $repository AND ctx.branch = $branch
            RETURN ctx.id AS from_id, ctx.name AS from_name,
                   c.id AS to_id, c.name AS to_name,
                   'CONTEXT_OF' AS relationship_type
            """
        else:
            raise ValueError(f"Unknown relationship type: {relationship_type}")

        rows = client.fetch_all(query, {"repository": repository, "branch": branch})

        return [
            {
                "from_id": row["from_id"],
                "from_name": row["from_name"],
                "to_id": row["to_id"],
                "to_name": row["to_name"],
                "relationship_type": row["relationship_type"],
            }
            for row in rows
        ]

    async def query_dependencies(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
        direction: str = "both",
        depth: int = 1,
    ) -> dict[str, Any]:
        """Query component dependencies.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.
            direction: Direction of dependencies ('in', 'out', 'both').
            depth: Maximum traversal depth.

        Returns:
            Dictionary with dependency information.
        """
        component_repo = await self._container.get_component_repository()

        # Get the component
        component = await component_repo.find_by_id(repository, component_id, branch)
        if not component:
            return {
                "error": f"Component not found: {component_id}",
                "dependencies": [],
                "dependents": [],
            }

        dependencies = []
        dependents = []

        if direction in ("out", "both"):
            deps = await component_repo.get_dependencies(
                repository, component_id, branch
            )
            dependencies = [
                {"id": d.id, "name": d.name, "kind": d.kind}
                for d in deps
            ]

        if direction in ("in", "both"):
            deps = await component_repo.get_dependents(repository, component_id, branch)
            dependents = [
                {"id": d.id, "name": d.name, "kind": d.kind}
                for d in deps
            ]

        # Get related items for deeper traversal
        related = []
        if depth > 1:
            related_items = await component_repo.get_related_items(
                repository, component_id, branch, max_depth=depth, direction=direction
            )
            related = related_items

        return {
            "component": {
                "id": component.id,
                "name": component.name,
                "kind": component.kind,
            },
            "dependencies": dependencies,
            "dependents": dependents,
            "related": related,
            "depth": depth,
            "direction": direction,
        }

    async def query_governance(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Query governance rules for a component.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            Dictionary with governance information.
        """
        component_repo = await self._container.get_component_repository()
        rule_repo = await self._container.get_rule_repository()
        decision_repo = await self._container.get_decision_repository()

        # Get the component
        component = await component_repo.find_by_id(repository, component_id, branch)
        if not component:
            return {
                "error": f"Component not found: {component_id}",
                "rules": [],
                "decisions": [],
            }

        # Get governing rules
        rules = await rule_repo.get_rules_governing_component(
            repository, component_id, branch
        )

        # Get affecting decisions
        decisions = await decision_repo.get_decisions_affecting_component(
            repository, component_id, branch
        )

        return {
            "component": {
                "id": component.id,
                "name": component.name,
            },
            "rules": [
                {
                    "id": r.id,
                    "name": r.name,
                    "content": r.content,
                    "status": r.status.value if r.status else None,
                    "priority": r.priority,
                }
                for r in rules
            ],
            "decisions": [
                {
                    "id": d.id,
                    "name": d.name,
                    "date": d.date,
                    "status": d.status.value if d.status else None,
                    "rationale": d.rationale,
                }
                for d in decisions
            ],
        }

    async def query_history(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Query component history.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            Dictionary with component history.
        """
        component_repo = await self._container.get_component_repository()
        context_repo = await self._container.get_context_repository()

        # Get the component
        component = await component_repo.find_by_id(repository, component_id, branch)
        if not component:
            return {
                "error": f"Component not found: {component_id}",
                "contexts": [],
            }

        # Get related contexts
        contexts = await context_repo.get_contexts_for_component(
            repository, component_id, branch
        )

        return {
            "component": {
                "id": component.id,
                "name": component.name,
                "created_at": (
                    component.created_at.isoformat()
                    if component.created_at
                    else None
                ),
                "updated_at": (
                    component.updated_at.isoformat()
                    if component.updated_at
                    else None
                ),
            },
            "contexts": [
                {
                    "id": c.id,
                    "name": c.name,
                    "date": c.iso_date,
                    "agent": c.agent,
                    "summary": c.summary,
                    "observation": c.observation,
                }
                for c in contexts
            ],
        }

    async def query_tags(
        self,
        repository: str,
        tag_id: Optional[str] = None,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Query tags and tagged items.

        Args:
            repository: The repository name.
            tag_id: Optional specific tag ID to query.
            branch: The branch name.

        Returns:
            Dictionary with tag information.
        """
        tag_repo = await self._container.get_tag_repository()

        if tag_id:
            # Get specific tag and its items
            tag = await tag_repo.find_by_id(repository, tag_id, branch)
            if not tag:
                return {
                    "error": f"Tag not found: {tag_id}",
                    "tag": None,
                    "items": [],
                }

            items = await tag_repo.get_items_with_tag(repository, tag_id, branch)

            return {
                "tag": {
                    "id": tag.id,
                    "name": tag.name,
                    "color": tag.color,
                    "description": tag.description,
                    "category": tag.category,
                },
                "items": items,
            }
        else:
            # Get all tags with usage stats
            tags = await tag_repo.get_all_tags(repository, branch)
            stats = await tag_repo.get_tag_usage_stats(repository, branch)

            # Create lookup for stats
            stats_lookup = {s["id"]: s["usage_count"] for s in stats}

            return {
                "tags": [
                    {
                        "id": t.id,
                        "name": t.name,
                        "color": t.color,
                        "description": t.description,
                        "category": t.category,
                        "usage_count": stats_lookup.get(t.id, 0),
                    }
                    for t in tags
                ],
                "total_tags": len(tags),
            }
