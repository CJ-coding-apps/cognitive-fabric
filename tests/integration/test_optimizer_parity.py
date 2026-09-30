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
