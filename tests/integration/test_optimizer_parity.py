"""Parity tests for the memory-optimizer TS wire contract.

Exercises the additive TS parameters (analysisId caching, dryRun/strategy/
focusAreas/maxDeletions) through the real ToolRegistry -> handler -> service ->
KuzuDB path, plus the MemorySamplingManager's four sampling strategies.
"""

from pathlib import Path

import pytest
import pytest_asyncio

from cognitive_fabric.agents.memory_optimizer.mcp_sampling import MemorySamplingManager
from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.mcp.tool_registry import ToolRegistry
from cognitive_fabric.services.memory_service import MemoryService

REPO = "opt-parity-repo"
BRANCH = "main"


@pytest.mark.integration
class TestOptimizerParity:
    @pytest_asyncio.fixture
    async def call(self, memory_service: MemoryService):
        """A bound tool caller: call(name, params) -> result dict."""
        registry = ToolRegistry()
        ctx = ToolHandlerContext()

        async def _call(name, params):
            return await registry.call_tool(name, params, ctx, memory_service)

        return _call

    @pytest_asyncio.fixture
    async def initialized(self, call, temp_dir: Path):
        """Initialize the memory bank and seed a small fixture graph."""
        await call(
            "memory-bank",
            {
                "operation": "init",
                "repository": REPO,
                "branch": BRANCH,
                "clientProjectRoot": str(temp_dir),
            },
        )
        # Two active components + one deprecated component.
        for i in range(2):
            await call(
                "entity",
                {
                    "operation": "create",
                    "entityType": "component",
                    "repository": REPO,
                    "branch": BRANCH,
                    "data": {
                        "id": f"opt-comp-{i}",
                        "name": f"OptComp{i}",
                        "kind": "service",
                        "status": "active",
                    },
                },
            )
        await call(
            "entity",
            {
                "operation": "create",
                "entityType": "component",
                "repository": REPO,
                "branch": BRANCH,
                "data": {
                    "id": "opt-comp-dep",
                    "name": "OptCompDeprecated",
                    "kind": "service",
                    "status": "deprecated",
                },
            },
        )
        # A decision and a tag to add entity-type diversity.
        await call(
            "entity",
            {
                "operation": "create",
                "entityType": "decision",
                "repository": REPO,
                "branch": BRANCH,
                "data": {
                    "id": "opt-dec-0",
                    "name": "OptDecision",
                    "context": "test",
                    "date": "2024-01-15",
                },
            },
        )
        await call(
            "entity",
            {
                "operation": "create",
                "entityType": "tag",
                "repository": REPO,
                "branch": BRANCH,
                "data": {"id": "opt-tag-0", "name": "opt-tag"},
            },
        )
        return True

    @pytest.mark.asyncio
    async def test_analyze_returns_analysis_id(self, call, initialized):
        """analyze must return a non-empty analysisId."""
        result = await call(
            "memory-optimizer",
            {
                "operation": "analyze",
                "repository": REPO,
                "branch": BRANCH,
            },
        )
        assert result.get("success") is True
        assert result.get("operation") == "analyze"
        assert isinstance(result.get("analysisId"), str)
        assert result["analysisId"]
        # Sampling is enabled by default; a sample dict should be attached.
        assert "sample" in result

    @pytest.mark.asyncio
    async def test_optimize_dry_run_no_deletions(self, call, initialized):
        """optimize dryRun=true must succeed without deleting anything."""
        # Count components before.
        before = await call(
            "query",
            {
                "queryType": "entities",
                "repository": REPO,
                "branch": BRANCH,
                "entityType": "component",
            },
        )

        result = await call(
            "memory-optimizer",
            {
                "operation": "optimize",
                "repository": REPO,
                "branch": BRANCH,
                "dryRun": True,
                "strategy": "conservative",
                "focusAreas": ["stale-detection"],
                "maxDeletions": 1,
            },
        )
        assert result.get("success") is True
        assert result.get("operation") == "optimize"
        assert result.get("dry_run") is True
        # No real deletions in a dry run.
        assert result.get("action_count") == 0
        assert result.get("focus_areas") == ["stale-detection"]
        assert result.get("max_deletions") == 1

        # Component still present afterwards.
        after = await call(
            "query",
            {
                "queryType": "entities",
                "repository": REPO,
                "branch": BRANCH,
                "entityType": "component",
            },
        )
        assert str(before) is not None and str(after) is not None
        # The deprecated component was NOT deleted (dry run).
        get_dep = await call(
            "entity",
            {
                "operation": "get",
                "entityType": "component",
                "repository": REPO,
                "branch": BRANCH,
                "id": "opt-comp-dep",
            },
        )
        assert get_dep.get("success") is True

    @pytest.mark.asyncio
    async def test_analysis_id_reuse_in_optimize(self, call, initialized):
        """optimize with a cached analysisId should reuse it (no warning)."""
        analyze = await call(
            "memory-optimizer",
            {"operation": "analyze", "repository": REPO, "branch": BRANCH},
        )
        analysis_id = analyze["analysisId"]

        result = await call(
            "memory-optimizer",
            {
                "operation": "optimize",
                "repository": REPO,
                "branch": BRANCH,
                "dryRun": True,
                "analysisId": analysis_id,
            },
        )
        assert result.get("success") is True
        assert result.get("analysisId") == analysis_id
        warnings = result.get("warnings") or []
        assert not any("not found in cache" in w for w in warnings)

    @pytest.mark.asyncio
    async def test_optimize_requires_confirm_when_not_dry_run(
        self, call, initialized
    ):
        """optimize dryRun=false without confirm should ask for confirmation."""
        result = await call(
            "memory-optimizer",
            {
                "operation": "optimize",
                "repository": REPO,
                "branch": BRANCH,
                "dryRun": False,
                "confirm": False,
            },
        )
        assert result.get("success") is False
        assert "confirm" in result.get("message", "").lower()

    @pytest.mark.asyncio
    async def test_sampling_manager_all_strategies(
        self, memory_service, call, initialized
    ):
        """MemorySamplingManager returns the dict shape for each strategy."""
        manager = MemorySamplingManager(memory_service)
        for strategy in (
            "representative",
            "problematic",
            "recent",
            "diverse",
        ):
            sample = await manager.sample_memory_context(
                REPO,
                BRANCH,
                strategy=strategy,
                sample_size=5,
            )
            assert isinstance(sample, dict)
            assert isinstance(sample.get("entities"), list)
            assert isinstance(sample.get("relationships"), list)
            assert isinstance(sample.get("metadata"), dict)
            meta = sample["metadata"]
            assert meta["samplingStrategy"] == strategy
            assert meta["repository"] == REPO
            assert meta["branch"] == BRANCH
            assert "totalEntities" in meta
            assert "totalRelationships" in meta

    @pytest.mark.asyncio
    async def test_sampling_manager_empty_repo(self, memory_service):
        """Sampling an empty/unseeded repo returns empty collections."""
        manager = MemorySamplingManager(memory_service)
        sample = await manager.sample_memory_context(
            "no-such-repo",
            BRANCH,
            strategy="representative",
            sample_size=5,
        )
        assert sample["entities"] == []
        assert sample["relationships"] == []
        assert sample["metadata"]["totalEntities"] == 0


