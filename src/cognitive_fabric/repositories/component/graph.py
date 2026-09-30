"""Graph traversal operations mixin for ComponentRepository."""

from typing import TYPE_CHECKING, Any, Optional

from cognitive_fabric.types.entities import Component

if TYPE_CHECKING:
    from cognitive_fabric.repositories.base import BaseRepository


class ComponentGraphMixin:
    """Mixin providing graph traversal operations for components."""

    async def get_dependencies(
        self: "BaseRepository",
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> list[Component]:
        """Get components that this component depends on.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            List of dependency components.
        """
        graph_id = self.create_graph_unique_id(repository, branch, component_id)

        query = """
        MATCH (c:Component {graph_unique_id: $graph_id})-[:DEPENDS_ON]->(dep:Component)
        WHERE dep.branch = $branch
        RETURN dep.graph_unique_id AS graph_unique_id,
               dep.id AS id, dep.name AS name, dep.kind AS kind,
               dep.status AS status, dep.depends_on AS depends_on,
               dep.description AS description, dep.metadata AS metadata,
               dep.repository AS repository, dep.branch AS branch,
               dep.created_at AS created_at, dep.updated_at AS updated_at
        ORDER BY dep.name
        """

        rows = self.fetch_all(query, {"graph_id": graph_id, "branch": branch})
        return [self._row_to_component(row, repository, branch) for row in rows]

    async def get_dependents(
        self: "BaseRepository",
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> list[Component]:
        """Get components that depend on this component.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            List of dependent components.
        """
        graph_id = self.create_graph_unique_id(repository, branch, component_id)

        query = """
        MATCH (dep:Component)-[:DEPENDS_ON]->(c:Component {graph_unique_id: $graph_id})
        WHERE dep.branch = $branch
        RETURN dep.graph_unique_id AS graph_unique_id,
               dep.id AS id, dep.name AS name, dep.kind AS kind,
               dep.status AS status, dep.depends_on AS depends_on,
               dep.description AS description, dep.metadata AS metadata,
               dep.repository AS repository, dep.branch AS branch,
               dep.created_at AS created_at, dep.updated_at AS updated_at
        ORDER BY dep.name
        """

        rows = self.fetch_all(query, {"graph_id": graph_id, "branch": branch})
        return [self._row_to_component(row, repository, branch) for row in rows]

    async def find_shortest_path(
        self: "BaseRepository",
        repository: str,
        start_id: str,
        end_id: str,
        branch: str = "main",
        max_depth: int = 10,
    ) -> Optional[dict[str, Any]]:
        """Find the shortest path between two components.

        Args:
            repository: The repository name.
            start_id: The starting component ID.
            end_id: The ending component ID.
            branch: The branch name.
            max_depth: Maximum path depth.

        Returns:
            Path information including nodes and length, or None if no path.
        """
        start_graph_id = self.create_graph_unique_id(repository, branch, start_id)
        end_graph_id = self.create_graph_unique_id(repository, branch, end_id)

        # `end` is a reserved keyword in Cypher; use src/dst. kuzu expresses list
        # projection via list_transform (not the `[x IN list | expr]` form).
        query = f"""
        MATCH p = (src:Component {{graph_unique_id: $start_id}})
                  -[:DEPENDS_ON*1..{max_depth}]->
                  (dst:Component {{graph_unique_id: $end_id}})
        RETURN list_transform(nodes(p), x -> x.id) AS path_nodes,
               length(p) AS path_length
        ORDER BY path_length ASC
        LIMIT 1
        """

        row = self.fetch_one(query, {
            "start_id": start_graph_id,
            "end_id": end_graph_id,
        })

        if row is None:
            return None

        return {
            "path_found": True,
            "path": row.get("path_nodes", []),
            "path_length": row.get("path_length", 0),
        }

    async def get_related_items(
        self: "BaseRepository",
        repository: str,
        component_id: str,
        branch: str = "main",
        max_depth: int = 2,
        direction: str = "both",
    ) -> list[dict[str, Any]]:
        """Get items related to a component.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.
            max_depth: Maximum traversal depth.
            direction: Relationship direction ('in', 'out', 'both').

        Returns:
            List of related items with type and path info.
        """
        graph_id = self.create_graph_unique_id(repository, branch, component_id)

        # Build direction-specific pattern
        if direction == "in":
            pattern = f"<-[*1..{max_depth}]-"
        elif direction == "out":
            pattern = f"-[*1..{max_depth}]->"
        else:
            pattern = f"-[*1..{max_depth}]-"

        query = f"""
        MATCH (start:Component {{graph_unique_id: $graph_id}}){pattern}(related)
        WHERE related.branch = $branch
          AND start <> related
        RETURN DISTINCT related.id AS id,
               related.name AS name,
               labels(related)[0] AS type
        LIMIT 100
        """

        rows = self.fetch_all(query, {"graph_id": graph_id, "branch": branch})

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
            }
            for row in rows
        ]

    async def create_dependency_relationship(
        self: "BaseRepository",
        repository: str,
        from_component_id: str,
        to_component_id: str,
        branch: str = "main",
    ) -> bool:
        """Create a DEPENDS_ON relationship between components.

        Args:
            repository: The repository name.
            from_component_id: The source component ID.
            to_component_id: The target component ID.
            branch: The branch name.

        Returns:
            True if created, False otherwise.
        """
        from_graph_id = self.create_graph_unique_id(
            repository, branch, from_component_id
        )
        to_graph_id = self.create_graph_unique_id(
            repository, branch, to_component_id
        )

        query = """
        MATCH (from:Component {graph_unique_id: $from_id})
        MATCH (to:Component {graph_unique_id: $to_id})
        MERGE (from)-[:DEPENDS_ON]->(to)
        RETURN count(*) AS created
        """

        result = self.fetch_one(query, {
            "from_id": from_graph_id,
            "to_id": to_graph_id,
        })

        return result is not None and result.get("created", 0) > 0

    async def remove_dependency_relationship(
        self: "BaseRepository",
        repository: str,
        from_component_id: str,
        to_component_id: str,
        branch: str = "main",
    ) -> bool:
        """Remove a DEPENDS_ON relationship between components.

        Args:
            repository: The repository name.
            from_component_id: The source component ID.
            to_component_id: The target component ID.
            branch: The branch name.

        Returns:
            True if removed, False otherwise.
        """
        from_graph_id = self.create_graph_unique_id(
            repository, branch, from_component_id
        )
        to_graph_id = self.create_graph_unique_id(
            repository, branch, to_component_id
        )

        query = """
        MATCH (from:Component {graph_unique_id: $from_id})
              -[r:DEPENDS_ON]->
              (to:Component {graph_unique_id: $to_id})
        DELETE r
        RETURN count(*) AS deleted
        """

        result = self.fetch_one(query, {
            "from_id": from_graph_id,
            "to_id": to_graph_id,
        })

        return result is not None and result.get("deleted", 0) > 0
