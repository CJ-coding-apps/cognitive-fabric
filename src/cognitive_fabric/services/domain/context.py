"""Context service for session context tracking operations."""

from typing import TYPE_CHECKING, Any, Optional

import structlog

from cognitive_fabric.types.entities import Context, ContextInput

if TYPE_CHECKING:
    from cognitive_fabric.services.service_container import ServiceContainer

logger = structlog.get_logger(__name__)


class ContextService:
    """Service for context tracking operations."""

    def __init__(self, container: "ServiceContainer") -> None:
        """Initialize the context service.

        Args:
            container: The service container for dependency injection.
        """
        self._container = container

    async def update_context(
        self,
        repository: str,
        input_data: ContextInput,
    ) -> Context:
        """Create or update a context entry.

        Args:
            repository: The repository name.
            input_data: The context input data.

        Returns:
            The created/updated context.
        """
        logger.debug(
            "Updating context",
            repository=repository,
            context_id=input_data.id,
        )

        context_repo = await self._container.get_context_repository()
        return await context_repo.upsert_context(repository, input_data)

    async def get_context(
        self,
        repository: str,
        context_id: str,
        branch: str = "main",
    ) -> Optional[Context]:
        """Get a context by ID.

        Args:
            repository: The repository name.
            context_id: The context ID.
            branch: The branch name.

        Returns:
            The context if found, None otherwise.
        """
        context_repo = await self._container.get_context_repository()
        return await context_repo.find_by_id(repository, context_id, branch)

    async def get_recent_contexts(
        self,
        repository: str,
        branch: str = "main",
        limit: int = 10,
    ) -> list[Context]:
        """Get recent context entries.

        Args:
            repository: The repository name.
            branch: The branch name.
            limit: Maximum number of contexts to return.

        Returns:
            List of recent contexts.
        """
        context_repo = await self._container.get_context_repository()
        return await context_repo.get_recent_contexts(repository, branch, limit)

    async def get_context_for_component(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> list[Context]:
        """Get contexts related to a component.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            List of contexts related to the component.
        """
        context_repo = await self._container.get_context_repository()
        return await context_repo.get_contexts_for_component(
            repository, component_id, branch
        )

    async def get_contexts_by_agent(
        self,
        repository: str,
        agent: str,
        branch: str = "main",
    ) -> list[Context]:
        """Get contexts by agent.

        Args:
            repository: The repository name.
            agent: The agent identifier.
            branch: The branch name.

        Returns:
            List of contexts from the agent.
        """
        context_repo = await self._container.get_context_repository()
        return await context_repo.get_contexts_by_agent(repository, agent, branch)

    async def get_contexts_by_date_range(
        self,
        repository: str,
        start_date: str,
        end_date: str,
        branch: str = "main",
    ) -> list[Context]:
        """Get contexts within a date range.

        Args:
            repository: The repository name.
            start_date: Start date (ISO format).
            end_date: End date (ISO format).
            branch: The branch name.

        Returns:
            List of contexts within the date range.
        """
        context_repo = await self._container.get_context_repository()
        return await context_repo.get_contexts_by_date_range(
            repository, start_date, end_date, branch
        )

    async def link_context_to_component(
        self,
        repository: str,
        context_id: str,
        component_id: str,
        branch: str = "main",
    ) -> bool:
        """Create a relationship between a context and a component.

        Args:
            repository: The repository name.
            context_id: The context ID.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            True if the relationship was created, False otherwise.
        """
        context_repo = await self._container.get_context_repository()
        return await context_repo.create_context_of_relationship(
            repository, context_id, component_id, branch
        )

    async def delete_context(
        self,
        repository: str,
        context_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a context.

        Args:
            repository: The repository name.
            context_id: The context ID.
            branch: The branch name.

        Returns:
            True if deleted, False otherwise.
        """
        context_repo = await self._container.get_context_repository()
        return await context_repo.delete_context(repository, context_id, branch)

    async def get_latest_context(
        self,
        repository: str,
        branch: str = "main",
    ) -> Optional[Context]:
        """Get the latest context entry.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            The latest context, or None if none exist.
        """
        context_repo = await self._container.get_context_repository()
        return await context_repo.get_latest_context(repository, branch)

    async def get_context_summary(
        self,
        repository: str,
        branch: str = "main",
        limit: int = 5,
    ) -> dict[str, Any]:
        """Get a summary of recent context activity.

        Args:
            repository: The repository name.
            branch: The branch name.
            limit: Number of recent contexts to summarize.

        Returns:
            Summary dictionary with recent activity.
        """
        context_repo = await self._container.get_context_repository()
        recent_contexts = await context_repo.get_recent_contexts(
            repository, branch, limit
        )

        summaries = []
        agents = set()
        key_findings = []

        for ctx in recent_contexts:
            summaries.append({
                "id": ctx.id,
                "name": ctx.name,
                "date": ctx.iso_date,
                "agent": ctx.agent,
                "summary": ctx.summary,
            })
            if ctx.agent:
                agents.add(ctx.agent)
            if ctx.key_findings:
                key_findings.extend(ctx.key_findings)

        return {
            "total_recent": len(recent_contexts),
            "agents_active": list(agents),
            "recent_contexts": summaries,
            "key_findings": key_findings[:10],  # Limit to 10 findings
        }
