# Cognitive-Fabric

A unified **Python** MCP server for a graph "memory bank" on **KuzuDB**, extended
with a **Cognitive Fabric** layer: in-process symbolic (AST) ingestion, a
semantic (vector) search layer, and a "dream"/evolution engine that distills
episodic memory into the semantic graph.

This is the single-runtime successor to the split TypeScript-core + Python-sidecar
design: there is **no Arrow Flight sidecar and no network data-plane port** — the
tree-sitter, embedding, and LLM work all run in-process.

> **Provenance:** derived from and extends the Apache-2.0 project
> [KuzuMem-MCP](https://github.com/Jakedismo/KuzuMem-MCP) (via its Python port).
> See `NOTICE`. Licensed under Apache-2.0 (`LICENSE`).

## Features

- **Graph memory bank** on KuzuDB — components, decisions, rules, context, files,
  tags, metadata; repository + branch isolation via `repo:branch:id` keys.
- **13 MCP tools**: `memory-bank`, `entity`, `context`, `query`, `associate`,
  `analyze`, `detect`, `introspect`, `bulk-import`, `search`, `delete`,
  `memory-optimizer`, and **`fabric`**.
- **Cognitive Fabric**:
  - **Symbolic ingestion** — tree-sitter parses a project into `Symbol`/`File`
    nodes + `DEFINED_IN` edges (in-process).
  - **Semantic search** — LanceDB vector store over ingested symbols (optional
    `[semantic]` extra); degrades gracefully when not installed.
  - **Dream engine** — distills recent `Context` into `Decision` nodes +
    `JUSTIFIES` edges via an LLM (skips cleanly when no API key is set).
  - **Provenance graph** — `EVOLVED_FROM`, `JUSTIFIES`, `DEFINED_IN`,
    `REALISED_BY`, `RECORDS`, `CONTRAVENES` relationships.
- **AI memory optimizer** with snapshots + rollback; graph algorithms
  (PageRank, Louvain, k-core, shortest path); stdio MCP transport.

## Installation

Requires Python 3.11+.

```bash
git clone <your-repo-url> cognitive-fabric && cd cognitive-fabric
python -m venv .venv && source .venv/bin/activate

# Base install (memory bank + fabric ingestion via tree-sitter)
pip install -e .

# Semantic search: LanceDB + fastembed local embeddings (pure ONNX, no torch —
# works everywhere, incl. Python 3.13)
pip install -e '.[semantic]'

# Or just the vector store (LanceDB) to use OpenAI embeddings (OPENAI_API_KEY)
pip install -e '.[vectordb]'

# Dev tools
pip install -e '.[dev]'
```

## Quick start (CLI)

```bash
# Create a database
cognitive-fabric init ./data/mem.db

# Ingest a project's symbols/files into the graph (Cognitive Fabric)
cognitive-fabric fabric-ingest ./data/mem.db my-app --path /path/to/project

# Inspect
cognitive-fabric info ./data/mem.db
cognitive-fabric query ./data/mem.db "MATCH (s:Symbol) RETURN s.id LIMIT 10"
```

## Running as an MCP server

```bash
cognitive-fabric serve --db-path ./data/mem.db   # stdio transport
```

Register in your MCP client (e.g. Claude Code):

```json
{
  "mcpServers": {
    "cognitive-fabric": {
      "command": "cognitive-fabric",
      "args": ["serve", "--db-path", "/absolute/path/to/mem.db"]
    }
  }
}
```

## MCP tools

| Tool | Description |
|------|-------------|
| `memory-bank` | Initialize and manage memory banks |
| `entity` | CRUD for all entity types |
| `context` | Session/episodic context |
| `query` | Structured graph queries |
| `associate` | Create relationships between entities |
| `analyze` | Graph algorithms (PageRank, Louvain, k-core, shortest path) |
| `detect` | Pattern/anomaly detection (cycles, islands) |
| `introspect` | Schema inspection |
| `bulk-import` | Batch entity operations |
| `search` | `fulltext` / `by-name` / `by-kind` / `semantic` / `hybrid` |
| `delete` | Safe deletion operations |
| `memory-optimizer` | AI-powered memory optimization + snapshots/rollback |
| `fabric` | Cognitive Fabric operations (see below) |

### The `fabric` tool

| Operation | Purpose |
|-----------|---------|
| `ingest-ast` | Scan a project (`path`) → persist `Symbol`/`File` nodes + `DEFINED_IN` edges (+ index in the vector store) |
| `query-evolution` | Trace an entity's `EVOLVED_FROM` lineage (`itemId`, `itemType`) |
| `query-rationale` | Find the `Decision`s that `JUSTIFIES` an entity (`itemId`) |
| `record-event` | Record an episodic `Context` event for later distillation |
| `dream` | Distill recent context into `Decision`s + `JUSTIFIES` edges (needs an LLM key) |
| `link-evolution` / `link-to-file` / `link-to-symbol` | Create provenance/lineage edges |

## Entity types

Repository, Component, Decision, Rule, Context, File, Tag, Metadata, and the
Cognitive Fabric nodes **Symbol**, **Requirement**, **Trace**.

## Configuration

Settings load from environment (prefix `COGNITIVE_FABRIC_`) or a `.env` file
(see `.env.example`). Key vars:

- `COGNITIVE_FABRIC_LLM_PROVIDER` (`openai` | `anthropic`) + `OPENAI_API_KEY` /
  `ANTHROPIC_API_KEY` — enables the dream engine.
- `COGNITIVE_FABRIC_FABRIC_DATA_DIR` — where the LanceDB vector store lives.
- `COGNITIVE_FABRIC_FABRIC_EMBEDDING_PROVIDER` (`sentence-transformers` |
  `openai`).

## Development

```bash
pip install -e '.[dev]'
pytest                 # unit + integration (real kuzu)
pytest -m integration  # integration only
ruff check src tests
mypy src
```

Tests that need the optional semantic stack (`[semantic]`) or a tree-sitter
parser pack are skipped automatically when those are not installed.

## Architecture

```
MCP client (stdio)
      │
   MCP server ── tool handlers ── domain services ── repositories ── KuzuDB
                     │                    │
                     │              DataFabricService ── SymbolicIngestor (tree-sitter)
                     │              DreamService       ── LanceDB VectorStore (semantic)
                     └── fabric / search / entity / ...   LLM (openai|anthropic)
```

Everything runs in one Python process over stdio; the fabric ML runs in-process
(no sidecar, no network data plane). See
[docs/architecture.md](docs/architecture.md) and [docs/fabric.md](docs/fabric.md).

## Project structure

```
src/cognitive_fabric/
├── agents/         # AI memory optimizer
├── cli/            # Click CLI
├── db/             # KuzuDB client + schema
├── fabric/         # In-process ingestor (tree-sitter) + vector store (LanceDB)
├── mcp/            # MCP server, tools, handlers
├── repositories/   # Data access layer
├── services/       # Domain services (incl. data_fabric, dream)
├── types/          # Pydantic models
└── utils/          # Utilities
```

## License

Apache-2.0 — see `LICENSE` and `NOTICE`.
