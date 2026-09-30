"""Integration tests for KuzuDB operations."""

import pytest
import pytest_asyncio

from cognitive_fabric.db.kuzu_client import KuzuDBClient
from cognitive_fabric.repositories.component_repo import ComponentRepository
from cognitive_fabric.repositories.decision_repo import DecisionRepository
from cognitive_fabric.repositories.tag_repo import TagRepository
from cognitive_fabric.types.entities import (
    ComponentInput,
    DecisionInput,
    TagInput,
)


@pytest.mark.integration
class TestKuzuClientOperations:
    """Tests for KuzuDB client operations."""

    @pytest.mark.asyncio
    async def test_client_initialization(self, kuzu_client: KuzuDBClient):
        """Test that client initializes correctly."""
        assert kuzu_client is not None
        # Client is usable: a trivial query round-trips.
        result = kuzu_client.fetch_all("RETURN 1 AS n")
        assert result[0]["n"] == 1

    @pytest.mark.asyncio
    async def test_schema_creation(self, kuzu_client: KuzuDBClient):
        """Test that schema is created on initialization."""
        # Query for node tables via the client's public API.
        result = kuzu_client.fetch_all("CALL show_tables() RETURN *")
        table_names = [r.get("name") for r in result]

        # Check for expected tables
        expected_tables = [
            "Repository", "Component", "Decision", "Rule",
            "Context", "File", "Tag", "Metadata"
        ]
        for table in expected_tables:
            assert table in table_names, f"Table {table} not found"


@pytest.mark.integration
class TestComponentRepository:
    """Tests for ComponentRepository operations."""

    @pytest_asyncio.fixture
    async def component_repo(self, kuzu_client: KuzuDBClient):
        """Create a ComponentRepository for testing."""
        return ComponentRepository(kuzu_client)

    @pytest.mark.asyncio
    async def test_create_component(
        self,
        component_repo: ComponentRepository,
        sample_repository: str,
        sample_branch: str,
        sample_component_data: dict,
    ):
        """Test creating a component."""
        component_input = ComponentInput(**sample_component_data)

        component = await component_repo.upsert_component(
            sample_repository,
            component_input,
        )

        assert component is not None
        assert component.id == sample_component_data["id"]
        assert component.name == sample_component_data["name"]

    @pytest.mark.asyncio
    async def test_find_component_by_id(
        self,
        component_repo: ComponentRepository,
        sample_repository: str,
        sample_branch: str,
        sample_component_data: dict,
    ):
        """Test finding a component by ID."""
        # First create
        component_input = ComponentInput(**sample_component_data)
        await component_repo.upsert_component(sample_repository, component_input)

        # Then find
        found = await component_repo.find_by_id(
            sample_repository,
            sample_component_data["id"],
            sample_branch,
        )

        assert found is not None
        assert found.id == sample_component_data["id"]

    @pytest.mark.asyncio
    async def test_update_component(
        self,
        component_repo: ComponentRepository,
        sample_repository: str,
        sample_branch: str,
        sample_component_data: dict,
    ):
        """Test updating a component (via upsert)."""
        # Create
        component_input = ComponentInput(**sample_component_data)
        await component_repo.upsert_component(sample_repository, component_input)

        # Update by re-upserting with a changed name
        updated_input = ComponentInput(
            **{**sample_component_data, "name": "UpdatedComponent"}
        )
        await component_repo.upsert_component(sample_repository, updated_input)

        updated = await component_repo.find_by_id(
            sample_repository,
            sample_component_data["id"],
            sample_branch,
        )
        assert updated is not None
        assert updated.name == "UpdatedComponent"

    @pytest.mark.asyncio
    async def test_delete_component(
        self,
        component_repo: ComponentRepository,
        sample_repository: str,
        sample_branch: str,
        sample_component_data: dict,
    ):
        """Test deleting a component."""
        # Create
        component_input = ComponentInput(**sample_component_data)
        await component_repo.upsert_component(sample_repository, component_input)

        # Delete
        result = await component_repo.delete_component(
            sample_repository,
            sample_component_data["id"],
            sample_branch,
        )

        assert result is True

        # Verify deleted
        found = await component_repo.find_by_id(
            sample_repository,
            sample_component_data["id"],
            sample_branch,
        )
        assert found is None

    @pytest.mark.asyncio
    async def test_component_dependencies(
        self,
        component_repo: ComponentRepository,
        sample_repository: str,
        sample_branch: str,
    ):
        """Test component dependency relationships."""
        # Create two components
        comp1 = ComponentInput(id="comp-1", name="Component1")
        comp2 = ComponentInput(id="comp-2", name="Component2", depends_on=["comp-1"])

        await component_repo.upsert_component(sample_repository, comp1)
        await component_repo.upsert_component(sample_repository, comp2)

        # Create dependency relationship
        await component_repo.create_dependency_relationship(
            sample_repository, "comp-2", "comp-1", sample_branch
        )

        # Get dependencies
        deps = await component_repo.get_dependencies(
            sample_repository, "comp-2", sample_branch
        )

        assert len(deps) == 1
        assert deps[0].id == "comp-1"

        # Get dependents
        dependents = await component_repo.get_dependents(
            sample_repository, "comp-1", sample_branch
        )

        assert len(dependents) == 1
        assert dependents[0].id == "comp-2"


