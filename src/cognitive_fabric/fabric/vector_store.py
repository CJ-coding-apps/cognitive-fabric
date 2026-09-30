"""Vector store for the Cognitive Fabric semantic layer.

Backed by LanceDB (mutable tables, so it sidesteps KuzuDB's immutable vector
index limitation). Embeddings are produced by OpenAI when OPENAI_API_KEY is set,
otherwise by a local sentence-transformers model (no API key required).

Symbols from every repository/branch live in a single `symbols` table with
`repository`/`branch` columns; queries pre-filter on those, keeping projects
isolated within one store. lancedb / sentence-transformers are imported lazily.
"""

import os
from typing import Any, Callable, Optional


def _escape(value: str) -> str:
    """Escape a value for a LanceDB SQL-style filter string."""
    return str(value).replace("'", "''")


class VectorStore:
    TABLE = "symbols"

    def __init__(
        self,
        data_dir: Optional[str] = None,
        embedder: Optional[Callable[[list[str]], list[list[float]]]] = None,
    ) -> None:
        import lancedb  # lazy: optional dependency

        self._data_dir = data_dir or os.environ.get("FABRIC_DATA_DIR", "./.fabric_data")
        db_path = os.path.join(self._data_dir, "lancedb")
        os.makedirs(db_path, exist_ok=True)
        self._db = lancedb.connect(db_path)

        # Optional injected embedder (used for testing / custom backends).
        self._embedder = embedder
        self._openai = None
        self._fastembed = None
        self._st_model = None

        if embedder is None:
            # Resolve an embedding backend eagerly so misconfiguration fails fast.
            # Preference: OpenAI (if key set) -> fastembed (local, pure ONNX, no
            # torch) -> sentence-transformers (optional, requires torch).
            if os.environ.get("OPENAI_API_KEY"):
                try:
                    from openai import OpenAI

                    self._openai = OpenAI()
                    self._embed_model = os.environ.get(
                        "FABRIC_EMBED_MODEL", "text-embedding-3-small"
                    )
                except Exception:
                    self._openai = None
            if self._openai is None:
                try:
                    from fastembed import TextEmbedding

                    self._embed_model = os.environ.get(
                        "FABRIC_EMBED_MODEL", "BAAI/bge-small-en-v1.5"
                    )
                    self._fastembed = TextEmbedding(self._embed_model)
                except Exception:
                    from sentence_transformers import SentenceTransformer

                    self._embed_model = os.environ.get(
                        "FABRIC_EMBED_MODEL", "all-MiniLM-L6-v2"
                    )
                    self._st_model = SentenceTransformer(self._embed_model)

    @property
    def backend(self) -> str:
        if self._embedder is not None:
            return "custom"
        if self._openai is not None:
            return "openai"
        if self._fastembed is not None:
            return "fastembed"
        return "sentence-transformers"

    def _embed(self, texts: list[str]) -> list[list[float]]:
        if not texts:
            return []
        if self._embedder is not None:
            return self._embedder(texts)
        if self._openai is not None:
            resp = self._openai.embeddings.create(model=self._embed_model, input=texts)
            return [d.embedding for d in resp.data]
        if self._fastembed is not None:
            # fastembed.embed yields numpy arrays; convert to plain float lists.
            return [[float(x) for x in vec] for vec in self._fastembed.embed(texts)]
        # sentence-transformers; normalize for cosine similarity.
        return self._st_model.encode(texts, normalize_embeddings=True).tolist()

    def upsert(
        self, repository: str, branch: str, symbols: list[dict[str, Any]]
    ) -> int:
        """Replace the vector rows for (repository, branch) with the given symbols.

        Each symbol dict has: id, name, kind, signature, file_id.
        Returns the number of rows upserted.
        """
        rows = []
        texts = []
        for s in symbols:
            text = " ".join(
                str(s.get(k) or "") for k in ("name", "kind", "signature")
            ).strip()
            if not text:
                text = str(s.get("id") or "")
            texts.append(text)
        vectors = self._embed(texts)
        for s, vec in zip(symbols, vectors):
            rows.append(
                {
                    "symbol_id": str(s.get("id")),
                    "repository": repository,
                    "branch": branch,
                    "name": str(s.get("name") or s.get("id")),
                    "file_id": str(s.get("file_id") or ""),
                    "vector": vec,
                }
            )

        if self.TABLE in self._db.table_names():
            tbl = self._db.open_table(self.TABLE)
            tbl.delete(
                f"repository = '{_escape(repository)}' AND branch = '{_escape(branch)}'"
            )
            if rows:
                tbl.add(rows)
        elif rows:
            self._db.create_table(self.TABLE, data=rows)

        return len(rows)

    def search(
        self,
        repository: str,
        branch: str,
        query: str,
        limit: int = 10,
        threshold: float = 0.0,
    ) -> list[dict[str, Any]]:
        """Cosine-similarity search over the symbols for (repository, branch).

        Returns a list of {symbol_id, name, file_id, score} sorted by score desc.
        """
        if self.TABLE not in self._db.table_names():
            return []
        query_vec = self._embed([query])
        if not query_vec:
            return []
        tbl = self._db.open_table(self.TABLE)
        where = f"repository = '{_escape(repository)}' AND branch = '{_escape(branch)}'"
        hits = (
            tbl.search(query_vec[0])
            .metric("cosine")
            .where(where, prefilter=True)
            .limit(limit)
            .to_list()
        )
        results = []
        for h in hits:
            # cosine distance in [0, 2]; convert to a similarity score.
            score = 1.0 - float(h.get("_distance", 1.0))
            if score < threshold:
                continue
            results.append(
                {
                    "symbol_id": h.get("symbol_id"),
                    "name": h.get("name"),
                    "file_id": h.get("file_id"),
                    "score": score,
                }
            )
        results.sort(key=lambda r: r["score"], reverse=True)
        return results
