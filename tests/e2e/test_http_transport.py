"""The HTTP transport's Host/Origin guard, and the loopback-only bind.

Binding ``127.0.0.1`` is not on its own a control. A page in a browser can reach
loopback, and DNS rebinding lets a name the attacker controls resolve there — at
which point the page's requests arrive carrying the attacker's ``Host`` and reach
every tool this server registers. The SDK's middleware refuses exactly those
requests, but only when it is handed settings; with none, it leaves the check off.
So these tests drive real requests at the real app and assert on the status the
guard returns, rather than asserting that a settings object was constructed.
"""

import contextlib
from pathlib import Path

import httpx
import pytest

from cognitive_fabric.mcp.server import (
    create_http_app,
    create_server,
    loopback_hosts,
    loopback_origins,
    require_loopback,
)

# A real port, not 0: the allowlist is built from the port actually bound, and a
# wildcard would defeat the point of naming the host at all.
PORT = 8137
BASE = f"http://127.0.0.1:{PORT}"

INITIALIZE = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "initialize",
    "params": {
        "protocolVersion": "2024-11-05",
        "capabilities": {},
        "clientInfo": {"name": "cf-http-test", "version": "0"},
    },
}


@contextlib.asynccontextmanager
async def serving(db_path: Path):
    """The app the server actually serves, with its session manager running.

    A context manager rather than a fixture: the session manager's task group belongs
    to the task that opened it, and pytest-asyncio does not guarantee that a fixture's
    setup and teardown run in the same one.
    """
    server = await create_server(str(db_path))
    application = create_http_app(server, "127.0.0.1", PORT)
    async with application.router.lifespan_context(application):
        yield application


async def _post(app, headers: dict[str, str]) -> httpx.Response:
    # The trailing slash is the endpoint itself. Starlette answers a bare `/mcp`
    # with a 307 from the mount, before the guard runs, so posting there would
    # test the router rather than the thing under test.
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url=BASE) as client:
        return await client.post("/mcp/", headers=headers, json=INITIALIZE)


def _headers(**extra: str) -> dict[str, str]:
    return {
        "Host": f"127.0.0.1:{PORT}",
        "Accept": "application/json, text/event-stream",
        "Content-Type": "application/json",
        **extra,
    }


@pytest.mark.e2e
class TestHttpTransport:
    @pytest.mark.asyncio
    async def test_a_loopback_client_is_served(self, db_path: Path):
        """The check must not be a wall: a client on loopback still gets through."""
        async with serving(db_path) as app:
            response = await _post(app, _headers())

        assert response.status_code == 200, response.text
        assert "serverInfo" in response.text

    @pytest.mark.asyncio
    async def test_a_request_naming_another_host_is_refused(self, db_path: Path):
        """What a DNS-rebinding page sends: our address, a Host it controls."""
        async with serving(db_path) as app:
            response = await _post(app, _headers(Host="evil.example"))

        assert response.status_code == 421, response.text

    @pytest.mark.asyncio
    async def test_a_page_on_another_origin_is_refused(self, db_path: Path):
        """The same page, naming a Host we do serve but coming from elsewhere."""
        async with serving(db_path) as app:
            response = await _post(app, _headers(Origin="http://evil.example"))

        assert response.status_code == 403, response.text


@pytest.mark.unit
class TestTheBindItself:
    @pytest.mark.parametrize(
        "host", ["0.0.0.0", "192.168.1.5", "10.0.0.1", "::", "example.com"]
    )
    def test_anything_but_loopback_is_refused(self, host: str):
        with pytest.raises(ValueError, match="no authentication"):
            require_loopback(host)

    @pytest.mark.parametrize("host", ["127.0.0.1", "127.0.0.5", "::1", "localhost"])
    def test_loopback_spellings_are_accepted(self, host: str):
        require_loopback(host)

    @pytest.mark.asyncio
    async def test_run_http_server_refuses_before_it_binds(self, db_path: Path):
        """The refusal has to come before anything is listening, not after."""
        from cognitive_fabric.mcp.server import run_http_server

        with pytest.raises(ValueError, match="no authentication"):
            await run_http_server(db_path=str(db_path), host="0.0.0.0", port=PORT)

    def test_the_allowlists_name_this_bind_and_nothing_else(self):
        assert loopback_hosts("127.0.0.1", PORT) == [
            f"127.0.0.1:{PORT}",
            f"localhost:{PORT}",
        ]
        assert loopback_origins("127.0.0.1", PORT) == [
            f"http://127.0.0.1:{PORT}",
            f"http://localhost:{PORT}",
        ]
