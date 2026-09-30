"""Integration tests for the real LanceDB VectorStore.

Uses a deterministic stub embedder (injected) so the actual LanceDB code path —
table create, delete-by-filter, cosine search, repo/branch isolation — is
exercised without the heavy embedding stack (torch is unavailable in this env).
Skipped when lancedb is not installed.
"""

import hashlib

import pytest

pytest.importorskip("lancedb")

from cognitive_fabric.fabric.vector_store import VectorStore  # noqa: E402


def _stub_embedder(texts: list[str]) -> list[list[float]]:
    """Deterministic 8-dim embedding derived from a hash of each text."""
    vecs = []
    for t in texts:
        digest = hashlib.sha256(t.encode()).digest()
        vecs.append([b / 255.0 for b in digest[:8]])
    return vecs


SYMBOLS = [
    {"id": "a.py:login", "name": "login", "kind": "function",
     "signature": "def login()", "file_id": "a.py"},
    {"id": "a.py:logout", "name": "logout", "kind": "function",
     "signature": "def logout()", "file_id": "a.py"},
]


@pytest.mark.integration
def test_vector_store_upsert_search_and_isolation(tmp_path):
    vs = VectorStore(data_dir=str(tmp_path), embedder=_stub_embedder)
    assert vs.backend == "custom"

    n = vs.upsert("repo", "main", SYMBOLS)
    assert n == 2

    # Search returns rows for the right repo/branch (threshold low to accept all).
    results = vs.search("repo", "main", "login", limit=5, threshold=-1.0)
    assert results
    assert {r["symbol_id"] for r in results} <= {"a.py:login", "a.py:logout"}
    assert all("score" in r for r in results)

    # Repo/branch isolation: a different repo has no rows.
    assert vs.search("other", "main", "login", threshold=-1.0) == []


@pytest.mark.integration
def test_vector_store_upsert_replaces_repo_branch(tmp_path):
    vs = VectorStore(data_dir=str(tmp_path), embedder=_stub_embedder)
    vs.upsert("repo", "main", SYMBOLS)
    # Re-upsert with a single symbol replaces the previous rows for repo/main.
    vs.upsert("repo", "main", [SYMBOLS[0]])
    results = vs.search("repo", "main", "x", limit=10, threshold=-1.0)
    assert {r["symbol_id"] for r in results} == {"a.py:login"}


@pytest.mark.integration
def test_vector_store_real_fastembed_embeddings(tmp_path, monkeypatch):
    """Full local semantic path: real fastembed (ONNX) embeddings + real LanceDB."""
    pytest.importorskip("fastembed")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)

    vs = VectorStore(data_dir=str(tmp_path))  # no injected embedder -> fastembed
    assert vs.backend == "fastembed"

    vs.upsert("repo", "main", SYMBOLS)  # login, logout
    results = vs.search(
        "repo", "main", "user authentication sign in", limit=5, threshold=0.0
    )
    assert results
    assert {r["symbol_id"] for r in results} <= {"a.py:login", "a.py:logout"}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_data_fabric_semantic_search_real_store(memory_service, tmp_path):
    """End-to-end semantic search through DataFabricService + real LanceDB."""
    container = await memory_service.get_service_container()
    svc = await container.get_data_fabric_service()
    vs = VectorStore(data_dir=str(tmp_path), embedder=_stub_embedder)
    vs.upsert("repo", "main", SYMBOLS)

    resp = await svc.semantic_search(
        "repo", "main", "login", limit=5, threshold=-1.0, vector_store=vs
    )
    assert resp["available"] is True
    assert resp["results"]
