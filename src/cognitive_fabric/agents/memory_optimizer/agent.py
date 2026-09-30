"""Memory Optimization Agent - Main orchestrator."""

from typing import Any, Dict, List, Optional

import structlog

from cognitive_fabric.agents.memory_optimizer.base import BaseMemoryAgent
from cognitive_fabric.agents.memory_optimizer.context_builder import (
    MemoryContextBuilder,
)
from cognitive_fabric.agents.memory_optimizer.prompt_manager import PromptManager
from cognitive_fabric.agents.memory_optimizer.services.analysis import (
    MemoryAnalysisService,
)
from cognitive_fabric.agents.memory_optimizer.services.execution import (
    OptimizationExecutionService,
)
from cognitive_fabric.agents.memory_optimizer.services.planning import (
    OptimizationPlanService,
)
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.services.snapshot_service import SnapshotService
from cognitive_fabric.types.optimization import (
    AgentAnalysisResult as AnalysisResult,
)
from cognitive_fabric.types.optimization import (
    AgentOptimizationPlan as OptimizationPlan,
)
from cognitive_fabric.types.optimization import (
    ExecutionResult,
    OptimizationStrategy,
)

logger = structlog.get_logger(__name__)


class MemoryOptimizationAgent(BaseMemoryAgent):
    """Agent for optimizing memory banks.

    This agent orchestrates the analysis, planning, and execution of
    memory bank optimizations. It can work with or without LLM enhancement.
    """

    def __init__(
        self,
        memory_service: MemoryService,
        snapshot_service: Optional[SnapshotService] = None,
        llm_client: Optional[Any] = None,
    ) -> None:
        """Initialize the memory optimization agent.

        Args:
            memory_service: The memory service instance.
            snapshot_service: Optional snapshot service for rollback support.
            llm_client: Optional LLM client for enhanced analysis.
        """
        super().__init__(memory_service)
        self._llm_client = llm_client

        # Create snapshot service if not provided
        if snapshot_service is None:
            self._snapshot_service = SnapshotService(memory_service)
        else:
            self._snapshot_service = snapshot_service

        # Initialize components
        self._context_builder = MemoryContextBuilder(memory_service)
        self._prompt_manager = PromptManager()

        # Initialize services
        self._analysis_service = MemoryAnalysisService(
            memory_service,
            self._context_builder,
            self._prompt_manager,
        )
        self._planning_service = OptimizationPlanService(
            memory_service,
            self._context_builder,
            self._prompt_manager,
        )
        self._execution_service = OptimizationExecutionService(
            memory_service,
            self._snapshot_service,
        )

    @property
    def name(self) -> str:
        """Get the agent name."""
        return "memory-optimizer"

    @property
    def description(self) -> str:
        """Get the agent description."""
        return (
            "Analyzes and optimizes memory banks by identifying and removing "
            "redundant, deprecated, or orphaned entities."
        )

    async def analyze(
        self,
        repository: str,
        branch: str = "main",
        use_llm: bool = False,
    ) -> AnalysisResult:
        """Analyze a memory bank for optimization opportunities.

        Args:
            repository: The repository name.
            branch: The branch name.
            use_llm: Whether to use LLM for enhanced analysis.

        Returns:
            Analysis results.
        """
        logger.info(
            "Starting memory analysis",
            repository=repository,
            branch=branch,
            use_llm=use_llm,
        )

        return await self._analysis_service.analyze(
            repository,
            branch,
            use_llm=use_llm and self._llm_client is not None,
            llm_client=self._llm_client,
        )

    async def plan(
        self,
        repository: str,
        branch: str = "main",
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
        use_llm: bool = False,
    ) -> OptimizationPlan:
        """Create an optimization plan for a memory bank.

        Args:
            repository: The repository name.
            branch: The branch name.
            strategy: The optimization strategy.
            use_llm: Whether to use LLM for enhanced planning.

        Returns:
            The optimization plan.
        """
        logger.info(
            "Creating optimization plan",
            repository=repository,
            branch=branch,
            strategy=strategy.value,
            use_llm=use_llm,
        )

        return await self._planning_service.create_plan(
            repository,
            branch,
            strategy,
            use_llm=use_llm and self._llm_client is not None,
            llm_client=self._llm_client,
        )

    async def execute(
        self,
        plan: OptimizationPlan,
        dry_run: bool = False,
        create_snapshot: bool = True,
    ) -> ExecutionResult:
        """Execute an optimization plan.

        Args:
            plan: The optimization plan to execute.
            dry_run: If True, simulate without making changes.
            create_snapshot: Whether to create a snapshot before execution.

        Returns:
            Execution results.
        """
        logger.info(
            "Executing optimization plan",
            plan_id=plan.id,
            dry_run=dry_run,
            create_snapshot=create_snapshot,
        )

        return await self._execution_service.execute_plan(
            plan,
            dry_run=dry_run,
            create_snapshot=create_snapshot,
        )

    async def optimize(
        self,
        repository: str,
        branch: str = "main",
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
        use_llm: bool = False,
        dry_run: bool = False,
        create_snapshot: bool = True,
    ) -> Dict[str, Any]:
        """Full optimization workflow: analyze, plan, and execute.

        Args:
            repository: The repository name.
            branch: The branch name.
            strategy: The optimization strategy.
            use_llm: Whether to use LLM for enhanced analysis/planning.
            dry_run: If True, simulate without making changes.
            create_snapshot: Whether to create a snapshot before execution.

        Returns:
            Combined results from analysis, planning, and execution.
        """
        logger.info(
            "Starting full optimization workflow",
            repository=repository,
            branch=branch,
            strategy=strategy.value,
            use_llm=use_llm,
            dry_run=dry_run,
        )

        # Step 1: Analyze
        analysis = await self.analyze(repository, branch, use_llm)

        # Step 2: Plan
        plan = await self.plan(repository, branch, strategy, use_llm)

        # Step 3: Execute
        execution = await self.execute(plan, dry_run, create_snapshot)

        return {
            "analysis": analysis.model_dump(mode="json"),
            "plan": plan.model_dump(mode="json"),
            "execution": execution.model_dump(mode="json"),
            "summary": {
                "repository": repository,
                "branch": branch,
                "strategy": strategy.value,
                "health_score": analysis.health_score,
                "issues_found": len(analysis.issues),
                "actions_planned": len(plan.actions),
                "actions_executed": execution.summary.get("executed", 0),
                "actions_failed": execution.summary.get("failed", 0),
                "snapshot_id": execution.snapshot_id,
                "dry_run": dry_run,
            },
        }

    async def rollback(
        self,
        repository: str,
        snapshot_id: str,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """Rollback to a previous snapshot.

        Args:
            repository: The repository name.
            snapshot_id: The snapshot ID to rollback to.
            branch: The branch name.

        Returns:
            Rollback result.
        """
        logger.info(
            "Rolling back to snapshot",
            repository=repository,
            snapshot_id=snapshot_id,
            branch=branch,
        )

        return await self._execution_service.rollback(
            repository, snapshot_id, branch
        )

    async def list_snapshots(
        self,
        repository: str,
        branch: str = "main",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """List available snapshots.

        Args:
            repository: The repository name.
            branch: The branch name.
            limit: Maximum number of snapshots to return.

        Returns:
            List of snapshot metadata.
        """
        return await self._execution_service.list_snapshots(
            repository, branch, limit
        )

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
            Component details including dependencies and relationships.
        """
        return await self._context_builder.get_component_details(
            repository, component_id, branch
        )

    def set_llm_client(self, llm_client: Any) -> None:
        """Set or update the LLM client.

        Args:
            llm_client: The LLM client (OpenAI or Anthropic compatible).
        """
        self._llm_client = llm_client

    async def run(
        self,
        repository: str,
        branch: str = "main",
        **kwargs: Any,
    ) -> Dict[str, Any]:
        """Run the agent (BaseMemoryAgent interface).

        Args:
            repository: The repository name.
            branch: The branch name.
            **kwargs: Additional arguments passed to optimize().

        Returns:
            Optimization results.
        """
        strategy_str = kwargs.get("strategy", "balanced")
        strategy = OptimizationStrategy(strategy_str)

        return await self.optimize(
            repository=repository,
            branch=branch,
            strategy=strategy,
            use_llm=kwargs.get("use_llm", False),
            dry_run=kwargs.get("dry_run", False),
            create_snapshot=kwargs.get("create_snapshot", True),
        )
