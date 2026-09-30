"""Prompt manager for memory optimization agents."""

import json
from typing import Any, Dict

import structlog

logger = structlog.get_logger(__name__)


class PromptManager:
    """Manages prompts for memory optimization."""

    SYSTEM_PROMPT = (
        "You are an expert memory bank optimization assistant. Your role is to "
        "analyze software project memory banks and suggest optimizations to "
        "improve organization, reduce redundancy, and maintain clarity.\n"
        "\n"
        "You have access to a graph-based memory bank containing:\n"
    ) + """- Components: Software modules, services, and features
- Decisions: Architectural decisions and their rationale
- Rules: Coding standards and guidelines
- Context: Session summaries and observations
- Tags: Labels for categorization
- Files: Source file references

Your analysis should consider:
1. Circular dependencies that may indicate design issues
2. Orphaned components with no connections
3. Deprecated items that can be removed
4. Redundant or duplicate entries
5. Missing relationships that should exist
6. Stale context entries that are no longer relevant

Always explain your reasoning and provide actionable recommendations."""

    ANALYSIS_PROMPT_TEMPLATE = (
        "Analyze the following memory bank state and provide optimization "
        "recommendations.\n"
    ) + """
## Memory Bank: {repository}:{branch}

### Statistics
{statistics}

### Pattern Analysis
- Circular Dependencies: {cycles_count}
- Disconnected Islands: {islands_count}
- Strongly Connected Groups: {strongly_connected_count}

### Component Summary
- Total: {total_components}
- Active: {active_components}
- Deprecated: {deprecated_components}
- Planned: {planned_components}

### Top Components by Importance (PageRank)
{top_components}

### Governance
- Rules: {rules_count} ({active_rules} active)
- Decisions: {decisions_count}

Please analyze this memory bank and provide:
1. Health assessment (score 0-100)
2. Key issues identified
3. Prioritized recommendations for optimization
4. Risk assessment for suggested changes

Format your response as JSON with the following structure:
```json
{{
  "health_score": <number>,
  "assessment": "<summary>",
  "issues": [
""" + (
        '    {{"type": "<type>", "severity": "high|medium|low", '
        '"description": "<desc>", "affected": [<ids>]}}'
    ) + """
  ],
  "recommendations": [
""" + (
        '    {{"priority": 1, "action": "<action>", "reason": "<reason>", '
        '"impact": "<impact>", "risk": "high|medium|low"}}'
    ) + """
  ]
}}
```"""

    OPTIMIZATION_PROMPT_TEMPLATE = (
        "Plan optimizations for the following memory bank using the "
        "{strategy} strategy.\n"
    ) + """
## Memory Bank: {repository}:{branch}

### Current Analysis
{analysis_summary}

### Optimization Candidates
{candidates}

### Strategy Configuration: {strategy}
{strategy_config}

Based on the {strategy} strategy, create an optimization plan that:
1. Respects the strategy constraints (max_deletions, require_no_dependents, etc.)
2. Prioritizes high-impact, low-risk changes
3. Maintains system integrity
4. Preserves important relationships

Format your response as JSON with the following structure:
```json
{{
  "plan_id": "<uuid>",
  "strategy": "{strategy}",
  "actions": [
    {{
      "action_type": "delete|update|merge",
      "entity_type": "component|rule|tag",
      "entity_id": "<id>",
      "reason": "<reason>",
      "risk_level": "low|medium|high",
      "dependencies_affected": [<ids>]
    }}
  ],
  "summary": {{
    "total_actions": <number>,
    "deletions": <number>,
    "updates": <number>,
    "estimated_impact": "<description>"
  }}
}}
```"""

    def __init__(self) -> None:
        """Initialize the prompt manager."""
        self._prompts: Dict[str, str] = {
            "system": self.SYSTEM_PROMPT,
            "analysis": self.ANALYSIS_PROMPT_TEMPLATE,
            "optimization": self.OPTIMIZATION_PROMPT_TEMPLATE,
        }

    def get_system_prompt(self) -> str:
        """Get the system prompt.

        Returns:
            The system prompt string.
        """
        return self._prompts["system"]

    def build_analysis_prompt(self, context: Dict[str, Any]) -> str:
        """Build the analysis prompt from context.

        Args:
            context: The analysis context dictionary.

        Returns:
            The formatted analysis prompt.
        """
        stats = context.get("statistics", {})
        patterns = context.get("patterns", {})
        components = context.get("components", {})
        governance = context.get("governance", {})

        # Format top components
        top_components = components.get("top_by_pagerank", [])
        top_components_str = "\n".join([
            f"- {c.get('name', c.get('id'))}: rank={c.get('rank', 0):.3f}"
            for c in top_components[:5]
        ])

        return self.ANALYSIS_PROMPT_TEMPLATE.format(
            repository=context.get("repository", "unknown"),
            branch=context.get("branch", "main"),
            statistics=json.dumps(stats.get("counts", {}), indent=2),
            cycles_count=patterns.get("cycles", 0),
            islands_count=patterns.get("islands", 0),
            strongly_connected_count=patterns.get("strongly_connected", 0),
            total_components=components.get("total", 0),
            active_components=components.get("active", 0),
            deprecated_components=components.get("deprecated", 0),
            planned_components=components.get("planned", 0),
            top_components=top_components_str or "None",
            rules_count=governance.get("rules_count", 0),
            active_rules=governance.get("active_rules", 0),
            decisions_count=governance.get("decisions_count", 0),
        )

    def build_optimization_prompt(self, context: Dict[str, Any]) -> str:
        """Build the optimization prompt from context.

        Args:
            context: The optimization context dictionary.

        Returns:
            The formatted optimization prompt.
        """
        strategy = context.get("strategy", "balanced")
        candidates = context.get("optimization_candidates", {})
        strategy_config = context.get("strategy_config", {})

        # Build analysis summary
        analysis_summary = f"""
- Health: Based on pattern analysis
- Cycles: {context.get('patterns', {}).get('cycles', 0)}
- Islands: {context.get('patterns', {}).get('islands', 0)}
- Deprecated Components: {context.get('components', {}).get('deprecated', 0)}
"""

        # Format candidates
        component_candidates = candidates.get("components", [])
        candidates_str = "\n".join([
            f"- {c['name']} ({c['id']}): {', '.join(c.get('reasons', []))}"
            for c in component_candidates[:20]
        ])

        orphaned_tags = candidates.get("orphaned_tags", [])
        if orphaned_tags:
            candidates_str += "\n\nOrphaned Tags:\n" + "\n".join([
                f"- {t['name']} ({t['id']})"
                for t in orphaned_tags[:10]
            ])

        return self.OPTIMIZATION_PROMPT_TEMPLATE.format(
            repository=context.get("repository", "unknown"),
            branch=context.get("branch", "main"),
            strategy=strategy,
            analysis_summary=analysis_summary,
            candidates=candidates_str or "No optimization candidates found",
            strategy_config=json.dumps(strategy_config, indent=2),
        )

    def parse_analysis_response(self, response: str) -> Dict[str, Any]:
        """Parse the analysis response from the LLM.

        Args:
            response: The raw LLM response.

        Returns:
            Parsed analysis dictionary.
        """
        try:
            # Try to extract JSON from the response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse analysis response", error=str(e))

        # Return a default structure if parsing fails
        return {
            "health_score": 50,
            "assessment": "Unable to parse analysis response",
            "issues": [],
            "recommendations": [],
            "raw_response": response,
        }

    def parse_optimization_response(self, response: str) -> Dict[str, Any]:
        """Parse the optimization response from the LLM.

        Args:
            response: The raw LLM response.

        Returns:
            Parsed optimization plan dictionary.
        """
        try:
            # Try to extract JSON from the response
            json_start = response.find("{")
            json_end = response.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                return json.loads(json_str)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse optimization response", error=str(e))

        # Return a default structure if parsing fails
        return {
            "plan_id": "error",
            "strategy": "unknown",
            "actions": [],
            "summary": {
                "total_actions": 0,
                "deletions": 0,
                "updates": 0,
                "estimated_impact": "Unable to parse response",
            },
            "raw_response": response,
        }
