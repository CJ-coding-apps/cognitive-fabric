"""CRUD operations mixin for ComponentRepository."""

from typing import TYPE_CHECKING, Any, Optional

from cognitive_fabric.types.entities import Component, ComponentInput, ComponentStatus

if TYPE_CHECKING:
    from cognitive_fabric.repositories.base import BaseRepository


class ComponentCrudMixin:
    """Mixin providing CRUD operations for components."""

    async def find_by_id(
        self: "BaseRepository",
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> Optional[Component]:
        """Find a component by ID.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            The Component if found, None otherwise.
        """
        graph_id = self.create_graph_unique_id(repository, branch, component_id)

        query = """
        MATCH (c:Component {graph_unique_id: $graph_id})
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.kind AS kind,
               c.status AS status, c.depends_on AS depends_on,
               c.description AS description, c.metadata AS metadata,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        LIMIT 1
        """

        row = self.fetch_one(query, {"graph_id": graph_id})

        if row is None:
            return None

        return self._row_to_component(row, repository, branch)

    async def get_active_components(
        self: "BaseRepository",
        repository: str,
        branch: str = "main",
    ) -> list[Component]:
        """Get all active components.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of active components.
        """
        query = """
        MATCH (c:Component)
        WHERE c.repository = $repository
          AND c.branch = $branch
          AND c.status = 'active'
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.kind AS kind,
               c.status AS status, c.depends_on AS depends_on,
               c.description AS description, c.metadata AS metadata,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        ORDER BY c.name
        """

        rows = self.fetch_all(query, {"repository": repository, "branch": branch})
        return [self._row_to_component(row, repository, branch) for row in rows]

    async def get_all_components(
        self: "BaseRepository",
        repository: str,
        branch: str = "main",
    ) -> list[Component]:
        """Get all components regardless of status.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all components.
        """
        query = """
        MATCH (c:Component)
        WHERE c.repository = $repository AND c.branch = $branch
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.kind AS kind,
               c.status AS status, c.depends_on AS depends_on,
               c.description AS description, c.metadata AS metadata,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        ORDER BY c.name
        """

        rows = self.fetch_all(query, {"repository": repository, "branch": branch})
        return [self._row_to_component(row, repository, branch) for row in rows]

    async def upsert_component(
        self: "BaseRepository",
        repository: str,
        input_data: ComponentInput,
    ) -> Component:
        """Create or update a component.

        Args:
            repository: The repository name.
            input_data: The component input data.

        Returns:
            The upserted Component.
        """
        branch = input_data.branch or "main"
        graph_id = self.create_graph_unique_id(repository, branch, input_data.id)
        now = self.get_current_timestamp()

        # Use MERGE for upsert
        query = """
        MERGE (c:Component {graph_unique_id: $graph_id})
        ON CREATE SET
            c.id = $id,
            c.name = $name,
            c.kind = $kind,
            c.status = $status,
            c.depends_on = $depends_on,
            c.description = $description,
            c.metadata = $metadata,
            c.repository = $repository,
            c.branch = $branch,
            c.created_at = $now,
            c.updated_at = $now
        ON MATCH SET
            c.name = $name,
            c.kind = $kind,
            c.status = $status,
            c.depends_on = $depends_on,
            c.description = $description,
            c.metadata = $metadata,
            c.updated_at = $now
        RETURN c.graph_unique_id AS graph_unique_id
        """

        import json

        params = {
            "graph_id": graph_id,
            "id": input_data.id,
            "name": input_data.name,
            "kind": input_data.kind or "",
            "status": (input_data.status or ComponentStatus.ACTIVE).value,
            "depends_on": input_data.depends_on or [],
            "description": input_data.description or "",
            "metadata": json.dumps(input_data.metadata) if input_data.metadata else "",
            "repository": repository,
            "branch": branch,
            "now": now,
        }

        self.execute_query(query, params)

        return Component(
            id=input_data.id,
            repository=repository,
            branch=branch,
            name=input_data.name,
            kind=input_data.kind,
            status=input_data.status or ComponentStatus.ACTIVE,
            depends_on=input_data.depends_on,
            description=input_data.description,
            metadata=input_data.metadata,
            created_at=now,
            updated_at=now,
        )

    async def update_component_status(
        self: "BaseRepository",
        repository: str,
        component_id: str,
        branch: str,
        status: ComponentStatus,
    ) -> Optional[Component]:
        """Update a component's status.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.
            status: The new status.

        Returns:
            The updated Component, or None if not found.
        """
        graph_id = self.create_graph_unique_id(repository, branch, component_id)
        now = self.get_current_timestamp()

        query = """
        MATCH (c:Component {graph_unique_id: $graph_id})
        SET c.status = $status, c.updated_at = $now
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.kind AS kind,
               c.status AS status, c.depends_on AS depends_on,
               c.description AS description, c.metadata AS metadata,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        """

        row = self.fetch_one(query, {
            "graph_id": graph_id,
            "status": status.value,
            "now": now,
        })

        if row is None:
            return None

        return self._row_to_component(row, repository, branch)

    async def delete_component(
        self: "BaseRepository",
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a component and its relationships.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            True if deleted, False if not found.
        """
        graph_id = self.create_graph_unique_id(repository, branch, component_id)

        query = """
        MATCH (c:Component {graph_unique_id: $graph_id})
        DETACH DELETE c
        RETURN count(*) AS deleted
        """

        result = self.fetch_one(query, {"graph_id": graph_id})
        return result is not None and result.get("deleted", 0) > 0

    def _row_to_component(
        self: "BaseRepository",
        row: dict[str, Any],
        repository: str,
        branch: str,
    ) -> Component:
        """Convert a database row to a Component.

        Args:
            row: The database row.
            repository: The repository name.
            branch: The branch name.

        Returns:
            The Component instance.
        """
        import json

        metadata = row.get("metadata")
        if isinstance(metadata, str):
            # Empty string (the stored default) must become None for Optional[dict].
            try:
                metadata = json.loads(metadata) if metadata else None
            except json.JSONDecodeError:
                metadata = None

        status_str = row.get("status")
        status = None
        if status_str:
            try:
                status = ComponentStatus(status_str)
            except ValueError:
                status = ComponentStatus.ACTIVE

        return Component(
            id=row["id"],
            repository=repository,
            branch=branch,
            name=row["name"],
            kind=row.get("kind"),
            status=status,
            depends_on=row.get("depends_on"),
            description=row.get("description"),
            metadata=metadata,
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )
