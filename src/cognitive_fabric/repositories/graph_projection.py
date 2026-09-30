"""Native KuzuDB graph-projection lifecycle for graph algorithms.

Mirrors the TS ``graph-projection-manager``: create a projected graph over the
given node/relationship tables, run native ALGO functions against it, and always
drop it afterward. KuzuDB's ``algo`` extension is statically linked into the
wheel, so ``page_rank`` / ``k_core_decomposition`` / ``louvain`` /
``*_connected_components`` are available without any INSTALL/LOAD.
"""

from contextlib import contextmanager
from typing import Iterator
from uuid import uuid4

from cognitive_fabric.db.kuzu_client import KuzuDBClient
from cognitive_fabric.utils.security import (
    sanitize_projection_name,
    validate_label,
    validate_relationship_type,
)


def _drop_projection(client: KuzuDBClient, name: str) -> None:
    """Drop a projected graph, ignoring the error when it does not exist."""
    try:
        client.execute_query(f"CALL drop_projected_graph('{name}')")
    except Exception:
        # No DROP IF EXISTS in kuzu 0.11.x; a missing projection raises.
        pass


def _connected_node_tables(client: KuzuDBClient, rel_tables: list[str]) -> list[str]:
    """Return every node table connected to any of ``rel_tables``.

    ``project_graph`` rejects a projection whose relationship tables reference a
    node table that is not also projected. The base memory graph only wires
    DEPENDS_ON between Components, but the Cognitive Fabric layer widens some rel
    tables (e.g. DEPENDS_ON also links Symbol->Symbol), so the projected node set
    must be expanded to cover those endpoints. This introspects the catalog via
    ``SHOW_CONNECTION`` so the projection stays valid regardless of which pairs a
    rel table declares.
    """
    found: list[str] = []
    for rel in rel_tables:
        try:
            rows = client.fetch_all(f"CALL SHOW_CONNECTION('{rel}') RETURN *")
        except Exception:
            continue
        for row in rows:
            # SHOW_CONNECTION yields (source table, dest table, source pk,
            # dest pk). Only the two table-name columns are relevant.
            for key in ("source table name", "destination table name"):
                value = row.get(key)
                if (
                    isinstance(value, str)
                    and value
                    and value not in found
                    and validate_label(value)
                ):
                    found.append(value)
    return found


@contextmanager
def projected_graph(
    client: KuzuDBClient,
    name: str,
    node_tables: list[str],
    rel_tables: list[str],
) -> Iterator[str]:
    """Create a native projected graph and guarantee its cleanup.

    Args:
        client: The KuzuDB client.
        name: Prefix for the projection name (sanitized before use; a unique
            suffix is appended — see below).
        node_tables: Node table names to project (validated against the label
            whitelist — ``project_graph`` cannot parameterize table names, so
            they are interpolated and must be trusted).
        rel_tables: Relationship table names to project (validated against the
            relationship whitelist).

    Yields:
        The projection name to pass to algorithm ``CALL``s.

    Raises:
        ValueError: If any table name is not in the security whitelist.
    """
    for label in node_tables:
        if not validate_label(label):
            raise ValueError(f"Invalid node table: {label}")
    for rel in rel_tables:
        if not validate_relationship_type(rel):
            raise ValueError(f"Invalid relationship table: {rel}")

    # Ensure every node table referenced by the projected rel tables is included
    # (Cognitive Fabric widens some base rel tables, e.g. DEPENDS_ON also links
    # Symbol->Symbol). project_graph errors otherwise.
    effective_nodes = list(node_tables)
    for label in _connected_node_tables(client, rel_tables):
        if label not in effective_nodes:
            effective_nodes.append(label)

    # The projection name is generated here, not supplied by the caller, and is
    # unique per call. `project_graph` / `drop_projected_graph` are
    # database-global, so a caller-chosen or shared name (e.g. a bare "cycles")
    # lets one session drop a projection another session is still reading. The
    # caller's `name` survives only as a sanitized, human-readable prefix.
    safe = f"{sanitize_projection_name(name) or 'p_graph'}_{uuid4().hex[:12]}"
    nodes = "[" + ", ".join(f"'{t}'" for t in effective_nodes) + "]"
    rels = "[" + ", ".join(f"'{t}'" for t in rel_tables) + "]"

    client.execute_query(f"CALL project_graph('{safe}', {nodes}, {rels})")
    try:
        yield safe
    finally:
        _drop_projection(client, safe)
