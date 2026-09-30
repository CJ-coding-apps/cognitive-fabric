"""Service container for lazy-loading dependency injection."""

import asyncio
from typing import TYPE_CHECKING, Any, Dict, Optional

import structlog

if TYPE_CHECKING:
    from cognitive_fabric.db.kuzu_client import KuzuDBClient
    from cognitive_fabric.repositories import (
        ComponentRepository,
        ContextRepository,
        DecisionRepository,
        FileRepository,
        MetadataRepository,
        RepositoryRepository,
        RequirementRepository,
        RuleRepository,
        SymbolRepository,
        TagRepository,
        TraceRepository,
    )
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

logger = structlog.get_logger(__name__)


class ServiceContainer:
    """Lazy-loading service container for dependency injection.

    This container manages the lifecycle of services and repositories,
    creating them on-demand and caching them for reuse.
    """

    _instance: Optional["ServiceContainer"] = None
    _lock = asyncio.Lock()

    def __init__(self, kuzu_client: "KuzuDBClient") -> None:
        """Initialize the service container.

        Args:
            kuzu_client: The KuzuDB client instance.
        """
        self._kuzu_client = kuzu_client
        self._repositories: Dict[str, Any] = {}
        self._services: Dict[str, Any] = {}
        self._service_locks: Dict[str, asyncio.Lock] = {}

    @classmethod
    async def get_instance(
        cls,
        kuzu_client: Optional["KuzuDBClient"] = None,
    ) -> "ServiceContainer":
        """Get the singleton instance of the service container.

        Args:
            kuzu_client: The KuzuDB client (required on first call).

        Returns:
            The service container instance.

        Raises:
            ValueError: If kuzu_client is not provided on first call.
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    if kuzu_client is None:
                        raise ValueError(
                            "kuzu_client is required when creating ServiceContainer"
                        )
                    cls._instance = cls(kuzu_client)
                    logger.info("ServiceContainer initialized")
        return cls._instance

    @classmethod
    def reset_instance(cls) -> None:
        """Reset the singleton instance. Useful for testing."""
        cls._instance = None

    async def get_kuzu_client(self) -> "KuzuDBClient":
        """Get the KuzuDB client.

        Returns:
            The KuzuDB client instance.
        """
        return self._kuzu_client

    # Repository getters

    async def _get_or_create_repository(
        self,
        name: str,
        factory: callable,
    ) -> Any:
        """Get or create a repository.

        Args:
            name: The repository name.
            factory: Factory function to create the repository.

        Returns:
            The repository instance.
        """
        if name not in self._repositories:
            self._repositories[name] = factory(self._kuzu_client)
        return self._repositories[name]

    async def get_repository_repository(self) -> "RepositoryRepository":
        """Get the repository repository.

        Returns:
            The RepositoryRepository instance.
        """
        from cognitive_fabric.repositories import RepositoryRepository

        return await self._get_or_create_repository(
            "repository",
            RepositoryRepository,
        )

    async def get_component_repository(self) -> "ComponentRepository":
        """Get the component repository.

        Returns:
            The ComponentRepository instance.
        """
        from cognitive_fabric.repositories import ComponentRepository

        return await self._get_or_create_repository(
            "component",
            ComponentRepository,
        )

    async def get_decision_repository(self) -> "DecisionRepository":
        """Get the decision repository.

        Returns:
            The DecisionRepository instance.
        """
        from cognitive_fabric.repositories import DecisionRepository

        return await self._get_or_create_repository(
            "decision",
            DecisionRepository,
        )

    async def get_rule_repository(self) -> "RuleRepository":
        """Get the rule repository.

        Returns:
            The RuleRepository instance.
        """
        from cognitive_fabric.repositories import RuleRepository

        return await self._get_or_create_repository(
            "rule",
            RuleRepository,
        )

    async def get_context_repository(self) -> "ContextRepository":
        """Get the context repository.

        Returns:
            The ContextRepository instance.
        """
        from cognitive_fabric.repositories import ContextRepository

        return await self._get_or_create_repository(
            "context",
            ContextRepository,
        )

    async def get_metadata_repository(self) -> "MetadataRepository":
        """Get the metadata repository.

        Returns:
            The MetadataRepository instance.
        """
        from cognitive_fabric.repositories import MetadataRepository

        return await self._get_or_create_repository(
            "metadata",
            MetadataRepository,
        )

    async def get_file_repository(self) -> "FileRepository":
        """Get the file repository.

        Returns:
            The FileRepository instance.
        """
        from cognitive_fabric.repositories import FileRepository

        return await self._get_or_create_repository(
            "file",
            FileRepository,
        )

    async def get_tag_repository(self) -> "TagRepository":
        """Get the tag repository.

        Returns:
            The TagRepository instance.
        """
        from cognitive_fabric.repositories import TagRepository

        return await self._get_or_create_repository(
            "tag",
            TagRepository,
        )

    async def get_symbol_repository(self) -> "SymbolRepository":
        """Get the symbol repository (Cognitive Fabric)."""
        from cognitive_fabric.repositories import SymbolRepository

        return await self._get_or_create_repository("symbol", SymbolRepository)

    async def get_requirement_repository(self) -> "RequirementRepository":
        """Get the requirement repository (Cognitive Fabric)."""
        from cognitive_fabric.repositories import RequirementRepository

        return await self._get_or_create_repository(
            "requirement", RequirementRepository
        )

    async def get_trace_repository(self) -> "TraceRepository":
        """Get the trace repository (Cognitive Fabric)."""
        from cognitive_fabric.repositories import TraceRepository

        return await self._get_or_create_repository("trace", TraceRepository)

    # Service getters

    async def _get_or_create_service(
        self,
        name: str,
        factory: callable,
    ) -> Any:
        """Get or create a service with thread-safe lazy loading.

        Args:
            name: The service name.
            factory: Factory function to create the service.

        Returns:
            The service instance.
        """
        if name not in self._services:
            if name not in self._service_locks:
                self._service_locks[name] = asyncio.Lock()

            async with self._service_locks[name]:
                if name not in self._services:
                    self._services[name] = factory(self)
                    logger.debug(f"Created service: {name}")

        return self._services[name]

    async def get_memory_bank_service(self) -> "MemoryBankService":
        """Get the memory bank service.

        Returns:
            The MemoryBankService instance.
        """
        from cognitive_fabric.services.domain import MemoryBankService

        return await self._get_or_create_service(
            "memory_bank",
            MemoryBankService,
        )

    async def get_entity_service(self) -> "EntityService":
        """Get the entity service.

        Returns:
            The EntityService instance.
        """
        from cognitive_fabric.services.domain import EntityService

        return await self._get_or_create_service(
            "entity",
            EntityService,
        )

    async def get_context_service(self) -> "ContextService":
        """Get the context service.

        Returns:
            The ContextService instance.
        """
        from cognitive_fabric.services.domain import ContextService

        return await self._get_or_create_service(
            "context",
            ContextService,
        )

    async def get_metadata_service(self) -> "MetadataService":
        """Get the metadata service.

        Returns:
            The MetadataService instance.
        """
        from cognitive_fabric.services.domain import MetadataService

        return await self._get_or_create_service(
            "metadata",
            MetadataService,
        )

    async def get_graph_query_service(self) -> "GraphQueryService":
        """Get the graph query service.

        Returns:
            The GraphQueryService instance.
        """
        from cognitive_fabric.services.domain import GraphQueryService

        return await self._get_or_create_service(
            "graph_query",
            GraphQueryService,
        )

    async def get_graph_analysis_service(self) -> "GraphAnalysisService":
        """Get the graph analysis service.

        Returns:
            The GraphAnalysisService instance.
        """
        from cognitive_fabric.services.domain import GraphAnalysisService

        return await self._get_or_create_service(
            "graph_analysis",
            GraphAnalysisService,
        )

    async def get_data_fabric_service(self) -> "DataFabricService":
        """Get the data fabric service (Cognitive Fabric)."""
        from cognitive_fabric.services.domain import DataFabricService

        return await self._get_or_create_service("data_fabric", DataFabricService)

    async def get_dream_service(self) -> "DreamService":
        """Get the dream service (Cognitive Fabric)."""
        from cognitive_fabric.services.domain import DreamService

        return await self._get_or_create_service("dream", DreamService)
