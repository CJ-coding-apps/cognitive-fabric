# CLI Reference

Cognitive-Fabric provides a command-line interface for server management and database operations.

## Installation

The CLI is automatically installed with the package:

```bash
pip install cognitive_fabric-mcp
```

Two commands are available:
- `cognitive_fabric` - Main CLI with all commands
- `cognitive_fabric-server` - Direct server startup

## Global Options

```bash
cognitive_fabric [OPTIONS] COMMAND [ARGS]...

Options:
  --version   Show version and exit
  -v, --verbose  Enable verbose output
  --help      Show help message and exit
```

## Commands

### serve

Start the MCP server with stdio transport.

```bash
cognitive_fabric serve [OPTIONS]
```

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--db-path` | `-d` | PATH | env var | Path to KuzuDB database |
| `--log-level` | `-l` | CHOICE | INFO | Logging level |
| `--json-logs` | | FLAG | false | Output logs as JSON |

**Examples:**

```bash
# Start with default settings
cognitive_fabric serve

# Specify database path
cognitive_fabric serve --db-path /data/memory.db

# Debug mode with JSON logs
cognitive_fabric serve --log-level DEBUG --json-logs

# With verbose output
cognitive_fabric -v serve --db-path ./data/memory.db
```

**Environment Variables:**
- `COGNITIVE_FABRIC_DB_PATH` - Default database path

---

### init

Initialize a new KuzuDB database with schema.

```bash
cognitive_fabric init [OPTIONS] DB_PATH
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `DB_PATH` | PATH | Path for the new database |

**Options:**

| Option | Short | Type | Description |
|--------|-------|------|-------------|
| `--force` | `-f` | FLAG | Reinitialize existing database |

**Examples:**

```bash
# Initialize new database
cognitive_fabric init ./data/memory.db

# Force reinitialize
cognitive_fabric init -f ./data/memory.db
```

---

### info

Show information about a KuzuDB database.

```bash
cognitive_fabric info DB_PATH
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `DB_PATH` | PATH | Path to existing database |

**Output:**

```
Cognitive Fabric Database Info
========================================
Path: /data/memory.db

Entity Counts:
  repository: 3
  component: 45
  decision: 12
  rule: 8
  context: 156
  file: 230
  tag: 15
  metadata: 3
```

---

### optimize

Run memory optimization on a repository.

```bash
cognitive_fabric optimize [OPTIONS] DB_PATH REPOSITORY
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `DB_PATH` | PATH | Path to database |
| `REPOSITORY` | STRING | Repository name |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--branch` | `-b` | STRING | main | Branch name |
| `--strategy` | `-s` | CHOICE | balanced | Optimization strategy |
| `--dry-run` | | FLAG | false | Simulate without changes |

**Strategy Choices:**
- `conservative` - Minimal changes (max 5 deletions)
- `balanced` - Moderate cleanup (max 20 deletions)
- `aggressive` - Maximum cleanup (max 50 deletions)

**Examples:**

```bash
# Dry run with balanced strategy
cognitive_fabric optimize ./data/memory.db my-app --dry-run

# Conservative optimization on feature branch
cognitive_fabric optimize ./data/memory.db my-app -b feature/auth -s conservative

# Aggressive cleanup
cognitive_fabric optimize ./data/memory.db my-app --strategy aggressive
```

**Output:**

```
Optimization Summary
========================================
Repository: my-app
Branch: main
Strategy: balanced
Health Score: 78
Issues Found: 5
Actions Planned: 12
Actions Executed: 12
Actions Failed: 0
Snapshot ID: snap-20240115-103045
```

---

### rollback

Rollback to a previous snapshot.

```bash
cognitive_fabric rollback [OPTIONS] DB_PATH REPOSITORY SNAPSHOT_ID
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `DB_PATH` | PATH | Path to database |
| `REPOSITORY` | STRING | Repository name |
| `SNAPSHOT_ID` | STRING | Snapshot ID to restore |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--branch` | `-b` | STRING | main | Branch name |

**Examples:**

```bash
# Rollback to specific snapshot
cognitive_fabric rollback ./data/memory.db my-app snap-20240115-103045

