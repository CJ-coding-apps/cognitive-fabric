"""Main memory service orchestrating all memory operations."""

import asyncio
from typing import TYPE_CHECKING, Any, Optional

import structlog

from cognitive_fabric.db.kuzu_client import KuzuDBClient
from cognitive_fabric.services.service_container import ServiceContainer

if TYPE_CHECKING:
    from cognitive_fabric.services.domain import (
        ContextService,
        DataFabricService,
        DreamService,
        EntityService,
        GraphAnalysisService,
        GraphQueryService,
        MemoryBankService,
        MetadataService,
    )
    from cognitive_fabric.services.snapshot_service import SnapshotService

logger = structlog.get_logger(__name__)


class MemoryService:
    """Main service orchestrating all memory operations.

    This service provides a unified interface to all memory operations
    and manages the service container lifecycle.
    """

    _instance: Optional["MemoryService"] = None
    _lock = asyncio.Lock()

    def __init__(self, db_path: str) -> None:
        """Initialize the memory service.

        Args:
            db_path: Path to the KuzuDB database.
        """
        self._db_path = db_path
        self._kuzu_client: Optional[KuzuDBClient] = None
        self._container: Optional[ServiceContainer] = None
        self._snapshot_service: Optional["SnapshotService"] = None
        self._initialized = False

    @classmethod
    async def get_instance(cls, db_path: Optional[str] = None) -> "MemoryService":
        """Get the singleton instance of the memory service.

        Args:
            db_path: Path to the KuzuDB database (required on first call).

        Returns:
            The MemoryService instance.

        Raises:
            ValueError: If db_path is not provided on first call.
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    if db_path is None:
                        raise ValueError(
                            "db_path is required when creating MemoryService"
                        )
                    cls._instance = cls(db_path)
                    await cls._instance.initialize()
                    logger.info("MemoryService initialized", db_path=db_path)
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        if cls._instance is not None:
            cls._instance._initialized = False
            cls._instance._kuzu_client = None
            cls._instance._container = None
        cls._instance = None
        ServiceContainer.reset_instance()

    async def initialize(self) -> None:
        """Initialize the memory service and its dependencies."""
        if self._initialized:
            return

        logger.info("Initializing MemoryService", db_path=self._db_path)

        # Create and initialize KuzuDB client
        self._kuzu_client = KuzuDBClient(self._db_path)
        await self._kuzu_client.initialize()

        # Create service container
        self._container = await ServiceContainer.get_instance(self._kuzu_client)

        # Create snapshot service
        from cognitive_fabric.services.snapshot_service import SnapshotService
        self._snapshot_service = SnapshotService(self._db_path, self._container)

        self._initialized = True
        logger.info("MemoryService initialization complete")

    async def close(self) -> None:
        """Close the memory service and release resources."""
        if self._kuzu_client:
            await self._kuzu_client.close()
            self._kuzu_client = None

        self._initialized = False
        logger.info("MemoryService closed")

    def _ensure_initialized(self) -> None:
        """Ensure the service is initialized."""
        if not self._initialized:
            raise RuntimeError(
                "MemoryService not initialized. Call initialize() first."
            )

    # Service property accessors

    @property
    async def memory_bank(self) -> "MemoryBankService":
        """Get the memory bank service.

        Returns:
            The MemoryBankService instance.
        """
        self._ensure_initialized()
        return await self._container.get_memory_bank_service()

    @property
    async def entity(self) -> "EntityService":
        """Get the entity service.

        Returns:
            The EntityService instance.
        """
        self._ensure_initialized()
        return await self._container.get_entity_service()

    @property
    async def context(self) -> "ContextService":
        """Get the context service.

        Returns:
            The ContextService instance.
        """
        self._ensure_initialized()
        return await self._container.get_context_service()

    @property
    async def metadata(self) -> "MetadataService":
        """Get the metadata service.

        Returns:
            The MetadataService instance.
        """
        self._ensure_initialized()
        return await self._container.get_metadata_service()

    @property
    async def graph_query(self) -> "GraphQueryService":
        """Get the graph query service.

        Returns:
            The GraphQueryService instance.
        """
        self._ensure_initialized()
        return await self._container.get_graph_query_service()

    @property
    async def graph_analysis(self) -> "GraphAnalysisService":
        """Get the graph analysis service.

        Returns:
            The GraphAnalysisService instance.
        """
        self._ensure_initialized()
        return await self._container.get_graph_analysis_service()

    @property
    async def data_fabric(self) -> "DataFabricService":
        """Get the data fabric service (Cognitive Fabric)."""
        self._ensure_initialized()
        return await self._container.get_data_fabric_service()

    @property
    async def dream(self) -> "DreamService":
        """Get the dream service (Cognitive Fabric)."""
        self._ensure_initialized()
        return await self._container.get_dream_service()

    @property
    def snapshot(self) -> "SnapshotService":
        """Get the snapshot service.

        Returns:
            The SnapshotService instance.
        """
        self._ensure_initialized()
        return self._snapshot_service

    # Convenience methods for common operations

    async def get_service_container(self) -> ServiceContainer:
        """Get the service container.

        Returns:
            The ServiceContainer instance.
        """
        self._ensure_initialized()
        return self._container

    async def get_kuzu_client(self) -> KuzuDBClient:
        """Get the KuzuDB client.

        Returns:
            The KuzuDBClient instance.
        """
        self._ensure_initialized()
        return self._kuzu_client

    async def health_check(self) -> dict[str, Any]:
        """Perform a health check on the memory service.

        Returns:
            Health check results.
        """
        self._ensure_initialized()

        kuzu_health = await self._kuzu_client.health_check()

        return {
            "status": "healthy" if kuzu_health["connected"] else "unhealthy",
            "initialized": self._initialized,
            "database": kuzu_health,
        }

    async def get_statistics(
        self,
        repository: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Get memory bank statistics.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            Statistics dictionary.
        """
        self._ensure_initialized()

        graph_analysis = await self.graph_analysis
        entity_service = await self.entity

        # Get counts
        components = await entity_service.get_all_components(repository, branch)
        decisions = await entity_service.get_all_decisions(repository, branch)
        rules = await entity_service.get_all_rules(repository, branch)
        tags = await entity_service.get_all_tags(repository, branch)

        # Get graph statistics
        graph_stats = await graph_analysis.get_graph_statistics(repository, branch)

        return {
            "repository": repository,
            "branch": branch,
            "counts": {
                "components": len(components),
                "decisions": len(decisions),
                "rules": len(rules),
                "tags": len(tags),
            },
            "graph": graph_stats,
        }
