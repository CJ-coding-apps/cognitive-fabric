# MCP Tools Reference

Cognitive-Fabric provides 13 MCP tools for memory management. This document describes each tool, its operations, and parameters.

## Tool Overview

| Tool | Description |
|------|-------------|
| [memory-bank](#memory-bank) | Initialize and manage memory banks |
| [entity](#entity) | CRUD operations for all entity types |
| [context](#context) | Session context tracking |
| [query](#query) | Structured graph queries |
| [associate](#associate) | Create relationships between entities |
| [analyze](#analyze) | Run graph algorithms |
| [detect](#detect) | Pattern detection in graphs |
| [introspect](#introspect) | Schema inspection |
| [bulk-import](#bulk-import) | Batch entity operations |
| [search](#search) | Full-text search |
| [delete](#delete) | Safe deletion operations |
| [memory-optimizer](#memory-optimizer) | AI-powered memory optimization |
| [fabric](#fabric) | Code-evolution memory: AST ingestion, rationale and trace links |

---

## memory-bank

Initialize and manage memory banks for repositories.

### Operations

#### init

Initialize a new memory bank or connect to an existing one.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"init"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name (default: "main") |
| clientProjectRoot | string | Yes | Absolute path to project root |

**Example:**
```json
{
  "operation": "init",
  "repository": "my-app",
  "branch": "main",
  "clientProjectRoot": "/home/user/projects/my-app"
}
```

**Response:**
```json
{
  "success": true,
  "repository": "my-app",
  "branch": "main",
  "message": "Memory bank initialized"
}
```

#### get-metadata

Get memory bank metadata.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"get-metadata"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

#### update-metadata

Update memory bank metadata.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"update-metadata"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| metadata | object | Yes | Metadata content to update |

---

## entity

CRUD operations for all entity types.

### Operations

#### create

Create a new entity.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"create"` |
| entityType | string | Yes | Entity type (see below) |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| data | object | Yes | Entity data |

**Entity Types:**
- `component` - Software components
- `decision` - Architectural decisions
- `rule` - Governance rules
- `file` - File references
- `tag` - Tags for categorization

Session context entries are not an `entity` type; they have their own tool
(`context`), and `entity` refuses the name.

**Example - Create Component:**
```json
{
  "operation": "create",
  "entityType": "component",
  "repository": "my-app",
  "branch": "main",
  "data": {
    "id": "auth-service",
    "name": "Authentication Service",
    "kind": "service",
    "status": "active",
    "depends_on": ["user-service", "database"]
  }
}
```

**Example - Create Decision:**
```json
{
  "operation": "create",
  "entityType": "decision",
  "repository": "my-app",
  "data": {
    "id": "adr-001",
    "name": "Use PostgreSQL for primary database",
    "context": "Need ACID compliance and complex queries",
    "date": "2024-01-15",
    "status": "accepted"
  }
}
```

#### get

Retrieve an entity by ID.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"get"` |
| entityType | string | Yes | Entity type |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| id | string | Yes | Entity ID |

#### update

Update an existing entity.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"update"` |
| entityType | string | Yes | Entity type |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| id | string | Yes | Entity ID |
| data | object | Yes | Fields to update |

#### delete

Delete an entity.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"delete"` |
| entityType | string | Yes | Entity type |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| id | string | Yes | Entity ID |

---

## context

Manage session context entries.

### Operations

#### update

Add or update a context entry.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"update"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| agent | string | Yes | Agent identifier |
| summary | string | Yes | Context summary |
| observation | string | No | Additional observations |

There is no `relatedComponents`. A context entry is linked to a component by
`associate`'s `context-component` association, which is a separate call and a
separate relationship; a key passed here would be ignored.

**Example:**
```json
{
  "operation": "update",
  "repository": "my-app",
  "agent": "claude",
  "summary": "Discussed authentication implementation",
  "observation": "User prefers JWT over sessions"
}
```

---

## query

Structured queries against the memory graph.

The operation is named by `type`; `queryType` is accepted as an alias. Each row
below is the property that operation reads — a parameter an operation does not
list is ignored, and the call answers with an error about the property it
wanted.

### Operations

#### entities

Query entities by type with optional filters.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"entities"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| entityType | string | Yes | Entity type to query (the alias `label` is also accepted) |
| filters | object | No | `{"status": "active"}` is the only filter the service applies; other keys are ignored |

**Example:**
```json
{
  "type": "entities",
  "repository": "my-app",
  "entityType": "component",
  "filters": {"status": "active"}
}
```

#### dependencies

Get dependency graph for a component.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"dependencies"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| componentId | string | Yes | Component ID |
| direction | string | No | `"in"`, `"out"`, or `"both"` (default: `"both"`) |
| depth | integer | No | Traversal depth (default: 1) |

#### relationships

Query relationships of one type across the repository.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"relationships"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| relationshipType | string | Yes | Relationship type, e.g. `"DEPENDS_ON"` |

This is not a two-endpoint lookup: it returns every relationship of that type in
the repository. To walk from one component, use `dependencies`.

#### governance

Query governance rules and decisions for a component.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"governance"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| componentId | string | Yes | Component ID |

#### history

Get context history for a component.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"history"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| componentId | string | Yes | Component ID (the alias `itemId` is also accepted) |

There is no date range and no `limit`: the operation returns the component's
context entries in full.

#### tags

Query tags and tagged items.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"tags"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| tagId | string | No | Restrict to a single tag ID |

There is no category filter on this operation; a tag's category is returned as
data, not queried by.

---

## associate

Create relationships between entities.

The association is named by `type`; `associationType` is accepted as an alias.
`sourceId`/`targetId` name the two ends for every association; the named forms
below are accepted instead where they read more clearly.

### Operations

#### file-component

Associate a file with a component.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"file-component"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| fileId | string | Yes | File ID (or `sourceId`) |
| componentId | string | Yes | Component ID (or `targetId`) |

#### tag-item

Tag an item.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"tag-item"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| tagId | string | Yes | Tag ID |
| itemId | string | Yes | Item ID to tag |
| itemType | string | No | Item type (default: `"Component"`) |

**Example:**
```json
{
  "type": "tag-item",
  "repository": "my-app",
  "tagId": "backend",
  "itemId": "auth-service",
  "itemType": "Component"
}
```

---

## analyze

Run graph algorithms on the memory graph.

The algorithm is named by `type`; `algorithm` is accepted as an alias. All four
algorithms take `repository`, `branch` and the optional table scoping below;
the rows after that are the ones that algorithm alone reads.

**Common parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"pagerank"`, `"k-core"`, `"louvain"`, or `"shortest-path"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| nodeTableNames | array | No | Node tables to run over |
| relationshipTableNames | array | No | Relationship tables to run over |

### Operations

#### pagerank

Calculate PageRank scores for components.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| damping | number | No | Damping factor (default: 0.85) |
| maxIterations | integer | No | Iteration cap (default: 20) |

There is no `limit`: the algorithm returns every node it scored, ranked. Cut
the list in the caller.

**Response:**
```json
{
  "results": [
    {"id": "core-service", "name": "Core Service", "rank": 0.245},
    {"id": "auth-service", "name": "Auth Service", "rank": 0.189}
  ]
}
```

#### k-core

Calculate k-core decomposition.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| k | integer | No | Core number threshold (default: 2) |

#### louvain

Run Louvain community detection.

Takes the common parameters and nothing else.

#### shortest-path

Find shortest path between components.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| startNodeId | string | Yes | Source component ID (the alias `startId` is also accepted) |
| endNodeId | string | Yes | Target component ID (the alias `endId` is also accepted) |

---

## detect

Detect patterns in the memory graph.

The pattern is named by `type`; `pattern` is accepted as an alias. Each
operation takes `repository` and `branch`; `nodeTableNames` and
`relationshipTableNames` narrow the tables it walks.

### Operations

#### cycles

Detect circular dependencies.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"cycles"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

**Response:**
```json
{
  "cycles": [
    ["service-a", "service-b", "service-c", "service-a"]
  ],
  "count": 1
}
```

#### islands

Detect disconnected component groups.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"islands"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

#### strongly-connected

Find strongly connected components.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"strongly-connected"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

#### weakly-connected

Find weakly connected components.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"weakly-connected"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

#### path

Find the path between two components.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"path"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| startNodeId | string | Yes | Source component ID |
| endNodeId | string | Yes | Target component ID |

---

## introspect

Inspect the database schema and statistics.

The operation is named by `query`; `operation` is accepted as an alias.

### Operations

#### labels

Get all node labels (entity types).

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | `"labels"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

#### count

Get entity counts by type.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | `"count"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

**Response:**
```json
{
  "counts": {
    "Component": 45,
    "Decision": 12,
    "Rule": 8,
    "Context": 156,
    "File": 230,
    "Tag": 15
  }
}
```

#### properties

Get properties for an entity type.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | `"properties"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| target | string | Yes | Entity type to describe (the alias `label` is also accepted) |

#### indexes

Get database indexes.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | `"indexes"` |
| repository | string | Yes | Repository name |

#### statistics

Get graph and database statistics.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| query | string | Yes | `"statistics"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

---

## bulk-import

Batch import operations.

The entity kind is named by `type`; `entityType` (the singular) is accepted as
an alias. The batch itself is passed as `items`, or as the key matching the
kind — `components`, `decisions` or `rules`.

### Operations

#### components

Import multiple components.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| type | string | Yes | `"components"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| items | array | Yes | Array of component data (or `components`) |

**Example:**
```json
{
  "type": "components",
  "repository": "my-app",
  "items": [
    {"id": "svc-1", "name": "Service 1", "kind": "service"},
    {"id": "svc-2", "name": "Service 2", "kind": "service"}
  ]
}
```

#### decisions

Import multiple decisions. Same shape, with `type: "decisions"` and the batch
under `items` or `decisions`.

#### rules

Import multiple rules. Same shape, with `type: "rules"` and the batch under
`items` or `rules`.

---

## search

Search across the memory bank.

The search kind is named by `mode`; `searchType` is accepted as an alias.
`mode` is one of `fulltext`, `semantic`, `hybrid`, `by-name` or `by-kind`, and
defaults to `fulltext` when omitted. `threshold` (default `0.0`) applies to the
`semantic` and `hybrid` modes.

### Operations

#### fulltext

Full-text search across entities.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| mode | string | No | `"fulltext"` (default: `"fulltext"`) |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| query | string | Yes | Search query |
| entityTypes | array | No | Limit to specific types |
| limit | integer | No | Max results (default: 20) |

**Example:**
```json
{
  "mode": "fulltext",
  "repository": "my-app",
  "query": "authentication",
  "entityTypes": ["component", "decision"],
  "limit": 20
}
```

---

## delete

Safe deletion operations.

### Operations

#### single

Delete a single entity.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"single"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| entityType | string | Yes | Entity type |
| entityId | string | Yes | Entity ID |

#### bulk-by-type

Delete all entities of a type.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"bulk-by-type"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| entityType | string | Yes | Entity type |
| dryRun | boolean | No | If `true`, only report what would be deleted |

#### bulk-by-tag

Delete all items with a specific tag.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"bulk-by-tag"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| tagId | string | Yes | Tag ID |
| dryRun | boolean | No | If `true`, only report what would be deleted |

---

## memory-optimizer

AI-powered memory optimization.

### Operations

#### analyze

Analyze memory bank for optimization opportunities.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"analyze"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| enableMCPSampling | boolean | No | Analyze by sampling through MCP |
| samplingStrategy | string | No | `"representative"`, `"problematic"`, `"recent"`, or `"diverse"` |

There is no `useLlm`. The tool's analysis is rule-based; the LLM path is on the
`MemoryOptimizationAgent` API and is not reachable from the wire.

**Response:**
```json
{
  "healthScore": 85,
  "issues": [
    {
      "type": "circular_dependency",
      "severity": "high",
      "description": "Found 2 circular dependency groups",
      "affectedIds": ["svc-a", "svc-b"]
    }
  ],
  "recommendations": [
    {
      "priority": 1,
      "action": "Review circular dependencies",
      "reason": "May cause maintenance issues",
      "risk": "medium"
    }
  ]
}
```

#### optimize

Execute optimization with a strategy.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"optimize"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| strategy | string | No | `"conservative"`, `"balanced"`, `"aggressive"` (unset means `COGNITIVE_FABRIC_OPTIMIZER_DEFAULT_STRATEGY`) |
| dryRun | boolean | No | Simulate without changes (default: true) |
| confirm | boolean | Yes | Required when `dryRun` is false |
| maxDeletions | integer | No | Can only lower the effective limit, never raise it |
| focusAreas | array | No | Restrict the plan to specific cleanup areas |
| preserveCategories | array | No | Tag categories to keep regardless of the plan |
| analysisId | string | No | Reuse a cached `analyze` result |
| snapshotFailurePolicy | string | No | `"abort"`, `"continue"`, or `"warn"` (default: `"warn"`) |

#### rollback

Rollback to a previous snapshot.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"rollback"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| snapshotId | string | Yes | Snapshot ID |

#### list-snapshots

List available snapshots.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"list-snapshots"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

There is no `limit`: the operation returns the repository's snapshots in full.

#### create-snapshot

Create a snapshot without running an optimization.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"create-snapshot"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| description | string | No | Description stored with the snapshot |

---

## fabric

The code-evolution memory: ingest a project's symbols, record a change trace,
and link the two. Every operation takes `repository` and `branch`.

### Operations

#### ingest-ast

Parse a project directory into `Symbol` nodes and their relationships.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"ingest-ast"` |
| repository | string | Yes | Repository name |
| path | string | Yes | Project directory to scan |
| branch | string | No | Branch name |

#### dream

Run the consolidation pass over the ingested graph.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"dream"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

#### record-event

Record a change event for the evolution graph.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"record-event"` |
| repository | string | Yes | Repository name |
| eventSummary | string | Yes | Short summary of the change |
| eventObservation | string | No | Longer observation |
| itemId | string | No | Event ID; generated when omitted |
| branch | string | No | Branch name |

#### query-evolution

Read the evolution history for an item.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"query-evolution"` |
| repository | string | Yes | Repository name |
| itemId | string | Yes | Item ID |
| itemType | string | No | Item type (default: `"Symbol"`) |
| branch | string | No | Branch name |

#### query-rationale

Read the rationale linked to an item.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"query-rationale"` |
| repository | string | Yes | Repository name |
| itemId | string | Yes | Item ID |
| branch | string | No | Branch name |

#### link-evolution

Link an item to the item it supersedes.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"link-evolution"` |
| repository | string | Yes | Repository name |
| currentId | string | Yes | The newer item |
| previousId | string | Yes | The item it supersedes |
| itemType | string | No | Item type (default: `"Symbol"`) |
| branch | string | No | Branch name |

#### link-to-file

Link a symbol to the file that defines it.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"link-to-file"` |
| repository | string | Yes | Repository name |
| symbolId | string | Yes | Symbol ID |
| fileId | string | Yes | File ID |
| branch | string | No | Branch name |

#### link-to-symbol

Link an evolution trace to a symbol.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"link-to-symbol"` |
| repository | string | Yes | Repository name |
| traceId | string | Yes | Trace ID |
| symbolId | string | Yes | Symbol ID |
| branch | string | No | Branch name |

---

## Error Handling

All tools return errors in a consistent format:

```json
{
  "error": true,
  "code": "NOT_FOUND",
  "message": "Component 'unknown-id' not found",
  "details": {
    "entityType": "component",
    "entityId": "unknown-id"
  }
}
```

**Common Error Codes:**
| Code | Description |
|------|-------------|
| NOT_FOUND | Entity not found |
| VALIDATION_ERROR | Invalid parameters |
| CONFLICT | Entity already exists |
| DEPENDENCY_ERROR | Operation blocked by dependencies |
| DATABASE_ERROR | Database operation failed |
