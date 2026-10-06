"""Memory analysis service for optimization agent."""

from typing import Any, Dict, List, Optional

import structlog

from cognitive_fabric.agents.memory_optimizer.context_builder import (
    MemoryContextBuilder,
)
from cognitive_fabric.agents.memory_optimizer.prompt_manager import PromptManager
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.optimization import (
    AgentAnalysisResult as AnalysisResult,
)
from cognitive_fabric.types.optimization import (
    Issue,
    Recommendation,
)

logger = structlog.get_logger(__name__)


class MemoryAnalysisService:
    """Service for analyzing memory banks."""

    def __init__(
        self,
        memory_service: MemoryService,
        context_builder: MemoryContextBuilder,
        prompt_manager: PromptManager,
    ) -> None:
        """Initialize the analysis service.

        Args:
            memory_service: The memory service instance.
            context_builder: The context builder instance.
            prompt_manager: The prompt manager instance.
        """
        self._memory_service = memory_service
        self._context_builder = context_builder
        self._prompt_manager = prompt_manager

    async def analyze(
        self,
        repository: str,
        branch: str = "main",
        use_llm: bool = False,
        llm_client: Optional[Any] = None,
        model_name: Optional[str] = None,
    ) -> AnalysisResult:
        """Analyze the memory bank.

        Args:
            repository: The repository name.
            branch: The branch name.
            use_llm: Whether to use LLM for enhanced analysis.
            llm_client: Optional LLM client for enhanced analysis.
            model_name: The model to ask for. Comes from configuration, via the
                agent; this service chooses no model of its own.

        Returns:
            Analysis results.
        """
        logger.info("Analyzing memory bank", repository=repository, branch=branch)

        # Build context
        context = await self._context_builder.build_analysis_context(repository, branch)

        # Perform rule-based analysis
        issues = await self._detect_issues(context)
        recommendations = await self._generate_recommendations(context, issues)
        health_score = self._calculate_health_score(context, issues)

        # Optionally enhance with LLM
        llm_analysis = None
        if use_llm and llm_client:
            llm_analysis = await self._llm_analyze(context, llm_client, model_name)

        return AnalysisResult(
            repository=repository,
            branch=branch,
            health_score=health_score,
            issues=issues,
            recommendations=recommendations,
            statistics=context.get("statistics", {}),
            patterns={
                "cycles": context.get("patterns", {}).get("cycles", 0),
                "islands": context.get("patterns", {}).get("islands", 0),
                "strongly_connected": context.get("patterns", {}).get(
                    "strongly_connected", 0
                ),
            },
            llm_analysis=llm_analysis,
        )

    async def _detect_issues(self, context: Dict[str, Any]) -> List[Issue]:
        """Detect issues in the memory bank.

        Args:
            context: The analysis context.

        Returns:
            List of detected issues.
        """
        issues = []
        patterns = context.get("patterns", {})
        components = context.get("components", {})

        # Check for cycles
        cycles_count = patterns.get("cycles", 0)
        if cycles_count > 0:
            issues.append(Issue(
                type="circular_dependency",
                severity="high",
                description=f"Found {cycles_count} circular dependency group(s)",
                affected_ids=[
                    id for cycle in patterns.get("cycle_details", [])
                    for id in cycle
                ],
            ))

        # Check for islands
        islands_count = patterns.get("islands", 0)
        if islands_count > 1:
            issues.append(Issue(
                type="disconnected_components",
                severity="medium",
                description=f"Found {islands_count} disconnected component groups",
                affected_ids=[
                    id for island in patterns.get("island_details", [])
                    for id in island
                ],
            ))

        # Check for deprecated components
        deprecated_count = components.get("deprecated", 0)
        if deprecated_count > 0:
            issues.append(Issue(
                type="deprecated_components",
                severity="low",
                description=f"Found {deprecated_count} deprecated component(s)",
                affected_ids=[],  # Would need to fetch actual IDs
            ))

        # Orphaned-tag detection is not implemented: it needs orphaned tag data
        # that the analysis context does not carry.

        return issues

    async def _generate_recommendations(
        self,
        context: Dict[str, Any],
        issues: List[Issue],
    ) -> List[Recommendation]:
        """Generate recommendations based on issues.

        Args:
            context: The analysis context.
            issues: The detected issues.

        Returns:
            List of recommendations.
        """
        recommendations = []
        priority = 1

        for issue in issues:
            if issue.type == "circular_dependency":
                recommendations.append(Recommendation(
                    priority=priority,
                    action="Review and refactor circular dependencies",
                    reason=(
                        "Circular dependencies can cause maintenance issues "
                        "and make the codebase harder to understand"
                    ),
                    impact="Improved code modularity and reduced coupling",
                    risk="medium",
                    affected_ids=issue.affected_ids,
                ))
                priority += 1

            elif issue.type == "disconnected_components":
                recommendations.append(Recommendation(
                    priority=priority,
                    action="Connect or remove disconnected component groups",
                    reason=(
                        "Disconnected components may indicate orphaned or "
                        "obsolete code"
                    ),
                    impact="Cleaner dependency graph",
                    risk="low",
                    affected_ids=issue.affected_ids,
                ))
                priority += 1

            elif issue.type == "deprecated_components":
                recommendations.append(Recommendation(
                    priority=priority,
                    action="Remove deprecated components without dependents",
                    reason="Deprecated components add clutter and may cause confusion",
                    impact="Reduced memory bank size and improved clarity",
                    risk="low",
                    affected_ids=issue.affected_ids,
                ))
                priority += 1

        return recommendations

    def _calculate_health_score(
        self,
        context: Dict[str, Any],
        issues: List[Issue],
    ) -> int:
        """Calculate the health score.

        Args:
            context: The analysis context.
            issues: The detected issues.

        Returns:
            Health score (0-100).
        """
        score = 100

        for issue in issues:
            if issue.severity == "high":
                score -= 20
            elif issue.severity == "medium":
                score -= 10
            elif issue.severity == "low":
                score -= 5

        # Bonus for good practices
        components = context.get("components", {})
        if components.get("active", 0) > 0 and components.get("deprecated", 0) == 0:
            score = min(100, score + 5)

        return max(0, min(100, score))

    async def _llm_analyze(
        self,
        context: Dict[str, Any],
        llm_client: Any,
        model_name: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Perform LLM-enhanced analysis.

        Args:
            context: The analysis context.
            llm_client: The LLM client.
            model_name: The model to ask for, from configuration.

        Returns:
            LLM analysis results.
        """
        try:
            prompt = self._prompt_manager.build_analysis_prompt(context)
            system_prompt = self._prompt_manager.get_system_prompt()

            # Call LLM (interface depends on provider)
            if hasattr(llm_client, "chat"):
                # OpenAI-style client
                response = await llm_client.chat.completions.create(
                    model=model_name,
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": prompt},
                    ],
                )
                response_text = response.choices[0].message.content

            elif hasattr(llm_client, "messages"):
                # Anthropic-style client
                response = await llm_client.messages.create(
                    model=model_name,
                    max_tokens=2000,
                    system=system_prompt,
                    messages=[{"role": "user", "content": prompt}],
                )
                response_text = response.content[0].text

            else:
                logger.warning("Unknown LLM client type")
                return {}

            return self._prompt_manager.parse_analysis_response(response_text)

        except Exception as e:
            logger.error("LLM analysis failed", error=str(e))
            return {"error": str(e)}
