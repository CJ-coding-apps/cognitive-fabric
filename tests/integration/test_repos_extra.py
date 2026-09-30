"""Integration tests for the previously-untested repositories.

Exercises upsert + read round-trips (and a couple of relationships) against a
real KuzuDB to surface never-run divergences between models, schema, and queries.
"""

import pytest
import pytest_asyncio

from cognitive_fabric.db.kuzu_client import KuzuDBClient
from cognitive_fabric.repositories.component_repo import ComponentRepository
from cognitive_fabric.repositories.context_repo import ContextRepository
from cognitive_fabric.repositories.file_repo import FileRepository
from cognitive_fabric.repositories.metadata_repo import MetadataRepository
from cognitive_fabric.repositories.repository_repo import RepositoryRepository
from cognitive_fabric.repositories.rule_repo import RuleRepository
from cognitive_fabric.types.entities import (
    ComponentInput,
    ContextInput,
    FileInput,
    MetadataInput,
    RepositoryInput,
    RuleInput,
    RuleStatus,
)

REPO = "test-repo"
BRANCH = "main"


@pytest.mark.integration
class TestRepositoryRepository:
    @pytest.mark.asyncio
    async def test_create_find_exists(self, kuzu_client: KuzuDBClient):
        repo = RepositoryRepository(kuzu_client)
        created = await repo.create(RepositoryInput(name=REPO, branch=BRANCH))
        assert created is not None
        assert created.name == REPO

        found = await repo.find_by_name(REPO, BRANCH)
        assert found is not None and found.name == REPO
        assert await repo.exists(REPO, BRANCH) is True


@pytest.mark.integration
class TestRuleRepository:
    @pytest_asyncio.fixture
    async def rule_repo(self, kuzu_client: KuzuDBClient):
        return RuleRepository(kuzu_client)

    @pytest.mark.asyncio
    async def test_upsert_and_find(self, rule_repo: RuleRepository):
        rule_input = RuleInput(
            id="rule-001",
            name="TestRule",
            created="2024-01-15",
            content="Test content",
            triggers=["on-commit", "on-push"],
            status=RuleStatus.ACTIVE,
        )
        rule = await rule_repo.upsert_rule(REPO, rule_input)
        assert rule is not None and rule.id == "rule-001"

        found = await rule_repo.find_by_id(REPO, "rule-001", BRANCH)
        assert found is not None
        assert found.name == "TestRule"
        assert found.triggers == ["on-commit", "on-push"]


@pytest.mark.integration
class TestContextRepository:
    @pytest_asyncio.fixture
    async def context_repo(self, kuzu_client: KuzuDBClient):
        return ContextRepository(kuzu_client)

    @pytest.mark.asyncio
    async def test_upsert_and_find(self, context_repo: ContextRepository):
        ctx_input = ContextInput(
            id="ctx-001",
            name="TestContext",
            iso_date="2024-01-15",
            agent="test-agent",
            summary="Test summary",
            observation="Test observation",
        )
        ctx = await context_repo.upsert_context(REPO, ctx_input)
        assert ctx is not None and ctx.id == "ctx-001"

        found = await context_repo.find_by_id(REPO, "ctx-001", BRANCH)
        assert found is not None
        assert found.summary == "Test summary"


@pytest.mark.integration
class TestFileRepository:
    @pytest_asyncio.fixture
    async def file_repo(self, kuzu_client: KuzuDBClient):
        return FileRepository(kuzu_client)

    @pytest.mark.asyncio
    async def test_upsert_find_and_path(self, file_repo: FileRepository):
        file_input = FileInput(
            id="file-001",
            name="test.py",
            path="/src/test.py",
            mime_type="text/x-python",
            size=1024,
        )
        f = await file_repo.upsert_file(REPO, file_input)
        assert f is not None and f.id == "file-001"

        found = await file_repo.find_by_id(REPO, "file-001", BRANCH)
        assert found is not None and found.path == "/src/test.py"

        by_path = await file_repo.find_by_path(REPO, "/src/test.py", BRANCH)
        assert by_path is not None and by_path.id == "file-001"

    @pytest.mark.asyncio
    async def test_implements_relationship(
        self, file_repo: FileRepository, kuzu_client: KuzuDBClient
    ):
        comp_repo = ComponentRepository(kuzu_client)
        await comp_repo.upsert_component(
            REPO, ComponentInput(id="comp-x", name="CompX")
        )
        await file_repo.upsert_file(
            REPO, FileInput(id="file-x", name="x.py", path="/src/x.py")
        )

        ok = await file_repo.create_implements_relationship(
            REPO, "comp-x", "file-x", BRANCH
        )
        assert ok is True


@pytest.mark.integration
class TestMetadataRepository:
    @pytest_asyncio.fixture
    async def metadata_repo(self, kuzu_client: KuzuDBClient):
        return MetadataRepository(kuzu_client)

    @pytest.mark.asyncio
    async def test_upsert_and_find(self, metadata_repo: MetadataRepository):
        meta_input = MetadataInput(
            id="meta-001",
            name="metadata",
            tech_stack={"language": "python"},
            architecture="layered",
        )
        meta = await metadata_repo.upsert_metadata(REPO, meta_input)
        assert meta is not None and meta.id == "meta-001"

        found = await metadata_repo.find_by_id(REPO, "meta-001", BRANCH)
        assert found is not None
