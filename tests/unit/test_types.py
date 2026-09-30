"""Unit tests for type definitions."""


from cognitive_fabric.types.entities import (
    Component,
    ComponentStatus,
    Context,
    Decision,
    DecisionStatus,
    File,
    Repository,
    Rule,
    RuleStatus,
    Tag,
)
from cognitive_fabric.types.optimization import (
    AgentAnalysisResult,
    AgentOptimizationAction,
    AgentOptimizationPlan,
    ExecutionResult,
    Issue,
    OptimizationStrategy,
    Recommendation,
)


class TestEntityTypes:
    """Tests for entity type models."""

    def test_component_creation(self):
        """Test Component model creation."""
        component = Component(
            id="comp-001",
            name="TestComponent",
            kind="service",
            status=ComponentStatus.ACTIVE,
            repository="test-repo",
            branch="main",
        )

        assert component.id == "comp-001"
        assert component.name == "TestComponent"
        assert component.kind == "service"
        assert component.status == ComponentStatus.ACTIVE
        assert component.graph_unique_id() == "test-repo:main:comp-001"

    def test_component_with_depends_on(self):
        """Test Component with dependencies."""
        component = Component(
            id="comp-002",
            name="DependentComponent",
            depends_on=["comp-001", "comp-003"],
            repository="test-repo",
            branch="main",
        )

        assert component.depends_on == ["comp-001", "comp-003"]

    def test_decision_creation(self):
        """Test Decision model creation."""
        decision = Decision(
            id="dec-001",
            name="TestDecision",
            context="Test context",
            date="2024-01-15",
            status=DecisionStatus.ACCEPTED,
            repository="test-repo",
            branch="main",
        )

        assert decision.id == "dec-001"
        assert decision.name == "TestDecision"
        assert decision.status == DecisionStatus.ACCEPTED

    def test_rule_creation(self):
        """Test Rule model creation."""
        rule = Rule(
            id="rule-001",
            name="TestRule",
            content="Test content",
            triggers=["on-commit", "on-push"],
            status=RuleStatus.ACTIVE,
            created="2024-01-15",
            repository="test-repo",
            branch="main",
        )

        assert rule.id == "rule-001"
        assert rule.triggers == ["on-commit", "on-push"]
        assert rule.status == RuleStatus.ACTIVE

    def test_context_creation(self):
        """Test Context model creation."""
        context = Context(
            id="ctx-001",
            name="TestContext",
            iso_date="2024-01-15T10:30:00Z",
            agent="test-agent",
            summary="Test summary",
            repository="test-repo",
            branch="main",
        )

        assert context.id == "ctx-001"
        assert context.agent == "test-agent"

    def test_file_creation(self):
        """Test File model creation."""
        file = File(
            id="file-001",
            name="test.py",
            path="/src/test.py",
            size=1024,
            mime_type="text/x-python",
            repository="test-repo",
            branch="main",
        )

        assert file.id == "file-001"
        assert file.path == "/src/test.py"
        assert file.size == 1024

    def test_tag_creation(self):
        """Test Tag model creation."""
        tag = Tag(
            id="tag-001",
            name="test-tag",
            color="#FF0000",
            description="A test tag",
            category="testing",
            repository="test-repo",
            branch="main",
        )

        assert tag.id == "tag-001"
        assert tag.color == "#FF0000"

    def test_repository_creation(self):
        """Test Repository model creation."""
        repo = Repository(
            id="repo-001",
            name="test-repo",
            branch="main",
        )

        assert repo.id == "repo-001"
        assert repo.name == "test-repo"


class TestOptimizationTypes:
    """Tests for optimization type models."""

    def test_optimization_strategy_values(self):
        """Test OptimizationStrategy enum values."""
        assert OptimizationStrategy.CONSERVATIVE.value == "conservative"
        assert OptimizationStrategy.BALANCED.value == "balanced"
        assert OptimizationStrategy.AGGRESSIVE.value == "aggressive"

    def test_issue_creation(self):
        """Test Issue model creation."""
        issue = Issue(
            type="circular_dependency",
            severity="high",
            description="Found circular dependency",
            affected_ids=["comp-001", "comp-002"],
        )

        assert issue.type == "circular_dependency"
        assert issue.severity == "high"
        assert len(issue.affected_ids) == 2

    def test_recommendation_creation(self):
        """Test Recommendation model creation."""
        rec = Recommendation(
            priority=1,
            action="Remove deprecated component",
            reason="Component is no longer used",
            impact="Reduced complexity",
            risk="low",
            affected_ids=["comp-001"],
        )

        assert rec.priority == 1
        assert rec.risk == "low"

    def test_agent_analysis_result(self):
        """Test AgentAnalysisResult model creation."""
        result = AgentAnalysisResult(
            repository="test-repo",
            branch="main",
            health_score=85,
            issues=[],
            recommendations=[],
            statistics={"total": 10},
            patterns={"cycles": 0},
        )

        assert result.health_score == 85
        assert result.repository == "test-repo"

    def test_agent_optimization_action(self):
        """Test AgentOptimizationAction model creation."""
        action = AgentOptimizationAction(
            action_type="delete",
            entity_type="component",
            entity_id="comp-001",
            entity_name="TestComponent",
            reason="Component is orphaned",
            risk_level="low",
        )

        assert action.action_type == "delete"
        assert action.risk_level == "low"

    def test_agent_optimization_plan(self):
        """Test AgentOptimizationPlan model creation."""
        plan = AgentOptimizationPlan(
            id="plan-001",
            repository="test-repo",
            branch="main",
            strategy=OptimizationStrategy.BALANCED,
            actions=[],
            summary={"total_actions": 0},
        )

        assert plan.id == "plan-001"
        assert plan.strategy == OptimizationStrategy.BALANCED

    def test_execution_result(self):
        """Test ExecutionResult model creation."""
        result = ExecutionResult(
            plan_id="plan-001",
            repository="test-repo",
            branch="main",
            snapshot_id="snap-001",
            dry_run=False,
            executed=[],
            failed=[],
            skipped=[],
            summary={"total": 0},
        )

        assert result.plan_id == "plan-001"
        assert result.dry_run is False
        assert result.snapshot_id == "snap-001"
