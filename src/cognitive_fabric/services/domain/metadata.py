"""Metadata service for metadata operations."""

from typing import TYPE_CHECKING, Any, Optional

import structlog

from cognitive_fabric.types.entities import Metadata, MetadataInput

if TYPE_CHECKING:
    from cognitive_fabric.services.service_container import ServiceContainer

logger = structlog.get_logger(__name__)


class MetadataService:
    """Service for metadata operations."""

    def __init__(self, container: "ServiceContainer") -> None:
        """Initialize the metadata service.

        Args:
            container: The service container for dependency injection.
        """
        self._container = container

    async def get_metadata(
        self,
        repository: str,
        metadata_id: str,
        branch: str = "main",
    ) -> Optional[Metadata]:
        """Get metadata by ID.

        Args:
            repository: The repository name.
            metadata_id: The metadata ID.
            branch: The branch name.

        Returns:
            The metadata if found, None otherwise.
        """
        metadata_repo = await self._container.get_metadata_repository()
        return await metadata_repo.find_by_id(repository, metadata_id, branch)

    async def get_metadata_by_name(
        self,
        repository: str,
        name: str,
        branch: str = "main",
    ) -> Optional[Metadata]:
        """Get metadata by name.

        Args:
            repository: The repository name.
            name: The metadata name.
            branch: The branch name.

        Returns:
            The metadata if found, None otherwise.
        """
        metadata_repo = await self._container.get_metadata_repository()
        return await metadata_repo.find_by_name(repository, name, branch)

    async def upsert_metadata(
        self,
        repository: str,
        input_data: MetadataInput,
    ) -> Metadata:
        """Create or update metadata.

        Args:
            repository: The repository name.
            input_data: The metadata input data.

        Returns:
            The created/updated metadata.
        """
        logger.debug(
            "Upserting metadata",
            repository=repository,
            metadata_id=input_data.id,
        )

        metadata_repo = await self._container.get_metadata_repository()
        return await metadata_repo.upsert_metadata(repository, input_data)

    async def update_metadata_content(
        self,
        repository: str,
        metadata_id: str,
        branch: str,
        content: Any,
    ) -> Optional[Metadata]:
        """Update metadata content.

        Args:
            repository: The repository name.
            metadata_id: The metadata ID.
            branch: The branch name.
            content: The new content.

        Returns:
            The updated metadata, or None if not found.
        """
        metadata_repo = await self._container.get_metadata_repository()
        return await metadata_repo.update_content(
            repository, metadata_id, branch, content
        )

    async def delete_metadata(
        self,
        repository: str,
        metadata_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete metadata.

        Args:
            repository: The repository name.
            metadata_id: The metadata ID.
            branch: The branch name.

        Returns:
            True if deleted, False otherwise.
        """
        metadata_repo = await self._container.get_metadata_repository()
        return await metadata_repo.delete_metadata(repository, metadata_id, branch)

    async def get_all_metadata(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[Metadata]:
        """Get all metadata entries.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all metadata entries.
        """
        metadata_repo = await self._container.get_metadata_repository()
        return await metadata_repo.get_all_metadata(repository, branch)

    async def merge_metadata_content(
        self,
        repository: str,
        metadata_id: str,
        branch: str,
        updates: dict[str, Any],
    ) -> Optional[Metadata]:
        """Merge updates into existing metadata content.

        Args:
            repository: The repository name.
            metadata_id: The metadata ID.
            branch: The branch name.
            updates: Dictionary of updates to merge.

        Returns:
            The updated metadata, or None if not found.
        """
        metadata_repo = await self._container.get_metadata_repository()

        # Get existing metadata
        existing = await metadata_repo.find_by_id(repository, metadata_id, branch)
        if not existing:
            return None

        # Merge content
        current_content = existing.content if isinstance(existing.content, dict) else {}
        merged_content = {**current_content, **updates}

        return await metadata_repo.update_content(
            repository, metadata_id, branch, merged_content
        )
