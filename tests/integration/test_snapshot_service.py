"""The pre-deletion snapshot, against a real KuzuDB database.

The snapshot is what makes an optimization reversible, so these tests run the
real service on a real database file rather than a stub: every defect they
cover is a property of what is on disk. KuzuDB >= 0.11 stores a database as a
single file plus a sibling ``<path>.wal``, and every write since the last
``CHECKPOINT`` lives in the log rather than in the file -- so a copy taken
without a checkpoint holds no rows, and a restore that leaves a log behind
replays it over the file it just restored.
"""

import asyncio
from pathlib import Path

import pytest
import pytest_asyncio
from click.testing import CliRunner

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.mcp.tool_registry import ToolRegistry
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.services.snapshot_service import (
    SnapshotService,
    _remove_database,
    _wal_path,
)

REPO = "snapshot-repo"
BRANCH = "main"


async def _count_components(client) -> int:
    """How many Component rows the database holds."""
    return client.count("MATCH (c:Component) RETURN count(c)")


async def _seed_components(call, ids: range | list) -> None:
    """Create one deprecated component per id, through the tool surface."""
    for i in ids:
        result = await call(
            "entity",
            {
                "operation": "create",
                "entityType": "component",
                "repository": REPO,
                "branch": BRANCH,
                "data": {
                    "id": f"snap-comp-{i}",
                    "name": f"SnapComp{i}",
                    "kind": "service",
                    "status": "deprecated",
                },
            },
        )
        assert result.get("success") is True, result


@pytest.mark.integration
class TestSnapshotRoundTrip:
    """write rows -> snapshot -> optimizer deletes -> rollback -> rows are back.

    The whole path, over the tool surface the optimizer actually runs on:
    registry -> handler -> snapshot -> delete -> rollback -> reopen.
    """

    @pytest_asyncio.fixture
    async def call(self, memory_service: MemoryService):
        registry = ToolRegistry()
        ctx = ToolHandlerContext()

        async def _call(name, params):
            return await registry.call_tool(name, params, ctx, memory_service)

        return _call

    @pytest_asyncio.fixture
    async def seeded(self, call, temp_dir: Path) -> list[str]:
        await call(
            "memory-bank",
            {
                "operation": "init",
                "repository": REPO,
                "branch": BRANCH,
                "clientProjectRoot": str(temp_dir),
            },
        )
        await _seed_components(call, range(5))
        return [f"snap-comp-{i}" for i in range(5)]

    @pytest.mark.asyncio
    async def test_a_rollback_restores_every_row_the_optimizer_deleted(
        self, call, seeded, memory_service: MemoryService, db_path: Path
    ):
        client = await memory_service.get_kuzu_client()
        assert await _count_components(client) == 5

        run = await call(
            "memory-optimizer",
            {
                "operation": "optimize",
                "repository": REPO,
                "branch": BRANCH,
                "dryRun": False,
                "confirm": True,
                "strategy": "aggressive",
            },
        )
        assert run.get("success") is True, run
        snapshot_id = run.get("snapshot_id")
        assert snapshot_id, f"a real run must name its snapshot: {run}"

        deleted = 5 - await _count_components(client)
        assert deleted > 0, "nothing was deleted, so the rollback would prove nothing"

        rolled_back = await call(
            "memory-optimizer",
            {
                "operation": "rollback",
                "repository": REPO,
                "branch": BRANCH,
                "snapshotId": snapshot_id,
            },
        )
        assert rolled_back.get("success") is True, rolled_back

        # The same client object: the restore closed and reopened it in place.
        client = await memory_service.get_kuzu_client()
        assert await _count_components(client) == 5


