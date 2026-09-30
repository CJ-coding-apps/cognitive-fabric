"""Integration tests for the domain services (via MemoryService).

Exercises the service -> repository path for every entity type plus queries and
graph analysis, against a real KuzuDB, to surface never-run service-layer bugs.
"""

import pytest

from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.entities import (
    ComponentInput,
    ContextInput,
    DecisionInput,
    FileInput,
    MetadataInput,
    RuleInput,
)

REPO = "svc-repo"
BRANCH = "main"


@pytest.mark.integration
class TestMemoryBankService:
    @pytest.mark.asyncio
    async def test_init_and_get_metadata(self, memory_service: MemoryService):
        mb = await memory_service.memory_bank
        result = await mb.init_memory_bank(None, "/tmp/cf-test-project", REPO, BRANCH)
        assert result is not None

        meta = await mb.get_memory_bank_metadata(REPO, BRANCH)
        assert meta is not None

        assert await mb.check_memory_bank_exists(REPO, BRANCH) is True


@pytest.mark.integration
class TestEntityService:
    @pytest.mark.asyncio
    async def test_component_roundtrip(self, memory_service: MemoryService):
        entity = await memory_service.entity
        await entity.create_component(
            REPO, ComponentInput(id="c1", name="C1", kind="service")
        )
        got = await entity.get_component(REPO, "c1", BRANCH)
        assert got is not None and got.name == "C1"

    @pytest.mark.asyncio
    async def test_decision_roundtrip(self, memory_service: MemoryService):
        entity = await memory_service.entity
        await entity.create_decision(
            REPO, DecisionInput(id="d1", name="D1", date="2024-01-15")
        )
        got = await entity.get_decision(REPO, "d1", BRANCH)
        assert got is not None and got.name == "D1"

    @pytest.mark.asyncio
    async def test_rule_roundtrip(self, memory_service: MemoryService):
        entity = await memory_service.entity
        await entity.create_rule(
            REPO, RuleInput(id="r1", name="R1", created="2024-01-15", content="x")
        )
        got = await entity.get_rule(REPO, "r1", BRANCH)
        assert got is not None and got.name == "R1"

    @pytest.mark.asyncio
    async def test_file_roundtrip(self, memory_service: MemoryService):
        entity = await memory_service.entity
        await entity.create_file(
            REPO, FileInput(id="f1", name="a.py", path="/src/a.py")
        )
        got = await entity.get_file(REPO, "f1", BRANCH)
        assert got is not None and got.path == "/src/a.py"


@pytest.mark.integration
class TestContextService:
    @pytest.mark.asyncio
    async def test_context_roundtrip(self, memory_service: MemoryService):
        ctx = await memory_service.context
        await ctx.update_context(
            REPO,
            ContextInput(id="ctx1", name="Ctx1", iso_date="2024-01-15", summary="s"),
        )
        got = await ctx.get_context(REPO, "ctx1", BRANCH)
        assert got is not None


@pytest.mark.integration
class TestMetadataService:
    @pytest.mark.asyncio
    async def test_metadata_roundtrip(self, memory_service: MemoryService):
        md = await memory_service.metadata
        await md.upsert_metadata(
            REPO, MetadataInput(id="m1", name="metadata", architecture="layered")
        )
        got = await md.get_metadata(REPO, "m1", BRANCH)
        assert got is not None


@pytest.mark.integration
class TestGraphServices:
    @pytest.mark.asyncio
    async def test_query_entities(self, memory_service: MemoryService):
        entity = await memory_service.entity
        await entity.create_component(REPO, ComponentInput(id="qc1", name="QC1"))

        gq = await memory_service.graph_query
        results = await gq.query_entities(REPO, "component", BRANCH)
        assert isinstance(results, list)
        assert any(r.get("id") == "qc1" for r in results)

    @pytest.mark.asyncio
    async def test_graph_statistics(self, memory_service: MemoryService):
        ga = await memory_service.graph_analysis
        stats = await ga.get_graph_statistics(REPO, BRANCH)
        assert isinstance(stats, dict)
