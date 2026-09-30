"""End-to-end tests for MCP server + tool dispatch via the ToolRegistry.

Requires the low-level MCP SDK (1.x `Server` decorator API). Skipped when the
installed `mcp` package doesn't provide it. Tool workflows are driven through the
real ToolRegistry -> handler -> service -> KuzuDB path.
"""

import json
from pathlib import Path

import pytest
import pytest_asyncio
from mcp.server import Server

from cognitive_fabric.mcp.server import build_mcp_tools, create_server
from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.mcp.tool_registry import ToolRegistry
from cognitive_fabric.services.memory_service import MemoryService

pytestmark = pytest.mark.skipif(
    not hasattr(Server, "list_tools"),
    reason="Installed mcp SDK lacks the 1.x low-level Server decorator API",
)

# The frozen tool surface. Regenerate deliberately (and say so in the commit)
# when the surface really changes — a rename or schema edit must not pass
# silently, which is why this is an exact match and not a membership test.
SNAPSHOT_PATH = Path(__file__).parent / "tools_snapshot.json"


def _tool_surface(tool) -> dict:
    """The frozen part of one tool: what a client sees and classifies on.

    Descriptions are deliberately excluded — the published fingerprint is names,
    schemas and annotations. Extend this deliberately, not by accident.
    """
    annotations = tool.annotations
    return {
        "name": tool.name,
        "inputSchema": tool.inputSchema,
        "annotations": (
            None
            if annotations is None
            else {
                "readOnlyHint": annotations.readOnlyHint,
                "destructiveHint": annotations.destructiveHint,
            }
        ),
    }


def _live_surface() -> list:
    """The tool surface exactly as the server advertises it."""
    tools = build_mcp_tools(ToolRegistry())
    return sorted((_tool_surface(t) for t in tools), key=lambda t: t["name"])


def _saved_surface() -> list:
    return json.loads(SNAPSHOT_PATH.read_text())


@pytest.mark.e2e
class TestMCPServer:
    @pytest_asyncio.fixture
    async def mcp_server(self, db_path: Path):
        return await create_server(str(db_path))

    @pytest.mark.asyncio
    async def test_server_creation(self, mcp_server):
        assert mcp_server is not None

    @pytest.mark.asyncio
    async def test_list_tools(self):
        live, saved = _live_surface(), _saved_surface()
        assert [t["name"] for t in live] == [t["name"] for t in saved], (
            "The set of advertised tools changed. If that is intended, "
            f"re-freeze {SNAPSHOT_PATH.name}."
        )
        for live_tool, saved_tool in zip(live, saved):
            assert live_tool == saved_tool, (
                f"Tool surface changed for {live_tool['name']!r}. If that is "
                f"intended, re-freeze {SNAPSHOT_PATH.name}."
            )

    @pytest.mark.asyncio
    async def test_every_tool_is_annotated(self):
        """An unclassified tool must not reach a client."""
        for tool in build_mcp_tools(ToolRegistry()):
            assert tool.annotations is not None, (
                f"Tool {tool.name!r} has no annotations"
            )


@pytest.mark.e2e
class TestMCPToolWorkflow:
    @pytest_asyncio.fixture
    async def call(self, memory_service: MemoryService):
        """A bound tool caller: call(name, params) -> result dict."""
        registry = ToolRegistry()
        ctx = ToolHandlerContext()

        async def _call(name, params):
            return await registry.call_tool(name, params, ctx, memory_service)

        return _call

    async def _init(self, call, temp_dir):
        return await call(
            "memory-bank",
            {
                "operation": "init",
                "repository": "test-repo",
                "branch": "main",
                "clientProjectRoot": str(temp_dir),
            },
        )

    @pytest.mark.asyncio
    async def test_memory_bank_init_workflow(self, call, temp_dir: Path):
        result = await self._init(call, temp_dir)
        assert result.get("success") is True or "initialized" in str(result).lower()

    @pytest.mark.asyncio
    async def test_entity_crud_workflow(self, call, temp_dir: Path):
        await self._init(call, temp_dir)
        create_result = await call(
            "entity",
            {
                "operation": "create",
                "entityType": "component",
                "repository": "test-repo",
                "branch": "main",
                "data": {
                    "id": "test-component",
                    "name": "TestComponent",
                    "kind": "service",
                    "status": "active",
                },
            },
        )
        assert create_result.get("success") is True

        get_result = await call(
            "entity",
            {
                "operation": "get",
                "entityType": "component",
                "repository": "test-repo",
                "branch": "main",
                "id": "test-component",
            },
        )
        assert get_result is not None
        assert get_result.get("success") is True

    @pytest.mark.asyncio
    async def test_query_workflow(self, call, temp_dir: Path):
        await self._init(call, temp_dir)
        await call(
            "entity",
            {
                "operation": "create",
                "entityType": "component",
                "repository": "test-repo",
                "branch": "main",
                "data": {"id": "q-comp", "name": "QComponent", "kind": "service"},
            },
        )
        query_result = await call(
            "query",
            {
                "searchType": "entities",
                "operation": "entities",
                "repository": "test-repo",
                "branch": "main",
                "entityType": "component",
            },
        )
        assert query_result is not None

    @pytest.mark.asyncio
    async def test_introspect_workflow(self, call, temp_dir: Path):
        await self._init(call, temp_dir)
        labels = await call(
            "introspect",
            {"operation": "labels", "repository": "test-repo", "branch": "main"},
        )
        assert labels is not None

    @pytest.mark.asyncio
    async def test_analyze_workflow(self, call, temp_dir: Path):
        await self._init(call, temp_dir)
        for i in range(3):
            await call(
                "entity",
                {
                    "operation": "create",
                    "entityType": "component",
                    "repository": "test-repo",
                    "branch": "main",
                    "data": {
                        "id": f"a-comp-{i}",
                        "name": f"AComponent{i}",
                        "kind": "service",
                    },
                },
            )
        pagerank = await call(
            "analyze",
            {"operation": "pagerank", "repository": "test-repo", "branch": "main"},
        )
        assert pagerank is not None

    @pytest.mark.asyncio
    async def test_detect_workflow(self, call, temp_dir: Path):
        await self._init(call, temp_dir)
        cycles = await call(
            "detect",
            {"operation": "cycles", "repository": "test-repo", "branch": "main"},
        )
        assert cycles is not None
        islands = await call(
            "detect",
            {"operation": "islands", "repository": "test-repo", "branch": "main"},
        )
        assert islands is not None