# Rollback feature branch
cognitive_fabric rollback ./data/memory.db my-app snap-001 -b feature/auth
```

---

### list-snapshots

List available snapshots for a repository.

```bash
cognitive_fabric list-snapshots [OPTIONS] DB_PATH REPOSITORY
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `DB_PATH` | PATH | Path to database |
| `REPOSITORY` | STRING | Repository name |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--branch` | `-b` | STRING | main | Branch name |
| `--limit` | `-n` | INTEGER | 10 | Max snapshots to show |
| `--json` | | FLAG | false | Output as JSON |

**Examples:**

```bash
# List recent snapshots
cognitive_fabric list-snapshots ./data/memory.db my-app

# Limit to 5 snapshots
cognitive_fabric list-snapshots ./data/memory.db my-app -n 5

# JSON output for scripting
cognitive_fabric list-snapshots ./data/memory.db my-app --json
```

**Output (text):**

```
Available Snapshots
============================================================
ID: snap-20240115-103045
  Created: 2024-01-15T10:30:45Z
  Description: Pre-optimization snapshot for plan plan-abc123

ID: snap-20240114-091530
  Created: 2024-01-14T09:15:30Z
  Description: Manual backup before migration
```

**Output (JSON):**

```json
[
  {
    "id": "snap-20240115-103045",
    "created_at": "2024-01-15T10:30:45Z",
    "description": "Pre-optimization snapshot for plan plan-abc123"
  }
]
```

---

### query

Execute a raw Cypher query against the database.

```bash
cognitive_fabric query [OPTIONS] DB_PATH QUERY
```

**Arguments:**

| Argument | Type | Description |
|----------|------|-------------|
| `DB_PATH` | PATH | Path to database |
| `QUERY` | STRING | Cypher query to execute |

**Options:**

| Option | Short | Type | Default | Description |
|--------|-------|------|---------|-------------|
| `--json` | | FLAG | false | Output as JSON |

**Examples:**

```bash
# List all components
cognitive_fabric query ./data/memory.db "MATCH (n:Component) RETURN n.id, n.name LIMIT 10"

# Count entities
cognitive_fabric query ./data/memory.db "MATCH (n:Component) RETURN count(n) as count"

# JSON output
cognitive_fabric query ./data/memory.db "MATCH (n:Tag) RETURN n" --json

# Complex query
cognitive_fabric query ./data/memory.db "
  MATCH (c:Component)-[:DEPENDS_ON]->(d:Component)
  WHERE c.repository = 'my-app'
  RETURN c.name as component, d.name as dependency
"
```

**Output (text):**

```
id | name
------------------------------------------------------------
auth-service | Authentication Service
user-service | User Service
api-gateway | API Gateway
```

**Output (JSON):**

```json
[
  {"id": "auth-service", "name": "Authentication Service"},
  {"id": "user-service", "name": "User Service"},
  {"id": "api-gateway", "name": "API Gateway"}
]
```

---

## Exit Codes

| Code | Description |
|------|-------------|
| 0 | Success |
| 1 | General error |
| 2 | Invalid arguments |

## Using with Docker

All CLI commands can be run via Docker:

```bash
# Run command in container
docker compose run --rm cognitive_fabric-dev cognitive_fabric COMMAND [ARGS]

# Examples
docker compose run --rm cognitive_fabric-dev cognitive_fabric info /app/data/memory.db
docker compose run --rm cognitive_fabric-dev cognitive_fabric optimize /app/data/memory.db my-app --dry-run
```

## Scripting Examples

### Automated Optimization

```bash
#!/bin/bash
# Weekly optimization script

DB_PATH="/data/cognitive_fabric/memory.db"
REPOS=("app1" "app2" "app3")

for repo in "${REPOS[@]}"; do
    echo "Optimizing $repo..."
    cognitive_fabric optimize "$DB_PATH" "$repo" --strategy balanced
done
```

### Health Check

```bash
#!/bin/bash
# Check database health

DB_PATH="/data/cognitive_fabric/memory.db"

if cognitive_fabric info "$DB_PATH" > /dev/null 2>&1; then
    echo "Database healthy"
    exit 0
else
    echo "Database check failed"
    exit 1
fi
```

### Export Snapshots

```bash
#!/bin/bash
# Export snapshot list to file

DB_PATH="/data/cognitive_fabric/memory.db"
REPO="my-app"

cognitive_fabric list-snapshots "$DB_PATH" "$REPO" --json > snapshots.json
```
