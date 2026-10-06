"""Vector store for the Cognitive Fabric semantic layer.

Backed by LanceDB (mutable tables, so it sidesteps KuzuDB's immutable vector
index limitation).

The embedding backend is the one named in configuration
(`fabric_embedding_provider`), not whichever library happens to find a key in
the environment. It used to be the latter -- OpenAI if `OPENAI_API_KEY` was set,
otherwise a local model -- which meant exporting a key silently moved every new
vector into a different embedding space, at a different price, with the same
table on the other side. A cloud backend also requires a model to be named: an
embedding model fixes a price and a vector width, and vectors from two models
are not comparable, so there is no default to fall back to. The local backends
keep their own.

Symbols from every repository/branch live in a single `symbols` table with
`repository`/`branch` columns; queries pre-filter on those, keeping projects
isolated within one store. lancedb and the embedding backends are imported
lazily.
"""

import os
from typing import Any, Callable, Optional

from cognitive_fabric.config import Settings
from cognitive_fabric.config import settings as default_settings

# The local backends' own default models, named here rather than left to the
# library so that a backend upgrade cannot silently change the vectors this
# store has already written. Both are local: no vendor, no price, no key.
_FASTEMBED_DEFAULT_MODEL = "BAAI/bge-small-en-v1.5"
_SENTENCE_TRANSFORMERS_DEFAULT_MODEL = "all-MiniLM-L6-v2"


def _escape(value: str) -> str:
    """Escape a value for a LanceDB SQL-style filter string."""
    return str(value).replace("'", "''")


class VectorStore:
    TABLE = "symbols"

    def __init__(
        self,
        data_dir: Optional[str] = None,
        embedder: Optional[Callable[[list[str]], list[list[float]]]] = None,
        settings: Optional[Settings] = None,
    ) -> None:
        """Initialize the vector store.

        Args:
            data_dir: Where the LanceDB database lives. Defaults to the
                configured `fabric_data_dir`.
            embedder: Optional injected embedder, for testing or a custom
                backend. When given, no backend is resolved at all.
            settings: Settings to read. Defaults to the process-wide settings.

        Raises:
            ValueError: if the configured cloud backend has no model named, or
                a configured backend's library is not installed.
        """
        import lancedb  # lazy: optional dependency

        settings = settings or default_settings
        self._data_dir = data_dir or settings.fabric_data_dir or "./.fabric_data"
        db_path = os.path.join(self._data_dir, "lancedb")
        os.makedirs(db_path, exist_ok=True)
        self._db = lancedb.connect(db_path)

        # Optional injected embedder (used for testing / custom backends).
        self._embedder = embedder
        self._openai = None
        self._fastembed = None
        self._st_model = None
        self._backend = (
            "custom" if embedder is not None else settings.fabric_embedding_provider
        )
        self._embed_model = ""

        if embedder is None:
            self._resolve_backend(settings)

    def _resolve_backend(self, settings: Settings) -> None:
        """Build the one backend that configuration names.

        Resolved in `__init__` rather than on first use, so that a
        misconfiguration fails where the store is created. An unimportable
        backend is an error, not a reason to quietly switch to another one: the
        rows already in the table were written by a particular model, and
        answering a query with a different one returns plausible nonsense.
        """
        provider = settings.fabric_embedding_provider
        model = settings.fabric_embedding_model

        if provider == "openai":
            if not model:
                raise ValueError(
                    "the openai embedding backend has no default model. An "
                    "embedding model fixes both the price per million tokens "
                    "and the width of every vector already in the table, and "
                    "vectors from two models are not comparable, so this must "
                    "be a choice rather than a fallback. Set "
                    "COGNITIVE_FABRIC_FABRIC_EMBEDDING_MODEL to a model id from "
                    "https://platform.openai.com/docs/guides/embeddings."
                )
            try:
                from openai import OpenAI
            except Exception as e:
                raise ValueError(
                    f"the openai embedding backend is not installed: {e}"
                ) from e
            self._openai = OpenAI()
            self._embed_model = model
            return

        if provider == "fastembed":
            self._embed_model = model or _FASTEMBED_DEFAULT_MODEL
            try:
                from fastembed import TextEmbedding
            except Exception as e:
                raise ValueError(
                    f"the fastembed embedding backend is not installed: {e}"
                ) from e
            self._fastembed = TextEmbedding(self._embed_model)
            return

        self._embed_model = model or _SENTENCE_TRANSFORMERS_DEFAULT_MODEL
        try:
            from sentence_transformers import SentenceTransformer
        except Exception as e:
            raise ValueError(
                f"the sentence-transformers embedding backend is not installed: {e}"
            ) from e
        self._st_model = SentenceTransformer(self._embed_model)

    @property
    def backend(self) -> str:
        return self._backend

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
