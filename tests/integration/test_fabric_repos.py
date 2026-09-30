"""Integration tests for the Cognitive Fabric substrate (Symbol/Requirement/Trace).

Exercises the new node/rel tables, repositories, link methods, and the
EntityService fabric wrappers against a real KuzuDB.
"""

import pytest
import pytest_asyncio

from cognitive_fabric.db.kuzu_client import KuzuDBClient
from cognitive_fabric.repositories.file_repo import FileRepository
from cognitive_fabric.repositories.graph_projection import projected_graph
from cognitive_fabric.repositories.requirement_repo import RequirementRepository
from cognitive_fabric.repositories.symbol_repo import SymbolRepository
from cognitive_fabric.repositories.trace_repo import TraceRepository
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.entities import (
    FileInput,
    RequirementInput,
    SymbolInput,
    TraceInput,
)

REPO = "fab-repo"
BRANCH = "main"


@pytest.mark.integration
class TestSymbolRepository:
    @pytest_asyncio.fixture
    async def symbol_repo(self, kuzu_client: KuzuDBClient):
        return SymbolRepository(kuzu_client)

    @pytest.mark.asyncio
    async def test_upsert_and_find(self, symbol_repo: SymbolRepository):
        s = await symbol_repo.upsert_symbol(
            REPO,
            SymbolInput(
                id="a.py:foo", name="foo", kind="function", signature="def foo()"
            ),
        )
        assert s.id == "a.py:foo"
        found = await symbol_repo.find_by_id(REPO, "a.py:foo", BRANCH)
        assert found is not None
        assert found.name == "foo"
        assert found.signature == "def foo()"

    @pytest.mark.asyncio
    async def test_evolution_and_defined_in(
        self, symbol_repo: SymbolRepository, kuzu_client: KuzuDBClient
    ):
        await symbol_repo.upsert_symbol(REPO, SymbolInput(id="v1", name="foo"))
        await symbol_repo.upsert_symbol(REPO, SymbolInput(id="v2", name="foo"))
        assert await symbol_repo.link_evolution(REPO, "v2", "v1", BRANCH) is True

        file_repo = FileRepository(kuzu_client)
        await file_repo.upsert_file(
            REPO, FileInput(id="a.py", name="a.py", path="a.py")
        )
        assert await symbol_repo.link_to_file(REPO, "v2", "a.py", BRANCH) is True


@pytest.mark.integration
class TestRequirementRepository:
    @pytest_asyncio.fixture
    async def req_repo(self, kuzu_client: KuzuDBClient):
        return RequirementRepository(kuzu_client)

    @pytest.mark.asyncio
    async def test_upsert_find_and_realised_by(
        self, req_repo: RequirementRepository, kuzu_client: KuzuDBClient
    ):
        r = await req_repo.upsert_requirement(
            REPO,
            RequirementInput(id="req-1", name="Auth", description="Users can log in"),
        )
        assert r.id == "req-1"
        found = await req_repo.find_by_id(REPO, "req-1", BRANCH)
        assert found is not None and found.description == "Users can log in"

        # REALISED_BY a symbol
        symbol_repo = SymbolRepository(kuzu_client)
        await symbol_repo.upsert_symbol(REPO, SymbolInput(id="login", name="fn"))
        assert (
            await req_repo.link_realised_by(REPO, "req-1", "login", "Symbol", BRANCH)
            is True
        )

    @pytest.mark.asyncio
    async def test_realised_by_rejects_bad_target(
        self, req_repo: RequirementRepository
    ):
        with pytest.raises(ValueError):
            await req_repo.link_realised_by(REPO, "req-1", "x", "Rule", BRANCH)


@pytest.mark.integration
class TestTraceRepository:
    @pytest_asyncio.fixture
    async def trace_repo(self, kuzu_client: KuzuDBClient):
        return TraceRepository(kuzu_client)

    @pytest.mark.asyncio
    async def test_upsert_find_and_records(
        self, trace_repo: TraceRepository, kuzu_client: KuzuDBClient
    ):
        t = await trace_repo.upsert_trace(
            REPO, TraceInput(id="tr-1", name="run-1", trace_type="test", content="ok")
        )
        assert t.id == "tr-1"
        found = await trace_repo.find_by_id(REPO, "tr-1", BRANCH)
        assert found is not None and found.trace_type == "test"

        symbol_repo = SymbolRepository(kuzu_client)
        await symbol_repo.upsert_symbol(REPO, SymbolInput(id="s1", name="s1"))
        assert await trace_repo.link_to_symbol(REPO, "tr-1", "s1", BRANCH) is True


@pytest.mark.integration
class TestEntityServiceFabric:
    @pytest.mark.asyncio
    async def test_fabric_wrappers(self, memory_service: MemoryService):
        entity = await memory_service.entity

        await entity.create_symbol(
            REPO, SymbolInput(id="mod:fn", name="fn", kind="function")
        )
        assert (await entity.get_symbol(REPO, "mod:fn", BRANCH)).name == "fn"

        await entity.create_requirement(REPO, RequirementInput(id="R1", name="Req1"))
        assert (await entity.get_requirement(REPO, "R1", BRANCH)).name == "Req1"

        await entity.create_trace(REPO, TraceInput(id="T1", name="Trace1"))
        assert (await entity.get_trace(REPO, "T1", BRANCH)).name == "Trace1"

        # relationships via the service
        await entity.create_file(REPO, FileInput(id="m.py", name="m.py", path="m.py"))
        assert await entity.link_symbol_to_file(REPO, "mod:fn", "m.py", BRANCH) is True
        assert await entity.link_trace_to_symbol(REPO, "T1", "mod:fn", BRANCH) is True
        assert (
            await entity.link_requirement_realised_by(
                REPO, "R1", "mod:fn", "Symbol", BRANCH
            )
            is True
        )


@pytest.mark.integration
class TestGraphProjectionIsolation:
    @pytest.mark.asyncio
    async def test_projection_names_are_unique_per_call(
        self, kuzu_client: KuzuDBClient
    ):
        """Two calls with the same requested name must not share a projection.

        ``project_graph`` / ``drop_projected_graph`` are database-global, so a
        caller-supplied or fixed name lets one session drop a projection another
        session is still reading.
        """
        with projected_graph(
            kuzu_client, "cycles", ["Component"], ["DEPENDS_ON"]
        ) as outer:
            with projected_graph(
                kuzu_client, "cycles", ["Component"], ["DEPENDS_ON"]
            ) as inner:
                assert inner != outer
                names = {row["name"] for row in _live_projections(kuzu_client)}
                assert {outer, inner} <= names

            # The inner context dropped only its own projection. If the names
            # had collided, `outer` would be gone here.
            names = {row["name"] for row in _live_projections(kuzu_client)}
            assert outer in names
            assert inner not in names
            # ... and the surviving projection is still usable.
            assert (
                kuzu_client.fetch_all(
                    f"CALL weakly_connected_components('{outer}') "
                    "RETURN node.id AS id LIMIT 1"
                )
                == []
            )

        assert _live_projections(kuzu_client) == []


def _live_projections(client: KuzuDBClient) -> list[dict]:
    return client.fetch_all("CALL show_projected_graphs() RETURN *")
