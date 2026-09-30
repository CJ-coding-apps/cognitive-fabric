"""Component repository combining all component operations."""

from cognitive_fabric.db.kuzu_client import KuzuDBClient
from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.repositories.component.algorithms import ComponentAlgorithmMixin
from cognitive_fabric.repositories.component.crud import ComponentCrudMixin
from cognitive_fabric.repositories.component.graph import ComponentGraphMixin


class ComponentRepository(
    ComponentCrudMixin,
    ComponentGraphMixin,
    ComponentAlgorithmMixin,
    BaseRepository,
):
    """Repository for Component entity operations.

    This class combines all component-related operations from the mixins:
    - ComponentCrudMixin: Basic CRUD operations
    - ComponentGraphMixin: Graph traversal operations
    - ComponentAlgorithmMixin: Graph algorithm operations
    """

    def __init__(self, client: KuzuDBClient) -> None:
        """Initialize the component repository.

        Args:
            client: The KuzuDB client instance.
        """
        super().__init__(client)
