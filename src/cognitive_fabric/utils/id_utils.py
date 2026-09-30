"""Graph unique ID utilities for repository/branch/entity isolation."""

from typing import NamedTuple


class GraphUniqueIdParts(NamedTuple):
    """Parsed parts of a graph unique ID."""

    repository_name: str
    branch_name: str
    item_id: str


def format_graph_unique_id(
    repository_name: str,
    branch_name: str,
    item_id: str,
) -> str:
    """Generate composite graph-unique ID.

    Format: repositoryName:branchName:itemId

    Args:
        repository_name: The repository name.
        branch_name: The branch name.
        item_id: The entity ID.

    Returns:
        A composite graph-unique ID string.

    Raises:
        ValueError: If any required field is empty or contains colons.
    """
    if not repository_name or not branch_name or not item_id:
        raise ValueError("repository_name, branch_name, and item_id are required")

    if ":" in repository_name:
        raise ValueError(f'Repository name cannot contain colons: "{repository_name}"')

    if ":" in branch_name:
        raise ValueError(f'Branch name cannot contain colons: "{branch_name}"')

    return f"{repository_name}:{branch_name}:{item_id}"


def parse_graph_unique_id(graph_unique_id: str) -> GraphUniqueIdParts:
    """Parse composite graph-unique ID back into components.

    Expected format: repositoryName:branchName:itemId

    Args:
        graph_unique_id: The composite ID to parse.

    Returns:
        A GraphUniqueIdParts named tuple.

    Raises:
        ValueError: If the ID format is invalid.
    """
    if not graph_unique_id:
        raise ValueError("graph_unique_id cannot be empty")

    # Max 2 splits to preserve item_id colons (if any)
    parts = graph_unique_id.split(":", 2)

    if len(parts) < 3:
        raise ValueError(
            "Invalid graph_unique_id format. "
            "Expected repositoryName:branchName:itemId"
        )

    repository_name, branch_name, item_id = parts

    if not repository_name or not branch_name or not item_id:
        raise ValueError("Invalid graph_unique_id: empty component detected")

    return GraphUniqueIdParts(repository_name, branch_name, item_id)


def create_repository_node_id(repository_name: str, branch_name: str) -> str:
    """Create synthetic repository node ID.

    Format: repositoryName:branchName

    Args:
        repository_name: The repository name.
        branch_name: The branch name.

    Returns:
        A repository node ID string.
    """
    if not repository_name:
        raise ValueError("repository_name is required")

    branch = branch_name if branch_name else "main"

    if ":" in repository_name:
        raise ValueError(f'Repository name cannot contain colons: "{repository_name}"')

    if ":" in branch:
        raise ValueError(f'Branch name cannot contain colons: "{branch}"')

    return f"{repository_name}:{branch}"
