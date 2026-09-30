"""Query executor for KuzuDB operations."""

import time
from typing import TYPE_CHECKING, Any, Optional

import structlog

if TYPE_CHECKING:
    import kuzu

logger = structlog.get_logger("QueryExecutor")


class QueryExecutor:
    """Executes Cypher queries against KuzuDB with logging and timing."""

    def __init__(self, connection: "kuzu.Connection") -> None:
        """Initialize the query executor.

        Args:
            connection: The KuzuDB connection.
        """
        self._connection = connection
        self._logger = logger.bind(component="QueryExecutor")

    def execute(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
        timeout_ms: Optional[int] = None,
    ) -> "kuzu.QueryResult":
        """Execute a Cypher query.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.
            timeout_ms: Optional timeout in milliseconds.

        Returns:
            The query result.

        Raises:
            Exception: If query execution fails.
        """
        start_time = time.perf_counter()
        log = self._logger.bind(query=query[:100])

        try:
            if params:
                result = self._connection.execute(query, params)
            else:
                result = self._connection.execute(query)

            duration_ms = (time.perf_counter() - start_time) * 1000
            log.debug(
                "Query executed",
                duration_ms=round(duration_ms, 2),
                has_params=params is not None,
            )

            return result

        except Exception as e:
            duration_ms = (time.perf_counter() - start_time) * 1000
            log.error(
                "Query failed",
                duration_ms=round(duration_ms, 2),
                error=str(e),
                params=params,
            )
            raise

    def execute_many(
        self,
        queries: list[tuple[str, Optional[dict[str, Any]]]],
    ) -> list["kuzu.QueryResult"]:
        """Execute multiple queries in sequence.

        Args:
            queries: List of (query, params) tuples.

        Returns:
            List of query results.
        """
        results = []
        for query, params in queries:
            result = self.execute(query, params)
            results.append(result)
        return results

    def fetch_one(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Execute a query and fetch the first row as a dict.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.

        Returns:
            The first row as a dict, or None if no results.
        """
        result = self.execute(query, params)

        if result.has_next():
            row = result.get_next()
            columns = result.get_column_names()
            return dict(zip(columns, row))

        return None

    def fetch_all(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Execute a query and fetch all rows as dicts.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.

        Returns:
            All rows as a list of dicts.
        """
        result = self.execute(query, params)
        columns = result.get_column_names()

        rows = []
        while result.has_next():
            row = result.get_next()
            rows.append(dict(zip(columns, row)))

        return rows

    def fetch_scalar(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Execute a query and fetch a single scalar value.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.

        Returns:
            The first column of the first row, or None.
        """
        result = self.execute(query, params)

        if result.has_next():
            row = result.get_next()
            return row[0] if row else None

        return None

    def count(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> int:
        """Execute a count query.

        Args:
            query: The Cypher query string (should return a count).
            params: Optional query parameters.

        Returns:
            The count value.
        """
        value = self.fetch_scalar(query, params)
        return int(value) if value is not None else 0


def normalize_kuzu_row(
    row: list[Any],
    columns: list[str],
) -> dict[str, Any]:
    """Normalize a Kuzu row to a dictionary.

    Args:
        row: The row data as a list.
        columns: The column names.

    Returns:
        A dict mapping column names to values.
    """
    return dict(zip(columns, row))


def extract_node_properties(node: Any) -> dict[str, Any]:
    """Extract properties from a Kuzu node object.

    Args:
        node: The Kuzu node object.

    Returns:
        A dict of node properties.
    """
    if hasattr(node, "_properties"):
        return dict(node._properties)
    elif isinstance(node, dict):
        return node
    else:
        return {"value": node}
