"""Base memory agent class."""

from abc import ABC, abstractmethod
from typing import Any, Dict, Optional

import structlog

from cognitive_fabric.llm import get_model_name
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.optimization import OptimizationStrategy

logger = structlog.get_logger(__name__)


class BaseMemoryAgent(ABC):
    """Base class for memory optimization agents."""

    def __init__(
        self,
        memory_service: MemoryService,
        model_provider: Optional[str] = None,
        model_name: Optional[str] = None,
    ) -> None:
        """Initialize the base memory agent.

        Args:
            memory_service: The memory service instance.
            model_provider: The AI model provider ('openai' or 'anthropic').
                Defaults to the configured `llm_provider`. Not defaulted here,
                so that the provider chosen in configuration is the one used.
            model_name: Optional specific model name to use. Defaults to the
                configured model for the provider, resolved on use.
        """
        self._memory_service = memory_service
        self._model_provider = model_provider
        self._model_name = model_name
        self._logger = logger.bind(agent=self.__class__.__name__)

    def _resolve_model_name(self) -> str:
        """The configured model for this agent's provider.

        Resolved when an LLM is about to be used, not in `__init__`. Building an
        agent is not using an LLM, and the optimizer's rule-based paths have to
        keep working with no model configured -- raising at construction would
        take the whole tool down to enforce a setting only the optional LLM path
        needs. No model id appears here: the value comes from configuration, so
        the model is the operator's choice and never this package's.

        Raises:
            LlmNotConfiguredError: if the provider has no model configured.
        """
        if self._model_name:
            return self._model_name
        return get_model_name(provider=self._model_provider)

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
