# Entity Schemas

This document describes the Pydantic models for all entity types in Cognitive-Fabric.

## Base Entity

All entities inherit from `BaseEntity`:

```python
class BaseEntity(BaseModel):
    id: str
    repository: str
    branch: str = "main"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    def graph_unique_id(self) -> str:
        """Generate unique ID for graph storage."""
        return f"{self.repository}:{self.branch}:{self.id}"
```

## Component

Represents a software component or module.

```python
class ComponentStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PLANNED = "planned"

class Component(BaseEntity):
    name: str
    kind: Optional[str] = None          # e.g., "service", "library", "module"
    depends_on: Optional[List[str]] = None  # List of component IDs
    status: Optional[ComponentStatus] = ComponentStatus.ACTIVE
```

### Example

```json
{
  "id": "auth-service",
  "name": "Authentication Service",
  "kind": "service",
  "status": "active",
  "depends_on": ["user-service", "database"],
  "repository": "my-app",
  "branch": "main"
}
```

## Decision

Represents an architectural decision record (ADR).

```python
class DecisionStatus(str, Enum):
    PROPOSED = "proposed"
    ACCEPTED = "accepted"
    DEPRECATED = "deprecated"
    SUPERSEDED = "superseded"

class Decision(BaseEntity):
    name: str
    context: Optional[str] = None       # Decision context/background
    date: Optional[str] = None          # ISO date string
    status: Optional[DecisionStatus] = DecisionStatus.PROPOSED
```

### Example

```json
{
  "id": "adr-001",
  "name": "Use PostgreSQL for Primary Database",
  "context": "Need ACID compliance and support for complex queries",
  "date": "2024-01-15",
  "status": "accepted",
  "repository": "my-app",
  "branch": "main"
}
```

## Rule

Represents a governance rule or coding standard.

```python
class RuleStatus(str, Enum):
    ACTIVE = "active"
    DEPRECATED = "deprecated"
    PROPOSED = "proposed"

class Rule(BaseEntity):
    name: str
    created: Optional[str] = None       # ISO date string
    triggers: Optional[List[str]] = None  # Events that trigger the rule
    content: Optional[str] = None       # Rule content/description
    status: Optional[RuleStatus] = RuleStatus.ACTIVE
```

### Example

```json
{
  "id": "rule-001",
  "name": "All Services Must Have Health Checks",
  "created": "2024-01-01",
  "triggers": ["service-creation", "deployment"],
  "content": "Every service must expose a /health endpoint...",
  "status": "active",
  "repository": "my-app",
  "branch": "main"
}
```

## Context

Represents a session context or conversation summary.

```python
class Context(BaseEntity):
    name: str
    iso_date: Optional[str] = None      # ISO timestamp
    agent: Optional[str] = None         # Agent identifier
    summary: Optional[str] = None       # Context summary
    observation: Optional[str] = None   # Additional observations
```

### Example

```json
{
  "id": "ctx-20240115-001",
  "name": "Authentication Implementation Discussion",
  "iso_date": "2024-01-15T10:30:00Z",
  "agent": "claude",
  "summary": "Discussed JWT vs session-based authentication",
  "observation": "User prefers JWT for stateless architecture",
  "repository": "my-app",
  "branch": "main"
}
```

## File

Represents a source code file reference.

```python
class File(BaseEntity):
    name: str
    path: Optional[str] = None          # File path
    size: Optional[int] = None          # File size in bytes
    mime_type: Optional[str] = None     # MIME type
    metadata: Optional[str] = None      # Additional metadata (JSON string)
```

### Example

```json
{
  "id": "file-auth-service",
  "name": "auth_service.py",
  "path": "/src/services/auth_service.py",
  "size": 4096,
  "mime_type": "text/x-python",
  "repository": "my-app",
  "branch": "main"
}
```

## Tag

Represents a classification tag.

```python
class Tag(BaseEntity):
    name: str
    color: Optional[str] = None         # Hex color code
    description: Optional[str] = None   # Tag description
    category: Optional[str] = None      # Tag category
```

### Example

```json
{
  "id": "tag-backend",
  "name": "backend",
  "color": "#3498db",
  "description": "Backend services and components",
  "category": "layer",
  "repository": "my-app",
  "branch": "main"
}
```

## Metadata

Represents project metadata.

```python
class MetadataContent(BaseModel):
    """Structured metadata content."""
    projectName: Optional[str] = None
    techStack: Optional[List[str]] = None
    version: Optional[str] = None
    description: Optional[str] = None

class Metadata(BaseEntity):
    name: str
    content: Optional[MetadataContent] = None
```

### Example

```json
{
  "id": "meta-project",
  "name": "Project Metadata",
  "content": {
    "projectName": "My App",
    "techStack": ["Python", "FastAPI", "PostgreSQL"],
    "version": "1.0.0",
    "description": "A sample application"
  },
  "repository": "my-app",
  "branch": "main"
}
```

## Repository

Represents a code repository.

```python
class Repository(BaseModel):
    id: str
    name: str
    branch: str = "main"
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
```

### Example

```json
{
  "id": "my-app",
  "name": "my-app",
  "branch": "main",
  "created_at": "2024-01-01T00:00:00Z"
}
```

## Input Types

For creating entities, use the corresponding input types:

```python
class ComponentInput(BaseModel):
    id: str
    name: str
    kind: Optional[str] = None
    status: Optional[str] = None
    depends_on: Optional[List[str]] = None

class DecisionInput(BaseModel):
    id: str
    name: str
    context: Optional[str] = None
    date: Optional[str] = None
    status: Optional[str] = None

class RuleInput(BaseModel):
    id: str
    name: str
    created: Optional[str] = None
    triggers: Optional[List[str]] = None
    content: Optional[str] = None
    status: Optional[str] = None

# ... similar for other entities
```

## Optimization Types

### OptimizationStrategy

```python
class OptimizationStrategy(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
```

### Issue

```python
class Issue(BaseModel):
    type: str                           # Issue type identifier
    severity: Literal["low", "medium", "high"]
    description: str
    affected_ids: List[str] = []
```

### Recommendation

```python
class Recommendation(BaseModel):
    priority: int                       # 1 = highest priority
    action: str                         # Recommended action
    reason: str                         # Why this is recommended
    impact: str                         # Expected impact
    risk: Literal["low", "medium", "high"]
    affected_ids: List[str] = []
```

### ExecutionResult

```python
class ExecutionResult(BaseModel):
    plan_id: str
    repository: str
    branch: str
    snapshot_id: Optional[str] = None
    dry_run: bool
    executed: List[Dict[str, Any]] = []
    failed: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []
    summary: Dict[str, Any] = {}
```

## Validation

All models use Pydantic v2 validation:

```python
from pydantic import ValidationError

try:
    component = Component(
        id="",  # Will fail - empty string
        name="Test",
        repository="my-app"
    )
except ValidationError as e:
    print(e.errors())
```

## Serialization

Models can be serialized to JSON:

```python
component = Component(
    id="auth-service",
    name="Auth Service",
    repository="my-app",
    branch="main"
)

# To dict
data = component.model_dump()

# To JSON string
json_str = component.model_dump_json()

# For database (mode="json" handles datetime)
db_data = component.model_dump(mode="json")
```
