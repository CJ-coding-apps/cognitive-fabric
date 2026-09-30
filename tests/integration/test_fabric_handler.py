"""Integration tests for the fabric MCP handler + semantic/hybrid search.

Drives the handlers against a real memory_service (real kuzu), validating the
handler -> service -> repository -> graph path end to end. The MCP server itself
is not exercised (see the env note in README); handler logic is what matters.
"""

import pytest

from cognitive_fabric.mcp.handlers.fabric import fabric_handler
from cognitive_fabric.mcp.handlers.search import search_handler
from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.entities import (
    ComponentInput,
    ContextInput,
    DecisionInput,
    FileInput,
    SymbolInput,
    TraceInput,
)
from cognitive_fabric.utils.id_utils import format_graph_unique_id

REPO = "h-repo"
BRANCH = "main"


async def _fab(op, memory_service, context=None, **kw):
    params = {"operation": op, "repository": REPO, "branch": BRANCH, **kw}
    return await fabric_handler(params, context, memory_service)


@pytest.mark.integration
class TestFabricHandler:
    @pytest.mark.asyncio
    async def test_record_event(self, memory_service: MemoryService):
        r = await _fab(
            "record-event", memory_service,
            eventSummary="did x", eventObservation="it worked",
        )
        assert r["success"] is True

    @pytest.mark.asyncio
    async def test_record_event_requires_fields(self, memory_service: MemoryService):
        r = await _fab("record-event", memory_service, eventSummary="x")
        assert r["success"] is False

    @pytest.mark.asyncio
    async def test_links_and_query_evolution(self, memory_service: MemoryService):
        entity = await memory_service.entity
        await entity.create_symbol(REPO, SymbolInput(id="s1", name="s1"))
        await entity.create_symbol(REPO, SymbolInput(id="s2", name="s2"))
        await entity.create_file(REPO, FileInput(id="f.py", name="f.py", path="f.py"))
        await entity.create_trace(REPO, TraceInput(id="t1", name="t1"))

        assert (
            await _fab("link-to-file", memory_service, symbolId="s1", fileId="f.py")
        )["success"] is True
        assert (
            await _fab("link-to-symbol", memory_service, traceId="t1", symbolId="s1")
        )["success"] is True
        assert (
            await _fab(
                "link-evolution", memory_service,
                itemType="symbol", currentId="s2", previousId="s1",
            )
        )["success"] is True

        qe = await _fab(
            "query-evolution", memory_service, itemId="s2", itemType="Symbol"
        )
        assert qe["success"] is True
        ids = {row["id"] for row in qe["data"]["lineage"]}
        assert {"s1", "s2"} <= ids  # self (0-hop) + ancestor

    @pytest.mark.asyncio
    async def test_query_rationale(self, memory_service: MemoryService):
        entity = await memory_service.entity
        await entity.create_symbol(REPO, SymbolInput(id="sym", name="sym"))
        await entity.create_decision(
            REPO, DecisionInput(id="d1", name="D1", date="2024-01-01")
        )
        kuzu = await memory_service.get_kuzu_client()
        kuzu.execute_query(
            "MATCH (d:Decision {graph_unique_id: $d}) "
            "MATCH (s:Symbol {graph_unique_id: $s}) MERGE (d)-[:JUSTIFIES]->(s)",
            {
                "d": format_graph_unique_id(REPO, BRANCH, "d1"),
                "s": format_graph_unique_id(REPO, BRANCH, "sym"),
            },
        )
        qr = await _fab("query-rationale", memory_service, itemId="sym")
        assert qr["success"] is True
        assert any(row["id"] == "d1" for row in qr["data"]["decisions"])

    @pytest.mark.asyncio
    async def test_dream_skips_without_llm(self, memory_service: MemoryService):
        ctx = await memory_service.context
        await ctx.update_context(
            REPO, ContextInput(id="c1", name="c1", iso_date="2024-01-01", summary="s")
        )
        r = await _fab("dream", memory_service)
        assert r["success"] is True
        assert r["data"]["status"] == "skipped"

    @pytest.mark.asyncio
    async def test_unknown_operation(self, memory_service: MemoryService):
        r = await _fab("nope", memory_service)
        assert r["success"] is False

    @pytest.mark.asyncio
    async def test_ingest_ast(self, memory_service: MemoryService, tmp_path):
        pytest.importorskip("tree_sitter_language_pack")
        (tmp_path / "m.py").write_text("def hello():\n    return 1\n")
        ctx = ToolHandlerContext(client_project_root=str(tmp_path))
        r = await _fab("ingest-ast", memory_service, context=ctx, path=str(tmp_path))
        assert r["success"] is True
        assert r["data"]["symbols_upserted"] >= 1

    @pytest.mark.asyncio
    async def test_ingest_ast_refused_without_session_root(
        self, memory_service: MemoryService, tmp_path
    ):
        """No clientProjectRoot -> nothing to confine against -> refuse.

        Deliberately not gated on the tree-sitter extra: this is the confinement
        check, and it must run wherever the suite runs.
        """
        (tmp_path / "m.py").write_text("def hello():\n    return 1\n")
        r = await _fab("ingest-ast", memory_service, path=str(tmp_path))
        assert r["success"] is False
        assert "clientProjectRoot" in r["error"]

    @pytest.mark.asyncio
    async def test_ingest_ast_refused_outside_session_root(
        self, memory_service: MemoryService, tmp_path
    ):
        root = tmp_path / "root"
        root.mkdir()
        outside = tmp_path / "outside"
        outside.mkdir()
        (outside / "m.py").write_text("def hello():\n    return 1\n")
        ctx = ToolHandlerContext(client_project_root=str(root))
        r = await _fab("ingest-ast", memory_service, context=ctx, path=str(outside))
        assert r["success"] is False
        assert "clientProjectRoot" in r["error"]

    @pytest.mark.asyncio
    async def test_ingest_ast_refused_traversal(
        self, memory_service: MemoryService, tmp_path
    ):
        root = tmp_path / "root"
        root.mkdir()
        ctx = ToolHandlerContext(client_project_root=str(root))
        r = await _fab("ingest-ast", memory_service, context=ctx, path="../")
        assert r["success"] is False


@pytest.mark.integration
class TestSearchSemanticHybrid:
    @pytest.mark.asyncio
    async def test_semantic_search_runs(self, memory_service: MemoryService):
        r = await search_handler(
            {
                "searchType": "semantic", "repository": REPO,
                "query": "foo", "branch": BRANCH,
            },
            None,
            memory_service,
        )
        assert r["success"] is True
        assert r["searchType"] == "semantic"
        assert isinstance(r["results"], list)
        # Nothing ingested for this repo -> no results (whether the semantic
        # layer is available or gracefully degraded).
        assert r["results"] == []

    @pytest.mark.asyncio
    async def test_hybrid_includes_fulltext(self, memory_service: MemoryService):
        entity = await memory_service.entity
        await entity.create_component(
            REPO, ComponentInput(id="c-auth", name="AuthService", kind="service")
        )
        r = await search_handler(
            {
                "searchType": "hybrid",
                "repository": REPO,
                "query": "auth",
                "branch": BRANCH,
                "entityTypes": ["component"],
            },
            None,
            memory_service,
        )
        assert r["success"] is True
        assert any(res["id"] == "c-auth" for res in r["results"])
