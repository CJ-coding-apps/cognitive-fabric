"""Wire-contract tests: TypeScript KuzuMem-MCP parameter names.

Each conformed tool is exercised through the real ToolRegistry -> handler ->
service -> KuzuDB path using the TS wire parameter names (the additive
aliases), asserting the tools accept them and return a non-error result.
"""

from pathlib import Path

import pytest
import pytest_asyncio

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.mcp.tool_registry import ToolRegistry
from cognitive_fabric.services.memory_service import MemoryService

REPO = "wire-repo"
BRANCH = "main"


@pytest.mark.integration
class TestWireContract:
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
        """Initialize the memory bank and seed a component + tag."""
        await call(
            "memory-bank",
            {
                "operation": "init",
                "repository": REPO,
                "branch": BRANCH,
                "clientProjectRoot": str(temp_dir),
            },
        )
        await call(
            "entity",
            {
                "operation": "create",
                "entityType": "component",
                "repository": REPO,
                "branch": BRANCH,
                "data": {"id": "wc-comp", "name": "WireComp", "kind": "service"},
            },
        )
        await call(
            "entity",
            {
                "operation": "create",
                "entityType": "tag",
                "repository": REPO,
                "branch": BRANCH,
                "data": {"id": "wc-tag", "name": "WireTag"},
            },
        )
        return call

    @pytest.mark.asyncio
    async def test_query_type_alias(self, initialized):
        call = initialized
        result = await call(
            "query",
            {
                "type": "entities",
                "repository": REPO,
                "branch": BRANCH,
                "label": "component",
            },
        )
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_introspect_query_and_target_alias(self, initialized):
        call = initialized
        result = await call(
            "introspect",
            {
                "query": "properties",
                "target": "Component",
                "repository": REPO,
                "branch": BRANCH,
            },
        )
        assert result.get("success") is True
        assert result.get("label") == "Component"

    @pytest.mark.asyncio
    async def test_search_mode_alias(self, initialized):
        call = initialized
        result = await call(
            "search",
            {
                "mode": "fulltext",
                "repository": REPO,
                "branch": BRANCH,
                "query": "Wire",
            },
        )
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_search_semantic_mode(self, initialized):
        # In Cognitive Fabric, `mode: semantic` is a real search path backed by
        # the vector store (not a graceful-degrade stub). It must accept the TS
        # wire `mode` alias, report success, and expose the fabric `available`
        # flag.
        call = initialized
        result = await call(
            "search",
            {
                "mode": "semantic",
                "repository": REPO,
                "branch": BRANCH,
                "query": "Wire",
                "threshold": 0.5,
            },
        )
        assert result.get("success") is True
        assert result.get("searchType") == "semantic"
        assert "available" in result

    @pytest.mark.asyncio
    async def test_associate_tag_item_ts_names(self, initialized):
        call = initialized
        result = await call(
            "associate",
            {
                "type": "tag-item",
                "repository": REPO,
                "branch": BRANCH,
                "itemId": "wc-comp",
                "tagId": "wc-tag",
                "entityType": "Component",
            },
        )
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_delete_operation_alias(self, initialized):
        call = initialized
        result = await call(
            "delete",
            {
                "operation": "bulk-by-filter",
                "repository": REPO,
                "branch": BRANCH,
                "targetType": "component",
                "filterNamePattern": "nonexistent-xyz",
                "dryRun": True,
            },
        )
        assert result.get("success") is True
        assert result.get("dryRun") is True

    @pytest.mark.asyncio
    async def test_bulk_import_type_and_typed_array(self, initialized):
        call = initialized
        result = await call(
            "bulk-import",
            {
                "type": "components",
                "repository": REPO,
                "branch": BRANCH,
                "components": [
                    {"id": "wc-bulk-1", "name": "Bulk1", "kind": "service"},
                    {"id": "wc-bulk-2", "name": "Bulk2", "kind": "service"},
                ],
            },
        )
        assert result.get("success") is True
        assert result.get("imported_count") == 2

    @pytest.mark.asyncio
    async def test_context_flat_params(self, initialized):
        call = initialized
        result = await call(
            "context",
            {
                "operation": "update",
                "repository": REPO,
                "branch": BRANCH,
                "id": "wc-ctx",
                "name": "WireContext",
                "agent": "wire-agent",
                "summary": "flat summary",
                "observation": "flat observation",
            },
        )
        assert result.get("success") is True

    @pytest.mark.asyncio
    async def test_entity_data_field_aliases(self, initialized):
        call = initialized
        result = await call(
            "entity",
            {
                "operation": "create",
                "entityType": "decision",
                "repository": REPO,
                "branch": BRANCH,
                "data": {
                    "id": "wc-dec",
                    "name": "WireDecision",
                    "date": "2026-01-01",
                    "decisionStatus": "accepted",
                },
            },
        )
        assert result.get("success") is True
        entity = result.get("entity", {})
        assert entity.get("status") == "accepted"

    @pytest.mark.asyncio
    async def test_entity_file_field_aliases(self, initialized):
        call = initialized
        result = await call(
            "entity",
            {
                "operation": "create",
                "entityType": "file",
                "repository": REPO,
                "branch": BRANCH,
                "data": {
                    "id": "wc-file",
                    "name": "wire.py",
                    "path": "/src/wire.py",
                    "size_bytes": 2048,
                    "content_hash": "abc123",
                    "language": "python",
                },
            },
        )
        assert result.get("success") is True
        entity = result.get("entity", {})
        assert entity.get("size") == 2048
        assert entity.get("checksum") == "abc123"
