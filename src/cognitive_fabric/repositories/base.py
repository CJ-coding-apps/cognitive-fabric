"""Base repository class for all repositories."""

from abc import ABC
from datetime import datetime, timezone
from typing import Any, Optional, TypeVar

import structlog

from cognitive_fabric.db.kuzu_client import KuzuDBClient
from cognitive_fabric.utils.id_utils import format_graph_unique_id
from cognitive_fabric.utils.security import escape_cypher_string

T = TypeVar("T")

logger = structlog.get_logger("Repository")


class BaseRepository(ABC):
    """Base class for all repositories.

    Provides common functionality for database operations including:
    - Query execution
    - Result normalization
    - ID generation
    - Timestamp handling
    """

    def __init__(self, kuzu_client: KuzuDBClient) -> None:
        """Initialize the repository.

        Args:
            kuzu_client: The KuzuDB client.
        """
        self._kuzu_client = kuzu_client
        self._logger = logger.bind(
            repository=self.__class__.__name__,
            db_path=kuzu_client.db_path,
        )

    @property
    def kuzu_client(self) -> KuzuDBClient:
        """Get the KuzuDB client."""
        return self._kuzu_client

    def execute_query(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Execute a query with logging.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.

        Returns:
            The query result.
        """
        return self._kuzu_client.execute_query(query, params)

    def fetch_one(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Fetch one result row.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.

        Returns:
            The first row as a dict, or None.
        """
        return self._kuzu_client.fetch_one(query, params)

    def fetch_all(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Fetch all result rows.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.

        Returns:
            All rows as a list of dicts.
        """
        return self._kuzu_client.fetch_all(query, params)

    def count(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> int:
        """Execute a count query.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.

        Returns:
            The count value.
        """
        return self._kuzu_client.count(query, params)

    @staticmethod
    def create_graph_unique_id(
        repository: str,
        branch: str,
        entity_id: str,
    ) -> str:
        """Create a graph-unique ID.

        Args:
            repository: The repository name.
            branch: The branch name.
            entity_id: The entity ID.

        Returns:
            The graph-unique ID.
        """
        return format_graph_unique_id(repository, branch, entity_id)

    @staticmethod
    def escape_string(value: str) -> str:
        """Escape a string for Cypher.

        Args:
            value: The string to escape.

        Returns:
            The escaped string.
        """
        return escape_cypher_string(value)

    @staticmethod
    def get_current_timestamp() -> datetime:
        """Get the current timestamp.

        Returns:
            The current UTC datetime (naive, for KuzuDB TIMESTAMP columns).
        """
        # naive UTC (== deprecated utcnow()) so it binds to KuzuDB TIMESTAMP.
        return datetime.now(timezone.utc).replace(tzinfo=None)

    @staticmethod
    def normalize_timestamp(value: Any) -> Optional[datetime]:
        """Normalize a timestamp value.

        Args:
            value: The timestamp value from the database.

        Returns:
            A datetime object, or None.
        """
        if value is None:
            return None

        if isinstance(value, datetime):
            return value

        if isinstance(value, str):
            try:
                # Try ISO format
                return datetime.fromisoformat(value.replace("Z", "+00:00"))
            except ValueError:
                pass

            try:
                # Try common formats
                for fmt in [
                    "%Y-%m-%d %H:%M:%S",
                    "%Y-%m-%d %H:%M:%S.%f",
                    "%Y-%m-%dT%H:%M:%S",
                    "%Y-%m-%dT%H:%M:%S.%f",
                ]:
                    return datetime.strptime(value, fmt)
            except ValueError:
                pass

        return None

    def normalize_row(
        self,
        row: dict[str, Any],
        repository: str,
        branch: str,
    ) -> dict[str, Any]:
        """Normalize a database row with repository context.

        Args:
            row: The raw database row.
            repository: The repository name.
            branch: The branch name.

        Returns:
            The normalized row with repository/branch context.
        """
        normalized = dict(row)
        normalized["repository"] = repository
        normalized["branch"] = branch

        # Normalize timestamps
        if "created_at" in normalized:
            normalized["created_at"] = self.normalize_timestamp(
                normalized["created_at"]
            )
        if "updated_at" in normalized:
            normalized["updated_at"] = self.normalize_timestamp(
                normalized["updated_at"]
            )

        return normalized
