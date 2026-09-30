# Memory Optimizer Agent Guide

The Memory Optimizer Agent is an AI-powered system for analyzing and optimizing memory banks. It identifies redundant, deprecated, or orphaned entities and safely removes them while maintaining system integrity.

## Overview

The optimizer follows a three-phase workflow:

```
┌──────────┐     ┌──────────┐     ┌──────────┐
│ Analyze  │ ──► │   Plan   │ ──► │ Execute  │
└──────────┘     └──────────┘     └──────────┘
     │                │                │
     ▼                ▼                ▼
  Health         Optimization     Snapshot +
  Score +        Actions          Safe Delete
  Issues         (dry run)
```

## Getting Started

### Basic Analysis

Analyze your memory bank to get a health score and identify issues:

```json
{
  "operation": "analyze",
  "repository": "my-app",
  "branch": "main"
}
```

**Response:**
```json
{
  "healthScore": 78,
  "issues": [
    {
      "type": "circular_dependency",
      "severity": "high",
      "description": "Found 2 circular dependency groups",
      "affectedIds": ["svc-a", "svc-b", "svc-c"]
    },
    {
      "type": "deprecated_components",
      "severity": "low",
      "description": "Found 5 deprecated components",
      "affectedIds": ["old-auth", "legacy-db", ...]
    }
  ],
  "recommendations": [
    {
      "priority": 1,
      "action": "Review and refactor circular dependencies",
      "reason": "Circular dependencies cause maintenance issues",
      "risk": "medium"
    }
  ],
  "statistics": {
    "totalComponents": 45,
    "activeComponents": 38,
    "deprecatedComponents": 5,
    "orphanedComponents": 2
  }
}
```

### Dry Run Optimization

Test optimization without making changes:

```json
{
  "operation": "optimize",
  "repository": "my-app",
  "branch": "main",
  "strategy": "balanced",
  "dryRun": true
}
```

### Full Optimization

Execute optimization with automatic snapshot:

```json
{
  "operation": "optimize",
  "repository": "my-app",
  "branch": "main",
  "strategy": "balanced",
  "dryRun": false
}
```

## Optimization Strategies

### Conservative

Best for production systems where stability is critical.

| Setting | Value |
|---------|-------|
| Stale threshold | 180 days |
| Max deletions | 5 |
| Delete orphaned tags | No |
| Require no dependents | Yes |

```json
{
  "operation": "optimize",
  "repository": "my-app",
  "strategy": "conservative"
}
```

### Balanced (Default)

Good for regular maintenance with moderate cleanup.

| Setting | Value |
|---------|-------|
| Stale threshold | 90 days |
| Max deletions | 20 |
| Delete orphaned tags | Yes |
| Require no dependents | No |

```json
{
  "operation": "optimize",
  "repository": "my-app",
  "strategy": "balanced"
}
```

### Aggressive

For major cleanup or before migrations.

| Setting | Value |
|---------|-------|
| Stale threshold | 30 days |
| Max deletions | 50 |
| Delete orphaned tags | Yes |
| Require no dependents | No |

```json
{
  "operation": "optimize",
  "repository": "my-app",
  "strategy": "aggressive"
}
```

## Analysis Details

### Health Score

The health score (0-100) is calculated based on:

| Factor | Impact |
|--------|--------|
| Circular dependencies | -20 per group |
| Disconnected islands | -10 per group |
| Deprecated components | -5 per component |
| Orphaned components | -5 per component |
| Clean structure bonus | +5 |

### Issue Types

| Type | Severity | Description |
|------|----------|-------------|
| `circular_dependency` | High | Components depend on each other in a cycle |
| `disconnected_components` | Medium | Component groups with no connections |
| `deprecated_components` | Low | Components marked as deprecated |
| `orphaned_tags` | Low | Tags with no associated items |
| `stale_context` | Low | Context entries older than threshold |

### Pattern Detection

The analyzer detects these patterns:

- **Cycles**: A → B → C → A
- **Islands**: Disconnected component groups
- **Strongly Connected**: Components reachable from each other
- **Hub Components**: High-connectivity components (via PageRank)

## Optimization Actions

### Delete Actions

Remove entities that are:
- Deprecated with no dependents
- Orphaned (no dependencies and no dependents)
- Stale (not updated within threshold)

```json
{
  "actionType": "delete",
  "entityType": "component",
  "entityId": "old-auth-service",
  "reason": "Component is deprecated and has no dependents",
  "riskLevel": "low"
}
```

### Update Actions

Update entity status or properties:

