"""Graph analysis service for graph algorithms and pattern detection."""

from typing import TYPE_CHECKING, Any, Optional

import structlog

if TYPE_CHECKING:
    from cognitive_fabric.services.service_container import ServiceContainer

logger = structlog.get_logger(__name__)


class GraphAnalysisService:
    """Service for graph analysis operations."""

    def __init__(self, container: "ServiceContainer") -> None:
        """Initialize the graph analysis service.

        Args:
            container: The service container for dependency injection.
        """
        self._container = container

    async def run_pagerank(
        self,
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
        """Run PageRank analysis on components.

        Args:
            repository: The repository name.
            branch: The branch name.
            damping_factor: PageRank damping factor.
            max_iterations: Maximum iterations.
            tolerance: Convergence tolerance.
            node_tables: Node tables to project (default ["Component"]).
            rel_tables: Relationship tables to project (default ["DEPENDS_ON"]).
            projected_graph_name: Name for the temporary projected graph.

        Returns:
            List of components with PageRank scores.
        """
        logger.debug(
            "Running PageRank",
            repository=repository,
            branch=branch,
        )

        component_repo = await self._container.get_component_repository()
        return await component_repo.run_pagerank(
            repository,
            branch,
            damping_factor,
            max_iterations,
            tolerance,
            node_tables=node_tables,
            rel_tables=rel_tables,
            projected_graph_name=projected_graph_name,
        )

    async def run_k_core(
        self,
        repository: str,
        k: int = 2,
        branch: str = "main",
        *,
        node_tables: Optional[list[str]] = None,
        rel_tables: Optional[list[str]] = None,
        projected_graph_name: str = "kcore",
    ) -> list[dict[str, Any]]:
        """Run k-core decomposition on components.

        Args:
            repository: The repository name.
            k: The k value for k-core (minimum degree).
            branch: The branch name.
            node_tables: Node tables to project (default ["Component"]).
            rel_tables: Relationship tables to project (default ["DEPENDS_ON"]).
            projected_graph_name: Name for the temporary projected graph.

        Returns:
            List of components in the k-core.
        """
        logger.debug(
            "Running k-core decomposition",
            repository=repository,
            branch=branch,
            k=k,
        )

        component_repo = await self._container.get_component_repository()
        return await component_repo.run_k_core_decomposition(
            repository,
            branch,
            k,
            node_tables=node_tables,
            rel_tables=rel_tables,
            projected_graph_name=projected_graph_name,
        )

    async def run_louvain(
        self,
        repository: str,
        branch: str = "main",
        *,
        node_tables: Optional[list[str]] = None,
        rel_tables: Optional[list[str]] = None,
        projected_graph_name: str = "louvain",
    ) -> list[dict[str, Any]]:
        """Run Louvain community detection on components.

        Args:
            repository: The repository name.
            branch: The branch name.
            node_tables: Node tables to project (default ["Component"]).
            rel_tables: Relationship tables to project (default ["DEPENDS_ON"]).
            projected_graph_name: Name for the temporary projected graph.

        Returns:
            List of components with community assignments.
        """
        logger.debug(
            "Running Louvain community detection",
            repository=repository,
            branch=branch,
        )

        component_repo = await self._container.get_component_repository()
        return await component_repo.run_louvain_community_detection(
            repository,
            branch,
            node_tables=node_tables,
            rel_tables=rel_tables,
            projected_graph_name=projected_graph_name,
        )

    async def find_shortest_path(
        self,
        repository: str,
        start_id: str,
        end_id: str,
        branch: str = "main",
        max_depth: int = 10,
    ) -> Optional[dict[str, Any]]:
        """Find shortest path between components.

        Args:
            repository: The repository name.
            start_id: The starting component ID.
            end_id: The ending component ID.
            branch: The branch name.
            max_depth: Maximum path depth.

        Returns:
            Path information, or None if no path exists.
        """
        logger.debug(
            "Finding shortest path",
            repository=repository,
            start_id=start_id,
            end_id=end_id,
        )

        component_repo = await self._container.get_component_repository()
        return await component_repo.find_shortest_path(
            repository, start_id, end_id, branch, max_depth
        )

    async def detect_cycles(
        self,
        repository: str,
        branch: str = "main",
        *,
        node_tables: Optional[list[str]] = None,
        rel_tables: Optional[list[str]] = None,
        projected_graph_name: str = "cycles",
    ) -> list[list[str]]:
        """Detect cycles in the dependency graph.

        Args:
            repository: The repository name.
            branch: The branch name.
            node_tables: Node tables to project (default ["Component"]).
            rel_tables: Relationship tables to project (default ["DEPENDS_ON"]).
            projected_graph_name: Name for the temporary projected graph.

        Returns:
            List of cycle groups (component ID lists).
        """
        logger.debug(
            "Detecting cycles",
            repository=repository,
            branch=branch,
        )

        component_repo = await self._container.get_component_repository()
        return await component_repo.get_strongly_connected_components(
            repository,
            branch,
            node_tables=node_tables,
            rel_tables=rel_tables,
            projected_graph_name=projected_graph_name,
        )

    async def detect_islands(
        self,
        repository: str,
        branch: str = "main",
        *,
        node_tables: Optional[list[str]] = None,
        rel_tables: Optional[list[str]] = None,
        projected_graph_name: str = "islands",
    ) -> list[list[str]]:
        """Detect disconnected islands in the graph.

        Islands are weakly connected components with more than one node
        that are isolated from the main graph.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of island groups (component ID lists).
        """
        logger.debug(
            "Detecting islands",
            repository=repository,
            branch=branch,
        )

        component_repo = await self._container.get_component_repository()
        connected = await component_repo.get_weakly_connected_components(
            repository,
            branch,
            node_tables=node_tables,
            rel_tables=rel_tables,
            projected_graph_name=projected_graph_name,
        )

        # Filter to only include groups with more than one node (actual islands)
        # and exclude the largest group (main component)
        if not connected:
            return []

        # Sort by size, largest first
        sorted_groups = sorted(connected, key=len, reverse=True)

        # Return all groups except the largest (main graph)
        # Only include groups with 2+ nodes
        islands = [group for group in sorted_groups[1:] if len(group) >= 1]

        return islands

    async def get_strongly_connected(
        self,
        repository: str,
        branch: str = "main",
        *,
        node_tables: Optional[list[str]] = None,
        rel_tables: Optional[list[str]] = None,
        projected_graph_name: str = "scc",
    ) -> list[list[str]]:
        """Get strongly connected components.

        These are groups of components where every component is reachable
        from every other component in the group (circular dependencies).

        Args:
            repository: The repository name.
            branch: The branch name.
            node_tables: Node tables to project (default ["Component"]).
            rel_tables: Relationship tables to project (default ["DEPENDS_ON"]).
            projected_graph_name: Name for the temporary projected graph.

        Returns:
            List of strongly connected component groups.
        """
        logger.debug(
            "Getting strongly connected components",
            repository=repository,
            branch=branch,
        )

        component_repo = await self._container.get_component_repository()
        return await component_repo.get_strongly_connected_components(
            repository,
            branch,
            node_tables=node_tables,
            rel_tables=rel_tables,
            projected_graph_name=projected_graph_name,
        )

    async def get_weakly_connected(
        self,
        repository: str,
        branch: str = "main",
        *,
        node_tables: Optional[list[str]] = None,
        rel_tables: Optional[list[str]] = None,
        projected_graph_name: str = "wcc",
    ) -> list[list[str]]:
        """Get weakly connected components.

        These are groups of components that are connected when ignoring
        edge direction.

        Args:
            repository: The repository name.
            branch: The branch name.
            node_tables: Node tables to project (default ["Component"]).
            rel_tables: Relationship tables to project (default ["DEPENDS_ON"]).
            projected_graph_name: Name for the temporary projected graph.

        Returns:
            List of weakly connected component groups.
        """
        logger.debug(
            "Getting weakly connected components",
            repository=repository,
            branch=branch,
        )

        component_repo = await self._container.get_component_repository()
        return await component_repo.get_weakly_connected_components(
            repository,
            branch,
            node_tables=node_tables,
            rel_tables=rel_tables,
            projected_graph_name=projected_graph_name,
        )

    async def get_graph_statistics(
        self,
        repository: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Get comprehensive graph statistics.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            Dictionary with graph statistics.
        """
        component_repo = await self._container.get_component_repository()

        # Get all components
        components = await component_repo.get_all_components(repository, branch)
        total_components = len(components)

        # Get weakly connected components for island detection
        weak_connected = await component_repo.get_weakly_connected_components(
            repository, branch
        )

        # Get strongly connected components for cycle detection
        strong_connected = await component_repo.get_strongly_connected_components(
            repository, branch
        )

        # Calculate statistics
        num_islands = len(weak_connected) if weak_connected else 0
        num_cycles = len(strong_connected) if strong_connected else 0

        # Estimate edge count (dependencies)
        total_edges = sum(
            len(c.depends_on) if c.depends_on else 0
            for c in components
        )

        # Calculate density
        max_edges = (
            total_components * (total_components - 1)
            if total_components > 1
            else 1
        )
        density = total_edges / max_edges if max_edges > 0 else 0

        return {
            "repository": repository,
            "branch": branch,
            "total_components": total_components,
            "total_dependencies": total_edges,
            "num_weakly_connected": num_islands,
            "num_strongly_connected": num_cycles,
            "graph_density": round(density, 4),
            "has_cycles": num_cycles > 0,
            "is_connected": num_islands <= 1,
        }

    async def find_central_components(
        self,
        repository: str,
        branch: str = "main",
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """Find the most central components using PageRank.

        Args:
            repository: The repository name.
            branch: The branch name.
            limit: Maximum number of components to return.

        Returns:
            List of central components with their scores.
        """
        pagerank_results = await self.run_pagerank(repository, branch)
        return pagerank_results[:limit]

    async def find_hub_components(
        self,
        repository: str,
        branch: str = "main",
        min_connections: int = 3,
    ) -> list[dict[str, Any]]:
        """Find hub components (components with many connections).

        Args:
            repository: The repository name.
            branch: The branch name.
            min_connections: Minimum number of connections to be a hub.

        Returns:
            List of hub components with connection counts.
        """
        k_core_results = await self.run_k_core(repository, min_connections, branch)
        return k_core_results
