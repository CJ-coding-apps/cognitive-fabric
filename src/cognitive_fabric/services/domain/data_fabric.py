"""Data Fabric service: in-process AST ingestion into the graph + vector store.

Replaces the former Arrow Flight sidecar. `ingest_project` scans a project with
tree-sitter (in-process), persists File/Symbol nodes + DEFINED_IN edges through
the EntityService, and best-effort indexes symbols in the LanceDB vector store.
"""

from typing import TYPE_CHECKING, Any, Optional

import structlog

from cognitive_fabric.config import settings as default_settings
from cognitive_fabric.types.entities import FileInput, SymbolInput

if TYPE_CHECKING:
    from cognitive_fabric.services.service_container import ServiceContainer

logger = structlog.get_logger("DataFabricService")


class DataFabricService:
    """Symbolic ingestion and semantic indexing for the Cognitive Fabric."""

    def __init__(self, container: "ServiceContainer") -> None:
        self._container = container

    async def ingest_project(
        self,
        project_root: str,
        repository: str,
        branch: str = "main",
        *,
        ingestor: Optional[Any] = None,
        vector_store: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Scan a project and persist its symbols/files into the graph.

        Args:
            project_root: Directory to scan. Callers (MCP handler) must pass the
                session's clientProjectRoot so ingestion cannot read arbitrary paths.
            repository: Repository name.
            branch: Branch name.
            ingestor: Optional injected SymbolicIngestor (for testing).
            vector_store: Optional injected VectorStore (for testing).

        Returns:
            A summary dict of what was persisted/indexed.
        """
        logger.info(
            "ingest_project",
            project_root=project_root,
            repository=repository,
            branch=branch,
        )

        if ingestor is None:
            from cognitive_fabric.fabric.ingestor import SymbolicIngestor

            ingestor = SymbolicIngestor()

        symbols, files = ingestor.scan_project(project_root)
        entity = await self._container.get_entity_service()

        # 1. Upsert File nodes.
        files_upserted = 0
        for f in files:
            file_id = f.get("id")
            if not file_id:
                continue
            language = f.get("language")
            await entity.create_file(
                repository,
                FileInput(
                    id=str(file_id),
                    name=str(f.get("name") or file_id),
                    path=str(f.get("path") or file_id),
                    branch=branch,
                    checksum=f.get("hash"),
                    metrics={"language": language} if language else None,
                ),
            )
            files_upserted += 1

        # 2. Upsert Symbol nodes and link each to its File (DEFINED_IN).
        symbols_upserted = 0
        edges_created = 0
        for s in symbols:
            symbol_id = s.get("id")
            if not symbol_id:
                continue
            await entity.create_symbol(
                repository,
                SymbolInput(
                    id=str(symbol_id),
                    name=str(s.get("name") or symbol_id),
                    kind=s.get("kind"),
                    signature=s.get("signature"),
                    branch=branch,
                ),
            )
            symbols_upserted += 1
            file_id = s.get("file_id")
            if file_id:
                linked = await entity.link_symbol_to_file(
                    repository, str(symbol_id), str(file_id), branch
                )
                if linked:
                    edges_created += 1

        # 3. Best-effort semantic indexing (skips cleanly if deps unavailable).
        symbols_indexed = 0
        try:
            if vector_store is None:
                from cognitive_fabric.fabric.vector_store import VectorStore

                vector_store = VectorStore(data_dir=default_settings.fabric_data_dir)
            symbols_indexed = vector_store.upsert(repository, branch, symbols)
        except Exception as e:  # optional dependency / no backend
            logger.warning("semantic indexing skipped", error=str(e))

        result = {
            "success": True,
            "files_upserted": files_upserted,
            "symbols_upserted": symbols_upserted,
            "edges_created": edges_created,
            "symbols_indexed": symbols_indexed,
        }
        logger.info("ingest_project complete", **result)
        return result

    async def semantic_search(
        self,
        repository: str,
        branch: str,
        query: str,
        limit: int = 10,
        threshold: float = 0.0,
        *,
        vector_store: Optional[Any] = None,
    ) -> dict[str, Any]:
        """Vector search over ingested symbols.

        Returns {available, results, message?}; available=False (empty results)
        when the semantic layer is unavailable, so callers can degrade.
        """
        try:
            if vector_store is None:
                from cognitive_fabric.fabric.vector_store import VectorStore

                vector_store = VectorStore(data_dir=default_settings.fabric_data_dir)
            results = vector_store.search(repository, branch, query, limit, threshold)
            return {"available": True, "results": results}
        except Exception as e:
            logger.warning("semantic search unavailable", error=str(e))
            return {
                "available": False,
                "results": [],
                "message": f"Semantic search unavailable: {e}",
            }
