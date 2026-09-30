# Basic Usage Examples

This guide shows common operations with Cognitive-Fabric through Claude Code.

## Setting Up a New Project

### 1. Initialize Memory Bank

Ask Claude:
> Initialize a memory bank for my project "e-commerce-api" in the current directory

Claude will call:
```json
{
  "tool": "memory-bank",
  "arguments": {
    "operation": "init",
    "repository": "e-commerce-api",
    "branch": "main",
    "clientProjectRoot": "/path/to/e-commerce-api"
  }
}
```

### 2. Set Project Metadata

> Set the project metadata: we're using Python, FastAPI, PostgreSQL, and Redis

```json
{
  "tool": "memory-bank",
  "arguments": {
    "operation": "update-metadata",
    "repository": "e-commerce-api",
    "metadata": {
      "projectName": "E-Commerce API",
      "techStack": ["Python", "FastAPI", "PostgreSQL", "Redis"],
      "version": "1.0.0"
    }
  }
}
```

## Recording Architecture

### Add Components

> Record that we have these services: user-service, product-service, order-service, and payment-service

Claude creates each component:
```json
{
  "tool": "entity",
  "arguments": {
    "operation": "create",
    "type": "component",
    "repository": "e-commerce-api",
    "data": {
      "id": "user-service",
      "name": "User Service",
      "kind": "service",
      "status": "active"
    }
  }
}
```

### Add Dependencies

> The order-service depends on user-service and product-service

```json
{
  "tool": "entity",
  "arguments": {
    "operation": "update",
    "type": "component",
    "repository": "e-commerce-api",
    "id": "order-service",
    "data": {
      "depends_on": ["user-service", "product-service"]
    }
  }
}
```

### Record a Decision

> Record our decision to use JWT for authentication because we need stateless auth for horizontal scaling

```json
{
  "tool": "entity",
  "arguments": {
    "operation": "create",
    "type": "decision",
    "repository": "e-commerce-api",
    "data": {
      "id": "adr-001",
      "name": "Use JWT for Authentication",
      "context": "Need stateless authentication for horizontal scaling of microservices",
      "date": "2024-01-15",
      "status": "accepted"
    }
  }
}
```

### Add a Rule

> Add a rule that all services must expose a /health endpoint

```json
{
  "tool": "entity",
  "arguments": {
    "operation": "create",
    "type": "rule",
    "repository": "e-commerce-api",
    "data": {
      "id": "rule-health-check",
      "name": "Health Check Endpoint Required",
      "content": "All services must expose a GET /health endpoint that returns 200 when healthy",
      "triggers": ["service-creation", "deployment"],
      "status": "active"
    }
  }
}
```

## Organizing with Tags

### Create Tags

> Create tags for "backend", "frontend", and "infrastructure"

```json
{
  "tool": "entity",
  "arguments": {
    "operation": "create",
    "type": "tag",
    "repository": "e-commerce-api",
    "data": {
      "id": "tag-backend",
      "name": "backend",
      "color": "#3498db",
      "description": "Backend services",
      "category": "layer"
    }
  }
}
```

### Tag Components

> Tag the user-service and order-service as backend

```json
{
  "tool": "associate",
  "arguments": {
    "operation": "tag-item",
    "repository": "e-commerce-api",
    "tagId": "tag-backend",
    "itemId": "user-service",
    "itemType": "Component"
  }
}
```

## Querying Memory

### List All Components

> What components do we have?

```json
{
  "tool": "query",
  "arguments": {
    "operation": "entities",
    "repository": "e-commerce-api",
    "entityType": "component"
  }
}
```

### Get Component Dependencies

> What does order-service depend on?

```json
{
  "tool": "query",
  "arguments": {
    "operation": "dependencies",
    "repository": "e-commerce-api",
    "componentId": "order-service",
    "direction": "upstream"
  }
}
```

### Find Components by Tag

> Show me all backend components

```json
{
  "tool": "query",
  "arguments": {
    "operation": "tags",
    "repository": "e-commerce-api",
    "tagId": "tag-backend"
  }
}
```

### Get Governance Information

> What rules and decisions affect the payment-service?

```json
{
  "tool": "query",
  "arguments": {
    "operation": "governance",
    "repository": "e-commerce-api",
    "componentId": "payment-service"
  }
}
```

## Session Context

### Record Conversation Context

> Remember that we discussed implementing rate limiting for the API gateway

```json
{
  "tool": "context",
  "arguments": {
    "operation": "update",
    "repository": "e-commerce-api",
    "agent": "claude",
    "summary": "Discussed implementing rate limiting for the API gateway",
    "observation": "User wants to limit to 100 requests per minute per user",
    "relatedComponents": ["api-gateway"]
  }
}
```

### View Context History

> What have we discussed about the api-gateway?

```json
{
  "tool": "query",
  "arguments": {
    "operation": "history",
    "repository": "e-commerce-api",
    "componentId": "api-gateway"
  }
}
```

## Analysis

### Run PageRank

> Which are the most important components?

```json
{
  "tool": "analyze",
  "arguments": {
    "operation": "pagerank",
    "repository": "e-commerce-api",
    "limit": 5
  }
}
```

### Detect Issues

> Check for circular dependencies

```json
{
  "tool": "detect",
  "arguments": {
    "operation": "cycles",
    "repository": "e-commerce-api"
  }
}
```

### Find Disconnected Components

> Are there any isolated components?

```json
{
  "tool": "detect",
  "arguments": {
    "operation": "islands",
    "repository": "e-commerce-api"
  }
}
```

## Optimization

### Analyze Health

> Analyze the memory bank health

```json
{
  "tool": "memory-optimizer",
  "arguments": {
    "operation": "analyze",
    "repository": "e-commerce-api"
  }
}
```

### Dry Run Optimization

> What would a balanced optimization clean up?

```json
{
  "tool": "memory-optimizer",
  "arguments": {
    "operation": "optimize",
    "repository": "e-commerce-api",
    "strategy": "balanced",
    "dryRun": true
  }
}
```

### Execute Optimization

> Run the optimization

```json
{
  "tool": "memory-optimizer",
  "arguments": {
    "operation": "optimize",
    "repository": "e-commerce-api",
    "strategy": "balanced"
  }
}
```

## Searching

### Full-Text Search

> Search for anything related to "authentication"

```json
{
  "tool": "search",
  "arguments": {
    "operation": "fulltext",
    "repository": "e-commerce-api",
    "query": "authentication",
    "limit": 20
  }
}
```

## Cleanup

### Delete a Component

> Remove the deprecated legacy-auth component

```json
{
  "tool": "delete",
  "arguments": {
    "operation": "single",
    "repository": "e-commerce-api",
    "entityType": "component",
    "entityId": "legacy-auth"
  }
}
```

### Mark as Deprecated

> Mark the old-payment-gateway as deprecated

```json
{
  "tool": "entity",
  "arguments": {
    "operation": "update",
    "type": "component",
    "repository": "e-commerce-api",
    "id": "old-payment-gateway",
    "data": {
      "status": "deprecated"
    }
  }
}
```

## Common Workflows

### Starting a New Feature

1. Create the component
2. Add dependencies
3. Tag appropriately
4. Link to files
5. Record the context

### Architecture Review

1. Query all components
2. Run PageRank for importance
3. Detect cycles
4. Check for islands
5. Review governance

### Regular Maintenance

1. Analyze health score
2. Review issues
3. Run dry-run optimization
4. Execute if acceptable
5. Verify results
