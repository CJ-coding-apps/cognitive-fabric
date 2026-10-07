"""Integration tests for DataFabricService + DreamService (in-process, no Flight).

Uses injected fakes for the ingestor / vector store / LLM so the persistence
and distillation logic is validated against real kuzu without the heavy optional
dependencies (tree-sitter / lancedb / sentence-transformers / LLM SDKs).
"""

import json

import pytest

from cognitive_fabric import config as fabric_config
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.entities import ContextInput, SymbolInput

REPO = "svc-fab"
BRANCH = "main"


class _FakeIngestor:
    def __init__(self, symbols, files):
        self._symbols = symbols
        self._files = files

    def scan_project(self, root_path):
        return self._symbols, self._files


class _FakeVectorStore:
    def __init__(self):
        self.calls = []

    def upsert(self, repository, branch, symbols):
        self.calls.append((repository, branch, len(symbols)))
        return len(symbols)

    def search(self, repository, branch, query, limit=10, threshold=0.0):
        return [
            {"symbol_id": "a.py:foo", "name": "foo", "file_id": "a.py", "score": 0.9}
        ]


class _FakeAnthropicClient:
    """Duck-typed anthropic-style client (has `.messages`, not `.chat`)."""

    def __init__(self, payload: str):
        self._payload = payload
        self.requests: list[dict] = []

    class _Messages:
        def __init__(self, payload, requests):
            self._payload = payload
            self._requests = requests

        def create(self, **kwargs):
            self._requests.append(kwargs)
            block = type("Block", (), {"text": self._payload})()
            return type("Resp", (), {"content": [block]})()

    @property
    def messages(self):
        return self._Messages(self._payload, self.requests)


class _FakeOpenAIClient:
    """Duck-typed openai-style client (has `.chat`, not `.messages`)."""

    def __init__(self, payload: str):
        self._payload = payload
        self.requests: list[dict] = []

    class _Completions:
        def __init__(self, payload, requests):
            self._payload = payload
            self._requests = requests

        def create(self, **kwargs):
            self._requests.append(kwargs)
            message = type("Message", (), {"content": self._payload})()
            choice = type("Choice", (), {"message": message})()
            return type("Resp", (), {"choices": [choice]})()

    class _Chat:
        def __init__(self, payload, requests):
            self.completions = _FakeOpenAIClient._Completions(payload, requests)

    @property
    def chat(self):
        return self._Chat(self._payload, self.requests)


@pytest.mark.integration
class TestDataFabricService:
    @pytest.mark.asyncio
    async def test_ingest_persists_symbols_files_and_edges(
        self, memory_service: MemoryService
    ):
        container = await memory_service.get_service_container()
        svc = await container.get_data_fabric_service()

        ingestor = _FakeIngestor(
            symbols=[
                {
                    "id": "a.py:foo",
                    "name": "foo",
                    "kind": "function_definition",
                    "signature": "def foo()",
                    "file_id": "a.py",
                }
            ],
            files=[
                {
                    "id": "a.py", "name": "a.py", "path": "a.py",
                    "language": "python", "hash": "h",
                }
            ],
        )
        vs = _FakeVectorStore()

        result = await svc.ingest_project(
            "/ignored", REPO, BRANCH, ingestor=ingestor, vector_store=vs
        )
        assert result["files_upserted"] == 1
        assert result["symbols_upserted"] == 1
        assert result["edges_created"] == 1
        assert result["symbols_indexed"] == 1
        assert vs.calls == [(REPO, BRANCH, 1)]

        entity = await memory_service.entity
        assert (await entity.get_symbol(REPO, "a.py:foo", BRANCH)) is not None
        assert (await entity.get_file(REPO, "a.py", BRANCH)) is not None

        # DEFINED_IN edge exists
        kuzu = await memory_service.get_kuzu_client()
        rows = kuzu.fetch_all(
            "MATCH (s:Symbol)-[:DEFINED_IN]->(f:File) "
            "WHERE s.repository = $r RETURN count(*) AS n",
            {"r": REPO},
        )
        assert rows[0]["n"] == 1

    @pytest.mark.asyncio
    async def test_semantic_search_uses_vector_store(
        self, memory_service: MemoryService
    ):
        container = await memory_service.get_service_container()
        svc = await container.get_data_fabric_service()
        resp = await svc.semantic_search(
            REPO, BRANCH, "foo", vector_store=_FakeVectorStore()
        )
        assert resp["available"] is True
        assert resp["results"][0]["symbol_id"] == "a.py:foo"


