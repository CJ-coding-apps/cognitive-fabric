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
| type | string | Yes | Entity type (see below) |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| data | object | Yes | Entity data |

**Entity Types:**
- `component` - Software components
- `decision` - Architectural decisions
- `rule` - Governance rules
- `context` - Session context
- `file` - File references
- `tag` - Tags for categorization

**Example - Create Component:**
```json
{
  "operation": "create",
  "type": "component",
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
  "type": "decision",
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
| type | string | Yes | Entity type |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| id | string | Yes | Entity ID |

#### update

Update an existing entity.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"update"` |
| type | string | Yes | Entity type |
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
| type | string | Yes | Entity type |
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
| relatedComponents | array | No | Component IDs to link |

**Example:**
```json
{
  "operation": "update",
  "repository": "my-app",
  "agent": "claude",
  "summary": "Discussed authentication implementation",
  "observation": "User prefers JWT over sessions",
  "relatedComponents": ["auth-service"]
}
```

---

## query

Structured queries against the memory graph.

### Operations

#### entities

Query entities by type with optional filters.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"entities"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| entityType | string | Yes | Entity type to query |
| status | string | No | Filter by status |
| limit | integer | No | Max results (default: 100) |

**Example:**
```json
{
  "operation": "entities",
  "repository": "my-app",
  "entityType": "component",
  "status": "active",
  "limit": 50
}
```

#### dependencies

Get dependency graph for a component.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"dependencies"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| componentId | string | Yes | Component ID |
| direction | string | No | `"upstream"`, `"downstream"`, or `"both"` |
| depth | integer | No | Traversal depth (default: 3) |

#### relationships

Query relationships between entities.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"relationships"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| fromId | string | No | Source entity ID |
| toId | string | No | Target entity ID |
| type | string | No | Relationship type |

#### governance

Query governance rules and decisions for a component.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"governance"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| componentId | string | Yes | Component ID |

#### history

Get context history for a component.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"history"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| componentId | string | No | Component ID (optional) |
| startDate | string | No | ISO date start |
| endDate | string | No | ISO date end |
| limit | integer | No | Max results |

#### tags

Query tags and tagged items.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"tags"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| tagId | string | No | Specific tag ID |
| category | string | No | Tag category filter |

---

## associate

Create relationships between entities.

### Operations

#### file-component

Associate a file with a component.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"file-component"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| fileId | string | Yes | File ID |
| componentId | string | Yes | Component ID |

#### tag-item

Tag an item.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"tag-item"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| tagId | string | Yes | Tag ID |
| itemId | string | Yes | Item ID to tag |
| itemType | string | Yes | Item type (e.g., "Component") |

**Example:**
```json
{
  "operation": "tag-item",
  "repository": "my-app",
  "tagId": "backend",
  "itemId": "auth-service",
  "itemType": "Component"
}
```

---

## analyze

Run graph algorithms on the memory graph.

### Operations

#### pagerank

Calculate PageRank scores for components.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"pagerank"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| limit | integer | No | Top N results |

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
| operation | string | Yes | `"k-core"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| k | integer | No | Core number threshold |

#### louvain

Run Louvain community detection.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"louvain"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

#### shortest-path

Find shortest path between components.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"shortest-path"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| fromId | string | Yes | Source component ID |
| toId | string | Yes | Target component ID |

---

## detect

Detect patterns in the memory graph.

### Operations

#### cycles

Detect circular dependencies.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"cycles"` |
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
| operation | string | Yes | `"islands"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

#### strongly-connected

Find strongly connected components.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"strongly-connected"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

#### weakly-connected

Find weakly connected components.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"weakly-connected"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

---

## introspect

Inspect the database schema and statistics.

### Operations

#### labels

Get all node labels (entity types).

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"labels"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |

#### count

Get entity counts by type.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"count"` |
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
| operation | string | Yes | `"properties"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| entityType | string | Yes | Entity type |

#### indexes

Get database indexes.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"indexes"` |
| repository | string | Yes | Repository name |

---

## bulk-import

Batch import operations.

### Operations

#### components

Import multiple components.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"components"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| items | array | Yes | Array of component data |

**Example:**
```json
{
  "operation": "components",
  "repository": "my-app",
  "items": [
    {"id": "svc-1", "name": "Service 1", "kind": "service"},
    {"id": "svc-2", "name": "Service 2", "kind": "service"}
  ]
}
```

#### decisions

Import multiple decisions.

#### rules

Import multiple rules.

---

## search

Search across the memory bank.

### Operations

#### fulltext

Full-text search across entities.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"fulltext"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| query | string | Yes | Search query |
| entityTypes | array | No | Limit to specific types |
| limit | integer | No | Max results |

**Example:**
```json
{
  "operation": "fulltext",
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
| confirm | boolean | Yes | Must be `true` |

#### bulk-by-tag

Delete all items with a specific tag.

**Parameters:**
| Parameter | Type | Required | Description |
|-----------|------|----------|-------------|
| operation | string | Yes | `"bulk-by-tag"` |
| repository | string | Yes | Repository name |
| branch | string | No | Branch name |
| tagId | string | Yes | Tag ID |
| confirm | boolean | Yes | Must be `true` |

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
| useLlm | boolean | No | Use LLM for enhanced analysis |

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
| strategy | string | No | `"conservative"`, `"balanced"`, `"aggressive"` |
| dryRun | boolean | No | Simulate without changes |
| useLlm | boolean | No | Use LLM for planning |

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
| limit | integer | No | Max results |

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
