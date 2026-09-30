"""Memory bank service for initialization and metadata operations."""

from typing import TYPE_CHECKING, Any, Optional

import structlog

from cognitive_fabric.types.entities import MetadataInput, RepositoryInput
from cognitive_fabric.utils.id_utils import create_repository_node_id

if TYPE_CHECKING:
    from cognitive_fabric.services.service_container import ServiceContainer

logger = structlog.get_logger(__name__)


class MemoryBankService:
    """Service for memory bank initialization and metadata operations."""

    def __init__(self, container: "ServiceContainer") -> None:
        """Initialize the memory bank service.

        Args:
            container: The service container for dependency injection.
        """
        self._container = container

    async def init_memory_bank(
        self,
        context: Any,
        client_project_root: str,
        repository: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Initialize a memory bank for a repository.

        Args:
            context: The tool handler context.
            client_project_root: The client's project root path.
            repository: The repository name.
            branch: The branch name.

        Returns:
            Initialization result with status and metadata.
        """
        logger.info(
            "Initializing memory bank",
            repository=repository,
            branch=branch,
            client_project_root=client_project_root,
        )

        repo_repo = await self._container.get_repository_repository()
        metadata_repo = await self._container.get_metadata_repository()

        # Check if repository already exists
        existing = await repo_repo.find_by_name(repository, branch)

        if existing:
            logger.info(
                "Memory bank already exists",
                repository=repository,
                branch=branch,
            )

            # Get existing metadata
            repo_node_id = create_repository_node_id(repository, branch)
            metadata_list = await metadata_repo.get_metadata_for_repository(
                repo_node_id, repository, branch
            )

            metadata_dict = {}
            for m in metadata_list:
                metadata_dict[m.name] = m.content

            return {
                "success": True,
                "message": f"Memory bank already initialized for {repository}:{branch}",
                "repository": repository,
                "branch": branch,
                "created": False,
                "metadata": metadata_dict,
            }

        # Create new repository
        repo_input = RepositoryInput(
            name=repository,
            branch=branch,
            tech_stack=[],
            architecture="",
        )

        created_repo = await repo_repo.create(repo_input)

        # Create initial metadata
        metadata_input = MetadataInput(
            id=f"{repository}-metadata",
            name=repository,
            content={
                "client_project_root": client_project_root,
                "initialized_at": (
                    created_repo.created_at.isoformat()
                    if created_repo.created_at
                    else None
                ),
                "version": "1.0.0",
            },
            branch=branch,
        )

        await metadata_repo.upsert_metadata(repository, metadata_input)

        # Create relationship between repository and metadata
        await metadata_repo.create_has_metadata_relationship(
            repository,
            created_repo.id,
            metadata_input.id,
            branch,
        )

        logger.info(
            "Memory bank initialized successfully",
            repository=repository,
            branch=branch,
        )

        return {
            "success": True,
            "message": f"Memory bank initialized for {repository}:{branch}",
            "repository": repository,
            "branch": branch,
            "created": True,
            "metadata": metadata_input.content,
        }

    async def get_memory_bank_metadata(
        self,
        repository: str,
        branch: str = "main",
    ) -> Optional[dict[str, Any]]:
        """Get memory bank metadata.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            The metadata dictionary, or None if not found.
        """
        metadata_repo = await self._container.get_metadata_repository()
        repo_repo = await self._container.get_repository_repository()

        # Check if repository exists
        existing = await repo_repo.find_by_name(repository, branch)
        if not existing:
            return None

        # Get metadata
        repo_node_id = create_repository_node_id(repository, branch)
        metadata_list = await metadata_repo.get_metadata_for_repository(
            repo_node_id, repository, branch
        )

        if not metadata_list:
            return {
                "repository": repository,
                "branch": branch,
                "initialized": True,
                "metadata": {},
            }

        metadata_dict = {}
        for m in metadata_list:
            metadata_dict[m.name] = m.content

        return {
            "repository": repository,
            "branch": branch,
            "initialized": True,
            "metadata": metadata_dict,
            "repository_info": {
                "id": existing.id,
                "name": existing.name,
                "tech_stack": existing.tech_stack,
                "architecture": existing.architecture,
                "created_at": (
                    existing.created_at.isoformat()
                    if existing.created_at
                    else None
                ),
                "updated_at": (
                    existing.updated_at.isoformat()
                    if existing.updated_at
                    else None
                ),
            },
        }

    async def update_memory_bank_metadata(
        self,
        repository: str,
        branch: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Update memory bank metadata.

        Args:
            repository: The repository name.
            branch: The branch name.
            metadata: The metadata to update.

        Returns:
            The updated metadata.
        """
        metadata_repo = await self._container.get_metadata_repository()
        repo_repo = await self._container.get_repository_repository()

        # Check if repository exists
        existing = await repo_repo.find_by_name(repository, branch)
        if not existing:
            raise ValueError(f"Memory bank not initialized for {repository}:{branch}")

        # Get or create metadata
        existing_metadata = await metadata_repo.find_by_name(
            repository, repository, branch
        )

        if existing_metadata:
            # Merge with existing metadata
            merged_content = (
                existing_metadata.content
                if isinstance(existing_metadata.content, dict)
                else {}
            )
            merged_content.update(metadata)

            await metadata_repo.update_content(
                repository,
                existing_metadata.id,
                branch,
                merged_content,
            )

            return {
                "success": True,
                "message": "Metadata updated",
                "metadata": merged_content,
            }
        else:
            # Create new metadata
            metadata_input = MetadataInput(
                id=f"{repository}-metadata",
                name=repository,
                content=metadata,
                branch=branch,
            )

            await metadata_repo.upsert_metadata(repository, metadata_input)

            # Create relationship
            await metadata_repo.create_has_metadata_relationship(
                repository,
                existing.id,
                metadata_input.id,
                branch,
            )

            return {
                "success": True,
                "message": "Metadata created",
                "metadata": metadata,
            }

    async def check_memory_bank_exists(
        self,
        repository: str,
        branch: str = "main",
    ) -> bool:
        """Check if a memory bank exists.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            True if the memory bank exists, False otherwise.
        """
        repo_repo = await self._container.get_repository_repository()
        return await repo_repo.exists(repository, branch)

    async def delete_memory_bank(
        self,
        repository: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Delete a memory bank and all its data.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            Deletion result.
        """
        logger.warning(
            "Deleting memory bank",
            repository=repository,
            branch=branch,
        )

        repo_repo = await self._container.get_repository_repository()

        # Check if exists
        existing = await repo_repo.find_by_name(repository, branch)
        if not existing:
            return {
                "success": False,
                "message": f"Memory bank not found for {repository}:{branch}",
            }

        # Delete repository (cascades to related data through DETACH DELETE)
        deleted = await repo_repo.delete(existing.id)

        if deleted:
            logger.info(
                "Memory bank deleted",
                repository=repository,
                branch=branch,
            )
            return {
                "success": True,
                "message": f"Memory bank deleted for {repository}:{branch}",
            }

        return {
            "success": False,
            "message": "Failed to delete memory bank",
        }
