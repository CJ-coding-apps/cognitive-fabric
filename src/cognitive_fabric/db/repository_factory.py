"""Repository factory for singleton repository instances."""

import asyncio
from typing import TYPE_CHECKING, Optional

import structlog

if TYPE_CHECKING:
    from cognitive_fabric.db.kuzu_client import KuzuDBClient
    from cognitive_fabric.repositories.component_repo import ComponentRepository
    from cognitive_fabric.repositories.context_repo import ContextRepository
    from cognitive_fabric.repositories.decision_repo import DecisionRepository
    from cognitive_fabric.repositories.file_repo import FileRepository
    from cognitive_fabric.repositories.metadata_repo import MetadataRepository
    from cognitive_fabric.repositories.repository_repo import RepositoryRepository
    from cognitive_fabric.repositories.rule_repo import RuleRepository
    from cognitive_fabric.repositories.tag_repo import TagRepository

logger = structlog.get_logger("RepositoryFactory")


class RepositoryFactory:
    """Factory for creating and caching repository instances.

    Implements singleton pattern with per-database caching to ensure
    thread-safe repository access across the application.
    """

    _instance: Optional["RepositoryFactory"] = None
    _lock = asyncio.Lock()

    def __init__(self) -> None:
        """Initialize the repository factory with empty caches."""
        self._repository_cache: dict[str, "RepositoryRepository"] = {}
        self._component_cache: dict[str, "ComponentRepository"] = {}
        self._decision_cache: dict[str, "DecisionRepository"] = {}
        self._rule_cache: dict[str, "RuleRepository"] = {}
        self._context_cache: dict[str, "ContextRepository"] = {}
        self._metadata_cache: dict[str, "MetadataRepository"] = {}
        self._file_cache: dict[str, "FileRepository"] = {}
        self._tag_cache: dict[str, "TagRepository"] = {}
        self._logger = logger.bind(component="RepositoryFactory")

    @classmethod
    async def get_instance(cls) -> "RepositoryFactory":
        """Get the singleton factory instance.

        Returns:
            The singleton RepositoryFactory instance.
        """
        if cls._instance is None:
            async with cls._lock:
                if cls._instance is None:
                    cls._instance = cls()
                    logger.info("RepositoryFactory instance created")
        return cls._instance

    def get_repository_repository(
        self,
        kuzu_client: "KuzuDBClient",
    ) -> "RepositoryRepository":
        """Get or create a RepositoryRepository.

        Args:
            kuzu_client: The KuzuDB client.

        Returns:
            The RepositoryRepository instance.
        """
        from cognitive_fabric.repositories.repository_repo import RepositoryRepository

        db_path = kuzu_client.db_path
        if db_path not in self._repository_cache:
            self._repository_cache[db_path] = RepositoryRepository(kuzu_client)
            self._logger.debug("Created RepositoryRepository", db_path=db_path)
        return self._repository_cache[db_path]

    def get_component_repository(
        self,
        kuzu_client: "KuzuDBClient",
    ) -> "ComponentRepository":
        """Get or create a ComponentRepository.

        Args:
            kuzu_client: The KuzuDB client.

        Returns:
            The ComponentRepository instance.
        """
        from cognitive_fabric.repositories.component_repo import ComponentRepository

        db_path = kuzu_client.db_path
        if db_path not in self._component_cache:
            self._component_cache[db_path] = ComponentRepository(kuzu_client)
            self._logger.debug("Created ComponentRepository", db_path=db_path)
        return self._component_cache[db_path]

    def get_decision_repository(
        self,
        kuzu_client: "KuzuDBClient",
    ) -> "DecisionRepository":
        """Get or create a DecisionRepository.

        Args:
            kuzu_client: The KuzuDB client.

        Returns:
            The DecisionRepository instance.
        """
        from cognitive_fabric.repositories.decision_repo import DecisionRepository

        db_path = kuzu_client.db_path
        if db_path not in self._decision_cache:
            self._decision_cache[db_path] = DecisionRepository(kuzu_client)
            self._logger.debug("Created DecisionRepository", db_path=db_path)
        return self._decision_cache[db_path]

    def get_rule_repository(
        self,
        kuzu_client: "KuzuDBClient",
    ) -> "RuleRepository":
        """Get or create a RuleRepository.

        Args:
            kuzu_client: The KuzuDB client.

        Returns:
            The RuleRepository instance.
        """
        from cognitive_fabric.repositories.rule_repo import RuleRepository

        db_path = kuzu_client.db_path
        if db_path not in self._rule_cache:
            self._rule_cache[db_path] = RuleRepository(kuzu_client)
            self._logger.debug("Created RuleRepository", db_path=db_path)
        return self._rule_cache[db_path]

    def get_context_repository(
        self,
        kuzu_client: "KuzuDBClient",
    ) -> "ContextRepository":
        """Get or create a ContextRepository.

        Args:
            kuzu_client: The KuzuDB client.

        Returns:
            The ContextRepository instance.
        """
        from cognitive_fabric.repositories.context_repo import ContextRepository

        db_path = kuzu_client.db_path
        if db_path not in self._context_cache:
            self._context_cache[db_path] = ContextRepository(kuzu_client)
            self._logger.debug("Created ContextRepository", db_path=db_path)
        return self._context_cache[db_path]

    def get_metadata_repository(
        self,
        kuzu_client: "KuzuDBClient",
    ) -> "MetadataRepository":
        """Get or create a MetadataRepository.

        Args:
            kuzu_client: The KuzuDB client.

        Returns:
            The MetadataRepository instance.
        """
        from cognitive_fabric.repositories.metadata_repo import MetadataRepository

        db_path = kuzu_client.db_path
        if db_path not in self._metadata_cache:
            self._metadata_cache[db_path] = MetadataRepository(kuzu_client)
            self._logger.debug("Created MetadataRepository", db_path=db_path)
        return self._metadata_cache[db_path]

    def get_file_repository(
        self,
        kuzu_client: "KuzuDBClient",
    ) -> "FileRepository":
        """Get or create a FileRepository.

        Args:
            kuzu_client: The KuzuDB client.

        Returns:
            The FileRepository instance.
        """
        from cognitive_fabric.repositories.file_repo import FileRepository

        db_path = kuzu_client.db_path
        if db_path not in self._file_cache:
            self._file_cache[db_path] = FileRepository(kuzu_client)
            self._logger.debug("Created FileRepository", db_path=db_path)
        return self._file_cache[db_path]

    def get_tag_repository(
        self,
        kuzu_client: "KuzuDBClient",
    ) -> "TagRepository":
        """Get or create a TagRepository.

        Args:
            kuzu_client: The KuzuDB client.

        Returns:
            The TagRepository instance.
        """
        from cognitive_fabric.repositories.tag_repo import TagRepository

        db_path = kuzu_client.db_path
        if db_path not in self._tag_cache:
            self._tag_cache[db_path] = TagRepository(kuzu_client)
            self._logger.debug("Created TagRepository", db_path=db_path)
        return self._tag_cache[db_path]

    def clear_caches(self) -> None:
        """Clear all repository caches."""
        self._repository_cache.clear()
        self._component_cache.clear()
        self._decision_cache.clear()
        self._rule_cache.clear()
        self._context_cache.clear()
        self._metadata_cache.clear()
        self._file_cache.clear()
        self._tag_cache.clear()
        self._logger.info("All repository caches cleared")

    def clear_cache_for_db(self, db_path: str) -> None:
        """Clear caches for a specific database.

        Args:
            db_path: The database path to clear caches for.
        """
        self._repository_cache.pop(db_path, None)
        self._component_cache.pop(db_path, None)
        self._decision_cache.pop(db_path, None)
        self._rule_cache.pop(db_path, None)
        self._context_cache.pop(db_path, None)
        self._metadata_cache.pop(db_path, None)
        self._file_cache.pop(db_path, None)
        self._tag_cache.pop(db_path, None)
        self._logger.info("Caches cleared for database", db_path=db_path)
