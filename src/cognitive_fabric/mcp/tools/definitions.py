"""MCP tool definitions for all 13 tools (12 memory bank + fabric)."""

from typing import Dict, List, Optional

from cognitive_fabric.config import settings
from cognitive_fabric.mcp.tools.base import McpTool

# Tool 1: memory-bank
MEMORY_BANK_TOOL = McpTool.create(
    name="memory-bank",
    description=(
        "Initialize and manage memory banks. Operations: init, get-metadata, "
        "update-metadata."
    ),
    properties={
        "operation": {
            "type": "string",
            "enum": ["init", "get-metadata", "update-metadata"],
            "description": "The operation to perform",
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name (default: main)",
            "default": "main",
        },
        "clientProjectRoot": {
            "type": "string",
            "description": "The client's project root path (required for init)",
        },
        "metadata": {
            "type": "object",
            "description": "Metadata to update (for update-metadata operation)",
        },
    },
    required=["operation", "repository"],
)

# Tool 2: entity
ENTITY_TOOL = McpTool.create(
    name="entity",
    description=(
        "CRUD operations for all entity types: component, decision, rule, "
        "file, tag."
    ),
    properties={
        "operation": {
            "type": "string",
            "enum": ["create", "update", "get", "delete"],
            "description": "The operation to perform",
        },
        "entityType": {
            "type": "string",
            "enum": ["component", "decision", "rule", "file", "tag"],
            "description": "The type of entity",
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "id": {
            "type": "string",
            "description": (
                "Entity ID (required for get/delete, optional for "
                "create/update)"
            ),
        },
        "data": {
            "type": "object",
            "description": (
                "Entity data for create/update operations. Accepts TS wire "
                "field aliases: decisionStatus/ruleStatus->status, "
                "size_bytes->size, content_hash->checksum, plus optional "
                "language."
            ),
        },
    },
    required=["operation", "entityType", "repository"],
)

# Tool 3: context
CONTEXT_TOOL = McpTool.create(
    name="context",
    description="Track and update session context information.",
    properties={
        "operation": {
            "type": "string",
            "enum": ["update", "get-recent", "get-summary"],
            "description": "The operation to perform",
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "data": {
            "type": "object",
            "description": "Context data for update operation",
            "properties": {
                "id": {"type": "string"},
                "name": {"type": "string"},
                "agent": {"type": "string"},
                "summary": {"type": "string"},
                "observation": {"type": "string"},
                "key_findings": {"type": "array", "items": {"type": "string"}},
            },
        },
        "id": {
            "type": "string",
            "description": "TS wire (flat): context ID for update",
        },
        "name": {
            "type": "string",
            "description": "TS wire (flat): context name for update",
        },
        "agent": {
            "type": "string",
            "description": "TS wire (flat): agent for update",
        },
        "summary": {
            "type": "string",
            "description": "TS wire (flat): summary for update",
        },
        "observation": {
            "type": "string",
            "description": "TS wire (flat): observation for update",
        },
        "limit": {
            "type": "integer",
            "description": "Limit for get-recent operation",
            "default": 10,
        },
    },
    required=["operation", "repository"],
)

# Tool 4: query
QUERY_TOOL = McpTool.create(
    name="query",
    description=(
        "Structured graph queries: context, entities, relationships, "
        "dependencies, governance, history, tags."
    ),
    properties={
        "queryType": {
            "type": "string",
            "enum": [
                "context", "entities", "relationships", "dependencies",
                "governance", "history", "tags",
            ],
            "description": "The type of query to perform",
        },
        "type": {
            "type": "string",
            "enum": [
                "context", "entities", "relationships", "dependencies",
                "governance", "history", "tags",
            ],
            "description": "TS wire name for the query type (alias of queryType)",
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "entityType": {
            "type": "string",
            "description": "Entity type for entities query",
        },
        "relationshipType": {
            "type": "string",
            "description": "Relationship type for relationships query",
        },
        "componentId": {
            "type": "string",
            "description": "Component ID for dependencies/governance/history queries",
        },
        "tagId": {
            "type": "string",
            "description": "Tag ID for tags query",
        },
        "direction": {
            "type": "string",
            "enum": ["in", "out", "both"],
            "description": "Direction for dependency traversal",
            "default": "both",
        },
        "depth": {
            "type": "integer",
            "description": "Depth for dependency traversal",
            "default": 1,
        },
        "filters": {
            "type": "object",
            "description": "Optional filters for entities query",
        },
        "startItemId": {
            "type": "string",
            "description": "TS wire: starting item ID for traversal queries",
        },
        "relationshipFilter": {
            "type": "string",
            "description": "TS wire: relationship type filter for traversals",
        },
        "targetNodeTypeFilter": {
            "type": "string",
            "description": "TS wire: target node type filter for traversals",
        },
        "latest": {
            "type": "boolean",
            "description": "TS wire: return only the latest results",
        },
        "label": {
            "type": "string",
            "description": (
                "TS wire: node label / entity type for entities query"
            ),
        },
        "offset": {
            "type": "integer",
            "description": "TS wire: pagination offset",
        },
        "itemId": {
            "type": "string",
            "description": "TS wire: item ID for history query (alias of componentId)",
        },
        "itemType": {
            "type": "string",
            "description": "TS wire: item type for history query",
        },
    },
    required=["repository"],
)

# Tool 5: associate
ASSOCIATE_TOOL = McpTool.create(
    name="associate",
    description=(
        "Create relationships between entities: file-component, tag-item, "
        "decision-component, rule-component."
    ),
    properties={
        "associationType": {
            "type": "string",
            "enum": [
                "file-component", "tag-item", "decision-component",
                "rule-component", "context-component",
            ],
            "description": "The type of association to create",
        },
        "type": {
            "type": "string",
            "enum": [
                "file-component", "tag-item", "decision-component",
                "rule-component", "context-component",
            ],
            "description": "TS wire name for the association type (alias)",
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "sourceId": {
            "type": "string",
            "description": "The source entity ID",
        },
        "targetId": {
            "type": "string",
            "description": "The target entity ID",
        },
        "itemType": {
            "type": "string",
            "description": "Item type for tag-item association",
        },
        "fileId": {
            "type": "string",
            "description": "TS wire: file ID for file-component association",
        },
        "componentId": {
            "type": "string",
            "description": (
                "TS wire: component ID for file-component association"
            ),
        },
        "itemId": {
            "type": "string",
            "description": "TS wire: item ID for tag-item association",
        },
        "tagId": {
            "type": "string",
            "description": "TS wire: tag ID for tag-item association",
        },
        "entityType": {
            "type": "string",
            "description": (
                "TS wire: item label for tag-item association "
                "(Component/Decision/Rule/File/Context)"
            ),
        },
    },
    required=["repository"],
)

# Tool 6: analyze
ANALYZE_TOOL = McpTool.create(
    name="analyze",
    description=(
        "Run native KuzuDB graph algorithms over a projected graph: pagerank, "
        "k-core, louvain, shortest-path."
    ),
    properties={
        "type": {
            "type": "string",
            "enum": ["pagerank", "k-core", "louvain", "shortest-path"],
            "description": "The algorithm to run",
        },
        "algorithm": {
            "type": "string",
            "enum": ["pagerank", "k-core", "louvain", "shortest-path"],
            "description": "Alias for 'type' (legacy)",
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "nodeTableNames": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Node tables to project (default: [Component])",
        },
        "relationshipTableNames": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Relationship tables to project (default: [DEPENDS_ON])",
        },
        "damping": {
            "type": "number",
            "description": "PageRank damping factor",
            "default": 0.85,
        },
        "maxIterations": {
            "type": "integer",
            "description": "PageRank maximum iterations",
            "default": 20,
        },
        "k": {
            "type": "integer",
            "description": "K value for k-core algorithm",
            "default": 2,
        },
        "startNodeId": {
            "type": "string",
            "description": "Start component ID for shortest-path",
        },
        "endNodeId": {
            "type": "string",
            "description": "End component ID for shortest-path",
        },
        "startId": {
            "type": "string",
            "description": "Alias for 'startNodeId' (legacy)",
        },
        "endId": {
            "type": "string",
            "description": "Alias for 'endNodeId' (legacy)",
        },
    },
    required=["repository"],
)

# Tool 7: detect
DETECT_TOOL = McpTool.create(
    name="detect",
    description=(
        "Pattern detection: cycles, islands, path, strongly-connected, "
        "weakly-connected."
    ),
    properties={
        "type": {
            "type": "string",
            "enum": [
                "cycles",
                "islands",
                "path",
                "strongly-connected",
                "weakly-connected",
            ],
            "description": "The pattern to detect",
        },
        "pattern": {
            "type": "string",
            "enum": [
                "cycles",
                "islands",
                "path",
                "strongly-connected",
                "weakly-connected",
            ],
            "description": "Alias for 'type' (legacy)",
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "nodeTableNames": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Node tables to project (default: [Component])",
        },
        "relationshipTableNames": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Relationship tables to project (default: [DEPENDS_ON])",
        },
        "startNodeId": {
            "type": "string",
            "description": "Start component ID for path",
        },
        "endNodeId": {
            "type": "string",
            "description": "End component ID for path",
        },
    },
    required=["repository"],
)

# Tool 8: introspect
INTROSPECT_TOOL = McpTool.create(
    name="introspect",
    description="Schema introspection: labels, count, properties, indexes, statistics.",
    properties={
        "operation": {
            "type": "string",
            "enum": ["labels", "count", "properties", "indexes", "statistics"],
            "description": "The introspection operation",
        },
        "query": {
            "type": "string",
            "enum": ["labels", "count", "properties", "indexes", "statistics"],
            "description": "TS wire name for the introspection op (alias)",
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "label": {
            "type": "string",
            "description": "Node/relationship label for properties operation",
        },
        "target": {
            "type": "string",
            "description": "TS wire: node/relationship label (alias of label)",
        },
    },
    required=["repository"],
)

# Tool 9: bulk-import
BULK_IMPORT_TOOL = McpTool.create(
    name="bulk-import",
    description="Batch import operations for components, decisions, and rules.",
    properties={
        "entityType": {
            "type": "string",
            "enum": ["component", "decision", "rule"],
            "description": "The type of entities to import",
        },
        "type": {
            "type": "string",
            "enum": ["components", "decisions", "rules"],
            "description": (
                "TS wire name for the entity type (plural, alias of entityType)"
            ),
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "items": {
            "type": "array",
            "description": "Array of entities to import",
            "items": {"type": "object"},
        },
        "components": {
            "type": "array",
            "description": "TS wire: typed array of components to import",
            "items": {"type": "object"},
        },
        "decisions": {
            "type": "array",
            "description": "TS wire: typed array of decisions to import",
            "items": {"type": "object"},
        },
        "rules": {
            "type": "array",
            "description": "TS wire: typed array of rules to import",
            "items": {"type": "object"},
        },
    },
    required=["repository"],
)

# Tool 10: search
SEARCH_TOOL = McpTool.create(
    name="search",
    description="Search operations: fulltext, by-name, by-kind, semantic, hybrid.",
    properties={
        "searchType": {
            "type": "string",
            "enum": [
                "fulltext", "by-name", "by-kind", "semantic", "hybrid",
            ],
            "description": "The type of search",
        },
        "mode": {
            "type": "string",
            "enum": [
                "fulltext", "semantic", "hybrid", "by-name", "by-kind",
            ],
            "description": (
                "TS wire name for search mode (alias of searchType); "
                "semantic/hybrid use the Cognitive Fabric vector backend"
            ),
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "query": {
            "type": "string",
            "description": "The search query",
        },
        "entityTypes": {
            "type": "array",
            "description": (
                "Entity types to search (optional, searches all if not "
                "specified)"
            ),
            "items": {"type": "string"},
        },
        "limit": {
            "type": "integer",
            "description": "Maximum results to return",
            "default": 20,
        },
        "threshold": {
            "type": "number",
            "description": "Minimum similarity score for semantic/hybrid search",
            "default": 0.0,
        },
    },
    required=["repository"],
)

# Tool 11: delete
DELETE_TOOL = McpTool.create(
    name="delete",
    description="Safe deletion operations: single, bulk-by-type, bulk-by-tag.",
    properties={
        "deleteType": {
            "type": "string",
            "enum": [
                "single", "bulk-by-type", "bulk-by-tag", "bulk-by-status",
                "bulk-by-branch", "bulk-by-repository", "bulk-by-filter",
            ],
            "description": "The type of deletion",
        },
        "operation": {
            "type": "string",
            "enum": [
                "single", "bulk-by-type", "bulk-by-tag", "bulk-by-status",
                "bulk-by-branch", "bulk-by-repository", "bulk-by-filter",
            ],
            "description": "TS wire name for the delete type (alias)",
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "entityType": {
            "type": "string",
            "description": "Entity type for single/bulk-by-type deletion",
        },
        "entityId": {
            "type": "string",
            "description": "Entity ID for single deletion",
        },
        "tagId": {
            "type": "string",
            "description": "Tag ID for bulk-by-tag deletion",
        },
        "status": {
            "type": "string",
            "description": "Status for bulk-by-status deletion",
        },
        "targetType": {
            "type": "string",
            "description": "TS wire: entity type for bulk-by-filter deletion",
        },
        "targetBranch": {
            "type": "string",
            "description": "TS wire: branch to delete for bulk-by-branch",
        },
        "filterStatus": {
            "type": "string",
            "description": "TS wire: status filter for bulk-by-filter",
        },
        "filterCreatedBefore": {
            "type": "string",
            "description": "TS wire: created-before ISO date filter",
        },
        "filterCreatedAfter": {
            "type": "string",
            "description": "TS wire: created-after ISO date filter",
        },
        "filterNamePattern": {
            "type": "string",
            "description": "TS wire: name substring filter for bulk-by-filter",
        },
        "dryRun": {
            "type": "boolean",
            "description": "If true, only report what would be deleted",
            "default": False,
        },
    },
    required=["repository"],
)

# Tool 12: memory-optimizer
MEMORY_OPTIMIZER_TOOL = McpTool.create(
    name="memory-optimizer",
    description=(
        "AI-powered memory optimization: analyze, optimize, rollback, "
        "list-snapshots, create-snapshot."
    ),
    properties={
        "operation": {
            "type": "string",
            "enum": [
                "analyze", "optimize", "rollback", "list-snapshots",
                "create-snapshot",
            ],
            "description": "The operation to perform",
        },
        "repository": {
            "type": "string",
            "description": "The repository name",
        },
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "strategy": {
            "type": "string",
            "enum": ["conservative", "balanced", "aggressive"],
            "description": (
                "Optimization strategy. Unset means "
                "COGNITIVE_FABRIC_OPTIMIZER_DEFAULT_STRATEGY."
            ),
            "default": settings.optimizer_default_strategy,
        },
        "dryRun": {
            "type": "boolean",
            "description": (
                "TS wire: preview optimization actions without applying them"
            ),
            "default": True,
        },
        "confirm": {
            "type": "boolean",
            "description": (
                "TS wire: confirm a non-dry-run optimization (required when "
                "dryRun=false)"
            ),
            "default": False,
        },
        "maxDeletions": {
            "type": "integer",
            "description": (
                "TS wire: cap the number of entity deletions performed"
            ),
        },
        "focusAreas": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": [
                    "stale-detection",
                    "redundancy-removal",
                    "relationship-cleanup",
                    "dependency-optimization",
                    "tag-consolidation",
                    "orphan-removal",
                ],
            },
            "description": (
                "TS wire: restrict optimization to these categories "
                "(all if empty/absent)"
            ),
        },
        "preserveCategories": {
            "type": "array",
            "items": {"type": "string"},
            "description": (
                "TS wire: entity tag/category values to never delete"
            ),
        },
        "snapshotId": {
            "type": "string",
            "description": "Snapshot ID for rollback operation",
        },
        "analysisId": {
            "type": "string",
            "description": (
                "TS wire: cached analysis ID from a prior analyze call to "
                "reuse during optimize"
            ),
        },
        "enableMCPSampling": {
            "type": "boolean",
            "description": (
                "TS wire: attach a sampled memory context to analysis"
            ),
            "default": settings.optimizer_enable_mcp_sampling,
        },
        "samplingStrategy": {
            "type": "string",
            "enum": ["representative", "problematic", "recent", "diverse"],
            "description": "TS wire: memory sampling strategy",
            "default": settings.optimizer_default_sampling_strategy,
        },
        "snapshotFailurePolicy": {
            "type": "string",
            "enum": ["abort", "continue", "warn"],
            "description": (
                "TS wire: behavior when pre-optimization snapshot creation "
                "fails"
            ),
            "default": settings.optimizer_snapshot_failure_policy,
        },
        "description": {
            "type": "string",
            "description": "Description for create-snapshot operation",
        },
    },
    required=["operation", "repository"],
)

# Tool 13: fabric (Cognitive Fabric)
FABRIC_TOOL = McpTool.create(
    name="fabric",
    description=(
        "Cognitive Fabric operations: ingest-ast, dream, record-event, "
        "query-evolution, query-rationale, link-evolution, link-to-file, "
        "link-to-symbol."
    ),
    properties={
        "operation": {
            "type": "string",
            "enum": [
                "ingest-ast",
                "dream",
                "record-event",
                "query-evolution",
                "query-rationale",
                "link-evolution",
                "link-to-file",
                "link-to-symbol",
            ],
            "description": "The fabric operation to perform",
        },
        "repository": {"type": "string", "description": "The repository name"},
        "branch": {
            "type": "string",
            "description": "The branch name",
            "default": "main",
        },
        "path": {
            "type": "string",
            "description": (
                "Project directory to scan (ingest-ast). Must be an existing "
                "directory inside the session's clientProjectRoot."
            ),
        },
        "itemId": {
            "type": "string",
            "description": "Entity id (query-evolution / query-rationale)",
        },
        "itemType": {
            "type": "string",
            "description": "Entity label: Symbol|Requirement|Decision",
        },
        "currentId": {"type": "string", "description": "Current id (link-evolution)"},
        "previousId": {"type": "string", "description": "Previous id (link-evolution)"},
        "symbolId": {
            "type": "string",
            "description": "Symbol id (link-to-file / link-to-symbol)",
        },
        "fileId": {"type": "string", "description": "File id (link-to-file)"},
        "traceId": {"type": "string", "description": "Trace id (link-to-symbol)"},
        "eventSummary": {
            "type": "string",
            "description": "Event summary (record-event)",
        },
        "eventObservation": {
            "type": "string",
            "description": "Event observation (record-event)",
        },
    },
    required=["operation", "repository"],
)

# All tools list
MEMORY_BANK_MCP_TOOLS: List[McpTool] = [
    MEMORY_BANK_TOOL,
    ENTITY_TOOL,
    CONTEXT_TOOL,
    QUERY_TOOL,
    ASSOCIATE_TOOL,
    ANALYZE_TOOL,
    DETECT_TOOL,
    INTROSPECT_TOOL,
    BULK_IMPORT_TOOL,
    SEARCH_TOOL,
    DELETE_TOOL,
    MEMORY_OPTIMIZER_TOOL,
    FABRIC_TOOL,
]

# MCP annotations per tool, applied below. Kept as one table so the whole
# classification is reviewable in a single place: an MCP client (and maf's
# tool-classification layer) decides whether a call needs approval from these
# two hints, so they must describe what the tool actually does.
#
# Rule used here (tool-level = worst case over the tool's operations):
#   readOnlyHint=False  the tool performs any write.
#   destructiveHint=True  the tool can delete existing data, or replace whole
#                       existing structures/records (bulk upsert, ingest, or a
#                       dropped graph projection) — i.e. not purely additive.
#
# Entries that are *not* read-named, despite sounding so:
#   analyze / detect   CALL project_graph, and the projection is dropped again
#                      (drop_projected_graph) — database-global state.
#   bulk-import        writes through the entity upsert path (MERGE ... ON MATCH
#                      SET), so a re-import overwrites existing entities.
#   fabric             ingest-ast bulk-upserts File/Symbol nodes.
TOOL_ANNOTATIONS: Dict[str, Dict[str, bool]] = {
    # Performs no writes.
    "query": {"readOnlyHint": True, "destructiveHint": False},
    "introspect": {"readOnlyHint": True, "destructiveHint": False},
    "search": {"readOnlyHint": True, "destructiveHint": False},
    # Writes, additively: creates nodes/edges that are absent; memory-bank init
    # is a no-op when the bank already exists.
    "memory-bank": {"readOnlyHint": False, "destructiveHint": False},
    "context": {"readOnlyHint": False, "destructiveHint": False},
    "associate": {"readOnlyHint": False, "destructiveHint": False},
    # Writes, not additively: may delete or replace existing data.
    "entity": {"readOnlyHint": False, "destructiveHint": True},
    "analyze": {"readOnlyHint": False, "destructiveHint": True},
    "detect": {"readOnlyHint": False, "destructiveHint": True},
    "bulk-import": {"readOnlyHint": False, "destructiveHint": True},
    "delete": {"readOnlyHint": False, "destructiveHint": True},
    "memory-optimizer": {"readOnlyHint": False, "destructiveHint": True},
    "fabric": {"readOnlyHint": False, "destructiveHint": True},
}

for _tool in MEMORY_BANK_MCP_TOOLS:
    # KeyError (not a silent default) if a tool is added without a
    # classification: an unclassified tool must not reach a client.
    _tool.annotations = TOOL_ANNOTATIONS[_tool.name]


# Tool lookup by name
_TOOLS_BY_NAME: Dict[str, McpTool] = {tool.name: tool for tool in MEMORY_BANK_MCP_TOOLS}


def get_tool_by_name(name: str) -> Optional[McpTool]:
    """Get a tool by name.

    Args:
        name: The tool name.

    Returns:
        The tool if found, None otherwise.
    """
    return _TOOLS_BY_NAME.get(name)
