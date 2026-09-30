"""Base memory agent class."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import structlog

from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.optimization import OptimizationStrategy

logger = structlog.get_logger(__name__)


class BaseMemoryAgent(ABC):
    """Base class for memory optimization agents."""

    def __init__(
        self,
        memory_service: MemoryService,
        model_provider: str = "openai",
        model_name: Optional[str] = None,
    ) -> None:
        """Initialize the base memory agent.

        Args:
            memory_service: The memory service instance.
            model_provider: The AI model provider ('openai' or 'anthropic').
            model_name: Optional specific model name to use.
        """
        self._memory_service = memory_service
        self._model_provider = model_provider
        self._model_name = model_name or self._get_default_model()
        self._logger = logger.bind(agent=self.__class__.__name__)

    def _get_default_model(self) -> str:
        """Get the default model name for the provider.

        Returns:
            The default model name.
        """
        if self._model_provider == "anthropic":
            return "claude-3-haiku-20240307"
        return "gpt-4o-mini"

    @abstractmethod
    async def analyze(
        self,
        repository: str,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """Analyze the memory bank.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            Analysis results.
        """
        pass

    @abstractmethod
    async def optimize(
        self,
        repository: str,
        branch: str = "main",
        strategy: OptimizationStrategy = OptimizationStrategy.BALANCED,
    ) -> Dict[str, Any]:
        """Optimize the memory bank.

        Args:
            repository: The repository name.
            branch: The branch name.
            strategy: The optimization strategy to use.

        Returns:
            Optimization results.
        """
        pass

    async def _get_memory_statistics(
        self,
        repository: str,
        branch: str,
    ) -> Dict[str, Any]:
        """Get memory bank statistics.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            Statistics dictionary.
        """
        return await self._memory_service.get_statistics(repository, branch)

    async def _create_snapshot(
        self,
        repository: str,
        branch: str,
        description: str,
    ) -> str:
        """Create a snapshot before optimization.

        Args:
            repository: The repository name.
            branch: The branch name.
            description: Snapshot description.

        Returns:
            The snapshot ID.
        """
        snapshot = await self._memory_service.snapshot.create_snapshot(
            repository,
            branch,
            description=description,
        )
        return snapshot.id
