"""Security utilities for Cypher query sanitization."""

import re
from typing import Any

# Allowed node labels (whitelist)
ALLOWED_LABELS = frozenset({
    "Component",
    "Decision",
    "Rule",
    "Tag",
    "File",
    "Context",
    "Repository",
    "Metadata",
    # Cognitive Fabric
    "Symbol",
    "Requirement",
    "Trace",
})

# Allowed relationship types (whitelist)
ALLOWED_RELATIONSHIPS = frozenset({
    "DEPENDS_ON",
    "IMPLEMENTS",
    "TAGGED_WITH",
    "GOVERNS",
    "AFFECTS",
    "CONTEXT_OF",
    "PART_OF",
    "HAS_METADATA",
    # Cognitive Fabric
    "EVOLVED_FROM",
    "JUSTIFIES",
    "DEFINED_IN",
    "REALISED_BY",
    "CONTRAVENES",
    "RECORDS",
})


def escape_cypher_string(value: str) -> str:
    """Escape a string for safe use in Cypher queries.

    Args:
        value: The string to escape.

    Returns:
        The escaped string safe for Cypher.
    """
    if not isinstance(value, str):
        return str(value)

    # Escape backslashes first, then single quotes
    escaped = value.replace("\\", "\\\\")
    escaped = escaped.replace("'", "\\'")
    escaped = escaped.replace('"', '\\"')

    return escaped


def validate_label(label: str) -> bool:
    """Validate that a label is in the allowed whitelist.

    Args:
        label: The label to validate.

    Returns:
        True if the label is allowed, False otherwise.
    """
    return label in ALLOWED_LABELS


def validate_relationship_type(rel_type: str) -> bool:
    """Validate that a relationship type is in the allowed whitelist.

    Args:
        rel_type: The relationship type to validate.

    Returns:
        True if the relationship type is allowed, False otherwise.
    """
    return rel_type in ALLOWED_RELATIONSHIPS


def sanitize_identifier(identifier: str) -> str:
    """Sanitize an identifier (table/column name) for safe use.

    Only allows alphanumeric characters and underscores.

    Args:
        identifier: The identifier to sanitize.

    Returns:
        The sanitized identifier.

    Raises:
        ValueError: If the identifier is invalid.
    """
    if not identifier:
        raise ValueError("Identifier cannot be empty")

    # Only allow alphanumeric and underscore
    if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_]*$", identifier):
        raise ValueError(
            f"Invalid identifier: {identifier}. "
            "Must start with letter/underscore and contain only "
            "alphanumeric characters and underscores."
        )

    return identifier


def sanitize_projection_name(name: str) -> str:
    """Sanitize a graph projection name.

    Args:
        name: The projection name to sanitize.

    Returns:
        The sanitized projection name.
    """
    # Remove any non-alphanumeric characters except underscore and hyphen
    sanitized = re.sub(r"[^a-zA-Z0-9_-]", "_", name)

    # Ensure it starts with a letter
    if sanitized and not sanitized[0].isalpha():
        sanitized = "p_" + sanitized

    return sanitized


def build_safe_query_params(params: dict[str, Any]) -> dict[str, Any]:
    """Build safe query parameters by escaping string values.

    Args:
        params: The parameters to process.

    Returns:
        A new dict with escaped string values.
    """
    safe_params: dict[str, Any] = {}

    for key, value in params.items():
        if isinstance(value, str):
            safe_params[key] = escape_cypher_string(value)
        elif isinstance(value, list):
            safe_params[key] = [
                escape_cypher_string(v) if isinstance(v, str) else v for v in value
            ]
        else:
            safe_params[key] = value

    return safe_params


def check_injection_patterns(query: str) -> list[str]:
    """Check a query string for potential injection patterns.

    Args:
        query: The query to check.

    Returns:
        A list of warning messages for detected patterns.
    """
    warnings: list[str] = []

    # Patterns that might indicate injection attempts
    suspicious_patterns = [
        (r";\s*DROP", "DROP statement detected"),
        (r";\s*DELETE", "DELETE statement after semicolon"),
        (r";\s*CREATE", "CREATE statement after semicolon"),
        (r"LOAD\s+CSV", "LOAD CSV detected"),
        (r"CALL\s+db\.", "System procedure call detected"),
        (r"--", "SQL-style comment detected"),
        (r"/\*", "Block comment detected"),
    ]

    for pattern, message in suspicious_patterns:
        if re.search(pattern, query, re.IGNORECASE):
            warnings.append(message)

    return warnings