@pytest.mark.integration
class TestDecisionRepository:
    """Tests for DecisionRepository operations."""

    @pytest_asyncio.fixture
    async def decision_repo(self, kuzu_client: KuzuDBClient):
        """Create a DecisionRepository for testing."""
        return DecisionRepository(kuzu_client)

    @pytest.mark.asyncio
    async def test_create_decision(
        self,
        decision_repo: DecisionRepository,
        sample_repository: str,
        sample_branch: str,
        sample_decision_data: dict,
    ):
        """Test creating a decision."""
        decision_input = DecisionInput(**sample_decision_data)

        decision = await decision_repo.upsert_decision(
            sample_repository,
            decision_input,
        )

        assert decision is not None
        assert decision.id == sample_decision_data["id"]
        assert decision.name == sample_decision_data["name"]


@pytest.mark.integration
class TestTagRepository:
    """Tests for TagRepository operations."""

    @pytest_asyncio.fixture
    async def tag_repo(self, kuzu_client: KuzuDBClient):
        """Create a TagRepository for testing."""
        return TagRepository(kuzu_client)

    @pytest_asyncio.fixture
    async def component_repo(self, kuzu_client: KuzuDBClient):
        """Create a ComponentRepository for testing."""
        return ComponentRepository(kuzu_client)

    @pytest.mark.asyncio
    async def test_create_tag(
        self,
        tag_repo: TagRepository,
        sample_repository: str,
        sample_branch: str,
        sample_tag_data: dict,
    ):
        """Test creating a tag."""
        tag_input = TagInput(**sample_tag_data)

        tag = await tag_repo.upsert_tag(
            sample_repository,
            tag_input,
        )

        assert tag is not None
        assert tag.id == sample_tag_data["id"]
        assert tag.name == sample_tag_data["name"]

    @pytest.mark.asyncio
    async def test_tag_item(
        self,
        tag_repo: TagRepository,
        component_repo: ComponentRepository,
        sample_repository: str,
        sample_branch: str,
        sample_tag_data: dict,
        sample_component_data: dict,
    ):
        """Test tagging an item."""
        # Create tag and component
        tag_input = TagInput(**sample_tag_data)
        await tag_repo.upsert_tag(sample_repository, tag_input)

        component_input = ComponentInput(**sample_component_data)
        await component_repo.upsert_component(sample_repository, component_input)

        # Tag the component (item_id, item_type, tag_id)
        await tag_repo.create_tagged_with_relationship(
            sample_repository,
            sample_component_data["id"],
            "Component",
            sample_tag_data["id"],
            sample_branch,
        )

        # Get items with tag
        items = await tag_repo.get_items_with_tag(
            sample_repository,
            sample_tag_data["id"],
            sample_branch,
        )

        assert any(item.get("id") == sample_component_data["id"] for item in items)
