"""The database path has exactly one environment variable name.

The defect these guard against: the setting was called `db_path_override`, which
pydantic-settings reads from COGNITIVE_FABRIC_DB_PATH_OVERRIDE. That name appears
in one commented line of .env.example and nowhere else. Every other surface --
the CLI's `--db-path`, the Dockerfile, docker-compose.yml and
docs/guides/configuration.md -- uses COGNITIVE_FABRIC_DB_PATH.

The container does not run the CLI. It runs `python -m cognitive_fabric.main`,
which passes no path and takes the value from this setting alone. So the image
set a variable nothing read, started with `db_path=None`, and exited on
"db_path is required when creating MemoryService" before it could answer
`initialize`. The Docker job in CI is what caught it -- the image had never been
built. These tests are the same check without needing Docker.

`_env_file=None` keeps each test clear of a developer's own .env, which could
otherwise satisfy the positive assertion by accident or break the negative one.
"""

import pytest

from cognitive_fabric.config import Settings
from cognitive_fabric.mcp.server import create_server
from cognitive_fabric.services.memory_service import MemoryService


def _no_dotenv(monkeypatch):
    """Force server.py's Settings lookups to ignore a developer .env.

    server.py does `from cognitive_fabric.config import Settings`, so the name
    to patch is the one in *its* namespace.
    """
    monkeypatch.setattr(
        "cognitive_fabric.mcp.server.Settings",
        lambda **kw: Settings(_env_file=None, **kw),
    )


class TestOneNameForTheDatabasePath:
    def test_settings_reads_the_documented_env_var(self, monkeypatch, tmp_path):
        """The name in the Dockerfile and the docs is the name settings reads."""
        monkeypatch.setenv("COGNITIVE_FABRIC_DB_PATH", str(tmp_path / "a.db"))
        assert Settings(_env_file=None).db_path == str(tmp_path / "a.db")

    def test_the_second_name_is_not_read(self, monkeypatch, tmp_path):
        """Re-adding COGNITIVE_FABRIC_DB_PATH_OVERRIDE as an alias fails here.

        An alias would leave two names for one setting, which is how the two
        entry points came to disagree in the first place.
        """
        monkeypatch.setenv(
            "COGNITIVE_FABRIC_DB_PATH_OVERRIDE", str(tmp_path / "b.db")
        )
        assert Settings(_env_file=None).db_path is None

    def test_the_field_is_not_named_override(self):
        assert "db_path" in Settings.model_fields
        assert "db_path_override" not in Settings.model_fields


class TestTheEntryPointHonoursIt:
    async def test_a_path_from_the_environment_reaches_the_server(
        self, monkeypatch, tmp_path
    ):
        """`python -m cognitive_fabric.main` calls run_server() with no
        arguments, so the environment is the only route by which the
        container's COGNITIVE_FABRIC_DB_PATH can reach the server."""
        db = str(tmp_path / "env.db")
        monkeypatch.setenv("COGNITIVE_FABRIC_DB_PATH", db)
        _no_dotenv(monkeypatch)

        MemoryService.reset_instance()
        try:
            await create_server()  # no db_path argument: how main.py calls it
            service = MemoryService._instance
            assert service is not None, "no MemoryService was created"
            assert service._db_path == db
        finally:
            MemoryService.reset_instance()

    async def test_no_path_anywhere_fails_rather_than_starting_pathless(
        self, monkeypatch
    ):
        """With neither an argument nor the environment set, the server refuses.

        Starting without a database is the failure this module exists to
        prevent, so a silent default would be worse than the crash.
        """
        monkeypatch.delenv("COGNITIVE_FABRIC_DB_PATH", raising=False)
        _no_dotenv(monkeypatch)

        MemoryService.reset_instance()
        try:
            with pytest.raises(ValueError, match="db_path is required"):
                await create_server()
        finally:
            MemoryService.reset_instance()
