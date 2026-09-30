"""Decision repository for Decision entity operations."""

from typing import Any, Optional

from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.types.entities import Decision, DecisionInput, DecisionStatus


class DecisionRepository(BaseRepository):
    """Repository for Decision entity operations."""

    async def find_by_id(
        self,
        repository: str,
        decision_id: str,
        branch: str = "main",
    ) -> Optional[Decision]:
        """Find a decision by ID.

        Args:
            repository: The repository name.
            decision_id: The decision ID.
            branch: The branch name.

        Returns:
            The Decision if found, None otherwise.
        """
        graph_id = self.create_graph_unique_id(repository, branch, decision_id)

        query = """
        MATCH (d:Decision {graph_unique_id: $graph_id})
        RETURN d.graph_unique_id AS graph_unique_id,
               d.id AS id, d.name AS name, d.context AS context,
               d.date AS date, d.status AS status,
               d.rationale AS rationale, d.impact AS impact, d.tags AS tags,
               d.repository AS repository, d.branch AS branch,
               d.created_at AS created_at, d.updated_at AS updated_at
        LIMIT 1
        """

        row = self.fetch_one(query, {"graph_id": graph_id})

        if row is None:
            return None

        return self._row_to_decision(row, repository, branch)

    async def get_all_decisions(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[Decision]:
        """Get all decisions.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all decisions.
        """
        query = """
        MATCH (d:Decision)
        WHERE d.repository = $repository AND d.branch = $branch
        RETURN d.graph_unique_id AS graph_unique_id,
               d.id AS id, d.name AS name, d.context AS context,
               d.date AS date, d.status AS status,
               d.rationale AS rationale, d.impact AS impact, d.tags AS tags,
               d.repository AS repository, d.branch AS branch,
               d.created_at AS created_at, d.updated_at AS updated_at
        ORDER BY d.date DESC
        """

        rows = self.fetch_all(query, {"repository": repository, "branch": branch})
        return [self._row_to_decision(row, repository, branch) for row in rows]

    async def get_decisions_by_status(
        self,
        repository: str,
        status: DecisionStatus,
        branch: str = "main",
    ) -> list[Decision]:
        """Get decisions by status.

        Args:
            repository: The repository name.
            status: The decision status to filter by.
            branch: The branch name.

        Returns:
            List of decisions with the given status.
        """
        query = """
        MATCH (d:Decision)
        WHERE d.repository = $repository
          AND d.branch = $branch
          AND d.status = $status
        RETURN d.graph_unique_id AS graph_unique_id,
               d.id AS id, d.name AS name, d.context AS context,
               d.date AS date, d.status AS status,
               d.rationale AS rationale, d.impact AS impact, d.tags AS tags,
               d.repository AS repository, d.branch AS branch,
               d.created_at AS created_at, d.updated_at AS updated_at
        ORDER BY d.date DESC
        """

        rows = self.fetch_all(query, {
            "repository": repository,
            "branch": branch,
            "status": status.value,
        })
        return [self._row_to_decision(row, repository, branch) for row in rows]

    async def upsert_decision(
        self,
        repository: str,
        input_data: DecisionInput,
    ) -> Decision:
        """Create or update a decision.

        Args:
            repository: The repository name.
            input_data: The decision input data.

        Returns:
            The upserted Decision.
        """
        branch = input_data.branch or "main"
        graph_id = self.create_graph_unique_id(repository, branch, input_data.id)
        now = self.get_current_timestamp()

        query = """
        MERGE (d:Decision {graph_unique_id: $graph_id})
        ON CREATE SET
            d.id = $id,
            d.name = $name,
            d.context = $context,
            d.date = $date,
            d.status = $status,
            d.rationale = $rationale,
            d.impact = $impact,
            d.tags = $tags,
            d.repository = $repository,
            d.branch = $branch,
            d.created_at = $now,
            d.updated_at = $now
        ON MATCH SET
            d.name = $name,
            d.context = $context,
            d.date = $date,
            d.status = $status,
            d.rationale = $rationale,
            d.impact = $impact,
            d.tags = $tags,
            d.updated_at = $now
        RETURN d.graph_unique_id AS graph_unique_id
        """

        params = {
            "graph_id": graph_id,
            "id": input_data.id,
            "name": input_data.name,
            "context": input_data.context or "",
            "date": input_data.date or now.date().isoformat(),
            "status": (input_data.status or DecisionStatus.PROPOSED).value,
            "rationale": input_data.rationale or "",
            "impact": input_data.impact or [],
            "tags": input_data.tags or [],
            "repository": repository,
            "branch": branch,
            "now": now,
        }

        self.execute_query(query, params)

        return Decision(
            id=input_data.id,
            repository=repository,
            branch=branch,
            name=input_data.name,
            context=input_data.context,
            date=input_data.date or now.date().isoformat(),
            status=input_data.status or DecisionStatus.PROPOSED,
            rationale=input_data.rationale,
            impact=input_data.impact,
            tags=input_data.tags,
            created_at=now,
            updated_at=now,
        )

    async def update_decision_status(
        self,
        repository: str,
        decision_id: str,
        branch: str,
        status: DecisionStatus,
    ) -> Optional[Decision]:
        """Update a decision's status.

        Args:
            repository: The repository name.
            decision_id: The decision ID.
            branch: The branch name.
            status: The new status.

        Returns:
            The updated Decision, or None if not found.
        """
        graph_id = self.create_graph_unique_id(repository, branch, decision_id)
        now = self.get_current_timestamp()

        query = """
        MATCH (d:Decision {graph_unique_id: $graph_id})
        SET d.status = $status, d.updated_at = $now
        RETURN d.graph_unique_id AS graph_unique_id,
               d.id AS id, d.name AS name, d.context AS context,
               d.date AS date, d.status AS status,
               d.rationale AS rationale, d.impact AS impact, d.tags AS tags,
               d.repository AS repository, d.branch AS branch,
               d.created_at AS created_at, d.updated_at AS updated_at
        """

        row = self.fetch_one(query, {
            "graph_id": graph_id,
            "status": status.value,
            "now": now,
        })

        if row is None:
            return None

        return self._row_to_decision(row, repository, branch)

    async def delete_decision(
        self,
        repository: str,
        decision_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a decision and its relationships.

        Args:
            repository: The repository name.
            decision_id: The decision ID.
            branch: The branch name.

        Returns:
            True if deleted, False if not found.
        """
        graph_id = self.create_graph_unique_id(repository, branch, decision_id)

        query = """
        MATCH (d:Decision {graph_unique_id: $graph_id})
        DETACH DELETE d
        RETURN count(*) AS deleted
        """

        result = self.fetch_one(query, {"graph_id": graph_id})
        return result is not None and result.get("deleted", 0) > 0

    async def get_decisions_affecting_component(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> list[Decision]:
        """Get decisions that affect a specific component.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            List of decisions affecting the component.
        """
        component_graph_id = self.create_graph_unique_id(
            repository, branch, component_id
        )

        query = """
        MATCH (d:Decision)-[:AFFECTS]->(c:Component {graph_unique_id: $component_id})
        WHERE d.branch = $branch
        RETURN d.graph_unique_id AS graph_unique_id,
               d.id AS id, d.name AS name, d.context AS context,
               d.date AS date, d.status AS status,
               d.rationale AS rationale, d.impact AS impact, d.tags AS tags,
               d.repository AS repository, d.branch AS branch,
               d.created_at AS created_at, d.updated_at AS updated_at
        ORDER BY d.date DESC
        """

        rows = self.fetch_all(query, {
            "component_id": component_graph_id,
            "branch": branch,
        })
        return [self._row_to_decision(row, repository, branch) for row in rows]

    async def create_affects_relationship(
        self,
        repository: str,
        decision_id: str,
        component_id: str,
        branch: str = "main",
    ) -> bool:
        """Create an AFFECTS relationship between a decision and a component.

        Args:
            repository: The repository name.
            decision_id: The decision ID.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            True if created, False otherwise.
        """
        decision_graph_id = self.create_graph_unique_id(
            repository, branch, decision_id
        )
        component_graph_id = self.create_graph_unique_id(
            repository, branch, component_id
        )

        query = """
        MATCH (d:Decision {graph_unique_id: $decision_id})
        MATCH (c:Component {graph_unique_id: $component_id})
        MERGE (d)-[:AFFECTS]->(c)
        RETURN count(*) AS created
        """

        result = self.fetch_one(query, {
            "decision_id": decision_graph_id,
            "component_id": component_graph_id,
        })

        return result is not None and result.get("created", 0) > 0

    def _row_to_decision(
        self,
        row: dict[str, Any],
        repository: str,
        branch: str,
    ) -> Decision:
        """Convert a database row to a Decision.

        Args:
            row: The database row.
            repository: The repository name.
            branch: The branch name.

        Returns:
            The Decision instance.
        """
        status_str = row.get("status")
        status = None
        if status_str:
            try:
                status = DecisionStatus(status_str)
            except ValueError:
                status = DecisionStatus.PROPOSED

        return Decision(
            id=row["id"],
            repository=repository,
            branch=branch,
            name=row["name"],
            context=row.get("context"),
            date=row.get("date"),
            status=status,
            rationale=row.get("rationale"),
            impact=row.get("impact"),
            tags=row.get("tags"),
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )
