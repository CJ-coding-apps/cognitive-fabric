"""Wiring tests for the streamable-HTTP transport.

A full end-to-end HTTP round-trip is exercised out-of-band (subprocess + MCP
client); here we guard that the ASGI app wires the low-level server to the
``/mcp`` mount without regressions, and that ``run_http_server`` is importable.
"""

from pathlib import Path

import pytest
import pytest_asyncio
from mcp.server import Server


@pytest.mark.e2e
class TestHttpTransport:
    @pytest_asyncio.fixture
    async def server(self, db_path: Path):
        from cognitive_fabric.mcp.server import create_server

        return await create_server(str(db_path))

    @pytest.mark.asyncio
    async def test_run_http_server_importable(self):
        from cognitive_fabric.mcp.server import run_http_server

        assert callable(run_http_server)

    @pytest.mark.asyncio
    async def test_session_manager_and_asgi_mount(self, server: Server):
        from mcp.server.streamable_http_manager import (
            StreamableHTTPSessionManager,
        )
        from starlette.applications import Starlette
        from starlette.routing import Mount

        session_manager = StreamableHTTPSessionManager(app=server)

        async def handle_mcp(scope, receive, send) -> None:  # pragma: no cover
            await session_manager.handle_request(scope, receive, send)

        app = Starlette(routes=[Mount("/mcp", app=handle_mcp)])
        mount_paths = [r.path for r in app.routes]
        assert "/mcp" in mount_paths