@pytest.mark.integration
class TestTheWriteAheadLog:
    """A copy or a restore is only correct if the log is handled."""

    @pytest_asyncio.fixture
    async def call(self, memory_service: MemoryService):
        registry = ToolRegistry()
        ctx = ToolHandlerContext()

        async def _call(name, params):
            return await registry.call_tool(name, params, ctx, memory_service)

        return _call

    async def _init(self, call, temp_dir: Path) -> None:
        await call(
            "memory-bank",
            {
                "operation": "init",
                "repository": REPO,
                "branch": BRANCH,
                "clientProjectRoot": str(temp_dir),
            },
        )

    @pytest.mark.asyncio
    async def test_a_snapshot_checkpoints_before_it_copies(
        self, call, memory_service: MemoryService, db_path: Path, temp_dir: Path
    ):
        """Without the checkpoint the copy is a header and every row is in the log."""
        await self._init(call, temp_dir)
        await _seed_components(call, range(10))

        snapshot = await memory_service.snapshot.create_snapshot(REPO, BRANCH)

        assert not _wal_path(Path(db_path)).exists(), (
            "CHECKPOINT must fold the log into the file, or the copy holds no rows"
        )
        assert snapshot.size_bytes > 100_000, (
            f"{snapshot.size_bytes} bytes is a header, not ten rows"
        )

    @pytest.mark.asyncio
    async def test_a_restore_does_not_replay_the_log_of_the_state_it_replaces(
        self, call, memory_service: MemoryService, db_path: Path, temp_dir: Path
    ):
        """The leftover-log case.

        Rows written after the snapshot live in the log. Restoring over the file
        while that log is still on disk makes the next open replay it, and the
        database reports its pre-restore state instead of the snapshot's. Two
        things prevent that: the log is folded in before the pre-rollback
        backup, and it is deleted along with the file it belonged to.
        """
        await self._init(call, temp_dir)
        await _seed_components(call, range(10))

        snapshot = await memory_service.snapshot.create_snapshot(REPO, BRANCH)

        # Twenty more rows, none of them folded in: they are in the log.
        await _seed_components(call, range(10, 30))
        client = await memory_service.get_kuzu_client()
        assert await _count_components(client) == 30
        assert _wal_path(Path(db_path)).exists(), (
            "the writes after the snapshot should be in the log, not in the file -- "
            "otherwise this test is not in the case it means to be"
        )

        result = await memory_service.snapshot.rollback_to_snapshot(snapshot.id)
        assert result.get("success") is True, result

        client = await memory_service.get_kuzu_client()
        assert await _count_components(client) == 10, (
            "the log of the state we replaced replayed over the restore"
        )

    @pytest.mark.asyncio
    async def test_the_log_of_a_database_is_removed_with_it(self, temp_dir: Path):
        """The rule itself, at the point it is applied.

        A log left beside a database is replayed onto it on the next open, so
        the two have to be removed together. It is worth asserting directly,
        because on the restore path the checkpoint above usually takes the log
        first -- which would let the rule be dropped without any end-to-end
        test noticing until the day the checkpoint is skipped.
        """
        db_path = temp_dir / "removed_with_its_log"
        db_path.write_bytes(b"database")
        _wal_path(db_path).write_bytes(b"log")

        _remove_database(db_path)

        assert not db_path.exists()
        assert not _wal_path(db_path).exists()