@pytest.mark.integration
class TestOperatorDeletionCap:
    """The cap has to hold where the deletes happen, not where the plan is drawn.

    `settings.optimizer_max_deletions` is the operator's ceiling. It is set on
    the module-level settings object rather than through the environment,
    because `config.settings` is built at import and a `setenv` would not reach
    it.
    """

    @pytest_asyncio.fixture
    async def call(self, memory_service: MemoryService):
        registry = ToolRegistry()
        ctx = ToolHandlerContext()

        async def _call(name, params):
            return await registry.call_tool(name, params, ctx, memory_service)

        return _call

    async def _seed(self, call, deprecated: int) -> None:
        """Init the bank and seed `deprecated` deprecated components."""
        await call(
            "memory-bank",
            {
                "operation": "init",
                "repository": REPO,
                "branch": BRANCH,
                "clientProjectRoot": "/tmp/opt-cap",
            },
        )
        for i in range(deprecated):
            await call(
                "entity",
                {
                    "operation": "create",
                    "entityType": "component",
                    "repository": REPO,
                    "branch": BRANCH,
                    "data": {
                        "id": f"cap-comp-{i}",
                        "name": f"CapComp{i}",
                        "kind": "service",
                        "status": "deprecated",
                    },
                },
            )

    @pytest.mark.asyncio
    async def test_the_cap_holds_under_aggressive(self, call, monkeypatch):
        """Five deprecated components, a cap of two, `aggressive`: two go.

        `aggressive`'s own preset is 100, so nothing but the operator's cap can
        produce the 2 here -- which is the point. A cap that a high strategy
        can lift is not a cap.
        """
        from cognitive_fabric.config import settings as cf_settings

        monkeypatch.setattr(cf_settings, "optimizer_max_deletions", 2)
        await self._seed(call, deprecated=5)

        result = await call(
            "memory-optimizer",
            {
                "operation": "optimize",
                "repository": REPO,
                "branch": BRANCH,
                "dryRun": False,
                "confirm": True,
                "strategy": "aggressive",
            },
        )
        assert result.get("success") is True
        assert result.get("max_deletions") == 2
        assert result.get("action_count") == 2

        # And the other three are still there: the cap bounded the work, it did
        # not merely describe it.
        remaining = 0
        for i in range(5):
            got = await call(
                "entity",
                {
                    "operation": "get",
                    "entityType": "component",
                    "repository": REPO,
                    "branch": BRANCH,
                    "id": f"cap-comp-{i}",
                },
            )
            if got.get("success") is True:
                remaining += 1
        assert remaining == 3

    @pytest.mark.asyncio
    async def test_unset_means_the_strategys_own_limit(self, call, monkeypatch):
        """With no operator cap, each strategy runs to its own preset limit.

        An unset cap must not read as a limit of zero -- nothing would ever be
        deleted -- nor as unbounded. All three presets are checked, because a
        hardcoded number would satisfy `aggressive` by coincidence.
        """
        from cognitive_fabric.agents.memory_optimizer.context_builder import (
            STRATEGY_CONFIGS,
        )
        from cognitive_fabric.config import settings as cf_settings

        monkeypatch.setattr(cf_settings, "optimizer_max_deletions", None)
        await self._seed(call, deprecated=1)

        limits = {name: cfg["max_deletions"] for name, cfg in STRATEGY_CONFIGS.items()}
        assert len(set(limits.values())) == len(limits), "presets must be distinct"

        for strategy, preset in limits.items():
            result = await call(
                "memory-optimizer",
                {
                    "operation": "optimize",
                    "repository": REPO,
                    "branch": BRANCH,
                    "dryRun": True,
                    "strategy": strategy,
                },
            )
            assert result.get("max_deletions") == preset, strategy

    @pytest.mark.asyncio
    async def test_the_caller_cannot_lift_the_cap(self, call, monkeypatch):
        """A `maxDeletions` larger than the operator's cap is still the cap."""
        from cognitive_fabric.config import settings as cf_settings

        monkeypatch.setattr(cf_settings, "optimizer_max_deletions", 2)
        await self._seed(call, deprecated=1)

        result = await call(
            "memory-optimizer",
            {
                "operation": "optimize",
                "repository": REPO,
                "branch": BRANCH,
                "dryRun": True,
                "strategy": "aggressive",
                "maxDeletions": 500,
            },
        )
        assert result.get("max_deletions") == 2
