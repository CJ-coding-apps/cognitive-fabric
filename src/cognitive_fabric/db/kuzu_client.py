"""Main KuzuDB client orchestrator."""

from typing import Any, Callable, Optional, TypeVar

import structlog

from cognitive_fabric.db.connection_manager import ConnectionManager
from cognitive_fabric.db.query_executor import QueryExecutor
from cognitive_fabric.db.schema_manager import SchemaManager
from cognitive_fabric.utils.path_utils import get_default_db_path

logger = structlog.get_logger("KuzuDBClient")

T = TypeVar("T")


class KuzuDBClient:
    """Main orchestrator for KuzuDB operations.

    Provides a unified interface for database operations including:
    - Connection management
    - Schema initialization
    - Query execution
    - Transaction support
    """

    def __init__(
        self,
        db_path: Optional[str] = None,
        client_project_root: Optional[str] = None,
    ) -> None:
        """Initialize the KuzuDB client.

        Args:
            db_path: Direct path to the database directory.
            client_project_root: Project root for default db path calculation.
        """
        if db_path:
            self._db_path = db_path
        elif client_project_root:
            self._db_path = get_default_db_path(client_project_root)
        else:
            raise ValueError("Either db_path or client_project_root is required")

        self._connection_manager = ConnectionManager(self._db_path)
        self._query_executor: Optional[QueryExecutor] = None
        self._schema_manager: Optional[SchemaManager] = None
        self._initialized = False
        self._logger = logger.bind(db_path=self._db_path)

    @property
    def db_path(self) -> str:
        """Get the database path."""
        return self._db_path

    @property
    def is_initialized(self) -> bool:
        """Check if the client is initialized."""
        return self._initialized

    async def initialize(
        self,
        progress_callback: Optional[Callable[[str, int], None]] = None,
    ) -> None:
        """Initialize the database client and schema.

        Args:
            progress_callback: Optional callback for progress updates.
                Called with (message, percent).
        """
        if self._initialized:
            self._logger.debug("Already initialized")
            return

        self._logger.info("Initializing KuzuDB client")

        if progress_callback:
            progress_callback("Connecting to database", 10)

        # Connect to database
        connection = await self._connection_manager.connect()

        if progress_callback:
            progress_callback("Initializing query executor", 30)

        # Initialize query executor
        self._query_executor = QueryExecutor(connection)

        if progress_callback:
            progress_callback("Initializing schema manager", 50)

        # Initialize schema manager
        self._schema_manager = SchemaManager(connection)

        if progress_callback:
            progress_callback("Creating database schema", 70)

        # Initialize schema
        await self._schema_manager.initialize_schema()

        if progress_callback:
            progress_callback("Initialization complete", 100)

        self._initialized = True
        self._logger.info("KuzuDB client initialized")

    async def close(self) -> None:
        """Close the database connection."""
        self._logger.info("Closing KuzuDB client")
        await self._connection_manager.disconnect()
        self._query_executor = None
        self._schema_manager = None
        self._initialized = False
        self._logger.info("KuzuDB client closed")

    def _ensure_initialized(self) -> None:
        """Ensure the client is initialized.

        Raises:
            RuntimeError: If the client is not initialized.
        """
        if not self._initialized:
            raise RuntimeError(
                "KuzuDB client not initialized. Call initialize() first."
            )

    def execute_query(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Any:
        """Execute a Cypher query.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.

        Returns:
            The query result.
        """
        self._ensure_initialized()
        assert self._query_executor is not None
        return self._query_executor.execute(query, params)

    def fetch_one(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> Optional[dict[str, Any]]:
        """Execute a query and fetch the first row.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.

        Returns:
            The first row as a dict, or None.
        """
        self._ensure_initialized()
        assert self._query_executor is not None
        return self._query_executor.fetch_one(query, params)

    def fetch_all(
        self,
        query: str,
        params: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Execute a query and fetch all rows.

        Args:
            query: The Cypher query string.
            params: Optional query parameters.

        Returns:
            All rows as a list of dicts.
        """
        self._ensure_initialized()
        assert self._query_executor is not None
        return self._query_executor.fetch_all(query, params)

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
            The scalar value, or None.
        """
        self._ensure_initialized()
        assert self._query_executor is not None
        return self._query_executor.fetch_scalar(query, params)

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
        self._ensure_initialized()
        assert self._query_executor is not None
        return self._query_executor.count(query, params)

    async def transaction(
        self,
        operations: Callable[["KuzuDBClient"], T],
    ) -> T:
        """Execute operations in a transaction context.

        Note: KuzuDB uses auto-commit by default. This method provides
        a consistent interface for transactional semantics.

        Args:
            operations: A callable that performs database operations.

        Returns:
            The result of the operations.
        """
        self._ensure_initialized()

        try:
            result = operations(self)
            return result
        except Exception as e:
            self._logger.error("Transaction failed", error=str(e))
            raise

    async def health_check(self) -> bool:
        """Check if the database connection is healthy.

        Returns:
            True if healthy, False otherwise.
        """
        return await self._connection_manager.health_check()

    async def validate_schema(self) -> dict[str, bool]:
        """Validate the database schema.

        Returns:
            A dict mapping table names to existence status.
        """
        self._ensure_initialized()
        assert self._schema_manager is not None
        return await self._schema_manager.validate_schema()

    def get_info(self) -> dict[str, Any]:
        """Get information about the database client.

        Returns:
            A dict with client information.
        """
        return {
            "db_path": self._db_path,
            "initialized": self._initialized,
            **self._connection_manager.get_database_info(),
        }