@pytest.mark.integration
class TestAFailedSnapshot:
    """A snapshot that did not happen is a reason not to delete anything."""

    @pytest_asyncio.fixture
    async def call(self, memory_service: MemoryService):
        registry = ToolRegistry()
        ctx = ToolHandlerContext()

        async def _call(name, params):
            return await registry.call_tool(name, params, ctx, memory_service)

        return _call

    @pytest_asyncio.fixture
    async def seeded(self, call, temp_dir: Path) -> None:
        await call(
            "memory-bank",
            {
                "operation": "init",
                "repository": REPO,
                "branch": BRANCH,
                "clientProjectRoot": str(temp_dir),
            },
        )
        await _seed_components(call, range(4))

    @pytest.mark.asyncio
    async def test_abort_leaves_every_row_where_it_was(
        self, call, seeded, memory_service: MemoryService, monkeypatch
    ):
        """The default policy: no backup, no deletions, and an error that says so."""

        async def _checkpoint_fails(self) -> None:
            raise RuntimeError("CHECKPOINT left the write-ahead log in place")

        monkeypatch.setattr(SnapshotService, "_checkpoint", _checkpoint_fails)

        client = await memory_service.get_kuzu_client()
        before = await _count_components(client)

        result = await call(
            "memory-optimizer",
            {
                "operation": "optimize",
                "repository": REPO,
                "branch": BRANCH,
                "dryRun": False,
                "confirm": True,
                "strategy": "aggressive",
            },
        )

        assert result.get("success") is False, result
        assert "nothing was deleted" in result.get("error", ""), result
        assert await _count_components(client) == before

    @pytest.mark.asyncio
    async def test_an_explicit_opt_out_still_deletes(
        self, call, seeded, memory_service: MemoryService, monkeypatch
    ):
        """`continue` is the operator accepting an irreversible run; it must work."""
        from cognitive_fabric.config import settings as cf_settings

        async def _checkpoint_fails(self) -> None:
            raise RuntimeError("CHECKPOINT left the write-ahead log in place")

        monkeypatch.setattr(SnapshotService, "_checkpoint", _checkpoint_fails)
        monkeypatch.setattr(
            cf_settings, "optimizer_snapshot_failure_policy", "continue"
        )

        client = await memory_service.get_kuzu_client()
        before = await _count_components(client)

        result = await call(
            "memory-optimizer",
            {
                "operation": "optimize",
                "repository": REPO,
                "branch": BRANCH,
                "dryRun": False,
                "confirm": True,
                "strategy": "aggressive",
            },
        )

        assert result.get("success") is True, result
        assert result.get("snapshot_id") is None, "there was no snapshot to name"
        assert result.get("snapshotFailurePolicy") == "continue"
        assert await _count_components(client) < before, "the opt-out did not run"


@pytest.mark.integration
class TestTheRollbackCommand:
    """The CLI path, which is where an operator actually reaches this."""

    @staticmethod
    async def _seed_snapshot_and_delete(db_path: Path) -> str:
        """Three rows, a snapshot of them, then one deleted. Returns the snapshot id."""
        MemoryService.reset_instance()
        service = await MemoryService.get_instance(str(db_path))
        registry = ToolRegistry()
        ctx = ToolHandlerContext()

        async def call(name, params):
            return await registry.call_tool(name, params, ctx, service)

        try:
            await call(
                "memory-bank",
                {
                    "operation": "init",
                    "repository": REPO,
                    "branch": BRANCH,
                    "clientProjectRoot": str(db_path.parent),
                },
            )
            await _seed_components(call, range(3))

            snapshot = await service.snapshot.create_snapshot(REPO, BRANCH, "cli-test")

            client = await service.get_kuzu_client()
            client.execute_query(
                "MATCH (c:Component {id: $id}) DETACH DELETE c",
                {"id": "snap-comp-0"},
            )
            assert await _count_components(client) == 2

            return snapshot.id
        finally:
            await service.close()
            MemoryService.reset_instance()

    @staticmethod
    async def _count(db_path: Path) -> int:
        MemoryService.reset_instance()
        service = await MemoryService.get_instance(str(db_path))
        try:
            client = await service.get_kuzu_client()
            return await _count_components(client)
        finally:
            await service.close()
            MemoryService.reset_instance()

    def test_the_rollback_command_restores_the_snapshot(self, temp_dir: Path):
        from cognitive_fabric.cli.main import cli

        db_path = temp_dir / "cli_snapshot_db"
        snapshot_id = asyncio.run(self._seed_snapshot_and_delete(db_path))
        assert asyncio.run(self._count(db_path)) == 2

        result = CliRunner().invoke(
            cli, ["rollback", str(db_path), REPO, snapshot_id, "--branch", BRANCH]
        )

        assert result.exit_code == 0, result.output
        assert "Successfully rolled back" in result.output
        assert asyncio.run(self._count(db_path)) == 3
