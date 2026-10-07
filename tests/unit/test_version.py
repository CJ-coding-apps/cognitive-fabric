"""The version number has exactly one home, and everything reports it.

The defect these guard against: the distribution said 1.0.0, the CLI said
1.0.0, and the MCP handshake advertised 1.30.0 -- which was the *mcp* SDK's
version, because the server was constructed without one and the SDK falls back
to `pkg_version("mcp")`. An MCP client that checks a server's version on connect
had nothing real to check.
"""

import tomllib
from importlib.metadata import version
from pathlib import Path

from click.testing import CliRunner

from cognitive_fabric import __app_name__, __version__
from cognitive_fabric._version import DISTRIBUTION_NAME
from cognitive_fabric.cli.main import cli
from cognitive_fabric.mcp.server import create_server
from cognitive_fabric.services.memory_service import MemoryService

REPO_ROOT = Path(__file__).resolve().parents[2]


def _metadata_version() -> str:
    return version(DISTRIBUTION_NAME)


class TestSingleVersionSource:
    def test_package_version_comes_from_metadata(self):
        assert __version__ == _metadata_version()
        assert __version__ != "0.0.0.dev0", (
            "metadata not found; is the package installed?"
        )

    def test_distribution_name_matches_pyproject(self):
        """Renaming the package must fail here, not silently fall back."""
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
        assert pyproject["project"]["name"] == DISTRIBUTION_NAME

    def test_pyproject_version_matches_metadata(self):
        pyproject = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text())
        assert pyproject["project"]["version"] == _metadata_version()

    def test_cli_version_reports_the_metadata_version(self):
        result = CliRunner().invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert _metadata_version() in result.output


class TestMcpHandshakeVersion:
    """The values an MCP client sees in `serverInfo` on connect.

    `db_path` is the shared fixture: a file path in a temp dir, which is what
    Kuzu wants (it rejects a directory).
    """

    async def test_server_advertises_the_package_version(self, db_path):
        """Without an explicit `version=`, this is the mcp SDK's version."""
        MemoryService.reset_instance()
        try:
            server = await create_server(str(db_path))
            options = server.create_initialization_options()
            assert options.server_version == _metadata_version()
        finally:
            MemoryService.reset_instance()

    async def test_server_name_is_stable(self, db_path):
        MemoryService.reset_instance()
        try:
            server = await create_server(str(db_path))
            options = server.create_initialization_options()
            assert options.server_name == __app_name__
        finally:
            MemoryService.reset_instance()
