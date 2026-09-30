"""Repository provider for dependency injection."""

import asyncio
from typing import TYPE_CHECKING, Optional

import structlog

from cognitive_fabric.db.kuzu_client import KuzuDBClient
from cognitive_fabric.db.repository_factory import RepositoryFactory

if TYPE_CHECKING:
    from cognitive_fabric.repositories.component_repo import ComponentRepository
    from cognitive_fabric.repositories.context_repo import ContextRepository
    from cognitive_fabric.repositories.decision_repo import DecisionRepository
    from cognitive_fabric.repositories.file_repo import FileRepository
    from cognitive_fabric.repositories.metadata_repo import MetadataRepository
    from cognitive_fabric.repositories.repository_repo import RepositoryRepository
    from cognitive_fabric.repositories.rule_repo import RuleRepository
    from cognitive_fabric.repositories.tag_repo import TagRepository

logger = structlog.get_logger("RepositoryProvider")


class RepositoryProvider:
    """Provides repository instances for a specific database.

    This class manages the lifecycle of repositories for a given
    database path, providing a convenient interface for services
    to access repositories.
    """

    _instances: dict[str, "RepositoryProvider"] = {}
    _lock = asyncio.Lock()

    def __init__(self, kuzu_client: KuzuDBClient) -> None:
        """Initialize the repository provider.

        Args:
            kuzu_client: The KuzuDB client for this provider.
        """
        self._kuzu_client = kuzu_client
        self._factory: Optional[RepositoryFactory] = None
        self._logger = logger.bind(db_path=kuzu_client.db_path)

    @classmethod
    async def get_instance(
        cls,
        kuzu_client: KuzuDBClient,
    ) -> "RepositoryProvider":
        """Get or create a provider instance for a database.

        Args:
            kuzu_client: The KuzuDB client.

        Returns:
            The RepositoryProvider instance.
        """
        db_path = kuzu_client.db_path

        if db_path not in cls._instances:
            async with cls._lock:
                if db_path not in cls._instances:
                    provider = cls(kuzu_client)
                    provider._factory = await RepositoryFactory.get_instance()
                    cls._instances[db_path] = provider
                    logger.info(
                        "RepositoryProvider instance created",
                        db_path=db_path,
                    )

        return cls._instances[db_path]

    @classmethod
    def clear_instances(cls) -> None:
        """Clear all provider instances."""
        cls._instances.clear()
        logger.info("All RepositoryProvider instances cleared")

    @property
    def kuzu_client(self) -> KuzuDBClient:
        """Get the KuzuDB client."""
        return self._kuzu_client

    def _ensure_factory(self) -> RepositoryFactory:
        """Ensure the factory is initialized.

        Returns:
            The repository factory.

        Raises:
            RuntimeError: If the factory is not initialized.
        """
        if self._factory is None:
            raise RuntimeError(
                "RepositoryFactory not initialized. "
                "Use get_instance() to create the provider."
            )
        return self._factory

    @property
    def repository(self) -> "RepositoryRepository":
        """Get the RepositoryRepository."""
        return self._ensure_factory().get_repository_repository(self._kuzu_client)

    @property
    def component(self) -> "ComponentRepository":
        """Get the ComponentRepository."""
        return self._ensure_factory().get_component_repository(self._kuzu_client)

    @property
    def decision(self) -> "DecisionRepository":
        """Get the DecisionRepository."""
        return self._ensure_factory().get_decision_repository(self._kuzu_client)

    @property
    def rule(self) -> "RuleRepository":
        """Get the RuleRepository."""
        return self._ensure_factory().get_rule_repository(self._kuzu_client)

    @property
    def context(self) -> "ContextRepository":
        """Get the ContextRepository."""
        return self._ensure_factory().get_context_repository(self._kuzu_client)

    @property
    def metadata(self) -> "MetadataRepository":
        """Get the MetadataRepository."""
        return self._ensure_factory().get_metadata_repository(self._kuzu_client)

    @property
    def file(self) -> "FileRepository":
        """Get the FileRepository."""
        return self._ensure_factory().get_file_repository(self._kuzu_client)

    @property
    def tag(self) -> "TagRepository":
        """Get the TagRepository."""
        return self._ensure_factory().get_tag_repository(self._kuzu_client)
