"""Entity service for CRUD operations on all entity types."""

from typing import TYPE_CHECKING, Any, Optional

import structlog

from cognitive_fabric.types.entities import (
    Component,
    ComponentInput,
    ComponentStatus,
    Decision,
    DecisionInput,
    DecisionStatus,
    File,
    FileInput,
    Requirement,
    RequirementInput,
    Rule,
    RuleInput,
    RuleStatus,
    Symbol,
    SymbolInput,
    Tag,
    TagInput,
    Trace,
    TraceInput,
)

if TYPE_CHECKING:
    from cognitive_fabric.services.service_container import ServiceContainer

logger = structlog.get_logger(__name__)


class EntityService:
    """Service for entity CRUD operations."""

    def __init__(self, container: "ServiceContainer") -> None:
        """Initialize the entity service.

        Args:
            container: The service container for dependency injection.
        """
        self._container = container

    # Component operations

    async def create_component(
        self,
        repository: str,
        input_data: ComponentInput,
    ) -> Component:
        """Create or update a component.

        Args:
            repository: The repository name.
            input_data: The component input data.

        Returns:
            The created/updated component.
        """
        logger.debug(
            "Creating component",
            repository=repository,
            component_id=input_data.id,
        )

        component_repo = await self._container.get_component_repository()
        component = await component_repo.upsert_component(repository, input_data)

        # Handle depends_on relationships
        if input_data.depends_on:
            for dep_id in input_data.depends_on:
                await component_repo.create_dependency_relationship(
                    repository,
                    input_data.id,
                    dep_id,
                    input_data.branch or "main",
                )

        return component

    async def get_component(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> Optional[Component]:
        """Get a component by ID.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            The component if found, None otherwise.
        """
        component_repo = await self._container.get_component_repository()
        return await component_repo.find_by_id(repository, component_id, branch)

    async def update_component(
        self,
        repository: str,
        input_data: ComponentInput,
    ) -> Component:
        """Update a component (alias for create_component with upsert behavior).

        Args:
            repository: The repository name.
            input_data: The component input data.

        Returns:
            The updated component.
        """
        return await self.create_component(repository, input_data)

    async def update_component_status(
        self,
        repository: str,
        component_id: str,
        branch: str,
        status: ComponentStatus,
    ) -> Optional[Component]:
        """Update a component's status.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.
            status: The new status.

        Returns:
            The updated component, or None if not found.
        """
        component_repo = await self._container.get_component_repository()
        return await component_repo.update_component_status(
            repository, component_id, branch, status
        )

    async def delete_component(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a component.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            True if deleted, False otherwise.
        """
        logger.debug(
            "Deleting component",
            repository=repository,
            component_id=component_id,
        )

        component_repo = await self._container.get_component_repository()
        return await component_repo.delete_component(repository, component_id, branch)

    async def get_all_components(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[Component]:
        """Get all components.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all components.
        """
        component_repo = await self._container.get_component_repository()
        return await component_repo.get_all_components(repository, branch)

    # Decision operations

    async def create_decision(
        self,
        repository: str,
        input_data: DecisionInput,
    ) -> Decision:
        """Create or update a decision.

        Args:
            repository: The repository name.
            input_data: The decision input data.

        Returns:
            The created/updated decision.
        """
        logger.debug(
            "Creating decision",
            repository=repository,
            decision_id=input_data.id,
        )

        decision_repo = await self._container.get_decision_repository()
        return await decision_repo.upsert_decision(repository, input_data)

    async def get_decision(
        self,
        repository: str,
        decision_id: str,
        branch: str = "main",
    ) -> Optional[Decision]:
        """Get a decision by ID.

        Args:
            repository: The repository name.
            decision_id: The decision ID.
            branch: The branch name.

        Returns:
            The decision if found, None otherwise.
        """
        decision_repo = await self._container.get_decision_repository()
        return await decision_repo.find_by_id(repository, decision_id, branch)

    async def update_decision_status(
        self,
        repository: str,
        decision_id: str,
        branch: str,
        status: DecisionStatus,
    ) -> Optional[Decision]:
        """Update a decision's status.

        Args:
            repository: The repository name.
            decision_id: The decision ID.
            branch: The branch name.
            status: The new status.

        Returns:
            The updated decision, or None if not found.
        """
        decision_repo = await self._container.get_decision_repository()
        return await decision_repo.update_decision_status(
            repository, decision_id, branch, status
        )

    async def delete_decision(
        self,
        repository: str,
        decision_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a decision.

        Args:
            repository: The repository name.
            decision_id: The decision ID.
            branch: The branch name.

        Returns:
            True if deleted, False otherwise.
        """
        decision_repo = await self._container.get_decision_repository()
        return await decision_repo.delete_decision(repository, decision_id, branch)

    async def get_all_decisions(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[Decision]:
        """Get all decisions.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all decisions.
        """
        decision_repo = await self._container.get_decision_repository()
        return await decision_repo.get_all_decisions(repository, branch)

    # Rule operations

    async def create_rule(
        self,
        repository: str,
        input_data: RuleInput,
    ) -> Rule:
        """Create or update a rule.

        Args:
            repository: The repository name.
            input_data: The rule input data.

        Returns:
            The created/updated rule.
        """
        logger.debug(
            "Creating rule",
            repository=repository,
            rule_id=input_data.id,
        )

        rule_repo = await self._container.get_rule_repository()
        return await rule_repo.upsert_rule(repository, input_data)

    async def get_rule(
        self,
        repository: str,
        rule_id: str,
        branch: str = "main",
    ) -> Optional[Rule]:
        """Get a rule by ID.

        Args:
            repository: The repository name.
            rule_id: The rule ID.
            branch: The branch name.

        Returns:
            The rule if found, None otherwise.
        """
        rule_repo = await self._container.get_rule_repository()
        return await rule_repo.find_by_id(repository, rule_id, branch)

    async def update_rule_status(
        self,
        repository: str,
        rule_id: str,
        branch: str,
        status: RuleStatus,
    ) -> Optional[Rule]:
        """Update a rule's status.

        Args:
            repository: The repository name.
            rule_id: The rule ID.
            branch: The branch name.
            status: The new status.

        Returns:
            The updated rule, or None if not found.
        """
        rule_repo = await self._container.get_rule_repository()
        return await rule_repo.update_rule_status(repository, rule_id, branch, status)

    async def delete_rule(
        self,
        repository: str,
        rule_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a rule.

        Args:
            repository: The repository name.
            rule_id: The rule ID.
            branch: The branch name.

        Returns:
            True if deleted, False otherwise.
        """
        rule_repo = await self._container.get_rule_repository()
        return await rule_repo.delete_rule(repository, rule_id, branch)

    async def get_all_rules(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[Rule]:
        """Get all rules.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all rules.
        """
        rule_repo = await self._container.get_rule_repository()
        return await rule_repo.get_all_rules(repository, branch)

    # File operations

    async def create_file(
        self,
        repository: str,
        input_data: FileInput,
    ) -> File:
        """Create or update a file record.

        Args:
            repository: The repository name.
            input_data: The file input data.

        Returns:
            The created/updated file.
        """
        file_repo = await self._container.get_file_repository()
        return await file_repo.upsert_file(repository, input_data)

    async def get_file(
        self,
        repository: str,
        file_id: str,
        branch: str = "main",
    ) -> Optional[File]:
        """Get a file by ID.

        Args:
            repository: The repository name.
            file_id: The file ID.
            branch: The branch name.

        Returns:
            The file if found, None otherwise.
        """
        file_repo = await self._container.get_file_repository()
        return await file_repo.find_by_id(repository, file_id, branch)

    async def delete_file(
        self,
        repository: str,
        file_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a file.

        Args:
            repository: The repository name.
            file_id: The file ID.
            branch: The branch name.

        Returns:
            True if deleted, False otherwise.
        """
        file_repo = await self._container.get_file_repository()
        return await file_repo.delete_file(repository, file_id, branch)

    # Tag operations

    async def create_tag(
        self,
        repository: str,
        input_data: TagInput,
    ) -> Tag:
        """Create or update a tag.

        Args:
            repository: The repository name.
            input_data: The tag input data.

        Returns:
            The created/updated tag.
        """
        tag_repo = await self._container.get_tag_repository()
        return await tag_repo.upsert_tag(repository, input_data)

    async def get_tag(
        self,
        repository: str,
        tag_id: str,
        branch: str = "main",
    ) -> Optional[Tag]:
        """Get a tag by ID.

        Args:
            repository: The repository name.
            tag_id: The tag ID.
            branch: The branch name.

        Returns:
            The tag if found, None otherwise.
        """
        tag_repo = await self._container.get_tag_repository()
        return await tag_repo.find_by_id(repository, tag_id, branch)

    async def delete_tag(
        self,
        repository: str,
        tag_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a tag.

        Args:
            repository: The repository name.
            tag_id: The tag ID.
            branch: The branch name.

        Returns:
            True if deleted, False otherwise.
        """
        tag_repo = await self._container.get_tag_repository()
        return await tag_repo.delete_tag(repository, tag_id, branch)

    async def get_all_tags(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[Tag]:
        """Get all tags.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all tags.
        """
        tag_repo = await self._container.get_tag_repository()
        return await tag_repo.get_all_tags(repository, branch)

    # Generic entity operations

    async def get_entity(
        self,
        repository: str,
        entity_type: str,
        entity_id: str,
        branch: str = "main",
    ) -> Optional[Any]:
        """Get any entity by type and ID.

        Args:
            repository: The repository name.
            entity_type: The entity type (component, decision, rule, etc.).
            entity_id: The entity ID.
            branch: The branch name.

        Returns:
            The entity if found, None otherwise.
        """
        entity_type_lower = entity_type.lower()

        if entity_type_lower == "component":
            return await self.get_component(repository, entity_id, branch)
        elif entity_type_lower == "decision":
            return await self.get_decision(repository, entity_id, branch)
        elif entity_type_lower == "rule":
            return await self.get_rule(repository, entity_id, branch)
        elif entity_type_lower == "file":
            return await self.get_file(repository, entity_id, branch)
        elif entity_type_lower == "tag":
            return await self.get_tag(repository, entity_id, branch)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

    async def delete_entity(
        self,
        repository: str,
        entity_type: str,
        entity_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete any entity by type and ID.

        Args:
            repository: The repository name.
            entity_type: The entity type (component, decision, rule, etc.).
            entity_id: The entity ID.
            branch: The branch name.

        Returns:
            True if deleted, False otherwise.
        """
        entity_type_lower = entity_type.lower()

        if entity_type_lower == "component":
            return await self.delete_component(repository, entity_id, branch)
        elif entity_type_lower == "decision":
            return await self.delete_decision(repository, entity_id, branch)
        elif entity_type_lower == "rule":
            return await self.delete_rule(repository, entity_id, branch)
        elif entity_type_lower == "file":
            return await self.delete_file(repository, entity_id, branch)
        elif entity_type_lower == "tag":
            return await self.delete_tag(repository, entity_id, branch)
        elif entity_type_lower == "symbol":
            return await self.delete_symbol(repository, entity_id, branch)
        elif entity_type_lower == "requirement":
            return await self.delete_requirement(repository, entity_id, branch)
        elif entity_type_lower == "trace":
            return await self.delete_trace(repository, entity_id, branch)
        else:
            raise ValueError(f"Unknown entity type: {entity_type}")

    # =========================================================================
    # Cognitive Fabric operations (Symbol / Requirement / Trace)
    # =========================================================================

    async def create_symbol(
        self,
        repository: str,
        input_data: SymbolInput,
    ) -> Symbol:
        """Create or update a symbol."""
        symbol_repo = await self._container.get_symbol_repository()
        return await symbol_repo.upsert_symbol(repository, input_data)

    async def get_symbol(
        self,
        repository: str,
        symbol_id: str,
        branch: str = "main",
    ) -> Optional[Symbol]:
        """Get a symbol by ID."""
        symbol_repo = await self._container.get_symbol_repository()
        return await symbol_repo.find_by_id(repository, symbol_id, branch)

    async def delete_symbol(
        self,
        repository: str,
        symbol_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a symbol."""
        symbol_repo = await self._container.get_symbol_repository()
        return await symbol_repo.delete_symbol(repository, symbol_id, branch)

    async def link_symbol_to_file(
        self,
        repository: str,
        symbol_id: str,
        file_id: str,
        branch: str = "main",
    ) -> bool:
        """Create a DEFINED_IN edge from a symbol to a file."""
        symbol_repo = await self._container.get_symbol_repository()
        return await symbol_repo.link_to_file(repository, symbol_id, file_id, branch)

    async def link_symbol_evolution(
        self,
        repository: str,
        current_id: str,
        previous_id: str,
        branch: str = "main",
    ) -> bool:
        """Create an EVOLVED_FROM edge between two symbols."""
        symbol_repo = await self._container.get_symbol_repository()
        return await symbol_repo.link_evolution(
            repository, current_id, previous_id, branch
        )

    async def create_requirement(
        self,
        repository: str,
        input_data: RequirementInput,
    ) -> Requirement:
        """Create or update a requirement."""
        req_repo = await self._container.get_requirement_repository()
        return await req_repo.upsert_requirement(repository, input_data)

    async def get_requirement(
        self,
        repository: str,
        requirement_id: str,
        branch: str = "main",
    ) -> Optional[Requirement]:
        """Get a requirement by ID."""
        req_repo = await self._container.get_requirement_repository()
        return await req_repo.find_by_id(repository, requirement_id, branch)

    async def delete_requirement(
        self,
        repository: str,
        requirement_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a requirement."""
        req_repo = await self._container.get_requirement_repository()
        return await req_repo.delete_requirement(repository, requirement_id, branch)

    async def link_requirement_realised_by(
        self,
        repository: str,
        requirement_id: str,
        target_id: str,
        target_type: str = "Symbol",
        branch: str = "main",
    ) -> bool:
        """Create a REALISED_BY edge from a requirement to a symbol/component."""
        req_repo = await self._container.get_requirement_repository()
        return await req_repo.link_realised_by(
            repository, requirement_id, target_id, target_type, branch
        )

    async def link_requirement_evolution(
        self,
        repository: str,
        current_id: str,
        previous_id: str,
        branch: str = "main",
    ) -> bool:
        """Create an EVOLVED_FROM edge between two requirements."""
        req_repo = await self._container.get_requirement_repository()
        return await req_repo.link_evolution(
            repository, current_id, previous_id, branch
        )

    async def create_trace(
        self,
        repository: str,
        input_data: TraceInput,
    ) -> Trace:
        """Create or update a trace."""
        trace_repo = await self._container.get_trace_repository()
        return await trace_repo.upsert_trace(repository, input_data)

    async def get_trace(
        self,
        repository: str,
        trace_id: str,
        branch: str = "main",
    ) -> Optional[Trace]:
        """Get a trace by ID."""
        trace_repo = await self._container.get_trace_repository()
        return await trace_repo.find_by_id(repository, trace_id, branch)

    async def delete_trace(
        self,
        repository: str,
        trace_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a trace."""
        trace_repo = await self._container.get_trace_repository()
        return await trace_repo.delete_trace(repository, trace_id, branch)

    async def link_trace_to_symbol(
        self,
        repository: str,
        trace_id: str,
        symbol_id: str,
        branch: str = "main",
    ) -> bool:
        """Create a RECORDS edge from a trace to a symbol."""
        trace_repo = await self._container.get_trace_repository()
        return await trace_repo.link_to_symbol(repository, trace_id, symbol_id, branch)
