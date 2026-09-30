"""Protocol definitions for services."""

from typing import Any, Optional, Protocol, runtime_checkable

from cognitive_fabric.types.entities import (
    Component,
    ComponentInput,
    Context,
    ContextInput,
    Decision,
    DecisionInput,
    Metadata,
    MetadataInput,
    Rule,
    RuleInput,
)


@runtime_checkable
class MemoryBankServiceProtocol(Protocol):
    """Protocol for memory bank operations."""

    async def init_memory_bank(
        self,
        context: Any,
        client_project_root: str,
        repository: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Initialize a memory bank."""
        ...

    async def get_memory_bank_metadata(
        self,
        repository: str,
        branch: str = "main",
    ) -> Optional[dict[str, Any]]:
        """Get memory bank metadata."""
        ...

    async def update_memory_bank_metadata(
        self,
        repository: str,
        branch: str,
        metadata: dict[str, Any],
    ) -> dict[str, Any]:
        """Update memory bank metadata."""
        ...


@runtime_checkable
class EntityServiceProtocol(Protocol):
    """Protocol for entity CRUD operations."""

    async def create_component(
        self,
        repository: str,
        input_data: ComponentInput,
    ) -> Component:
        """Create a component."""
        ...

    async def get_component(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> Optional[Component]:
        """Get a component by ID."""
        ...

    async def update_component(
        self,
        repository: str,
        input_data: ComponentInput,
    ) -> Component:
        """Update a component."""
        ...

    async def delete_component(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a component."""
        ...

    async def create_decision(
        self,
        repository: str,
        input_data: DecisionInput,
    ) -> Decision:
        """Create a decision."""
        ...

    async def get_decision(
        self,
        repository: str,
        decision_id: str,
        branch: str = "main",
    ) -> Optional[Decision]:
        """Get a decision by ID."""
        ...

    async def create_rule(
        self,
        repository: str,
        input_data: RuleInput,
    ) -> Rule:
        """Create a rule."""
        ...

    async def get_rule(
        self,
        repository: str,
        rule_id: str,
        branch: str = "main",
    ) -> Optional[Rule]:
        """Get a rule by ID."""
        ...


@runtime_checkable
class ContextServiceProtocol(Protocol):
    """Protocol for context tracking operations."""

    async def update_context(
        self,
        repository: str,
        input_data: ContextInput,
    ) -> Context:
        """Create or update a context entry."""
        ...

    async def get_recent_contexts(
        self,
        repository: str,
        branch: str = "main",
        limit: int = 10,
    ) -> list[Context]:
        """Get recent context entries."""
        ...

    async def get_context_for_component(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> list[Context]:
        """Get contexts related to a component."""
        ...


@runtime_checkable
class MetadataServiceProtocol(Protocol):
    """Protocol for metadata operations."""

    async def get_metadata(
        self,
        repository: str,
        metadata_id: str,
        branch: str = "main",
    ) -> Optional[Metadata]:
        """Get metadata by ID."""
        ...

    async def upsert_metadata(
        self,
        repository: str,
        input_data: MetadataInput,
    ) -> Metadata:
        """Create or update metadata."""
        ...


@runtime_checkable
class GraphQueryServiceProtocol(Protocol):
    """Protocol for graph query operations."""

    async def query_context(
        self,
        repository: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Query context information."""
        ...

    async def query_entities(
        self,
        repository: str,
        entity_type: str,
        branch: str = "main",
        filters: Optional[dict[str, Any]] = None,
    ) -> list[dict[str, Any]]:
        """Query entities with optional filters."""
        ...

    async def query_relationships(
        self,
        repository: str,
        relationship_type: str,
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Query relationships by type."""
        ...

    async def query_dependencies(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
        direction: str = "both",
        depth: int = 1,
    ) -> dict[str, Any]:
        """Query component dependencies."""
        ...

    async def query_governance(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Query governance rules for a component."""
        ...

    async def query_history(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Query component history."""
        ...

    async def query_tags(
        self,
        repository: str,
        tag_id: Optional[str] = None,
        branch: str = "main",
    ) -> dict[str, Any]:
        """Query tags and tagged items."""
        ...


@runtime_checkable
class GraphAnalysisServiceProtocol(Protocol):
    """Protocol for graph analysis operations."""

    async def run_pagerank(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Run PageRank analysis."""
        ...

    async def run_k_core(
        self,
        repository: str,
        k: int = 2,
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Run k-core decomposition."""
        ...

    async def run_louvain(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Run Louvain community detection."""
        ...

    async def find_shortest_path(
        self,
        repository: str,
        start_id: str,
        end_id: str,
        branch: str = "main",
    ) -> Optional[dict[str, Any]]:
        """Find shortest path between components."""
        ...

    async def detect_cycles(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[list[str]]:
        """Detect cycles in the dependency graph."""
        ...

    async def detect_islands(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[list[str]]:
        """Detect disconnected islands in the graph."""
        ...

    async def get_strongly_connected(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[list[str]]:
        """Get strongly connected components."""
        ...

    async def get_weakly_connected(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[list[str]]:
        """Get weakly connected components."""
        ...
