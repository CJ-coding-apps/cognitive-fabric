"""Memory context builder for optimization agents."""

from typing import Any, Dict

import structlog

from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)


class MemoryContextBuilder:
    """Builds context information for memory optimization."""

    def __init__(self, memory_service: MemoryService) -> None:
        """Initialize the context builder.

        Args:
            memory_service: The memory service instance.
        """
        self._memory_service = memory_service

    async def build_analysis_context(
        self,
        repository: str,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """Build context for memory analysis.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            Analysis context dictionary.
        """
        # Get statistics
        stats = await self._memory_service.get_statistics(repository, branch)

        # Get graph analysis
        graph_analysis = await self._memory_service.graph_analysis

        # Detect patterns
        cycles = await graph_analysis.detect_cycles(repository, branch)
        islands = await graph_analysis.detect_islands(repository, branch)
        strongly_connected = await graph_analysis.get_strongly_connected(
            repository, branch
        )

        # Get PageRank for importance
        pagerank = await graph_analysis.run_pagerank(repository, branch)

        # Get entity service for detailed info
        entity_service = await self._memory_service.entity

        # Get components
        components = await entity_service.get_all_components(repository, branch)

        # Categorize components by status
        active_components = [
            c for c in components if c.status and c.status.value == "active"
        ]
        deprecated_components = [
            c for c in components if c.status and c.status.value == "deprecated"
        ]
        planned_components = [
            c for c in components if c.status and c.status.value == "planned"
        ]

        # Get rules and decisions
        rules = await entity_service.get_all_rules(repository, branch)
        decisions = await entity_service.get_all_decisions(repository, branch)
        tags = await entity_service.get_all_tags(repository, branch)

        return {
            "repository": repository,
            "branch": branch,
            "statistics": stats,
            "patterns": {
                "cycles": len(cycles),
                "cycle_details": cycles[:5],  # Limit for context size
                "islands": len(islands),
                "island_details": islands[:5],
                "strongly_connected": len(strongly_connected),
            },
            "components": {
                "total": len(components),
                "active": len(active_components),
                "deprecated": len(deprecated_components),
                "planned": len(planned_components),
                "top_by_pagerank": pagerank[:10],
            },
            "governance": {
                "rules_count": len(rules),
                "active_rules": len(
                    [r for r in rules if r.status and r.status.value == "active"]
                ),
                "decisions_count": len(decisions),
            },
            "tags": {
                "total": len(tags),
            },
        }

    async def build_optimization_context(
        self,
        repository: str,
        branch: str = "main",
        strategy: str = "balanced",
    ) -> Dict[str, Any]:
        """Build context for optimization planning.

        Args:
            repository: The repository name.
            branch: The branch name.
            strategy: The optimization strategy.

        Returns:
            Optimization context dictionary.
        """
        # Get analysis context first
        analysis = await self.build_analysis_context(repository, branch)

        # Get detailed component information for candidates
        entity_service = await self._memory_service.entity
        components = await entity_service.get_all_components(repository, branch)

        # Build optimization candidates
        candidates = []

        for component in components:
            candidate = {
                "id": component.id,
                "name": component.name,
                "kind": component.kind,
                "status": component.status.value if component.status else None,
                "depends_on": component.depends_on or [],
                "reasons": [],
            }

            # Check if deprecated
            if component.status and component.status.value == "deprecated":
                candidate["reasons"].append("deprecated_status")

            # Check if orphaned (no dependencies and no dependents)
            container = await self._memory_service.get_service_container()
            comp_repo = await container.get_component_repository()
            dependents = await comp_repo.get_dependents(
                repository, component.id, branch
            )

            if not component.depends_on and not dependents:
                candidate["reasons"].append("orphaned")

            if candidate["reasons"]:
                candidates.append(candidate)

        # Get orphaned tags
        tag_repo = await container.get_tag_repository()
        tag_stats = await tag_repo.get_tag_usage_stats(repository, branch)
        orphaned_tags = [t for t in tag_stats if t["usage_count"] == 0]

        return {
            **analysis,
            "strategy": strategy,
            "optimization_candidates": {
                "components": candidates,
                "orphaned_tags": orphaned_tags,
            },
            "strategy_config": self._get_strategy_config(strategy),
        }

    def _get_strategy_config(self, strategy: str) -> Dict[str, Any]:
        """Get configuration for the optimization strategy.

        Args:
            strategy: The strategy name.

        Returns:
            Strategy configuration.
        """
        configs = {
            "conservative": {
                "delete_deprecated": True,
                "require_no_dependents": True,
                "delete_orphaned_tags": False,
                "max_deletions": 10,
                "stale_days_threshold": 90,
            },
            "balanced": {
                "delete_deprecated": True,
                "require_no_dependents": False,
                "delete_orphaned_tags": True,
                "max_deletions": 50,
                "stale_days_threshold": 60,
            },
            "aggressive": {
                "delete_deprecated": True,
                "require_no_dependents": False,
                "delete_orphaned_tags": True,
                "max_deletions": 100,
                "stale_days_threshold": 30,
            },
        }
        return configs.get(strategy, configs["balanced"])

    async def get_component_details(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """Get detailed information about a component.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            Component details dictionary.
        """
        container = await self._memory_service.get_service_container()
        comp_repo = await container.get_component_repository()

        component = await comp_repo.find_by_id(repository, component_id, branch)
        if not component:
            return {"error": f"Component not found: {component_id}"}

        dependencies = await comp_repo.get_dependencies(
            repository, component_id, branch
        )
        dependents = await comp_repo.get_dependents(repository, component_id, branch)

        # Get related rules and decisions
        rule_repo = await container.get_rule_repository()
        decision_repo = await container.get_decision_repository()

        governing_rules = await rule_repo.get_rules_governing_component(
            repository, component_id, branch
        )
        affecting_decisions = await decision_repo.get_decisions_affecting_component(
            repository, component_id, branch
        )

        return {
            "component": component.model_dump(mode="json"),
            "dependencies": [{"id": d.id, "name": d.name} for d in dependencies],
            "dependents": [{"id": d.id, "name": d.name} for d in dependents],
            "governing_rules": [{"id": r.id, "name": r.name} for r in governing_rules],
            "affecting_decisions": [
                {"id": d.id, "name": d.name} for d in affecting_decisions
            ],
        }
