"""Graph algorithm operations mixin for ComponentRepository.

Backed by KuzuDB's native ``algo`` extension (statically linked). Each call
projects the requested node/relationship tables, runs the native function, then
filters results to the given ``repository``/``branch`` before returning. Because
DEPENDS_ON edges never cross a repository:branch boundary, the projected graph is
a disjoint union of per-repo subgraphs, so post-filtering yields correct
per-repository results.
"""

from typing import TYPE_CHECKING, Any, Optional

from cognitive_fabric.repositories.graph_projection import projected_graph

if TYPE_CHECKING:
    from cognitive_fabric.repositories.base import BaseRepository

_DEFAULT_NODES = ["Component"]
_DEFAULT_RELS = ["DEPENDS_ON"]


class ComponentAlgorithmMixin:
    """Mixin providing native graph algorithm operations for components."""

    def _run_grouping_algo(
        self: "BaseRepository",
        algo_call: str,
        group_column: str,
        repository: str,
        branch: str,
        projected_graph_name: str,
        node_tables: Optional[list[str]],
        rel_tables: Optional[list[str]],
    ) -> list[list[str]]:
        """Run a component-grouping algo (WCC/SCC) and return id groups."""
        node_tables = node_tables or _DEFAULT_NODES
        rel_tables = rel_tables or _DEFAULT_RELS
        with projected_graph(
            self.kuzu_client, projected_graph_name, node_tables, rel_tables
        ) as g:
            query = f"""
            CALL {algo_call}('{g}')
            WITH node, {group_column} AS group_id
            WHERE node.repository = $repository AND node.branch = $branch
            RETURN group_id, collect(node.id) AS ids
            ORDER BY group_id
            """
            rows = self.fetch_all(
                query, {"repository": repository, "branch": branch}
            )
        return [sorted(row["ids"]) for row in rows if row.get("ids")]

    async def run_pagerank(
        self: "BaseRepository",
        repository: str,
        branch: str = "main",
        damping_factor: float = 0.85,
        max_iterations: int = 20,
        tolerance: float = 0.0001,
        *,
        node_tables: Optional[list[str]] = None,
        rel_tables: Optional[list[str]] = None,
        projected_graph_name: str = "pagerank",
    ) -> list[dict[str, Any]]:
        """Run native PageRank on components.

        Returns:
            List of components with their PageRank scores, highest first.
        """
        node_tables = node_tables or _DEFAULT_NODES
        rel_tables = rel_tables or _DEFAULT_RELS
        with projected_graph(
            self.kuzu_client, projected_graph_name, node_tables, rel_tables
        ) as g:
            # damping/max_iterations are numeric and coerced, so safe to inline
            # (kuzu does not accept parameters in algo named-argument position).
            query = f"""
            CALL page_rank(
                '{g}',
                dampingFactor := {float(damping_factor)},
                maxIterations := {int(max_iterations)}
            )
            WITH node, rank
            WHERE node.repository = $repository AND node.branch = $branch
            RETURN node.id AS id, node.name AS name, rank AS score
            ORDER BY rank DESC
            """
            rows = self.fetch_all(
                query, {"repository": repository, "branch": branch}
            )

        return [
            {
                "id": row["id"],
                "name": row.get("name"),
                "rank": row.get("score", 0.0),
                "raw_score": row.get("score", 0.0),
            }
            for row in rows
        ]

    async def run_k_core_decomposition(
        self: "BaseRepository",
        repository: str,
        branch: str = "main",
        k: int = 2,
        *,
        node_tables: Optional[list[str]] = None,
        rel_tables: Optional[list[str]] = None,
        projected_graph_name: str = "kcore",
    ) -> list[dict[str, Any]]:
        """Run native k-core decomposition; return components with coreness >= k."""
        node_tables = node_tables or _DEFAULT_NODES
        rel_tables = rel_tables or _DEFAULT_RELS
        with projected_graph(
            self.kuzu_client, projected_graph_name, node_tables, rel_tables
        ) as g:
            query = f"""
            CALL k_core_decomposition('{g}')
            WITH node, k_degree
            WHERE node.repository = $repository AND node.branch = $branch
              AND k_degree >= {int(k)}
            RETURN node.id AS id, node.name AS name, k_degree
            ORDER BY k_degree DESC
            """
            rows = self.fetch_all(
                query, {"repository": repository, "branch": branch}
            )

        return [
            {
                "id": row["id"],
                "name": row.get("name"),
                "k_degree": row.get("k_degree", 0),
            }
            for row in rows
        ]

    async def run_louvain_community_detection(
        self: "BaseRepository",
        repository: str,
        branch: str = "main",
        *,
        node_tables: Optional[list[str]] = None,
        rel_tables: Optional[list[str]] = None,
        projected_graph_name: str = "louvain",
    ) -> list[dict[str, Any]]:
        """Run native Louvain community detection.

        Returns:
            List of components with their community assignments.
        """
        node_tables = node_tables or _DEFAULT_NODES
        rel_tables = rel_tables or _DEFAULT_RELS
        with projected_graph(
            self.kuzu_client, projected_graph_name, node_tables, rel_tables
        ) as g:
            query = f"""
            CALL louvain('{g}')
            WITH node, louvain_id
            WHERE node.repository = $repository AND node.branch = $branch
            RETURN node.id AS id, node.name AS name, node.kind AS kind,
                   louvain_id AS community_id
            ORDER BY community_id
            """
            rows = self.fetch_all(
                query, {"repository": repository, "branch": branch}
            )

        return [
            {
                "id": row["id"],
                "name": row.get("name"),
                "kind": row.get("kind"),
                "community_id": row.get("community_id", 0),
            }
            for row in rows
        ]

    async def get_strongly_connected_components(
        self: "BaseRepository",
        repository: str,
        branch: str = "main",
        *,
        node_tables: Optional[list[str]] = None,
        rel_tables: Optional[list[str]] = None,
        projected_graph_name: str = "scc",
    ) -> list[list[str]]:
        """Find strongly connected components (circular dependencies).

        Only groups with more than one node are returned — a singleton SCC is not
        a cycle.
        """
        groups = self._run_grouping_algo(
            "strongly_connected_components",
            "group_id",
            repository,
            branch,
            projected_graph_name,
            node_tables,
            rel_tables,
        )
        return [g for g in groups if len(g) > 1]

    async def get_weakly_connected_components(
        self: "BaseRepository",
        repository: str,
        branch: str = "main",
        *,
        node_tables: Optional[list[str]] = None,
        rel_tables: Optional[list[str]] = None,
        projected_graph_name: str = "wcc",
    ) -> list[list[str]]:
        """Find weakly connected components (connectivity groups, ignoring edge
        direction)."""
        return self._run_grouping_algo(
            "weakly_connected_components",
            "group_id",
            repository,
            branch,
            projected_graph_name,
            node_tables,
            rel_tables,
        )
