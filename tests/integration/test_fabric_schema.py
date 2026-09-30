"""Schema completeness test for the Cognitive Fabric tables."""

import pytest

from cognitive_fabric.db.kuzu_client import KuzuDBClient

EXPECTED_NODES = {"Symbol", "Requirement", "Trace"}
EXPECTED_RELS = {
    "EVOLVED_FROM",
    "JUSTIFIES",
    "DEFINED_IN",
    "REALISED_BY",
    "CONTRAVENES",
    "RECORDS",
}


@pytest.mark.integration
@pytest.mark.asyncio
async def test_fabric_tables_created(kuzu_client: KuzuDBClient):
    rows = kuzu_client.fetch_all("CALL show_tables() RETURN *")
    names = {r.get("name") for r in rows}
    missing = (EXPECTED_NODES | EXPECTED_RELS) - names
    assert not missing, f"missing fabric tables: {sorted(missing)}"
