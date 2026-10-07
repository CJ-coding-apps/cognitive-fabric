"""Connection manager for KuzuDB."""

import os
from pathlib import Path
from typing import TYPE_CHECKING, Optional

import structlog

if TYPE_CHECKING:
    import kuzu

logger = structlog.get_logger("ConnectionManager")


class ConnectionManager:
    """Manages KuzuDB database and connection lifecycle."""

    def __init__(self, db_path: str) -> None:
        """Initialize the connection manager.

        Args:
            db_path: Path to the KuzuDB database directory.
        """
        self._db_path = db_path
        self._database: Optional["kuzu.Database"] = None
        self._connection: Optional["kuzu.Connection"] = None
        self._logger = logger.bind(db_path=db_path)

    @property
    def db_path(self) -> str:
        """Get the database path."""
        return self._db_path

    @property
    def is_connected(self) -> bool:
        """Check if connected to the database."""
        return self._connection is not None

    async def connect(self) -> "kuzu.Connection":
        """Connect to the database, creating it if necessary.

        Returns:
            The database connection.
        """
        import kuzu

        if self._connection is not None:
            return self._connection

        self._logger.info("Connecting to database")

        # Ensure the PARENT directory exists; let KuzuDB create the database
        # itself. (KuzuDB >= 0.11 rejects a pre-created directory as the db path.)
        Path(self._db_path).parent.mkdir(parents=True, exist_ok=True)

        # Create database and connection
        self._database = kuzu.Database(self._db_path)
        self._connection = kuzu.Connection(self._database)

        self._logger.info("Connected to database")

        return self._connection

    async def disconnect(self) -> None:
        """Disconnect from the database."""
        if self._connection is not None:
            self._logger.info("Disconnecting from database")
            # Close explicitly rather than dropping the references and leaving
            # it to the garbage collector. The query executor and schema
            # manager hold the same connection, and the client only releases
            # them *after* this returns -- so the file stayed open past the
            # point the caller was told the client was closed, and a caller
            # that then replaced the database file was writing over a file the
            # database still had open.
            self._connection.close()
            if self._database is not None:
                self._database.close()
            self._connection = None
            self._database = None
            self._logger.info("Disconnected from database")

    async def get_connection(self) -> "kuzu.Connection":
        """Get the current connection, connecting if necessary.

        Returns:
            The database connection.
        """
        if self._connection is None:
            return await self.connect()
        return self._connection

    async def health_check(self) -> bool:
        """Check if the database connection is healthy.

        Returns:
            True if healthy, False otherwise.
        """
        try:
            conn = await self.get_connection()
            # Simple query to check connection
            result = conn.execute("RETURN 1")
            return result.has_next()
        except Exception as e:
            self._logger.error("Health check failed", error=str(e))
            return False

    async def reconnect(self) -> "kuzu.Connection":
        """Reconnect to the database.

        Returns:
            The new database connection.
        """
        await self.disconnect()
        return await self.connect()

    def get_database_info(self) -> dict[str, str]:
        """Get information about the database.

        Returns:
            A dict with database information.
        """
        return {
            "path": self._db_path,
            "connected": str(self.is_connected),
            "exists": str(os.path.exists(self._db_path)),
        }
