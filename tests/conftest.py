"""Pytest fixtures for KuzuMemPy tests."""

import asyncio
import shutil
import tempfile
from pathlib import Path
from typing import AsyncGenerator, Generator

import pytest
import pytest_asyncio

from cognitive_fabric.config import Settings
from cognitive_fabric.db.kuzu_client import KuzuDBClient
from cognitive_fabric.services.memory_service import MemoryService


@pytest.fixture(scope="session")
def event_loop():
    """Create an event loop for the test session."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Create a temporary directory for test files."""
    temp_path = Path(tempfile.mkdtemp(prefix="cognitive_fabric_test_"))
    yield temp_path
    shutil.rmtree(temp_path, ignore_errors=True)


@pytest.fixture(autouse=True)
def _isolate_fabric_data(tmp_path, monkeypatch):
    """Isolate the LanceDB vector store per test (avoids cross-test leakage via
    the default cwd-relative ./.fabric_data), and keep the repo clean."""
    monkeypatch.setenv("FABRIC_DATA_DIR", str(tmp_path / "fabric_data"))
    yield


@pytest.fixture
def db_path(temp_dir: Path) -> Path:
    """Get a path for a test database."""
    return temp_dir / "test_db"


@pytest.fixture
def settings(db_path: Path) -> Settings:
    """Create test settings."""
    return Settings(db_path=str(db_path))


@pytest_asyncio.fixture
async def kuzu_client(db_path: Path) -> AsyncGenerator[KuzuDBClient, None]:
    """Create and initialize a KuzuDB client for testing."""
    client = KuzuDBClient(str(db_path))
    await client.initialize()
    yield client
    # Cleanup is handled by temp_dir fixture


@pytest_asyncio.fixture
async def memory_service(db_path: Path) -> AsyncGenerator[MemoryService, None]:
    """Create a memory service for testing (fresh singleton per test)."""
    MemoryService.reset_instance()
    service = await MemoryService.get_instance(str(db_path))
    yield service
    await service.close()
    MemoryService.reset_instance()


@pytest.fixture
def sample_repository() -> str:
    """Return a sample repository name for testing."""
    return "test-repo"


@pytest.fixture
def sample_branch() -> str:
    """Return a sample branch name for testing."""
    return "main"


@pytest.fixture
def sample_component_data() -> dict:
    """Return sample component data for testing."""
    return {
        "id": "comp-001",
        "name": "TestComponent",
        "kind": "service",
        "status": "active",
        "depends_on": [],
    }


@pytest.fixture
def sample_decision_data() -> dict:
    """Return sample decision data for testing."""
    return {
        "id": "dec-001",
        "name": "TestDecision",
        "context": "Testing decision context",
        "date": "2024-01-15",
        "status": "accepted",
    }


@pytest.fixture
def sample_rule_data() -> dict:
    """Return sample rule data for testing."""
    return {
        "id": "rule-001",
        "name": "TestRule",
        "content": "Test rule content",
        "triggers": ["test-trigger"],
        "status": "active",
    }


@pytest.fixture
def sample_context_data() -> dict:
    """Return sample context data for testing."""
    return {
        "id": "ctx-001",
        "name": "TestContext",
        "iso_date": "2024-01-15T10:30:00Z",
        "agent": "test-agent",
        "summary": "Test summary",
        "observation": "Test observation",
    }


@pytest.fixture
def sample_file_data() -> dict:
    """Return sample file data for testing."""
    return {
        "id": "file-001",
        "name": "test.py",
        "path": "/src/test.py",
        "size": 1024,
        "mime_type": "text/x-python",
    }


@pytest.fixture
def sample_tag_data() -> dict:
    """Return sample tag data for testing."""
    return {
        "id": "tag-001",
        "name": "test-tag",
        "color": "#FF0000",
        "description": "A test tag",
        "category": "testing",
    }


@pytest.fixture
def sample_metadata_data() -> dict:
    """Return sample metadata data for testing."""
    return {
        "id": "meta-001",
        "name": "TestMetadata",
        "content": {
            "version": "1.0.0",
            "description": "Test metadata content",
        },
    }


# Markers for different test types
def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "unit: mark test as unit test")
    config.addinivalue_line("markers", "integration: mark test as integration test")
    config.addinivalue_line("markers", "e2e: mark test as end-to-end test")
    config.addinivalue_line("markers", "slow: mark test as slow")
