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

Execute optimization with automatic snapshot. A non-dry-run `optimize` needs
`confirm`, so that a real deletion is never one forgotten flag away:

```json
{
  "operation": "optimize",
  "repository": "my-app",
  "branch": "main",
  "strategy": "conservative",
  "dryRun": false,
  "confirm": true
}
```

## Optimization Strategies

<!-- BEGIN GENERATED: strategy table -->
| Strategy | Stale threshold (days) | Max deletions | Deletes orphaned tags | Requires no dependents |
|----------|------------------------|---------------|-----------------------|-----------------------|
| conservative | 90 | 10 | no | yes |
| **balanced** (default on an unrecognised strategy name) | 60 | 50 | yes | no |
| aggressive | 30 | 100 | yes | no |

The strategy that applies when none is requested is `COGNITIVE_FABRIC_OPTIMIZER_DEFAULT_STRATEGY`, which is `conservative`.
<!-- END GENERATED: strategy table -->

A deployment can impose a ceiling below any of these with
`COGNITIVE_FABRIC_OPTIMIZER_MAX_DELETIONS`; see the configuration guide. The
cap applies under every strategy, and a caller's own `maxDeletions` can only
lower the effective limit, never raise it.

```json
{
  "operation": "optimize",
  "repository": "my-app",
  "strategy": "conservative"
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
  "branch": "main"
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

The agent's own analysis and planning are rule-based. The rule-based path is
what the MCP tool exposes; the LLM path is reached through the
`MemoryOptimizationAgent` API, which takes an `llm_client`, not through a tool
argument.

### Setup

Configure the provider and name a model — there is no default, so the call
fails and says so rather than picking one for you:

```bash
export COGNITIVE_FABRIC_LLM_PROVIDER=openai
export OPENAI_API_KEY=sk-your-key
export COGNITIVE_FABRIC_OPENAI_MODEL=<model id from https://platform.openai.com/docs/models>
```

### LLM Benefits

- **Semantic Analysis**: Understands component purposes beyond names
- **Intelligent Grouping**: Identifies related components
- **Risk Assessment**: Better judgment on deletion safety
- **Contextual Recommendations**: More specific action items

## CLI Usage

The optimizer is reached through `optimize`; the CLI has no separate per-operation
commands for it.

### Analyze from CLI

```bash
cognitive-fabric optimize /path/to/db my-repo --strategy conservative --dry-run
```

### Full Optimization

```bash
cognitive-fabric optimize /path/to/db my-repo --strategy conservative
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

### The pre-deletion snapshot

Every run that is not a dry run copies the database in full before it touches
anything, and the snapshot id is reported so the run can be undone with
`rollback`. If that copy cannot be taken the default is to **abort**: nothing
is deleted and the error says why.

`COGNITIVE_FABRIC_OPTIMIZER_SNAPSHOT_FAILURE_POLICY` is a deployment setting
and deliberately not a tool argument. An agent that is about to delete memory
must not be able to waive the backup that makes the deletion reversible; the
opt-out belongs to the operator, who can set it to `warn` or `continue` and
accept an irreversible run.

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

These are the keys the `memory-optimizer` tool accepts. There is no `useLlm`:
the tool's analysis and planning are rule-based, and the LLM path is on the
agent API, not on the wire.

### Analyze

```json
{
  "operation": "analyze",
  "repository": "string",
  "branch": "string (optional, default \"main\")",
  "enableMCPSampling": "boolean (optional)",
  "samplingStrategy": "representative | problematic | recent | diverse"
}
```

### Optimize

```json
{
  "operation": "optimize",
  "repository": "string",
  "branch": "string (optional, default \"main\")",
  "strategy": "conservative | balanced | aggressive",
  "dryRun": "boolean (optional, default true)",
  "confirm": "boolean (required when dryRun is false)",
  "maxDeletions": "integer (optional, can only lower the effective cap)",
  "focusAreas": ["stale-detection", "redundancy-removal", "relationship-cleanup", "dependency-optimization", "tag-consolidation", "orphan-removal"],
  "preserveCategories": ["string"],
  "analysisId": "string (optional, reuses a cached analyze result)"
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
  "branch": "string (optional)"
}
```

### Create Snapshot

```json
{
  "operation": "create-snapshot",
  "repository": "string",
  "branch": "string (optional)",
  "description": "string (optional)"
}
```
