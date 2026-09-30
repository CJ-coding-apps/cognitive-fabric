"""Snapshot service for creating and managing database snapshots."""

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Optional

import structlog

from cognitive_fabric.types.optimization import SnapshotInfo

if TYPE_CHECKING:
    from cognitive_fabric.services.service_container import ServiceContainer

logger = structlog.get_logger(__name__)


class SnapshotService:
    """Service for creating and managing database snapshots.

    Snapshots allow rolling back to a previous state of the memory bank.
    """

    def __init__(
        self,
        db_path: str,
        container: "ServiceContainer",
    ) -> None:
        """Initialize the snapshot service.

        Args:
            db_path: Path to the KuzuDB database.
            container: The service container.
        """
        self._db_path = Path(db_path)
        self._container = container
        self._snapshots_dir = self._db_path.parent / "snapshots"
        self._manifest_path = self._snapshots_dir / "manifest.json"

        # Ensure snapshots directory exists
        self._snapshots_dir.mkdir(parents=True, exist_ok=True)

    def _load_manifest(self) -> dict[str, Any]:
        """Load the snapshots manifest.

        Returns:
            The manifest dictionary.
        """
        if self._manifest_path.exists():
            try:
                with open(self._manifest_path, "r") as f:
                    return json.load(f)
            except (json.JSONDecodeError, IOError) as e:
                logger.warning("Failed to load manifest", error=str(e))

        return {"snapshots": []}

    def _save_manifest(self, manifest: dict[str, Any]) -> None:
        """Save the snapshots manifest.

        Args:
            manifest: The manifest dictionary to save.
        """
        with open(self._manifest_path, "w") as f:
            json.dump(manifest, f, indent=2)

    async def create_snapshot(
        self,
        repository: str,
        branch: str = "main",
        description: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> SnapshotInfo:
        """Create a new snapshot of the database.

        Args:
            repository: The repository name.
            branch: The branch name.
            description: Optional description of the snapshot.
            metadata: Optional metadata to store with the snapshot.

        Returns:
            Information about the created snapshot.
        """
        timestamp = datetime.now(timezone.utc).replace(tzinfo=None)
        snapshot_id = f"{repository}_{branch}_{timestamp.strftime('%Y%m%d_%H%M%S')}"
        snapshot_path = self._snapshots_dir / snapshot_id

        logger.info(
            "Creating snapshot",
            snapshot_id=snapshot_id,
            repository=repository,
            branch=branch,
        )

        try:
            # Copy the database directory
            if self._db_path.exists():
                shutil.copytree(self._db_path, snapshot_path)
            else:
                logger.warning(
                    "Database path does not exist", db_path=str(self._db_path)
                )
                snapshot_path.mkdir(parents=True, exist_ok=True)

            # Calculate size
            size = sum(
                f.stat().st_size
                for f in snapshot_path.rglob("*")
                if f.is_file()
            )

            # Create snapshot info
            snapshot_info = SnapshotInfo(
                id=snapshot_id,
                repository=repository,
                branch=branch,
                created_at=timestamp,
                description=description or f"Snapshot of {repository}:{branch}",
                metadata=metadata or {},
                size_bytes=size,
            )

            # Update manifest
            manifest = self._load_manifest()
            manifest["snapshots"].append(snapshot_info.model_dump(mode="json"))
            self._save_manifest(manifest)

            logger.info(
                "Snapshot created",
                snapshot_id=snapshot_id,
                size_bytes=size,
            )

            return snapshot_info

        except Exception as e:
            logger.error(
                "Failed to create snapshot",
                snapshot_id=snapshot_id,
                error=str(e),
            )
            # Clean up partial snapshot
            if snapshot_path.exists():
                shutil.rmtree(snapshot_path, ignore_errors=True)
            raise

    async def rollback_to_snapshot(
        self,
        snapshot_id: str,
    ) -> dict[str, Any]:
        """Rollback the database to a previous snapshot.

        Args:
            snapshot_id: The ID of the snapshot to rollback to.

        Returns:
            Result of the rollback operation.
        """
        manifest = self._load_manifest()
        snapshot_entry = None

        for entry in manifest["snapshots"]:
            if entry["id"] == snapshot_id:
                snapshot_entry = entry
                break

        if not snapshot_entry:
            return {
                "success": False,
                "error": f"Snapshot not found: {snapshot_id}",
            }

        snapshot_path = self._snapshots_dir / snapshot_id

        if not snapshot_path.exists():
            return {
                "success": False,
                "error": f"Snapshot directory not found: {snapshot_id}",
            }

        logger.info(
            "Rolling back to snapshot",
            snapshot_id=snapshot_id,
        )

        try:
            # Create a backup of current state before rollback
            _ts = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
            backup_id = f"pre_rollback_{_ts}"
            backup_path = self._snapshots_dir / backup_id

            if self._db_path.exists():
                shutil.copytree(self._db_path, backup_path)
                logger.info("Created pre-rollback backup", backup_id=backup_id)

            # Remove current database
            if self._db_path.exists():
                shutil.rmtree(self._db_path)

            # Restore from snapshot
            shutil.copytree(snapshot_path, self._db_path)

            logger.info(
                "Rollback complete",
                snapshot_id=snapshot_id,
                backup_id=backup_id,
            )

            return {
                "success": True,
                "message": f"Rolled back to snapshot: {snapshot_id}",
                "snapshot_id": snapshot_id,
                "backup_id": backup_id,
                "repository": snapshot_entry.get("repository"),
                "branch": snapshot_entry.get("branch"),
            }

        except Exception as e:
            logger.error(
                "Failed to rollback",
                snapshot_id=snapshot_id,
                error=str(e),
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def list_snapshots(
        self,
        repository: Optional[str] = None,
        branch: Optional[str] = None,
    ) -> list[SnapshotInfo]:
        """List available snapshots.

        Args:
            repository: Optional repository filter.
            branch: Optional branch filter.

        Returns:
            List of snapshot information.
        """
        manifest = self._load_manifest()
        snapshots = []

        for entry in manifest["snapshots"]:
            # Apply filters
            if repository and entry.get("repository") != repository:
                continue
            if branch and entry.get("branch") != branch:
                continue

            # Check if snapshot directory still exists
            snapshot_path = self._snapshots_dir / entry["id"]
            if not snapshot_path.exists():
                continue

            try:
                snapshots.append(SnapshotInfo(**entry))
            except Exception as e:
                logger.warning(
                    "Invalid snapshot entry",
                    snapshot_id=entry.get("id"),
                    error=str(e),
                )

        # Sort by creation time, newest first
        snapshots.sort(key=lambda s: s.created_at, reverse=True)

        return snapshots

    async def delete_snapshot(
        self,
        snapshot_id: str,
    ) -> dict[str, Any]:
        """Delete a snapshot.

        Args:
            snapshot_id: The ID of the snapshot to delete.

        Returns:
            Result of the deletion.
        """
        manifest = self._load_manifest()
        found = False

        for i, entry in enumerate(manifest["snapshots"]):
            if entry["id"] == snapshot_id:
                manifest["snapshots"].pop(i)
                found = True
                break

        if not found:
            return {
                "success": False,
                "error": f"Snapshot not found in manifest: {snapshot_id}",
            }

        snapshot_path = self._snapshots_dir / snapshot_id

        try:
            if snapshot_path.exists():
                shutil.rmtree(snapshot_path)

            self._save_manifest(manifest)

            logger.info("Snapshot deleted", snapshot_id=snapshot_id)

            return {
                "success": True,
                "message": f"Deleted snapshot: {snapshot_id}",
                "snapshot_id": snapshot_id,
            }

        except Exception as e:
            logger.error(
                "Failed to delete snapshot",
                snapshot_id=snapshot_id,
                error=str(e),
            )
            return {
                "success": False,
                "error": str(e),
            }

    async def get_snapshot(
        self,
        snapshot_id: str,
    ) -> Optional[SnapshotInfo]:
        """Get information about a specific snapshot.

        Args:
            snapshot_id: The snapshot ID.

        Returns:
            Snapshot information, or None if not found.
        """
        manifest = self._load_manifest()

        for entry in manifest["snapshots"]:
            if entry["id"] == snapshot_id:
                snapshot_path = self._snapshots_dir / snapshot_id
                if snapshot_path.exists():
                    try:
                        return SnapshotInfo(**entry)
                    except Exception:
                        pass

        return None

    async def cleanup_old_snapshots(
        self,
        max_age_days: int = 30,
        max_count: int = 10,
    ) -> dict[str, Any]:
        """Clean up old snapshots.

        Args:
            max_age_days: Maximum age of snapshots to keep.
            max_count: Maximum number of snapshots to keep.

        Returns:
            Cleanup results.
        """
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        snapshots = await self.list_snapshots()

        deleted = []

        # Delete old snapshots
        for snapshot in snapshots:
            age_days = (now - snapshot.created_at).days
            if age_days > max_age_days:
                result = await self.delete_snapshot(snapshot.id)
                if result.get("success"):
                    deleted.append(snapshot.id)

        # Delete excess snapshots (keep newest)
        remaining = await self.list_snapshots()
        if len(remaining) > max_count:
            for snapshot in remaining[max_count:]:
                result = await self.delete_snapshot(snapshot.id)
                if result.get("success"):
                    deleted.append(snapshot.id)

        return {
            "success": True,
            "deleted_count": len(deleted),
            "deleted_snapshots": deleted,
            "remaining_count": len(await self.list_snapshots()),
        }