```json
{
  "actionType": "update",
  "entityType": "component",
  "entityId": "legacy-service",
  "reason": "Mark as deprecated based on age",
  "updates": {"status": "deprecated"}
}
```

## Snapshot Management

### Automatic Snapshots

Before any optimization execution (non-dry-run), a snapshot is automatically created:

```json
{
  "snapshotId": "snap-20240115-103045",
  "createdAt": "2024-01-15T10:30:45Z",
  "description": "Pre-optimization snapshot for plan plan-abc123"
}
```

### List Snapshots

```json
{
  "operation": "list-snapshots",
  "repository": "my-app",
  "branch": "main",
  "limit": 10
}
```

### Rollback

Restore to a previous snapshot:

```json
{
  "operation": "rollback",
  "repository": "my-app",
  "branch": "main",
  "snapshotId": "snap-20240115-103045"
}
```

## LLM-Enhanced Optimization

For more intelligent analysis, enable LLM support:

### Setup

1. Configure your LLM provider:
   ```bash
   export COGNITIVE_FABRIC_LLM_PROVIDER=openai
   export OPENAI_API_KEY=sk-your-key
   ```

2. Enable LLM in requests:
   ```json
   {
     "operation": "analyze",
     "repository": "my-app",
     "useLlm": true
   }
   ```

### LLM Benefits

- **Semantic Analysis**: Understands component purposes beyond names
- **Intelligent Grouping**: Identifies related components
- **Risk Assessment**: Better judgment on deletion safety
- **Contextual Recommendations**: More specific action items

### LLM Response Enhancement

With LLM enabled, you get additional insights:

```json
{
  "healthScore": 78,
  "issues": [...],
  "llmAnalysis": {
    "assessment": "The memory bank shows signs of organic growth with some technical debt. The authentication system has multiple deprecated components suggesting a recent migration.",
    "keyObservations": [
      "Auth system underwent migration, leaving deprecated components",
      "Database components tightly coupled, consider modularization"
    ],
    "suggestedPriorities": [
      "Clean up post-migration auth components",
      "Address circular dependency in payment system"
    ]
  }
}
```

## CLI Usage

### Analyze from CLI

```bash
cognitive_fabric optimize /path/to/db my-repo --strategy balanced --dry-run
```

### Full Optimization

```bash
cognitive_fabric optimize /path/to/db my-repo --strategy balanced
```

### Rollback from CLI

```bash
cognitive_fabric rollback /path/to/db my-repo snap-20240115-103045
```

### List Snapshots

```bash
cognitive_fabric list-snapshots /path/to/db my-repo
```

## Best Practices

### Regular Maintenance

1. **Weekly Analysis**: Run analysis to monitor health score
2. **Monthly Cleanup**: Execute balanced optimization
3. **Review Before**: Always use dry-run first

### Before Major Changes

1. Run aggressive dry-run to see potential cleanup
2. Review the planned actions
3. Create a manual snapshot
4. Execute with conservative strategy first
5. Verify system stability
6. Proceed to balanced if needed

### Production Safety

1. Always enable snapshots
2. Start with conservative strategy
3. Monitor for issues after optimization
4. Keep recent snapshots for quick rollback

## Troubleshooting

### High Number of Issues

If analysis shows many issues:

1. Start with conservative strategy
2. Address high-severity issues first
3. Run multiple small optimizations
4. Verify after each run

### Optimization Not Removing Expected Items

Check:
- Entity status (must be deprecated or orphaned)
- Dependents (conservative requires none)
- Strategy limits (max_deletions)

### Rollback Failed

1. Check snapshot exists: `list-snapshots`
2. Verify snapshot ID is correct
3. Check database permissions
4. Try manual restore from backup

### LLM Errors

1. Verify API key is set
2. Check LLM provider configuration
3. Ensure network connectivity
4. Fall back to rule-based analysis

## API Reference

### Analyze

```json
{
  "operation": "analyze",
  "repository": "string",
  "branch": "string (optional)",
  "useLlm": "boolean (optional)"
}
```

### Optimize

```json
{
  "operation": "optimize",
  "repository": "string",
  "branch": "string (optional)",
  "strategy": "conservative | balanced | aggressive",
  "dryRun": "boolean (optional)",
  "useLlm": "boolean (optional)"
}
```

### Rollback

```json
{
  "operation": "rollback",
  "repository": "string",
  "branch": "string (optional)",
  "snapshotId": "string"
}
```

### List Snapshots

```json
{
  "operation": "list-snapshots",
  "repository": "string",
  "branch": "string (optional)",
  "limit": "integer (optional)"
}
```
