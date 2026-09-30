"""Symbol repository for Symbol entity operations (Cognitive Fabric)."""

from typing import Any, Optional

from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.types.entities import Symbol, SymbolInput


class SymbolRepository(BaseRepository):
    """Repository for Symbol entity operations."""

    _RETURN = (
        "s.graph_unique_id AS graph_unique_id, s.id AS id, s.name AS name, "
        "s.kind AS kind, s.signature AS signature, s.docstring AS docstring, "
        "s.repository AS repository, s.branch AS branch, "
        "s.created_at AS created_at, s.updated_at AS updated_at"
    )

    async def find_by_id(
        self,
        repository: str,
        symbol_id: str,
        branch: str = "main",
    ) -> Optional[Symbol]:
        """Find a symbol by ID."""
        graph_id = self.create_graph_unique_id(repository, branch, symbol_id)
        query = f"""
        MATCH (s:Symbol {{graph_unique_id: $graph_id}})
        RETURN {self._RETURN}
        LIMIT 1
        """
        row = self.fetch_one(query, {"graph_id": graph_id})
        if row is None:
            return None
        return self._row_to_symbol(row, repository, branch)

    async def upsert_symbol(
        self,
        repository: str,
        input_data: SymbolInput,
    ) -> Symbol:
        """Create or update a symbol."""
        branch = input_data.branch or "main"
        graph_id = self.create_graph_unique_id(repository, branch, input_data.id)
        now = self.get_current_timestamp()

        query = """
        MERGE (s:Symbol {graph_unique_id: $graph_id})
        ON CREATE SET
            s.id = $id,
            s.name = $name,
            s.kind = $kind,
            s.signature = $signature,
            s.docstring = $docstring,
            s.repository = $repository,
            s.branch = $branch,
            s.created_at = $now,
            s.updated_at = $now
        ON MATCH SET
            s.name = $name,
            s.kind = $kind,
            s.signature = $signature,
            s.docstring = $docstring,
            s.updated_at = $now
        RETURN s.graph_unique_id AS graph_unique_id
        """
        params = {
            "graph_id": graph_id,
            "id": input_data.id,
            "name": input_data.name,
            "kind": input_data.kind or "",
            "signature": input_data.signature or "",
            "docstring": input_data.docstring or "",
            "repository": repository,
            "branch": branch,
            "now": now,
        }
        self.execute_query(query, params)

        return Symbol(
            id=input_data.id,
            repository=repository,
            branch=branch,
            name=input_data.name,
            kind=input_data.kind,
            signature=input_data.signature,
            docstring=input_data.docstring,
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
        """Create an EVOLVED_FROM edge: current symbol evolved from previous."""
        cur = self.create_graph_unique_id(repository, branch, current_id)
        prev = self.create_graph_unique_id(repository, branch, previous_id)
        query = """
        MATCH (cur:Symbol {graph_unique_id: $cur})
        MATCH (prev:Symbol {graph_unique_id: $prev})
        MERGE (cur)-[:EVOLVED_FROM]->(prev)
        RETURN count(*) AS created
        """
        result = self.fetch_one(query, {"cur": cur, "prev": prev})
        return result is not None and result.get("created", 0) > 0

    async def link_to_file(
        self,
        repository: str,
        symbol_id: str,
        file_id: str,
        branch: str = "main",
    ) -> bool:
        """Create a DEFINED_IN edge from a Symbol to a File.

        File uses `id` as its primary key (not graph_unique_id), so it is
        matched by id + repository/branch.
        """
        symbol_gid = self.create_graph_unique_id(repository, branch, symbol_id)
        query = """
        MATCH (s:Symbol {graph_unique_id: $symbol_gid})
        MATCH (f:File {id: $file_id})
        WHERE f.repository = $repository AND f.branch = $branch
        MERGE (s)-[:DEFINED_IN]->(f)
        RETURN count(*) AS created
        """
        result = self.fetch_one(query, {
            "symbol_gid": symbol_gid,
            "file_id": file_id,
            "repository": repository,
            "branch": branch,
        })
        return result is not None and result.get("created", 0) > 0

    async def delete_symbol(
        self,
        repository: str,
        symbol_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a symbol and its relationships."""
        graph_id = self.create_graph_unique_id(repository, branch, symbol_id)
        query = """
        MATCH (s:Symbol {graph_unique_id: $graph_id})
        DETACH DELETE s
        RETURN count(*) AS deleted
        """
        result = self.fetch_one(query, {"graph_id": graph_id})
        return result is not None and result.get("deleted", 0) > 0

    def _row_to_symbol(
        self,
        row: dict[str, Any],
        repository: str,
        branch: str,
    ) -> Symbol:
        return Symbol(
            id=row["id"],
            repository=repository,
            branch=branch,
            name=row["name"],
            kind=row.get("kind"),
            signature=row.get("signature"),
            docstring=row.get("docstring"),
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )
