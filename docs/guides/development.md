# Development Guide

This guide covers development setup, coding standards, and contribution guidelines for Cognitive-Fabric.

## Development Environment

### Prerequisites

- Docker and Docker Compose (recommended)
- Python 3.11+ (for local development)
- Git

### Setup with Docker (Recommended)

```bash
# Clone the repository
git clone https://github.com/your-repo/cognitive_fabric-mcp.git
cd cognitive_fabric-mcp

# Build the development container
docker compose build

# Start a development shell
docker compose run --rm cognitive_fabric-dev bash
```

### Local Setup

```bash
# Create virtual environment
python -m venv .venv
source .venv/bin/activate

# Install with development dependencies
pip install -e ".[dev]"
```

## Project Structure

```
cognitive_fabric-mcp/
├── src/cognitive_fabric/           # Main source code
│   ├── agents/              # AI agents
│   │   └── memory_optimizer/
│   ├── cli/                 # Click CLI
│   ├── db/                  # Database layer
│   ├── mcp/                 # MCP server and tools
│   │   ├── handlers/        # Tool handlers
│   │   └── tools/           # Tool definitions
│   ├── repositories/        # Data access layer
│   ├── services/            # Business logic
│   │   ├── core/            # Interfaces
│   │   └── domain/          # Domain services
│   ├── types/               # Pydantic models
│   └── utils/               # Utilities
├── tests/                   # Test suite
│   ├── unit/                # Unit tests
│   ├── integration/         # Integration tests
│   └── e2e/                 # End-to-end tests
├── docs/                    # Documentation
├── scripts/                 # Helper scripts
├── docker-compose.yml       # Docker configuration
├── Dockerfile               # Production image
├── Dockerfile.dev           # Development image
└── pyproject.toml           # Project configuration
```

## Running Tests

### All Tests

```bash
# Using Docker
docker compose run --rm test

# Locally
pytest
```

### Specific Test Types

```bash
# Unit tests only
docker compose run --rm test-unit
pytest tests/unit

# Integration tests
docker compose run --rm test-integration
pytest tests/integration -m integration

# E2E tests
docker compose run --rm test-e2e
pytest tests/e2e -m e2e
```

### With Coverage

```bash
# Docker
docker compose run --rm coverage

# Local
pytest --cov=cognitive_fabric --cov-report=html --cov-report=term
```

Coverage reports are generated in `htmlcov/`.

### Running Specific Tests

```bash
# Single file
pytest tests/unit/test_types.py

# Single test
pytest tests/unit/test_types.py::TestEntityTypes::test_component_creation

# By marker
pytest -m "not slow"
```

## Code Quality

### Linting

We use `ruff` for linting:

```bash
# Check
docker compose run --rm lint
ruff check src/ tests/

# Fix automatically
ruff check --fix src/ tests/
```

### Formatting

```bash
# Check formatting
docker compose run --rm format
ruff format --check src/ tests/

# Apply formatting
ruff format src/ tests/
```

### Type Checking

We use `mypy` for type checking:

```bash
docker compose run --rm typecheck
mypy src/
```

### Pre-commit Hooks

Install pre-commit hooks:

```bash
pip install pre-commit
pre-commit install
```

The hooks will run automatically on commit.

## Coding Standards

### Python Style

- Follow PEP 8
- Use type hints for all public functions
- Maximum line length: 88 characters
- Use docstrings (Google style)

### Example Code Style

```python
"""Module docstring describing the purpose."""

from typing import Any, Dict, List, Optional

import structlog

from cognitive_fabric.types.entities import Component

logger = structlog.get_logger(__name__)


class ComponentService:
    """Service for managing components.

    This service handles CRUD operations for components
    and their relationships.
    """

    def __init__(self, repository: ComponentRepository) -> None:
        """Initialize the service.

        Args:
            repository: The component repository instance.
        """
        self._repository = repository

    async def create_component(
        self,
        repo: str,
        data: ComponentInput,
        branch: str = "main",
    ) -> Component:
        """Create a new component.

        Args:
            repo: Repository name.
            data: Component input data.
            branch: Branch name.

        Returns:
            The created component.

        Raises:
            ValidationError: If data is invalid.
            ConflictError: If component already exists.
        """
        logger.info("Creating component", repo=repo, id=data.id)
        return await self._repository.create(repo, data, branch)
```

### Async Patterns

- Use `async/await` for all I/O operations
- Use `asyncio.Lock` for thread safety
- Prefer `async with` for context managers

```python
class SafeService:
    def __init__(self) -> None:
        self._lock = asyncio.Lock()

    async def safe_operation(self) -> None:
        async with self._lock:
            # Thread-safe operation
            pass
```

### Error Handling

- Use specific exception types
- Log errors with context
- Return structured error responses

```python
class EntityNotFoundError(Exception):
    """Raised when an entity is not found."""

    def __init__(self, entity_type: str, entity_id: str) -> None:
        self.entity_type = entity_type
        self.entity_id = entity_id
        super().__init__(f"{entity_type} '{entity_id}' not found")


async def get_component(self, id: str) -> Component:
    component = await self._repository.find_by_id(id)
    if component is None:
        raise EntityNotFoundError("Component", id)
    return component
```

## Adding New Features

### Adding a New Tool

1. **Define the tool schema** in `src/cognitive_fabric/mcp/tools/definitions.py`:

```python
NEW_TOOL = McpTool(
    name="new-tool",
    description="Description of the new tool",
    parameters={
        "type": "object",
        "properties": {
            "operation": {"type": "string", "enum": ["op1", "op2"]},
            "repository": {"type": "string"},
        },
        "required": ["operation", "repository"],
    },
)

# Add to the list
MEMORY_BANK_MCP_TOOLS.append(NEW_TOOL)
```

2. **Create the handler** in `src/cognitive_fabric/mcp/handlers/new_tool.py`:

```python
async def new_tool_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    operation = params["operation"]
    repository = params["repository"]

    if operation == "op1":
        return await _handle_op1(repository, memory_service)
    elif operation == "op2":
        return await _handle_op2(repository, memory_service)
    else:
        return {"error": f"Unknown operation: {operation}"}
```

3. **Register the handler** in `src/cognitive_fabric/mcp/handlers/__init__.py`:

```python
from .new_tool import new_tool_handler

TOOL_HANDLERS = {
    # ... existing handlers
    "new-tool": new_tool_handler,
}
```

4. **Add tests** in `tests/`:

```python
@pytest.mark.asyncio
async def test_new_tool_op1(tool_registry):
    result = await tool_registry.handle_tool_call(
        "new-tool",
        {"operation": "op1", "repository": "test-repo"},
    )
    assert result["success"] is True
```

### Adding a New Entity Type

1. **Define the model** in `src/cognitive_fabric/types/entities.py`:

```python
class NewEntity(BaseEntity):
    """New entity type."""

    name: str
    custom_field: Optional[str] = None
```

2. **Add schema DDL** in `src/cognitive_fabric/db/schema_manager.py`:

```python
CREATE NODE TABLE IF NOT EXISTS NewEntity (
    graph_unique_id STRING PRIMARY KEY,
    id STRING,
    name STRING,
    custom_field STRING,
    repository STRING,
    branch STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP
);
```

3. **Create the repository** in `src/cognitive_fabric/repositories/`:

```python
class NewEntityRepository(BaseRepository):
    """Repository for NewEntity operations."""

    async def create(self, repo: str, data: NewEntityInput, branch: str) -> NewEntity:
        # Implementation
        pass
```

4. **Update services** to support the new entity type.

## Testing Guidelines

### Test Structure

```python
"""Tests for component service."""

import pytest
import pytest_asyncio

from cognitive_fabric.services.domain.entity import EntityService


class TestComponentOperations:
    """Tests for component CRUD operations."""

    @pytest_asyncio.fixture
    async def entity_service(self, memory_service):
        """Create entity service for testing."""
        return await memory_service.entity

    @pytest.mark.asyncio
    async def test_create_component(self, entity_service):
        """Test creating a component."""
        # Arrange
        data = {"id": "test", "name": "Test"}

        # Act
        result = await entity_service.create_component("repo", data)

        # Assert
        assert result.id == "test"
        assert result.name == "Test"
```

### Test Markers

- `@pytest.mark.unit` - Unit tests
- `@pytest.mark.integration` - Integration tests
- `@pytest.mark.e2e` - End-to-end tests
- `@pytest.mark.slow` - Slow tests (skipped by default)

### Fixtures

Common fixtures are defined in `tests/conftest.py`:

- `temp_dir` - Temporary directory
- `db_path` - Test database path
- `kuzu_client` - Initialized KuzuDB client
- `memory_service` - Memory service instance
- `sample_*_data` - Sample data for each entity type

## Debugging

### Debug Logging

```bash
COGNITIVE_FABRIC_LOG_LEVEL=DEBUG cognitive_fabric serve
```

### Interactive Debugging

```python
import pdb; pdb.set_trace()  # Python debugger

# Or with IPython
import IPython; IPython.embed()
```

### VS Code Debugging

`.vscode/launch.json`:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Debug Server",
      "type": "python",
      "request": "launch",
      "module": "cognitive_fabric.main",
      "console": "integratedTerminal"
    },
    {
      "name": "Debug Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": ["-v", "tests/"],
      "console": "integratedTerminal"
    }
  ]
}
```

## Making a Release

1. Update version in `pyproject.toml`
2. Update CHANGELOG.md
3. Create a git tag:
   ```bash
   git tag -a v1.0.0 -m "Release 1.0.0"
   git push origin v1.0.0
   ```
4. Build and publish:
   ```bash
   pip install build twine
   python -m build
   twine upload dist/*
   ```

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/my-feature`
3. Make your changes
4. Run tests: `docker compose run --rm test`
5. Run linting: `docker compose run --rm lint`
6. Commit with clear messages
7. Push and create a Pull Request

### Pull Request Guidelines

- Include tests for new features
- Update documentation as needed
- Keep changes focused and atomic
- Ensure all CI checks pass
