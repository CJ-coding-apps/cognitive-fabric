"""Trace repository for Trace entity operations (Cognitive Fabric)."""

from typing import Any, Optional

from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.types.entities import Trace, TraceInput


class TraceRepository(BaseRepository):
    """Repository for Trace entity operations."""

    _RETURN = (
        "t.graph_unique_id AS graph_unique_id, t.id AS id, t.name AS name, "
        "t.trace_type AS trace_type, t.content AS content, "
        "t.repository AS repository, t.branch AS branch, "
        "t.created_at AS created_at, t.updated_at AS updated_at"
    )

    async def find_by_id(
        self,
        repository: str,
        trace_id: str,
        branch: str = "main",
    ) -> Optional[Trace]:
        """Find a trace by ID."""
        graph_id = self.create_graph_unique_id(repository, branch, trace_id)
        query = f"""
        MATCH (t:Trace {{graph_unique_id: $graph_id}})
        RETURN {self._RETURN}
        LIMIT 1
        """
        row = self.fetch_one(query, {"graph_id": graph_id})
        if row is None:
            return None
        return self._row_to_trace(row, repository, branch)

    async def upsert_trace(
        self,
        repository: str,
        input_data: TraceInput,
    ) -> Trace:
        """Create or update a trace."""
        branch = input_data.branch or "main"
        graph_id = self.create_graph_unique_id(repository, branch, input_data.id)
        now = self.get_current_timestamp()

        query = """
        MERGE (t:Trace {graph_unique_id: $graph_id})
        ON CREATE SET
            t.id = $id,
            t.name = $name,
            t.trace_type = $trace_type,
            t.content = $content,
            t.repository = $repository,
            t.branch = $branch,
            t.created_at = $now,
            t.updated_at = $now
        ON MATCH SET
            t.name = $name,
            t.trace_type = $trace_type,
            t.content = $content,
            t.updated_at = $now
        RETURN t.graph_unique_id AS graph_unique_id
        """
        params = {
            "graph_id": graph_id,
            "id": input_data.id,
            "name": input_data.name,
            "trace_type": input_data.trace_type or "",
            "content": input_data.content or "",
            "repository": repository,
            "branch": branch,
            "now": now,
        }
        self.execute_query(query, params)

        return Trace(
            id=input_data.id,
            repository=repository,
            branch=branch,
            name=input_data.name,
            trace_type=input_data.trace_type,
            content=input_data.content,
            created_at=now,
            updated_at=now,
        )

    async def link_to_symbol(
        self,
        repository: str,
        trace_id: str,
        symbol_id: str,
        branch: str = "main",
    ) -> bool:
        """Create a RECORDS edge from a Trace to a Symbol."""
        trace_gid = self.create_graph_unique_id(repository, branch, trace_id)
        symbol_gid = self.create_graph_unique_id(repository, branch, symbol_id)
        query = """
        MATCH (t:Trace {graph_unique_id: $trace_gid})
        MATCH (s:Symbol {graph_unique_id: $symbol_gid})
        MERGE (t)-[:RECORDS]->(s)
        RETURN count(*) AS created
        """
        result = self.fetch_one(
            query, {"trace_gid": trace_gid, "symbol_gid": symbol_gid}
        )
        return result is not None and result.get("created", 0) > 0

    async def delete_trace(
        self,
        repository: str,
        trace_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a trace and its relationships."""
        graph_id = self.create_graph_unique_id(repository, branch, trace_id)
        query = """
        MATCH (t:Trace {graph_unique_id: $graph_id})
        DETACH DELETE t
        RETURN count(*) AS deleted
        """
        result = self.fetch_one(query, {"graph_id": graph_id})
        return result is not None and result.get("deleted", 0) > 0

    def _row_to_trace(
        self,
        row: dict[str, Any],
        repository: str,
        branch: str,
    ) -> Trace:
        return Trace(
            id=row["id"],
            repository=repository,
            branch=branch,
            name=row["name"],
            trace_type=row.get("trace_type"),
            content=row.get("content"),
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )
