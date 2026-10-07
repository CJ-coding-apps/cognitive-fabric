# The Cognitive Fabric

The Cognitive Fabric is the layer built on top of the base KuzuDB memory bank. It
adds symbolic (AST) ingestion, a semantic (vector) search layer, and a
distillation ("dream") engine. Everything runs **in-process** — there is no Arrow
Flight sidecar and no network data-plane port (the design that superseded the
split TS-core + Python-sidecar architecture).

## Graph substrate

Node tables added: `Symbol`, `Requirement`, `Trace`.

Relationship tables added:

| Relationship | From → To | Meaning |
|--------------|-----------|---------|
| `DEFINED_IN` | Symbol → File | where a symbol is defined |
| `EVOLVED_FROM` | Symbol/Decision/Requirement → same | version lineage |
| `JUSTIFIES` | Decision → Symbol/Rule | why something exists |
| `REALISED_BY` | Requirement → Symbol/Component | intent → implementation |
| `RECORDS` | Trace → Symbol | runtime observation → code |
| `CONTRAVENES` | Decision → Rule | intentional deviation |

`DEPENDS_ON` and `PART_OF` were extended to also cover `Symbol`. All nodes use the
`repo:branch:id` graph-unique key for isolation (File is keyed by `id` +
repository/branch).

## Components

- **`SymbolicIngestor`** (`fabric/ingestor.py`) — tree-sitter parsing of
  `.py/.ts/.tsx/.js` into symbol + file dicts. Uses `tree-sitter-language-pack`
  (Python 3.13-compatible), falling back to `tree-sitter-languages`. Imported
  lazily; the rest of the package works without it.
- **`VectorStore`** (`fabric/vector_store.py`) — a LanceDB table of symbol
  embeddings. Embedding backend preference: OpenAI (if `OPENAI_API_KEY` is set) →
  **fastembed** (local, pure-ONNX, **no torch** — the default) →
  sentence-transformers (optional, `[semantic-st]`; no CI job installs it, so it
  is the one backend without a test behind it). A custom embedder can also be
  injected.
  LanceDB is used instead of KuzuDB's (immutable) vector index. Install with
  `pip install -e '.[semantic]'`.
- **`DataFabricService`** (`services/domain/data_fabric.py`) —
  `ingest_project(path, repo, branch)`: scan → upsert `File`/`Symbol` nodes +
  `DEFINED_IN` edges → best-effort vector index. `semantic_search(...)` queries
  the vector store and degrades gracefully when it is unavailable.
- **`DreamService`** (`services/domain/dream.py`) — gathers recent `Context`,
  asks an LLM (duck-typed OpenAI/Anthropic) to extract architectural decisions,
  and writes `Decision` nodes + `JUSTIFIES` edges. Returns `status: "skipped"`
  when no LLM provider is configured.

## Using it

Via the `fabric` MCP tool or the CLI:

```bash
cognitive-fabric fabric-ingest ./data/mem.db my-app --path /path/to/project
```

```json
{ "tool": "fabric", "arguments": { "operation": "ingest-ast", "repository": "my-app", "path": "/path/to/project" } }
{ "tool": "fabric", "arguments": { "operation": "query-rationale", "repository": "my-app", "itemId": "src/auth.py:login" } }
{ "tool": "fabric", "arguments": { "operation": "dream", "repository": "my-app" } }
{ "tool": "search", "arguments": { "searchType": "semantic", "repository": "my-app", "query": "authentication" } }
```

## Security

`ingest-ast` scans the `path` it is given; callers should pass a trusted project
root. No arbitrary network endpoint is exposed — all fabric work is in-process.

## Follow-on (not yet implemented)

Dream lifecycle hardening (log pruning, verification pass, idle/commit
auto-triggers), PII scrubbing before distillation, embeddings for all entity
types, and an optional HTTP transport + web graph explorer.
