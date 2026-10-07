# Architecture Overview

This document describes the architecture of Cognitive-Fabric, a Python MCP server for graph-based memory management.

## System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Client                                │
│                    (Claude Code, etc.)                          │
└─────────────────────────────────────────────────────────────────┘
                              │
                              │ stdio (JSON-RPC)
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                        MCP Server                                │
│  ┌───────────────┐  ┌──────────────┐  ┌───────────────────────┐ │
│  │ Tool Registry │  │ Tool Context │  │ 13 Tool Handlers      │ │
│  └───────────────┘  └──────────────┘  └───────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Services Layer                              │
│  ┌─────────────┐  ┌────────────┐  ┌────────────┐  ┌──────────┐ │
│  │MemoryService│  │EntityService│ │GraphAnalysis│ │ContextSvc│ │
│  └─────────────┘  └────────────┘  └────────────┘  └──────────┘ │
│  ┌─────────────────────────────────────────────────────────────┐ │
│  │                   Service Container (DI)                     │ │
│  └─────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                    Repository Layer                              │
│  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌────────┐ ┌───────────┐ │
│  │Component │ │ Decision │ │  Rule  │ │Context │ │Tag/File/..│ │
│  │   Repo   │ │   Repo   │ │  Repo  │ │  Repo  │ │   Repos   │ │
│  └──────────┘ └──────────┘ └────────┘ └────────┘ └───────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Database Layer                              │
│  ┌─────────────┐  ┌───────────────┐  ┌────────────────────────┐ │
│  │ KuzuDBClient│  │ QueryExecutor │  │    SchemaManager       │ │
│  └─────────────┘  └───────────────┘  └────────────────────────┘ │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                         KuzuDB                                   │
│                  (Embedded Graph Database)                       │
└─────────────────────────────────────────────────────────────────┘
```

## Layer Descriptions

### MCP Server Layer (`src/cognitive_fabric/mcp/`)

The MCP server layer handles protocol communication with MCP clients.

| Component | File | Purpose |
|-----------|------|---------|
| Server | `server.py` | Stdio server using official MCP SDK |
| Tool Registry | `tool_registry.py` | Registers and dispatches tool calls |
| Tool Context | `tool_context.py` | Session state for tool handlers |
| Tool Definitions | `tools/definitions.py` | Schema definitions for all 13 tools |
| Handlers | `handlers/*.py` | Implementation for each tool |

**Key Patterns:**
- Uses the official `mcp` Python SDK
- Stdio transport for Claude Code integration
- Async handlers for all operations

### Services Layer (`src/cognitive_fabric/services/`)

Business logic and orchestration layer.

| Service | File | Purpose |
|---------|------|---------|
| MemoryService | `memory_service.py` | Main singleton, coordinates all services |
| ServiceContainer | `service_container.py` | Lazy-loading dependency injection |
| MemoryBankService | `domain/memory_bank.py` | Memory bank lifecycle |
| EntityService | `domain/entity.py` | CRUD for all entity types |
| ContextService | `domain/context.py` | Session context management |
| GraphQueryService | `domain/graph_query.py` | Structured queries |
| GraphAnalysisService | `domain/graph_analysis.py` | Graph algorithms |
| SnapshotService | `snapshot_service.py` | Backup and restore |

**Key Patterns:**
- Singleton pattern for MemoryService
- Lazy loading via ServiceContainer
- Protocol-based interfaces for testability

### Repository Layer (`src/cognitive_fabric/repositories/`)

Data access layer implementing the repository pattern.

| Repository | File | Purpose |
|------------|------|---------|
| ComponentRepository | `component_repo.py` | Component CRUD + graph operations |
| DecisionRepository | `decision_repo.py` | Decision management |
| RuleRepository | `rule_repo.py` | Rule management |
| ContextRepository | `context_repo.py` | Context entries |
| FileRepository | `file_repo.py` | File references |
| TagRepository | `tag_repo.py` | Tags and tagging |
| MetadataRepository | `metadata_repo.py` | Project metadata |
| RepositoryRepository | `repository_repo.py` | Repository table |

**Component Repository Structure:**
```
repositories/component/
├── crud.py        # Create, read, update, delete
├── graph.py       # Traversals, dependencies
└── algorithms.py  # PageRank, Louvain, k-core
```

### Database Layer (`src/cognitive_fabric/db/`)

Low-level database operations.

| Component | File | Purpose |
|-----------|------|---------|
| KuzuDBClient | `kuzu_client.py` | Main orchestrator |
| ConnectionManager | `connection_manager.py` | Connection lifecycle |
| QueryExecutor | `query_executor.py` | Query execution with logging |
| SchemaManager | `schema_manager.py` | DDL operations |
| RepositoryFactory | `repository_factory.py` | Repository singletons |

## Data Model

### Node Tables (Entities)

```
┌────────────┐     ┌────────────┐     ┌──────────┐
│ Repository │     │ Component  │     │ Decision │
├────────────┤     ├────────────┤     ├──────────┤
│ id (PK)    │     │ graph_id   │     │ graph_id │
│ name       │     │ id         │     │ id       │
│ branch     │     │ name       │     │ name     │
│ created_at │     │ kind       │     │ context  │
│ updated_at │     │ status     │     │ date     │
└────────────┘     │ depends_on │     │ status   │
                   │ repository │     │ repo     │
                   │ branch     │     │ branch   │
                   └────────────┘     └──────────┘

┌──────────┐     ┌──────────┐     ┌──────────┐
│   Rule   │     │ Context  │     │   File   │
├──────────┤     ├──────────┤     ├──────────┤
│ graph_id │     │ graph_id │     │ id (PK)  │
│ id       │     │ id       │     │ name     │
│ name     │     │ name     │     │ path     │
│ content  │     │ iso_date │     │ size     │
│ triggers │     │ agent    │     │ mime_type│
│ status   │     │ summary  │     │ metadata │
└──────────┘     │ observ.  │     └──────────┘
                 └──────────┘

┌──────────┐     ┌──────────┐
│   Tag    │     │ Metadata │
├──────────┤     ├──────────┤
│ id (PK)  │     │ graph_id │
│ name     │     │ id       │
│ color    │     │ name     │
│ desc     │     │ content  │
│ category │     └──────────┘
└──────────┘
```

### Relationship Tables

| Relationship | From | To | Purpose |
|--------------|------|-----|---------|
| DEPENDS_ON | Component | Component | Dependency graph |
| IMPLEMENTS | Component | File | Code implementation |
| TAGGED_WITH | Component | Tag | Categorization |
| GOVERNS | Rule | Component | Governance rules |
| AFFECTS | Decision | Component | Decision impact |
| CONTEXT_OF | Context | Component | Session context |
| PART_OF | Component | Repository | Repository membership |
| HAS_METADATA | Repository | Metadata | Project metadata |

### Graph Unique ID Pattern

All entities use a composite key pattern for isolation:

```
graph_unique_id = "{repository}:{branch}:{entity_id}"
```

Example: `my-app:main:auth-service`

This enables:
- Multi-repository support in single database
- Branch-based isolation
- Safe cross-repository queries

## Memory Optimizer Agent

```
┌─────────────────────────────────────────────────────────────────┐
│                  MemoryOptimizationAgent                         │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐  │
│  │   Analyze   │→ │    Plan     │→ │       Execute           │  │
│  └─────────────┘  └─────────────┘  └─────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
         │                  │                    │
         ▼                  ▼                    ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────────────┐
│AnalysisService  │ │ PlanningService │ │   ExecutionService      │
│ - Detect issues │ │ - Rule-based    │ │ - Execute actions       │
│ - Health score  │ │ - LLM-enhanced  │ │ - Create snapshots      │
│ - Patterns      │ │ - Strategies    │ │ - Rollback support      │
└─────────────────┘ └─────────────────┘ └─────────────────────────┘
```

**Strategies:** the table is generated from `STRATEGY_CONFIGS` and embedded in
`docs/guides/configuration.md` and `docs/guides/memory-optimizer.md`, so the
numbers have one home. A restatement here was wrong three times over: it gave
every strategy a deletion limit lower than the code's.

## Design Patterns

### Singleton Pattern
Used for services that should have a single instance:
- `MemoryService` - Main service coordinator
- `RepositoryFactory` - Repository instance cache

### Repository Pattern
Data access abstracted through repositories:
- Each entity type has a dedicated repository
- Repositories handle Cypher query generation
- Mixin pattern for code organization

### Dependency Injection
Lazy-loading service container:
```python
class ServiceContainer:
    async def get_entity_service(self):
        return await self._get_or_create_service("entity", EntityService)
```

### Protocol-Based Interfaces
Services implement protocols for testability:
```python
class IEntityService(Protocol):
    async def create_component(self, repo: str, data: ComponentInput) -> Component: ...
```

## Security Considerations

### Query Sanitization
All user input is sanitized before Cypher execution:
- Parameter binding for values
- Identifier validation for table/column names
- No raw string interpolation in queries

### Branch Isolation
Memory banks are isolated by repository and branch:
- Queries automatically scoped to current context
- No cross-repository data leakage

### Snapshot Safety
Optimization operations create snapshots:
- Automatic backup before destructive operations
- Rollback available for all strategy executions

## Performance Considerations

### Connection Pooling
KuzuDB connections are managed efficiently:
- Single connection per database path
- Thread-safe access with async locks

### Lazy Loading
Services and repositories loaded on demand:
- Reduces startup time
- Memory efficient for unused features

### Query Optimization
Graph queries optimized for common patterns:
- Index usage for primary keys
- Efficient traversal patterns
- Pagination support for large results