@pytest.mark.integration
class TestRealIngestion:
    @pytest.mark.asyncio
    async def test_real_tree_sitter_ingest(
        self, memory_service: MemoryService, tmp_path
    ):
        # Skip if no tree-sitter parser pack is installed in this environment.
        pytest.importorskip("tree_sitter_language_pack")

        (tmp_path / "m.py").write_text(
            "def hello():\n    return 1\n\n"
            "class Foo:\n    def bar(self):\n        pass\n"
        )

        container = await memory_service.get_service_container()
        svc = await container.get_data_fabric_service()
        # Real ingestor (default); fake vector store to avoid the heavy ML stack.
        result = await svc.ingest_project(
            str(tmp_path), REPO, BRANCH, vector_store=_FakeVectorStore()
        )
        assert result["files_upserted"] == 1
        assert result["symbols_upserted"] >= 2  # hello, bar (+ maybe Foo)

        entity = await memory_service.entity
        assert (await entity.get_symbol(REPO, "m.py:hello", BRANCH)) is not None
        assert (await entity.get_file(REPO, "m.py", BRANCH)) is not None


@pytest.mark.integration
class TestDreamService:
    @pytest.mark.asyncio
    async def test_skips_when_no_episodic_memory(self, memory_service: MemoryService):
        container = await memory_service.get_service_container()
        dream = await container.get_dream_service()
        result = await dream.trigger_dream(REPO, BRANCH)
        assert result["status"] == "skipped"
        assert result["reason"] == "no_episodic_memory"

    @pytest.mark.asyncio
    async def test_skips_when_llm_not_configured(self, memory_service: MemoryService):
        ctx = await memory_service.context
        await ctx.update_context(
            REPO,
            ContextInput(id="c1", name="c1", iso_date="2024-01-15", summary="did x"),
        )
        container = await memory_service.get_service_container()
        dream = await container.get_dream_service()
        # No API key configured in this environment -> graceful skip.
        result = await dream.trigger_dream(REPO, BRANCH)
        assert result["status"] == "skipped"
        assert result["reason"] == "llm_not_configured"

    @pytest.mark.asyncio
    async def test_distills_decisions_and_justifies(
        self, memory_service: MemoryService, monkeypatch
    ):
        # A distillation call has to name a model, and this project ships no
        # default to name -- so the test configures one the way an operator
        # would, rather than relying on one compiled into the package. The
        # provider is set to match the fake client below, so the model sent is
        # the one configured for the provider being spoken to.
        monkeypatch.setattr(fabric_config.settings, "llm_provider", "anthropic")
        monkeypatch.setattr(
            fabric_config.settings, "anthropic_model", "an-example-model"
        )

        entity = await memory_service.entity
        await entity.create_symbol(REPO, SymbolInput(id="a.py:foo", name="foo"))
        ctx = await memory_service.context
        await ctx.update_context(
            REPO,
            ContextInput(
                id="c1", name="c1", iso_date="2024-01-15",
                summary="added foo", observation="foo does x",
            ),
        )

        payload = json.dumps({
            "decisions": [
                {
                    "id": "dec-1",
                    "name": "Introduce foo",
                    "rationale": "needed x",
                    "affected_symbols": ["a.py:foo"],
                }
            ]
        })
        fake_llm = _FakeAnthropicClient(payload)

        container = await memory_service.get_service_container()
        dream = await container.get_dream_service()
        result = await dream.trigger_dream(REPO, BRANCH, llm_client=fake_llm)

        assert result["status"] == "success"
        assert result["distilled_decisions"] == 1
        assert (await entity.get_decision(REPO, "dec-1", BRANCH)) is not None
        # The configured model, not a model named anywhere in the package.
        assert fake_llm.requests[0]["model"] == "an-example-model"

        kuzu = await memory_service.get_kuzu_client()
        rows = kuzu.fetch_all(
            "MATCH (d:Decision)-[:JUSTIFIES]->(s:Symbol) "
            "WHERE d.repository = $r RETURN count(*) AS n",
            {"r": REPO},
        )
        assert rows[0]["n"] == 1

    @pytest.mark.asyncio
    async def test_the_openai_request_carries_no_temperature(
        self, memory_service: MemoryService, monkeypatch
    ):
        """The OpenAI branch sends exactly the model and the messages.

        It used to send `temperature=0.2` on every call, and a reasoning model
        rejects any temperature but its own with "unsupported value" -- so
        distillation raised for everyone who had configured one. Asserting on
        the whole request rather than on the one absent key is deliberate: a
        parameter nobody chose is the defect, whichever its name.
        """
        monkeypatch.setattr(fabric_config.settings, "llm_provider", "openai")
        monkeypatch.setattr(
            fabric_config.settings, "openai_model", "an-example-model"
        )

        ctx = await memory_service.context
        await ctx.update_context(
            REPO,
            ContextInput(
                id="c1", name="c1", iso_date="2024-01-15",
                summary="added foo", observation="foo does x",
            ),
        )

        fake_llm = _FakeOpenAIClient(json.dumps({"decisions": []}))

        container = await memory_service.get_service_container()
        dream = await container.get_dream_service()
        result = await dream.trigger_dream(REPO, BRANCH, llm_client=fake_llm)

        assert result["status"] == "success"
        assert len(fake_llm.requests) == 1
        sent = fake_llm.requests[0]
        assert set(sent) == {"model", "messages"}
        assert sent["model"] == "an-example-model"
