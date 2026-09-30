"""Context repository for Context entity operations."""

from typing import Any, Optional

from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.types.entities import Context, ContextInput
from cognitive_fabric.utils.security import validate_label


class ContextRepository(BaseRepository):
    """Repository for Context entity operations."""

    async def find_by_id(
        self,
        repository: str,
        context_id: str,
        branch: str = "main",
    ) -> Optional[Context]:
        """Find a context by ID.

        Args:
            repository: The repository name.
            context_id: The context ID.
            branch: The branch name.

        Returns:
            The Context if found, None otherwise.
        """
        graph_id = self.create_graph_unique_id(repository, branch, context_id)

        query = """
        MATCH (c:Context {graph_unique_id: $graph_id})
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.iso_date AS iso_date,
               c.agent AS agent, c.summary AS summary,
               c.observation AS observation,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        LIMIT 1
        """

        row = self.fetch_one(query, {"graph_id": graph_id})

        if row is None:
            return None

        return self._row_to_context(row, repository, branch)

    async def get_all_contexts(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[Context]:
        """Get all contexts.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all contexts.
        """
        query = """
        MATCH (c:Context)
        WHERE c.repository = $repository AND c.branch = $branch
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.iso_date AS iso_date,
               c.agent AS agent, c.summary AS summary,
               c.observation AS observation,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        ORDER BY c.iso_date DESC
        """

        rows = self.fetch_all(query, {"repository": repository, "branch": branch})
        return [self._row_to_context(row, repository, branch) for row in rows]

    async def get_recent_contexts(
        self,
        repository: str,
        branch: str = "main",
        limit: int = 10,
    ) -> list[Context]:
        """Get the most recent contexts.

        Args:
            repository: The repository name.
            branch: The branch name.
            limit: Maximum number of contexts to return.

        Returns:
            List of recent contexts.
        """
        query = f"""
        MATCH (c:Context)
        WHERE c.repository = $repository AND c.branch = $branch
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.iso_date AS iso_date,
               c.agent AS agent, c.summary AS summary,
               c.observation AS observation,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        ORDER BY c.iso_date DESC
        LIMIT {limit}
        """

        rows = self.fetch_all(query, {"repository": repository, "branch": branch})
        return [self._row_to_context(row, repository, branch) for row in rows]

    async def get_contexts_by_agent(
        self,
        repository: str,
        agent: str,
        branch: str = "main",
    ) -> list[Context]:
        """Get contexts by agent.

        Args:
            repository: The repository name.
            agent: The agent identifier.
            branch: The branch name.

        Returns:
            List of contexts from the agent.
        """
        query = """
        MATCH (c:Context)
        WHERE c.repository = $repository
          AND c.branch = $branch
          AND c.agent = $agent
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.iso_date AS iso_date,
               c.agent AS agent, c.summary AS summary,
               c.observation AS observation,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        ORDER BY c.iso_date DESC
        """

        rows = self.fetch_all(query, {
            "repository": repository,
            "branch": branch,
            "agent": agent,
        })
        return [self._row_to_context(row, repository, branch) for row in rows]

    async def get_contexts_by_date_range(
        self,
        repository: str,
        start_date: str,
        end_date: str,
        branch: str = "main",
    ) -> list[Context]:
        """Get contexts within a date range.

        Args:
            repository: The repository name.
            start_date: Start date (ISO format).
            end_date: End date (ISO format).
            branch: The branch name.

        Returns:
            List of contexts within the date range.
        """
        query = """
        MATCH (c:Context)
        WHERE c.repository = $repository
          AND c.branch = $branch
          AND c.iso_date >= $start_date
          AND c.iso_date <= $end_date
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.iso_date AS iso_date,
               c.agent AS agent, c.summary AS summary,
               c.observation AS observation,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        ORDER BY c.iso_date DESC
        """

        rows = self.fetch_all(query, {
            "repository": repository,
            "branch": branch,
            "start_date": start_date,
            "end_date": end_date,
        })
        return [self._row_to_context(row, repository, branch) for row in rows]

    async def upsert_context(
        self,
        repository: str,
        input_data: ContextInput,
    ) -> Context:
        """Create or update a context.

        Args:
            repository: The repository name.
            input_data: The context input data.

        Returns:
            The upserted Context.
        """
        branch = input_data.branch or "main"
        graph_id = self.create_graph_unique_id(repository, branch, input_data.id)
        now = self.get_current_timestamp()

        query = """
        MERGE (c:Context {graph_unique_id: $graph_id})
        ON CREATE SET
            c.id = $id,
            c.name = $name,
            c.iso_date = $iso_date,
            c.agent = $agent,
            c.summary = $summary,
            c.observation = $observation,
            c.repository = $repository,
            c.branch = $branch,
            c.created_at = $now,
            c.updated_at = $now
        ON MATCH SET
            c.name = $name,
            c.iso_date = $iso_date,
            c.agent = $agent,
            c.summary = $summary,
            c.observation = $observation,
            c.updated_at = $now
        RETURN c.graph_unique_id AS graph_unique_id
        """

        params = {
            "graph_id": graph_id,
            "id": input_data.id,
            "name": input_data.name,
            "iso_date": input_data.iso_date or now.date().isoformat(),
            "agent": input_data.agent or "",
            "summary": input_data.summary or "",
            "observation": input_data.observation or "",
            "repository": repository,
            "branch": branch,
            "now": now,
        }

        self.execute_query(query, params)

        return Context(
            id=input_data.id,
            repository=repository,
            branch=branch,
            name=input_data.name,
            iso_date=input_data.iso_date or now.date().isoformat(),
            agent=input_data.agent,
            summary=input_data.summary,
            observation=input_data.observation,
            created_at=now,
            updated_at=now,
        )

    async def update_context(
        self,
        repository: str,
        context_id: str,
        branch: str,
        updates: dict[str, Any],
    ) -> Optional[Context]:
        """Update a context with partial data.

        Args:
            repository: The repository name.
            context_id: The context ID.
            branch: The branch name.
            updates: Dictionary of fields to update.

        Returns:
            The updated Context, or None if not found.
        """
        graph_id = self.create_graph_unique_id(repository, branch, context_id)
        now = self.get_current_timestamp()

        # Build dynamic SET clause
        set_clauses = ["c.updated_at = $now"]
        params = {"graph_id": graph_id, "now": now}

        allowed_fields = ["name", "iso_date", "agent", "summary", "observation"]
        for field in allowed_fields:
            if field in updates:
                set_clauses.append(f"c.{field} = ${field}")
                params[field] = updates[field]

        query = f"""
        MATCH (c:Context {{graph_unique_id: $graph_id}})
        SET {", ".join(set_clauses)}
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.iso_date AS iso_date,
               c.agent AS agent, c.summary AS summary,
               c.observation AS observation,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        """

        row = self.fetch_one(query, params)

        if row is None:
            return None

        return self._row_to_context(row, repository, branch)

    async def delete_context(
        self,
        repository: str,
        context_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a context and its relationships.

        Args:
            repository: The repository name.
            context_id: The context ID.
            branch: The branch name.

        Returns:
            True if deleted, False if not found.
        """
        graph_id = self.create_graph_unique_id(repository, branch, context_id)

        query = """
        MATCH (c:Context {graph_unique_id: $graph_id})
        DETACH DELETE c
        RETURN count(*) AS deleted
        """

        result = self.fetch_one(query, {"graph_id": graph_id})
        return result is not None and result.get("deleted", 0) > 0

    async def get_contexts_for_component(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> list[Context]:
        """Get contexts related to a specific component.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            List of contexts for the component.
        """
        component_graph_id = self.create_graph_unique_id(
            repository, branch, component_id
        )

        query = """
        MATCH (c:Context)-[:CONTEXT_OF]->
              (comp:Component {graph_unique_id: $component_id})
        WHERE c.branch = $branch
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.iso_date AS iso_date,
               c.agent AS agent, c.summary AS summary,
               c.observation AS observation,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        ORDER BY c.iso_date DESC
        """

        rows = self.fetch_all(query, {
            "component_id": component_graph_id,
            "branch": branch,
        })
        return [self._row_to_context(row, repository, branch) for row in rows]

    async def create_context_of_relationship(
        self,
        repository: str,
        context_id: str,
        component_id: str,
        branch: str = "main",
        target_type: str = "Component",
    ) -> bool:
        """Create a CONTEXT_OF relationship from a context to a target entity.

        Args:
            repository: The repository name.
            context_id: The context ID.
            component_id: The target entity ID.
            branch: The branch name.
            target_type: The target entity label (Component, Decision, or Rule).

        Returns:
            True if created, False otherwise.
        """
        # CONTEXT_OF targets are all graph_unique_id-keyed. Validate the label
        # against the whitelist before interpolating it.
        if not validate_label(target_type) or target_type not in (
            "Component",
            "Decision",
            "Rule",
        ):
            raise ValueError(f"Invalid CONTEXT_OF target type: {target_type}")

        context_graph_id = self.create_graph_unique_id(
            repository, branch, context_id
        )
        target_graph_id = self.create_graph_unique_id(
            repository, branch, component_id
        )

        query = f"""
        MATCH (ctx:Context {{graph_unique_id: $context_id}})
        MATCH (t:{target_type} {{graph_unique_id: $target_id}})
        MERGE (ctx)-[:CONTEXT_OF]->(t)
        RETURN count(*) AS created
        """

        result = self.fetch_one(query, {
            "context_id": context_graph_id,
            "target_id": target_graph_id,
        })

        return result is not None and result.get("created", 0) > 0

    async def get_latest_context(
        self,
        repository: str,
        branch: str = "main",
    ) -> Optional[Context]:
        """Get the latest context entry.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            The latest Context, or None if none exist.
        """
        query = """
        MATCH (c:Context)
        WHERE c.repository = $repository AND c.branch = $branch
        RETURN c.graph_unique_id AS graph_unique_id,
               c.id AS id, c.name AS name, c.iso_date AS iso_date,
               c.agent AS agent, c.summary AS summary,
               c.observation AS observation,
               c.repository AS repository, c.branch AS branch,
               c.created_at AS created_at, c.updated_at AS updated_at
        ORDER BY c.iso_date DESC
        LIMIT 1
        """

        row = self.fetch_one(query, {"repository": repository, "branch": branch})

        if row is None:
            return None

        return self._row_to_context(row, repository, branch)

    def _row_to_context(
        self,
        row: dict[str, Any],
        repository: str,
        branch: str,
    ) -> Context:
        """Convert a database row to a Context.

        Args:
            row: The database row.
            repository: The repository name.
            branch: The branch name.

        Returns:
            The Context instance.
        """
        return Context(
            id=row["id"],
            repository=repository,
            branch=branch,
            name=row["name"],
            iso_date=row.get("iso_date"),
            agent=row.get("agent"),
            summary=row.get("summary"),
            observation=row.get("observation"),
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )
