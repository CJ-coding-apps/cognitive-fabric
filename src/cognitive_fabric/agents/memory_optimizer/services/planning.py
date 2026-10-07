"""Optimization planning service for memory optimizer agent."""

import uuid
from typing import Any, Dict, List, Optional

import structlog

from cognitive_fabric.agents.memory_optimizer.context_builder import (
    MemoryContextBuilder,
    effective_max_deletions,
)
from cognitive_fabric.agents.memory_optimizer.prompt_manager import PromptManager
from cognitive_fabric.config import settings as default_settings
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.optimization import (
    AgentOptimizationAction as OptimizationAction,
)
from cognitive_fabric.types.optimization import (
    AgentOptimizationPlan as OptimizationPlan,
)
from cognitive_fabric.types.optimization import (
    OptimizationStrategy,
)

logger = structlog.get_logger(__name__)


class OptimizationPlanService:
    """Service for creating optimization plans."""

    def __init__(
        self,
        memory_service: MemoryService,
        context_builder: MemoryContextBuilder,
        prompt_manager: PromptManager,
    ) -> None:
        """Initialize the planning service.

        Args:
            memory_service: The memory service instance.
            context_builder: The context builder instance.
            prompt_manager: The prompt manager instance.
        """
        self._memory_service = memory_service
        self._context_builder = context_builder
        self._prompt_manager = prompt_manager

    async def create_plan(
        self,
        repository: str,
        branch: str = "main",
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
        use_llm: bool = False,
        llm_client: Optional[Any] = None,
        model_name: Optional[str] = None,
    ) -> OptimizationPlan:
        """Create an optimization plan.

        Args:
            repository: The repository name.
            branch: The branch name.
            strategy: The optimization strategy.
            use_llm: Whether to use LLM for planning.
            llm_client: Optional LLM client.
            model_name: The model to ask for. Comes from configuration, via the
                agent; this service chooses no model of its own.

        Returns:
            The optimization plan.
        """
        logger.info(
            "Creating optimization plan",
            repository=repository,
            branch=branch,
            strategy=strategy.value,
        )

        # Build context
        context = await self._context_builder.build_optimization_context(
            repository, branch, strategy.value
        )

        # Create rule-based plan
        actions = await self._create_rule_based_plan(context, strategy)

        # Optionally enhance with LLM
        if use_llm and llm_client:
            llm_plan = await self._create_llm_plan(context, llm_client, model_name)
            if llm_plan and llm_plan.get("actions"):
                # Merge LLM actions with rule-based actions
                actions = self._merge_plans(actions, llm_plan.get("actions", []))

        # Apply strategy limits
        actions = self._apply_strategy_limits(actions, strategy)

        plan_id = str(uuid.uuid4())

        return OptimizationPlan(
            id=plan_id,
            repository=repository,
            branch=branch,
            strategy=strategy,
            actions=actions,
            summary={
                "total_actions": len(actions),
                "deletions": len([a for a in actions if a.action_type == "delete"]),
                "updates": len([a for a in actions if a.action_type == "update"]),
            },
        )

    async def _create_rule_based_plan(
        self,
        context: Dict[str, Any],
        strategy: OptimizationStrategy,
    ) -> List[OptimizationAction]:
        """Create a rule-based optimization plan.

        Args:
            context: The optimization context.
            strategy: The optimization strategy.

        Returns:
            List of optimization actions.
        """
        actions = []
        candidates = context.get("optimization_candidates", {})
        strategy_config = context.get("strategy_config", {})

        # Process component candidates
        for candidate in candidates.get("components", []):
            reasons = candidate.get("reasons", [])

            # Handle deprecated components
            if "deprecated_status" in reasons:
                if strategy_config.get("delete_deprecated", True):
                    # Check dependents requirement
                    has_no_dependents = (
                        "orphaned" in reasons
                        or not strategy_config.get("require_no_dependents", True)
                    )

                    if has_no_dependents:
                        actions.append(OptimizationAction(
                            action_type="delete",
                            entity_type="component",
                            entity_id=candidate["id"],
                            entity_name=candidate.get("name"),
                            reason="Component is deprecated",
                            risk_level="low" if "orphaned" in reasons else "medium",
                        ))

            # Handle orphaned components (conservative strategy might skip these)
            elif (
                "orphaned" in reasons
                and strategy != OptimizationStrategy.CONSERVATIVE
            ):
                actions.append(OptimizationAction(
                    action_type="delete",
                    entity_type="component",
                    entity_id=candidate["id"],
                    entity_name=candidate.get("name"),
                    reason="Component has no dependencies or dependents",
                    risk_level="low",
                ))

        # Process orphaned tags
        if strategy_config.get("delete_orphaned_tags", False):
            for tag in candidates.get("orphaned_tags", []):
                actions.append(OptimizationAction(
                    action_type="delete",
                    entity_type="tag",
                    entity_id=tag["id"],
                    entity_name=tag.get("name"),
                    reason="Tag has no associated items",
                    risk_level="low",
                ))

        return actions

    async def _create_llm_plan(
        self,
        context: Dict[str, Any],
        llm_client: Any,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Create an LLM-enhanced optimization plan.

        Args:
            context: The optimization context.
            llm_client: The LLM client.
            model_name: The model to ask for, from configuration.

        Returns:
            LLM plan dictionary.
        """
        try:
            prompt = self._prompt_manager.build_optimization_prompt(context)
            system_prompt = self._prompt_manager.get_system_prompt()

            # Call LLM
            if hasattr(llm_client, "chat"):
                response = await llm_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                )
                response_text = response.choices[0].message.content

            elif hasattr(llm_client, "messages"):
                response = await llm_client.messages.create(
                    model=model_name,
                    max_tokens=2000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.content[0].text

            else:
                return {}

            return self._prompt_manager.parse_optimization_response(response_text)

        except Exception as e:
            logger.error("LLM planning failed", error=str(e))
            return {}

    def _merge_plans(
        self,
        rule_actions: List[OptimizationAction],
        llm_actions: List[Dict[str, Any]],
    ) -> List[OptimizationAction]:
        """Merge rule-based and LLM actions.

        Args:
            rule_actions: Rule-based actions.
            llm_actions: LLM-suggested actions.

        Returns:
            Merged list of actions.
        """
        # Start with rule-based actions
        merged = list(rule_actions)
        existing_ids = {a.entity_id for a in merged}

        # Add LLM actions that don't duplicate
        for llm_action in llm_actions:
            entity_id = llm_action.get("entity_id")
            if entity_id and entity_id not in existing_ids:
                merged.append(OptimizationAction(
                    action_type=llm_action.get("action_type", "delete"),
                    entity_type=llm_action.get("entity_type", "component"),
                    entity_id=entity_id,
                    entity_name=llm_action.get("entity_name"),
                    reason=llm_action.get("reason", "LLM recommendation"),
                    risk_level=llm_action.get("risk_level", "medium"),
                ))
                existing_ids.add(entity_id)

        return merged

    def _apply_strategy_limits(
        self,
        actions: List[OptimizationAction],
        strategy: str,
    ) -> List[OptimizationAction]:
        """Apply the deletion limit to a plan's actions.

        The limit caps deletions, and only deletions. It used to truncate the
        whole action list, so a plan of 30 low-risk status updates and 3
        deletions came out as 10 updates and no deletions under `conservative`
        -- a deletion limit that removed work it was not about, and reported a
        plan smaller than the memory actually needed.

        Args:
            actions: The list of actions.
            strategy: The strategy name, which selects the preset limit.

        Returns:
            The actions, with the lowest-risk deletions beyond the limit dropped.
        """
        max_deletions = effective_max_deletions(
            strategy, operator_cap=default_settings.optimizer_max_deletions
        )

        # Sort by risk level (low first)
        risk_order = {"low": 0, "medium": 1, "high": 2}
        ordered = sorted(actions, key=lambda a: risk_order.get(a.risk_level, 2))

        kept: List[OptimizationAction] = []
        deletions_kept = 0
        for action in ordered:
            if action.action_type == "delete":
                if deletions_kept >= max_deletions:
                    continue
                deletions_kept += 1
            kept.append(action)
        return kept
