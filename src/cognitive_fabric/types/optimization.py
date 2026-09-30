"""Optimization-related type definitions for memory optimizer agent."""

from datetime import datetime
from enum import Enum
from typing import Any, Literal, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Enums
# =============================================================================


class OptimizationStrategy(str, Enum):
    """Optimization aggressiveness strategy."""

    CONSERVATIVE = "conservative"  # 6 months stale threshold, max 5 deletions
    BALANCED = "balanced"  # 3 months stale threshold, max 20 deletions
    AGGRESSIVE = "aggressive"  # 1 month stale threshold, max 50 deletions


class SamplingStrategy(str, Enum):
    """Memory sampling strategy for context building."""

    REPRESENTATIVE = "representative"  # Uniform sampling of all memory types
    PROBLEMATIC = "problematic"  # Focus on inconsistencies and conflicts
    RECENT = "recent"  # Emphasize newly added entities
    DIVERSE = "diverse"  # Mix of different entity types


class ActionType(str, Enum):
    """Type of optimization action."""

    DELETE = "delete"
    MERGE = "merge"
    UPDATE = "update"
    MOVE = "move"


class RiskLevel(str, Enum):
    """Risk level assessment."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EntityType(str, Enum):
    """Entity types that can be optimized."""

    COMPONENT = "component"
    DECISION = "decision"
    RULE = "rule"
    FILE = "file"
    CONTEXT = "context"
    TAG = "tag"


# =============================================================================
# Strategy Configuration
# =============================================================================


class StrategyConfig(BaseModel):
    """Configuration for an optimization strategy."""

    stale_days_threshold: int
    max_deletions: int
    require_confirmation: bool = True
    preserve_recent_days: int = 7
    min_health_score: float = 0.3


STRATEGY_CONFIGS: dict[OptimizationStrategy, StrategyConfig] = {
    OptimizationStrategy.CONSERVATIVE: StrategyConfig(
        stale_days_threshold=180,
        max_deletions=5,
        require_confirmation=True,
        preserve_recent_days=30,
        min_health_score=0.5,
    ),
    OptimizationStrategy.BALANCED: StrategyConfig(
        stale_days_threshold=90,
        max_deletions=20,
        require_confirmation=True,
        preserve_recent_days=14,
        min_health_score=0.3,
    ),
    OptimizationStrategy.AGGRESSIVE: StrategyConfig(
        stale_days_threshold=30,
        max_deletions=50,
        require_confirmation=False,
        preserve_recent_days=7,
        min_health_score=0.2,
    ),
}


# =============================================================================
# Analysis Results
# =============================================================================


class StaleEntity(BaseModel):
    """An entity identified as potentially stale."""

    id: str
    type: EntityType
    name: str
    staleness: float = Field(ge=0.0, le=1.0, description="Staleness score 0-1")
    reason: str
    safe_to_delete: bool
    last_accessed: Optional[str] = None
    dependencies: list[str] = Field(default_factory=list)
    dependents: list[str] = Field(default_factory=list)


class RedundancyGroup(BaseModel):
    """A group of potentially redundant entities."""

    entity_ids: list[str]
    type: EntityType
    similarity_score: float
    suggested_action: str
    reason: str


class OptimizationOpportunity(BaseModel):
    """An identified optimization opportunity."""

    id: str
    type: str
    description: str
    impact: str
    effort: Literal["low", "medium", "high"]
    priority: Literal["low", "medium", "high"]


class RiskAssessment(BaseModel):
    """Risk assessment for optimization."""

    overall_risk: RiskLevel
    critical_entities_at_risk: list[str] = Field(default_factory=list)
    safeguards_recommended: list[str] = Field(default_factory=list)


class AnalysisSummary(BaseModel):
    """Summary of memory analysis."""

    total_entities_analyzed: int
    stale_entities_found: int
    redundancy_groups_found: int
    optimization_opportunities: int
    overall_health_score: float = Field(ge=0.0, le=1.0)


class AnalysisResult(BaseModel):
    """Complete result of memory analysis."""

    summary: AnalysisSummary
    stale_entities: list[StaleEntity] = Field(default_factory=list)
    redundancies: list[RedundancyGroup] = Field(default_factory=list)
    optimization_opportunities: list[OptimizationOpportunity] = Field(
        default_factory=list
    )
    recommendations: list[str] = Field(default_factory=list)
    risk_assessment: RiskAssessment


# =============================================================================
# Optimization Plan
# =============================================================================


class OptimizationAction(BaseModel):
    """A single optimization action to execute."""

    type: ActionType
    entity_id: str
    entity_type: EntityType
    target_entity_id: Optional[str] = None  # For merge/move operations
    reason: str
    priority: Literal["low", "medium", "high"]
    safety_checks: list[str] = Field(default_factory=list)


class EstimatedImpact(BaseModel):
    """Estimated impact of optimization plan."""

    entities_affected: int
    relationships_affected: int
    estimated_storage_savings: int  # bytes
    estimated_query_performance_gain: float  # percentage


class OptimizationPlan(BaseModel):
    """Complete optimization plan."""

    plan_id: str
    created_at: datetime
    strategy: OptimizationStrategy
    actions: list[OptimizationAction] = Field(default_factory=list)
    estimated_impact: EstimatedImpact
    risk_level: RiskLevel
    rollback_strategy: str


# =============================================================================
# Execution Results
# =============================================================================


class ActionResult(BaseModel):
    """Result of executing a single action."""

    action: OptimizationAction
    success: bool
    error: Optional[str] = None
    execution_time_ms: float


class OptimizationResult(BaseModel):
    """Complete result of optimization execution."""

    plan_id: str
    executed_at: datetime
    dry_run: bool
    total_actions: int
    successful_actions: int
    failed_actions: int
    action_results: list[ActionResult] = Field(default_factory=list)
    snapshot_id: Optional[str] = None
    rollback_available: bool


# =============================================================================
# Snapshot Management
# =============================================================================


class SnapshotInfo(BaseModel):
    """Information about a saved snapshot."""

    snapshot_id: str
    created_at: datetime
    repository: str
    branch: str
    entity_counts: dict[str, int]
    description: Optional[str] = None
    size_bytes: int


class RollbackResult(BaseModel):
    """Result of rolling back to a snapshot."""

    snapshot_id: str
    success: bool
    entities_restored: int
    relationships_restored: int
    error: Optional[str] = None


# =============================================================================
# Memory Context
# =============================================================================


class EntitySummary(BaseModel):
    """Summary of entities for a type."""

    count: int
    oldest: Optional[datetime] = None
    newest: Optional[datetime] = None


class RelationshipSummary(BaseModel):
    """Summary of relationships in the memory graph."""

    total_relationships: int
    relationships_by_type: dict[str, int] = Field(default_factory=dict)
    most_connected_items: list[dict[str, Any]] = Field(default_factory=list)


class MemoryContext(BaseModel):
    """Full context of memory state for optimization."""

    repository: str
    branch: str
    entity_summaries: dict[str, EntitySummary] = Field(default_factory=dict)
    relationship_summary: RelationshipSummary
    total_entities: int
    created_at: datetime


class MemorySample(BaseModel):
    """Sampled memory for LLM context."""

    strategy: SamplingStrategy
    sample_size: int
    entities: list[dict[str, Any]] = Field(default_factory=list)
    relationships: list[dict[str, Any]] = Field(default_factory=list)


# =============================================================================
# Agent Service Types (Simplified for agent workflow)
# =============================================================================


class Issue(BaseModel):
    """An issue detected during memory analysis."""

    type: str
    severity: Literal["low", "medium", "high"]
    description: str
    affected_ids: list[str] = Field(default_factory=list)


class Recommendation(BaseModel):
    """A recommendation from memory analysis."""

    priority: int
    action: str
    reason: str
    impact: str
    risk: Literal["low", "medium", "high"]
    affected_ids: list[str] = Field(default_factory=list)


class AgentAnalysisResult(BaseModel):
    """Analysis result from memory optimization agent."""

    repository: str
    branch: str
    health_score: int = Field(ge=0, le=100)
    issues: list[Issue] = Field(default_factory=list)
    recommendations: list[Recommendation] = Field(default_factory=list)
    statistics: dict[str, Any] = Field(default_factory=dict)
    patterns: dict[str, Any] = Field(default_factory=dict)
    llm_analysis: Optional[dict[str, Any]] = None


class AgentOptimizationAction(BaseModel):
    """A single optimization action for agent execution."""

    action_type: Literal["delete", "update", "merge"]
    entity_type: str
    entity_id: str
    entity_name: Optional[str] = None
    reason: str
    risk_level: Literal["low", "medium", "high"] = "medium"
    updates: Optional[dict[str, Any]] = None


class AgentOptimizationPlan(BaseModel):
    """Optimization plan created by the agent."""

    id: str
    repository: str
    branch: str
    strategy: OptimizationStrategy
    actions: list[AgentOptimizationAction] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)


class ExecutionResult(BaseModel):
    """Result of executing an optimization plan."""

    plan_id: str
    repository: str
    branch: str
    snapshot_id: Optional[str] = None
    dry_run: bool
    executed: list[dict[str, Any]] = Field(default_factory=list)
    failed: list[dict[str, Any]] = Field(default_factory=list)
    skipped: list[dict[str, Any]] = Field(default_factory=list)
    summary: dict[str, Any] = Field(default_factory=dict)
