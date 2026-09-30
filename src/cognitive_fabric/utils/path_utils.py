"""Path utilities for file and directory operations."""

import os
from pathlib import Path
from typing import Optional


def get_default_db_path(client_project_root: str, db_name: str = "kuzumem") -> str:
    """Get the default database path for a project.

    Args:
        client_project_root: The root directory of the client project.
        db_name: The database name (without extension).

    Returns:
        The full path to the database directory.
    """
    return os.path.join(client_project_root, ".kuzumem", db_name)


def ensure_directory(path: str) -> str:
    """Ensure a directory exists, creating it if necessary.

    Args:
        path: The directory path.

    Returns:
        The path to the directory.
    """
    Path(path).mkdir(parents=True, exist_ok=True)
    return path


def validate_path(
    path: str,
    must_exist: bool = False,
    root: Optional[str] = None,
) -> bool:
    """Validate a path string, optionally confining it to a root directory.

    Args:
        path: The path to validate.
        must_exist: If True, the path must exist.
        root: If given, the path must resolve inside this directory. Containment
            is checked on fully resolved (``realpath``) paths, so a ``..``
            traversal, an absolute path, or a symlink cannot escape the root.

    Returns:
        True if valid, False otherwise.
    """
    if not path:
        return False

    try:
        resolved = Path(path)

        # Check for path traversal attempts
        if ".." in resolved.parts:
            return False

        if root is not None:
            root_real = os.path.realpath(root)
            if not resolved.is_absolute():
                resolved = Path(root_real) / resolved
            resolved_real = os.path.realpath(resolved)
            # Separator-aware prefix check, so "/root-other" is not accepted as
            # being inside "/root".
            if resolved_real != root_real and not resolved_real.startswith(
                root_real + os.sep
            ):
                return False
            resolved = Path(resolved_real)

        if must_exist:
            return resolved.exists()

        return True

    except (OSError, ValueError):
        return False


def get_snapshot_path(
    client_project_root: str,
    repository: str,
    branch: str,
    snapshot_id: str,
) -> str:
    """Get the path for a snapshot file.

    Args:
        client_project_root: The root directory of the client project.
        repository: The repository name.
        branch: The branch name.
        snapshot_id: The snapshot identifier.

    Returns:
        The full path to the snapshot file.
    """
    snapshot_dir = os.path.join(
        client_project_root,
        ".kuzumem",
        "snapshots",
        repository,
        branch,
    )
    ensure_directory(snapshot_dir)
    return os.path.join(snapshot_dir, f"{snapshot_id}.snapshot")


def get_snapshots_directory(
    client_project_root: str,
    repository: str,
    branch: Optional[str] = None,
) -> str:
    """Get the snapshots directory path.

    Args:
        client_project_root: The root directory of the client project.
        repository: The repository name.
        branch: Optional branch name for branch-specific snapshots.

    Returns:
        The path to the snapshots directory.
    """
    if branch:
        return os.path.join(
            client_project_root,
            ".kuzumem",
            "snapshots",
            repository,
            branch,
        )
    return os.path.join(
        client_project_root,
        ".kuzumem",
        "snapshots",
        repository,
    )


def normalize_path(path: str) -> str:
    """Normalize a path string.

    Args:
        path: The path to normalize.

    Returns:
        The normalized path.
    """
    return os.path.normpath(os.path.abspath(path))
