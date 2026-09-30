"""Requirement repository for Requirement entity operations (Cognitive Fabric)."""

from typing import Any, Optional

from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.types.entities import (
    Requirement,
    RequirementInput,
    RequirementStatus,
)

# REALISED_BY targets that are permitted (whitelist for the dynamic label).
_REALISED_BY_TARGETS = {"Symbol", "Component"}


class RequirementRepository(BaseRepository):
    """Repository for Requirement entity operations."""

    _RETURN = (
        "r.graph_unique_id AS graph_unique_id, r.id AS id, r.name AS name, "
        "r.description AS description, r.priority AS priority, r.status AS status, "
        "r.repository AS repository, r.branch AS branch, "
        "r.created_at AS created_at, r.updated_at AS updated_at"
    )

    async def find_by_id(
        self,
        repository: str,
        requirement_id: str,
        branch: str = "main",
    ) -> Optional[Requirement]:
        """Find a requirement by ID."""
        graph_id = self.create_graph_unique_id(repository, branch, requirement_id)
        query = f"""
        MATCH (r:Requirement {{graph_unique_id: $graph_id}})
        RETURN {self._RETURN}
        LIMIT 1
        """
        row = self.fetch_one(query, {"graph_id": graph_id})
        if row is None:
            return None
        return self._row_to_requirement(row, repository, branch)

    async def upsert_requirement(
        self,
        repository: str,
        input_data: RequirementInput,
    ) -> Requirement:
        """Create or update a requirement."""
        branch = input_data.branch or "main"
        graph_id = self.create_graph_unique_id(repository, branch, input_data.id)
        now = self.get_current_timestamp()

        query = """
        MERGE (r:Requirement {graph_unique_id: $graph_id})
        ON CREATE SET
            r.id = $id,
            r.name = $name,
            r.description = $description,
            r.priority = $priority,
            r.status = $status,
            r.repository = $repository,
            r.branch = $branch,
            r.created_at = $now,
            r.updated_at = $now
        ON MATCH SET
            r.name = $name,
            r.description = $description,
            r.priority = $priority,
            r.status = $status,
            r.updated_at = $now
        RETURN r.graph_unique_id AS graph_unique_id
        """
        params = {
            "graph_id": graph_id,
            "id": input_data.id,
            "name": input_data.name,
            "description": input_data.description or "",
            "priority": input_data.priority or "",
            "status": (input_data.status or RequirementStatus.ACTIVE).value,
            "repository": repository,
            "branch": branch,
            "now": now,
        }
        self.execute_query(query, params)

        return Requirement(
            id=input_data.id,
            repository=repository,
            branch=branch,
            name=input_data.name,
            description=input_data.description,
            priority=input_data.priority,
            status=input_data.status or RequirementStatus.ACTIVE,
            created_at=now,
            updated_at=now,
        )

    async def link_evolution(
        self,
        repository: str,
        current_id: str,
        previous_id: str,
        branch: str = "main",
    ) -> bool:
        """Create an EVOLVED_FROM edge between two requirements."""
        cur = self.create_graph_unique_id(repository, branch, current_id)
        prev = self.create_graph_unique_id(repository, branch, previous_id)
        query = """
        MATCH (cur:Requirement {graph_unique_id: $cur})
        MATCH (prev:Requirement {graph_unique_id: $prev})
        MERGE (cur)-[:EVOLVED_FROM]->(prev)
        RETURN count(*) AS created
        """
        result = self.fetch_one(query, {"cur": cur, "prev": prev})
        return result is not None and result.get("created", 0) > 0

    async def link_realised_by(
        self,
        repository: str,
        requirement_id: str,
        target_id: str,
        target_type: str = "Symbol",
        branch: str = "main",
    ) -> bool:
        """Create a REALISED_BY edge from a Requirement to a Symbol/Component."""
        if target_type not in _REALISED_BY_TARGETS:
            raise ValueError(
                f"REALISED_BY target must be one of {_REALISED_BY_TARGETS}, "
                f"got {target_type!r}"
            )
        req_gid = self.create_graph_unique_id(repository, branch, requirement_id)
        tgt_gid = self.create_graph_unique_id(repository, branch, target_id)
        query = f"""
        MATCH (r:Requirement {{graph_unique_id: $req}})
        MATCH (t:{target_type} {{graph_unique_id: $tgt}})
        MERGE (r)-[:REALISED_BY]->(t)
        RETURN count(*) AS created
        """
        result = self.fetch_one(query, {"req": req_gid, "tgt": tgt_gid})
        return result is not None and result.get("created", 0) > 0

    async def delete_requirement(
        self,
        repository: str,
        requirement_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a requirement and its relationships."""
        graph_id = self.create_graph_unique_id(repository, branch, requirement_id)
        query = """
        MATCH (r:Requirement {graph_unique_id: $graph_id})
        DETACH DELETE r
        RETURN count(*) AS deleted
        """
        result = self.fetch_one(query, {"graph_id": graph_id})
        return result is not None and result.get("deleted", 0) > 0

    def _row_to_requirement(
        self,
        row: dict[str, Any],
        repository: str,
        branch: str,
    ) -> Requirement:
        status_str = row.get("status")
        status = None
        if status_str:
            try:
                status = RequirementStatus(status_str)
            except ValueError:
                status = RequirementStatus.ACTIVE

        return Requirement(
            id=row["id"],
            repository=repository,
            branch=branch,
            name=row["name"],
            description=row.get("description"),
            priority=row.get("priority"),
            status=status,
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )
