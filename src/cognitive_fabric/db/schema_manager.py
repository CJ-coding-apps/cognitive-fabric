"""Schema manager for KuzuDB DDL operations."""

from typing import TYPE_CHECKING

import structlog

if TYPE_CHECKING:
    import kuzu

logger = structlog.get_logger("SchemaManager")

# =============================================================================
# Node Table DDL
# =============================================================================

NODE_TABLE_DDL = """
-- Repository Node
CREATE NODE TABLE IF NOT EXISTS Repository (
    id STRING,
    name STRING,
    branch STRING,
    tech_stack STRING[],
    architecture STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);

-- Component Node
CREATE NODE TABLE IF NOT EXISTS Component (
    graph_unique_id STRING,
    id STRING,
    name STRING,
    kind STRING,
    status STRING,
    depends_on STRING[],
    description STRING,
    metadata STRING,
    repository STRING,
    branch STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (graph_unique_id)
);

-- Decision Node
CREATE NODE TABLE IF NOT EXISTS Decision (
    graph_unique_id STRING,
    id STRING,
    name STRING,
    context STRING,
    date STRING,
    status STRING,
    rationale STRING,
    impact STRING[],
    tags STRING[],
    repository STRING,
    branch STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (graph_unique_id)
);

-- Rule Node
CREATE NODE TABLE IF NOT EXISTS Rule (
    graph_unique_id STRING,
    id STRING,
    name STRING,
    created STRING,
    triggers STRING[],
    content STRING,
    status STRING,
    description STRING,
    scope STRING,
    severity STRING,
    category STRING,
    examples STRING[],
    repository STRING,
    branch STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (graph_unique_id)
);

-- Context Node
CREATE NODE TABLE IF NOT EXISTS Context (
    graph_unique_id STRING,
    id STRING,
    name STRING,
    iso_date STRING,
    agent STRING,
    related_issue STRING,
    summary STRING,
    observation STRING,
    decisions STRING[],
    observations STRING[],
    repository STRING,
    branch STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (graph_unique_id)
);

-- File Node
CREATE NODE TABLE IF NOT EXISTS File (
    id STRING,
    name STRING,
    path STRING,
    size INT64,
    mime_type STRING,
    content STRING,
    metrics STRING,
    checksum STRING,
    last_modified TIMESTAMP,
    repository STRING,
    branch STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);

-- Tag Node
CREATE NODE TABLE IF NOT EXISTS Tag (
    id STRING,
    name STRING,
    color STRING,
    description STRING,
    category STRING,
    repository STRING,
    branch STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (id)
);

-- Metadata Node
CREATE NODE TABLE IF NOT EXISTS Metadata (
    graph_unique_id STRING,
    id STRING,
    name STRING,
    content STRING,
    branch STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (graph_unique_id)
);

-- Symbol Node (Cognitive Fabric)
CREATE NODE TABLE IF NOT EXISTS Symbol (
    graph_unique_id STRING,
    id STRING,
    name STRING,
    kind STRING,
    signature STRING,
    docstring STRING,
    repository STRING,
    branch STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (graph_unique_id)
);

-- Requirement Node (Cognitive Fabric)
CREATE NODE TABLE IF NOT EXISTS Requirement (
    graph_unique_id STRING,
    id STRING,
    name STRING,
    description STRING,
    priority STRING,
    status STRING,
    repository STRING,
    branch STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (graph_unique_id)
);

-- Trace Node (Cognitive Fabric)
CREATE NODE TABLE IF NOT EXISTS Trace (
    graph_unique_id STRING,
    id STRING,
    name STRING,
    trace_type STRING,
    content STRING,
    repository STRING,
    branch STRING,
    created_at TIMESTAMP,
    updated_at TIMESTAMP,
    PRIMARY KEY (graph_unique_id)
);
"""

# =============================================================================
# Relationship Table DDL
# =============================================================================

RELATIONSHIP_TABLE_DDL = """
-- Component / Symbol Dependencies
CREATE REL TABLE IF NOT EXISTS DEPENDS_ON (
    FROM Component TO Component, FROM Symbol TO Symbol
);

-- Component to File Implementation
CREATE REL TABLE IF NOT EXISTS IMPLEMENTS (FROM Component TO File);

-- Tagging Relationships (multiple source types)
CREATE REL TABLE IF NOT EXISTS TAGGED_WITH (
    FROM Component TO Tag, FROM Decision TO Tag,
    FROM Rule TO Tag, FROM File TO Tag);

-- Governance Relationships
CREATE REL TABLE IF NOT EXISTS GOVERNS (FROM Rule TO Component);

CREATE REL TABLE IF NOT EXISTS AFFECTS (FROM Decision TO Component);

-- Context Relationships (context can annotate multiple entity types)
CREATE REL TABLE IF NOT EXISTS CONTEXT_OF (
    FROM Context TO Component, FROM Context TO Decision,
    FROM Context TO Rule);

-- Ownership Relationships (every entity type belongs to a Repository;
-- symbol in component is a Cognitive Fabric pair)
CREATE REL TABLE IF NOT EXISTS PART_OF (
    FROM Component TO Repository, FROM Decision TO Repository,
    FROM Rule TO Repository, FROM File TO Repository,
    FROM Tag TO Repository, FROM Context TO Repository,
    FROM Symbol TO Component);

-- Metadata Relationships
CREATE REL TABLE IF NOT EXISTS HAS_METADATA (FROM Repository TO Metadata);

-- Cognitive Fabric Relationships
CREATE REL TABLE IF NOT EXISTS EVOLVED_FROM (
    FROM Requirement TO Requirement,
    FROM Decision TO Decision,
    FROM Symbol TO Symbol
);
CREATE REL TABLE IF NOT EXISTS JUSTIFIES (
    FROM Decision TO Symbol, FROM Decision TO Rule
);
CREATE REL TABLE IF NOT EXISTS DEFINED_IN (FROM Symbol TO File);
CREATE REL TABLE IF NOT EXISTS REALISED_BY (
    FROM Requirement TO Component, FROM Requirement TO Symbol
);
CREATE REL TABLE IF NOT EXISTS CONTRAVENES (FROM Decision TO Rule);
CREATE REL TABLE IF NOT EXISTS RECORDS (FROM Trace TO Symbol);
"""


class SchemaManager:
    """Manages KuzuDB schema initialization and validation."""

    def __init__(self, connection: "kuzu.Connection") -> None:
        """Initialize the schema manager.

        Args:
            connection: The KuzuDB connection.
        """
        self._connection = connection
        self._logger = logger.bind(component="SchemaManager")

    async def initialize_schema(self) -> None:
        """Initialize the database schema with all tables.

        Creates node tables and relationship tables if they don't exist.
        """
        self._logger.info("Initializing database schema")

        # Parse and execute node table DDL
        node_statements = self._parse_ddl(NODE_TABLE_DDL)
        for statement in node_statements:
            await self._execute_ddl(statement)

        # Parse and execute relationship table DDL
        rel_statements = self._parse_ddl(RELATIONSHIP_TABLE_DDL)
        for statement in rel_statements:
            await self._execute_ddl(statement)

        self._logger.info(
            "Schema initialized",
            node_tables=len(node_statements),
            rel_tables=len(rel_statements),
        )

    def _parse_ddl(self, ddl: str) -> list[str]:
        """Parse DDL string into individual statements.

        Args:
            ddl: The DDL string with multiple statements.

        Returns:
            A list of individual DDL statements.
        """
        statements = []
        current_statement = []

        for line in ddl.strip().split("\n"):
            line = line.strip()

            # Skip empty lines and comments
            if not line or line.startswith("--"):
                continue

            current_statement.append(line)

            # Check if statement is complete (ends with ;)
            if line.endswith(";"):
                full_statement = " ".join(current_statement)
                # Remove trailing semicolon for Kuzu
                statements.append(full_statement.rstrip(";"))
                current_statement = []

        return statements

    async def _execute_ddl(self, statement: str) -> None:
        """Execute a single DDL statement.

        Args:
            statement: The DDL statement to execute.
        """
        try:
            self._connection.execute(statement)
            self._logger.debug("DDL executed", statement=statement[:80])
        except Exception as e:
            # Ignore "already exists" errors
            error_str = str(e).lower()
            if "already exists" in error_str or "already exist" in error_str:
                self._logger.debug(
                    "Table already exists",
                    statement=statement[:80],
                )
            else:
                self._logger.error(
                    "DDL execution failed",
                    statement=statement[:80],
                    error=str(e),
                )
                raise

    async def get_node_tables(self) -> list[str]:
        """Get list of existing node tables.

        Returns:
            A list of node table names.
        """
        try:
            result = self._connection.execute(
                "CALL show_tables() RETURN name WHERE type = 'NODE'"
            )
            tables = []
            while result.has_next():
                row = result.get_next()
                tables.append(row[0])
            return tables
        except Exception as e:
            self._logger.error("Failed to get node tables", error=str(e))
            return []

    async def get_rel_tables(self) -> list[str]:
        """Get list of existing relationship tables.

        Returns:
            A list of relationship table names.
        """
        try:
            result = self._connection.execute(
                "CALL show_tables() RETURN name WHERE type = 'REL'"
            )
            tables = []
            while result.has_next():
                row = result.get_next()
                tables.append(row[0])
            return tables
        except Exception as e:
            self._logger.error("Failed to get rel tables", error=str(e))
            return []

    async def validate_schema(self) -> dict[str, bool]:
        """Validate that all required tables exist.

        Returns:
            A dict mapping table names to existence status.
        """
        expected_node_tables = {
            "Repository",
            "Component",
            "Decision",
            "Rule",
            "Context",
            "File",
            "Tag",
            "Metadata",
            "Symbol",
            "Requirement",
            "Trace",
        }
        expected_rel_tables = {
            "DEPENDS_ON",
            "IMPLEMENTS",
            "TAGGED_WITH",
            "GOVERNS",
            "AFFECTS",
            "CONTEXT_OF",
            "PART_OF",
            "HAS_METADATA",
            "EVOLVED_FROM",
            "JUSTIFIES",
            "DEFINED_IN",
            "REALISED_BY",
            "CONTRAVENES",
            "RECORDS",
        }

        existing_node = set(await self.get_node_tables())
        existing_rel = set(await self.get_rel_tables())

        validation: dict[str, bool] = {}

        for table in expected_node_tables:
            validation[f"node:{table}"] = table in existing_node

        for table in expected_rel_tables:
            validation[f"rel:{table}"] = table in existing_rel

        return validation
