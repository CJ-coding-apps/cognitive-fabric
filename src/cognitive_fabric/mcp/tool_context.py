"""Tool handler context for MCP operations."""

from dataclasses import dataclass, field
from typing import Any, Dict, Optional


@dataclass
class ToolHandlerContext:
    """Context passed to tool handlers.

    This context provides session state and configuration
    that tool handlers may need during execution.
    """

    # Session state
    session: Dict[str, Any] = field(default_factory=dict)

    # Current repository and branch (set after memory-bank init)
    repository: Optional[str] = None
    branch: str = "main"

    # Client project root (set after memory-bank init)
    client_project_root: Optional[str] = None

    # Request metadata
    request_id: Optional[str] = None

    def set_memory_bank(
        self,
        repository: str,
        branch: str,
        client_project_root: str,
    ) -> None:
        """Set the current memory bank context.

        Args:
            repository: The repository name.
            branch: The branch name.
            client_project_root: The client's project root path.
        """
        self.repository = repository
        self.branch = branch
        self.client_project_root = client_project_root
        self.session["repository"] = repository
        self.session["branch"] = branch
        self.session["client_project_root"] = client_project_root

    def get_repository(self) -> str:
        """Get the current repository name.

        Returns:
            The repository name.

        Raises:
            ValueError: If no repository is set.
        """
        if not self.repository:
            raise ValueError(
                "No repository set. Initialize memory bank first with memory-bank tool."
            )
        return self.repository

    def get_branch(self) -> str:
        """Get the current branch name.

        Returns:
            The branch name.
        """
        return self.branch

    def is_initialized(self) -> bool:
        """Check if a memory bank has been initialized.

        Returns:
            True if a memory bank is initialized, False otherwise.
        """
        return self.repository is not None

    def to_dict(self) -> Dict[str, Any]:
        """Convert context to a dictionary.

        Returns:
            Dictionary representation of the context.
        """
        return {
            "repository": self.repository,
            "branch": self.branch,
            "client_project_root": self.client_project_root,
            "request_id": self.request_id,
            "initialized": self.is_initialized(),
        }
