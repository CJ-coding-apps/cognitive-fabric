"""Pydantic models for all 8 entity types."""

from datetime import datetime
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field

# =============================================================================
# Enums
# =============================================================================


class ComponentStatus(str, Enum):
    """Component lifecycle status."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PLANNED = "planned"


class DecisionStatus(str, Enum):
    """Decision lifecycle status."""

    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    REJECTED = "rejected"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"


class RuleStatus(str, Enum):
    """Rule lifecycle status."""

    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PROPOSED = "proposed"


# =============================================================================
# Base Entity
# =============================================================================


class BaseEntity(BaseModel):
    """Base entity with common fields for all entity types."""

    id: str
    repository: str
    branch: str = "main"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def graph_unique_id(self) -> str:
        """Generate the graph-unique ID for this entity."""
        return f"{self.repository}:{self.branch}:{self.id}"


# =============================================================================
# Repository
# =============================================================================


class Repository(BaseModel):
    """Repository entity - represents a code repository with branch."""

    id: str  # Synthetic ID: "name:branch"
    name: str
    branch: str = "main"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    tech_stack: Optional[list[str]] = None
    architecture: Optional[str] = None


class RepositoryInput(BaseModel):
    """Input model for creating/updating a Repository."""

    name: str
    branch: str = "main"
    tech_stack: Optional[list[str]] = None
    architecture: Optional[str] = None


# =============================================================================
# Component
# =============================================================================


class Component(BaseEntity):
    """Component entity - architectural units/microservices."""

    name: str
    kind: Optional[str] = None
    depends_on: Optional[list[str]] = None
    status: Optional[ComponentStatus] = ComponentStatus.ACTIVE
    description: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


class ComponentInput(BaseModel):
    """Input model for creating/updating a Component."""

    id: str
    name: str
    branch: Optional[str] = "main"
    kind: Optional[str] = None
    status: Optional[ComponentStatus] = ComponentStatus.ACTIVE
    depends_on: Optional[list[str]] = None
    description: Optional[str] = None
    metadata: Optional[dict[str, Any]] = None


# =============================================================================
# Decision
# =============================================================================


class Decision(BaseEntity):
    """Decision entity - design choices and governance."""

    name: str
    context: Optional[str] = None
    date: str  # ISO date format
    status: Optional[DecisionStatus] = DecisionStatus.ACCEPTED
    rationale: Optional[str] = None
    impact: Optional[list[str]] = None
    tags: Optional[list[str]] = None


class DecisionInput(BaseModel):
    """Input model for creating/updating a Decision."""

    id: str
    name: str
    branch: Optional[str] = "main"
    context: Optional[str] = None
    date: str
    status: Optional[DecisionStatus] = DecisionStatus.ACCEPTED
    rationale: Optional[str] = None
    impact: Optional[list[str]] = None
    tags: Optional[list[str]] = None


# =============================================================================
# Rule
# =============================================================================


class Rule(BaseEntity):
    """Rule entity - governance and constraints."""

    name: str
    created: str  # ISO date format
    triggers: Optional[list[str]] = None
    content: Optional[str] = None
    status: Optional[RuleStatus] = RuleStatus.ACTIVE
    description: Optional[str] = None
    scope: Optional[str] = None
    severity: Optional[str] = None
    category: Optional[str] = None
    examples: Optional[list[str]] = None


class RuleInput(BaseModel):
    """Input model for creating/updating a Rule."""

    id: str
    name: str
    branch: Optional[str] = "main"
    created: str
    triggers: Optional[list[str]] = None
    content: Optional[str] = None
    status: Optional[RuleStatus] = RuleStatus.ACTIVE
    description: Optional[str] = None
    scope: Optional[str] = None
    severity: Optional[str] = None
    category: Optional[str] = None
    examples: Optional[list[str]] = None


# =============================================================================
# Context
# =============================================================================


class Context(BaseEntity):
    """Context entity - session/conversation state."""

    name: str
    iso_date: str  # ISO date format: YYYY-MM-DD
    agent: Optional[str] = None
    related_issue: Optional[str] = None
    summary: Optional[str] = None
    observation: Optional[str] = None
    decisions: Optional[list[str]] = None
    observations: Optional[list[str]] = None


class ContextInput(BaseModel):
    """Input model for creating/updating a Context."""

    id: Optional[str] = None  # Auto-generated from iso_date if not provided
    name: Optional[str] = None
    branch: Optional[str] = "main"
    iso_date: Optional[str] = None
    agent: Optional[str] = None
    related_issue: Optional[str] = None
    summary: Optional[str] = None
    observation: Optional[str] = None
    decisions: Optional[list[str]] = None
    observations: Optional[list[str]] = None


# =============================================================================
# File
# =============================================================================


class File(BaseEntity):
    """File entity - code artifact references."""

    name: str
    path: str
    size: Optional[int] = None  # in bytes
    mime_type: Optional[str] = None
    content: Optional[str] = None
    metrics: Optional[dict[str, Any]] = None
    checksum: Optional[str] = None
    last_modified: Optional[datetime] = None


class FileInput(BaseModel):
    """Input model for creating/updating a File."""

    id: str
    name: str
    path: str
    branch: Optional[str] = "main"
    size: Optional[int] = None
    mime_type: Optional[str] = None
    content: Optional[str] = None
    metrics: Optional[dict[str, Any]] = None
    checksum: Optional[str] = None


# =============================================================================
# Tag
# =============================================================================


class Tag(BaseEntity):
    """Tag entity - classification metadata."""

    name: str
    color: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


class TagInput(BaseModel):
    """Input model for creating/updating a Tag."""

    id: str
    name: str
    branch: Optional[str] = "main"
    color: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None


# =============================================================================
# Metadata
# =============================================================================


class MetadataContent(BaseModel):
    """Content structure for Metadata entity.

    A flexible bag: `id` is optional and extra keys (e.g. init bookkeeping like
    client_project_root / initialized_at) are permitted.
    """

    model_config = {"extra": "allow"}

    id: Optional[str] = None
    project: Optional[dict[str, str]] = Field(
        default=None,
        description="Project info: name, created, description",
    )
    tech_stack: Optional[dict[str, str]] = None
    architecture: Optional[str] = None
    memory_spec_version: Optional[str] = None


class Metadata(BaseEntity):
    """Metadata entity - project context and tech stack."""

    name: str
    content: MetadataContent


class MetadataInput(BaseModel):
    """Input model for creating/updating Metadata."""

    id: str
    name: Optional[str] = "metadata"
    branch: Optional[str] = "main"
    content: Optional[MetadataContent] = None
    # Alternative flat fields for convenience
    project: Optional[dict[str, str]] = None
    tech_stack: Optional[dict[str, str]] = None
    architecture: Optional[str] = None
    memory_spec_version: Optional[str] = None


# =============================================================================
# Cognitive Fabric entities
# =============================================================================


class RequirementStatus(str, Enum):
    """Requirement lifecycle status."""

    DRAFT = "draft"
    ACTIVE = "active"
    SATISFIED = "satisfied"
    DEPRECATED = "deprecated"


class Symbol(BaseEntity):
    """Symbol entity - a code symbol (function, class, method)."""

    name: str
    kind: Optional[str] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None


class SymbolInput(BaseModel):
    """Input model for creating/updating a Symbol."""

    id: str
    name: str
    branch: Optional[str] = "main"
    kind: Optional[str] = None
    signature: Optional[str] = None
    docstring: Optional[str] = None


class Requirement(BaseEntity):
    """Requirement entity - a high-level intent/goal."""

    name: str
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[RequirementStatus] = RequirementStatus.ACTIVE


class RequirementInput(BaseModel):
    """Input model for creating/updating a Requirement."""

    id: str
    name: str
    branch: Optional[str] = "main"
    description: Optional[str] = None
    priority: Optional[str] = None
    status: Optional[RequirementStatus] = RequirementStatus.ACTIVE


class Trace(BaseEntity):
    """Trace entity - a runtime/episodic observation linked to code."""

    name: str
    trace_type: Optional[str] = None
    content: Optional[str] = None


class TraceInput(BaseModel):
    """Input model for creating/updating a Trace."""

    id: str
    name: str
    branch: Optional[str] = "main"
    trace_type: Optional[str] = None
    content: Optional[str] = None
