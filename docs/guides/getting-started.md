# Getting Started with Cognitive-Fabric

This guide will help you get Cognitive-Fabric up and running quickly.

## Prerequisites

- Docker and Docker Compose (recommended)
- OR Python 3.11+ for local installation

## Quick Start with Docker

### 1. Clone the Repository

```bash
git clone https://github.com/your-repo/cognitive-fabric.git
cd cognitive-fabric
```

### 2. Build the Container

```bash
docker compose build
```

### 3. Run the MCP Server

```bash
docker compose run --rm cognitive_fabric-dev
```

The server will start and listen on stdio for MCP protocol messages.

### 4. Verify Installation

Run the tests to verify everything is working:

```bash
docker compose run --rm test
```

## Local Installation (Alternative)

### 1. Create Virtual Environment

```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
```

### 2. Install Package

```bash
pip install -e ".[dev]"
```

### 3. Run the Server

```bash
cognitive_fabric serve
```

## Integrating with Claude Code

### MCP Configuration

Add Cognitive-Fabric to your Claude Code MCP settings:

**For Docker deployment:**

```json
{
  "mcpServers": {
    "cognitive_fabric": {
      "command": "docker",
      "args": [
        "compose",
        "-f", "/path/to/cognitive-fabric/docker-compose.yml",
        "run", "--rm", "-T", "cognitive_fabric"
      ]
    }
  }
}
```

**For local installation:**

```json
{
  "mcpServers": {
    "cognitive_fabric": {
      "command": "cognitive_fabric-server"
    }
  }
}
```

### Verify Integration

Once configured, ask Claude to initialize a memory bank:

```
Initialize a memory bank for my project "my-app"
```

Claude will use the `memory-bank` tool to create the memory bank.

## Your First Memory Bank

### Initialize the Memory Bank

Use the `memory-bank` tool to initialize:

```json
{
  "operation": "init",
  "repository": "my-app",
  "branch": "main",
  "clientProjectRoot": "/path/to/my-app"
}
```

### Add a Component

Use the `entity` tool to create a component:

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
    "status": "active"
  }
}
```

### Add a Decision

Record an architectural decision:

```json
{
  "operation": "create",
  "type": "decision",
  "repository": "my-app",
  "branch": "main",
  "data": {
    "id": "adr-001",
    "name": "Use JWT for Authentication",
    "context": "Need stateless authentication for microservices",
    "date": "2024-01-15",
    "status": "accepted"
  }
}
```

### Query Your Memory

Retrieve all components:

```json
{
  "operation": "entities",
  "repository": "my-app",
  "branch": "main",
  "entityType": "component"
}
```

## Basic Workflow

A typical workflow with Cognitive-Fabric:

1. **Initialize** a memory bank for your project
2. **Record** components, decisions, and rules as you work
3. **Associate** entities (tag components, link decisions to components)
4. **Query** the memory to recall context
5. **Analyze** the graph for insights (PageRank, cycles)
6. **Optimize** periodically to clean up stale data

## Next Steps

- Read the [Architecture Overview](../architecture.md) to understand the system
- Explore the [MCP Tools Reference](../api/tools.md) for all available operations
- Learn about [Entity Types](entities.md) and their schemas
- Set up [Memory Optimization](memory-optimizer.md) for automated cleanup

## Common Issues

### Server Won't Start

1. Check Docker is running: `docker info`
2. Rebuild the container: `docker compose build --no-cache`
3. Check logs: `docker compose logs`

### MCP Connection Failed

1. Verify the command path in your MCP config
2. Check that the server starts manually
3. Look for error messages in Claude Code's output panel

### Database Errors

1. Ensure the data directory is writable
2. Check disk space availability
3. Try initializing with a fresh database

See the [Troubleshooting Guide](troubleshooting.md) for more solutions.
