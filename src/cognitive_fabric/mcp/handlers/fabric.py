"""Handler for the fabric tool (Cognitive Fabric operations)."""

import datetime
import uuid
from typing import Any, Dict

import structlog

from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.types.entities import ContextInput
from cognitive_fabric.utils.id_utils import format_graph_unique_id

logger = structlog.get_logger(__name__)

# Node labels valid as EVOLVED_FROM lineage sources (validated before interpolation).
_EVOLUTION_LABELS = {"Symbol", "Requirement", "Decision"}


async def fabric_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle fabric tool operations."""
    operation = params["operation"]
    repository = params["repository"]
    branch = params.get("branch", "main")

    logger.debug("fabric handler", operation=operation, repository=repository)

    try:
        if operation == "ingest-ast":
            path = params.get("path")
            if not path:
                return {"success": False, "error": "path is required for ingest-ast"}
            data_fabric = await memory_service.data_fabric
            data = await data_fabric.ingest_project(path, repository, branch)
            return {
                "success": True,
                "operation": operation,
                "data": data,
                "message": (
                    f"Persisted {data['symbols_upserted']} symbols, "
                    f"{data['files_upserted']} files, "
                    f"{data['edges_created']} DEFINED_IN edges "
                    f"({data['symbols_indexed']} indexed)."
                ),
            }

        if operation == "dream":
            dream = await memory_service.dream
            data = await dream.trigger_dream(repository, branch)
            return {"success": True, "operation": operation, "data": data}

        if operation == "record-event":
            summary = params.get("eventSummary")
            observation = params.get("eventObservation")
            if not summary or not observation:
                return {
                    "success": False,
                    "error": "eventSummary and eventObservation are required",
                }
            ctx = await memory_service.context
            event_id = params.get("itemId") or f"evt-{uuid.uuid4().hex[:8]}"
            iso = datetime.datetime.now(datetime.timezone.utc).date().isoformat()
            await ctx.update_context(
                repository,
                ContextInput(
                    id=event_id,
                    name=str(summary)[:80],
                    iso_date=iso,
                    summary=summary,
                    observation=observation,
                    branch=branch,
                ),
            )
            return {
                "success": True,
                "operation": operation,
                "data": {"id": event_id},
                "message": "Episodic event recorded.",
            }

        if operation == "query-evolution":
            item_id = params.get("itemId")
            item_type = params.get("itemType", "Symbol")
            if not item_id:
                return {
                    "success": False,
                    "error": "itemId is required for query-evolution",
                }
            if item_type not in _EVOLUTION_LABELS:
                return {
                    "success": False,
                    "error": f"itemType must be one of {sorted(_EVOLUTION_LABELS)}",
                }
            kuzu = await memory_service.get_kuzu_client()
            gid = format_graph_unique_id(repository, branch, item_id)
            rows = kuzu.fetch_all(
                f"""
                MATCH (start:{item_type} {{graph_unique_id: $gid}})
                      -[:EVOLVED_FROM*0..]->(anc)
                RETURN anc.id AS id, anc.name AS name
                """,
                {"gid": gid},
            )
            return {
                "success": True,
                "operation": operation,
                "data": {"lineage": rows},
                "count": len(rows),
            }

        if operation == "query-rationale":
            item_id = params.get("itemId")
            if not item_id:
                return {
                    "success": False,
                    "error": "itemId is required for query-rationale",
                }
            kuzu = await memory_service.get_kuzu_client()
            gid = format_graph_unique_id(repository, branch, item_id)
            rows = kuzu.fetch_all(
                """
                MATCH (d:Decision)-[:JUSTIFIES]->(n {graph_unique_id: $gid})
                RETURN d.id AS id, d.name AS name, d.rationale AS rationale
                """,
                {"gid": gid},
            )
            return {
                "success": True,
                "operation": operation,
                "data": {"decisions": rows},
                "count": len(rows),
            }

        if operation == "link-evolution":
            current_id = params.get("currentId")
            previous_id = params.get("previousId")
            item_type = (params.get("itemType") or "Symbol").lower()
            if not current_id or not previous_id:
                return {
                    "success": False,
                    "error": "currentId and previousId are required",
                }
            entity = await memory_service.entity
            if item_type == "symbol":
                ok = await entity.link_symbol_evolution(
                    repository, current_id, previous_id, branch
                )
            elif item_type == "requirement":
                ok = await entity.link_requirement_evolution(
                    repository, current_id, previous_id, branch
                )
            else:
                return {
                    "success": False,
                    "error": "itemType must be 'symbol' or 'requirement'",
                }
            return {"success": ok, "operation": operation}

        if operation == "link-to-file":
            symbol_id = params.get("symbolId")
            file_id = params.get("fileId")
            if not symbol_id or not file_id:
                return {"success": False, "error": "symbolId and fileId are required"}
            entity = await memory_service.entity
            ok = await entity.link_symbol_to_file(
                repository, symbol_id, file_id, branch
            )
            return {"success": ok, "operation": operation}

        if operation == "link-to-symbol":
            trace_id = params.get("traceId")
            symbol_id = params.get("symbolId")
            if not trace_id or not symbol_id:
                return {"success": False, "error": "traceId and symbolId are required"}
            entity = await memory_service.entity
            ok = await entity.link_trace_to_symbol(
                repository, trace_id, symbol_id, branch
            )
            return {"success": ok, "operation": operation}

        return {"success": False, "error": f"Unknown operation: {operation}"}

    except Exception as e:
        logger.error("fabric handler error", operation=operation, error=str(e))
        return {"success": False, "error": str(e)}
