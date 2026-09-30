"""Handler for memory-optimizer tool."""

from typing import Any, Dict, List, Optional

import structlog

from cognitive_fabric.agents.memory_optimizer.mcp_sampling import MemorySamplingManager
from cognitive_fabric.config import settings
from cognitive_fabric.mcp.tool_context import ToolHandlerContext
from cognitive_fabric.services.memory_service import MemoryService

logger = structlog.get_logger(__name__)

# Cache for analysis results to enable multi-step analyze -> optimize workflows.
# Mirrors the TS handler's module-level analysisCache (Map). Keyed by analysisId.
_ANALYSIS_CACHE: Dict[str, Dict[str, Any]] = {}
_ANALYSIS_CACHE_MAX = 10
_ANALYSIS_COUNTER = 0

# Which optimization categories each focus area unlocks. Deprecated-component
# removal is stale/redundancy work; orphaned-tag removal is orphan cleanup.
_DEPRECATED_FOCUS = frozenset({
    "stale-detection",
    "redundancy-removal",
    "dependency-optimization",
})
_ORPHAN_TAG_FOCUS = frozenset({
    "orphan-removal",
    "tag-consolidation",
    "relationship-cleanup",
})


def _next_analysis_id(repository: str, branch: str, count: int) -> str:
    """Build a deterministic-ish analysis ID (no Date.now/random).

    Args:
        repository: The repository name.
        branch: The branch name.
        count: A count/discriminator (e.g. number of entities analyzed).

    Returns:
        A unique-per-process analysis ID string.
    """
    global _ANALYSIS_COUNTER
    _ANALYSIS_COUNTER += 1
    return f"analysis-{repository}-{branch}-{count}-{_ANALYSIS_COUNTER}"


def _cache_analysis(analysis_id: str, analysis: Dict[str, Any]) -> None:
    """Cache an analysis result, evicting the oldest when over capacity."""
    _ANALYSIS_CACHE[analysis_id] = analysis
    while len(_ANALYSIS_CACHE) > _ANALYSIS_CACHE_MAX:
        oldest_key = next(iter(_ANALYSIS_CACHE))
        _ANALYSIS_CACHE.pop(oldest_key, None)


async def memory_optimizer_handler(
    params: Dict[str, Any],
    context: ToolHandlerContext,
    memory_service: MemoryService,
) -> Dict[str, Any]:
    """Handle memory-optimizer tool operations.

    Args:
        params: Tool parameters.
        context: Tool handler context.
        memory_service: The memory service.

    Returns:
        Operation result.
    """
    operation = params["operation"]
    repository = params["repository"]
    branch = params.get("branch", "main")

    logger.debug(
        "memory-optimizer handler",
        operation=operation,
        repository=repository,
    )

    snapshot_service = memory_service.snapshot

    try:
        if operation == "analyze":
            return await _handle_analyze(params, memory_service, repository, branch)

        elif operation == "optimize":
            return await _handle_optimize(
                params, memory_service, snapshot_service, repository, branch
            )

        elif operation == "rollback":
            snapshot_id = params.get("snapshotId")

            if not snapshot_id:
                return {
                    "success": False,
                    "error": "snapshotId is required for rollback operation",
                }

            result = await snapshot_service.rollback_to_snapshot(snapshot_id)
            return result

        elif operation == "list-snapshots":
            snapshots = await snapshot_service.list_snapshots(repository, branch)

            return {
                "success": True,
                "operation": "list-snapshots",
                "snapshots": [s.model_dump(mode="json") for s in snapshots],
                "count": len(snapshots),
            }

        elif operation == "create-snapshot":
            description = params.get(
                "description", f"Manual snapshot for {repository}:{branch}"
            )

            snapshot = await snapshot_service.create_snapshot(
                repository,
                branch,
                description=description,
                metadata={"operation": "manual"},
            )

            return {
                "success": True,
                "operation": "create-snapshot",
                "snapshot": snapshot.model_dump(mode="json"),
            }

        else:
            return {
                "success": False,
                "error": f"Unknown operation: {operation}",
            }

    except Exception as e:
        logger.error(
            "Memory optimizer handler error",
            operation=operation,
            error=str(e),
        )
        return {
            "success": False,
            "error": str(e),
        }


async def _handle_analyze(
    params: Dict[str, Any],
    memory_service: MemoryService,
    repository: str,
    branch: str,
) -> Dict[str, Any]:
    """Handle the analyze operation, including caching and optional sampling."""
    enable_sampling = params.get(
        "enableMCPSampling", settings.optimizer_enable_mcp_sampling
    )
    sampling_strategy = params.get(
        "samplingStrategy", settings.optimizer_default_sampling_strategy
    )

    result = await _analyze_memory_bank(memory_service, repository, branch)

    # Deterministic-ish analysis ID derived from the entity count (no
    # Date.now()/random which may be unavailable in the sandbox).
    counts = result.get("statistics", {}).get("counts", {})
    entity_count = sum(int(v) for v in counts.values()) if counts else 0
    analysis_id = _next_analysis_id(repository, branch, entity_count)

    # Best-effort context sampling; failures never block analysis.
    if enable_sampling:
        try:
            sampler = MemorySamplingManager(memory_service)
            sample = await sampler.sample_memory_context(
                repository,
                branch,
                strategy=sampling_strategy,
                sample_size=settings.optimizer_default_sample_size,
            )
            result["sample"] = sample
        except Exception as exc:
            logger.warning(
                "Memory sampling failed; continuing without sample",
                error=str(exc),
            )
            result["sample"] = None

    result["analysisId"] = analysis_id

    # Cache the analysis so a later optimize call can reuse it.
    _cache_analysis(
        analysis_id,
        {
            "repository": repository,
            "branch": branch,
            "analysis": result,
        },
    )

    return {
        "success": True,
        "operation": "analyze",
        "analysisId": analysis_id,
        **result,
    }


async def _handle_optimize(
    params: Dict[str, Any],
    memory_service: MemoryService,
    snapshot_service: Any,
    repository: str,
    branch: str,
) -> Dict[str, Any]:
    """Handle the optimize operation with TS-parity options."""
    strategy = params.get("strategy", settings.optimizer_default_strategy)
    dry_run = params.get("dryRun", True)
    confirm = params.get("confirm", False)
    max_deletions = params.get("maxDeletions")
    focus_areas = params.get("focusAreas") or []
    preserve_categories = params.get("preserveCategories") or []
    analysis_id = params.get("analysisId")
    snapshot_failure_policy = params.get(
        "snapshotFailurePolicy", settings.optimizer_snapshot_failure_policy
    )

    warnings: List[str] = []

    # Reuse a cached analysis when a valid analysisId is supplied.
    cached_analysis: Optional[Dict[str, Any]] = None
    if analysis_id:
        cached = _ANALYSIS_CACHE.get(analysis_id)
        if cached:
            cached_analysis = cached.get("analysis")
        else:
            warnings.append(
                f"analysisId '{analysis_id}' not found in cache; "
                "recomputing analysis"
            )
    if cached_analysis is None:
        cached_analysis = await _analyze_memory_bank(
            memory_service, repository, branch
        )

    # A non-dry-run change requires explicit confirmation.
    if not dry_run and not confirm:
        return {
            "success": False,
            "operation": "optimize",
            "message": (
                "Confirmation required for actual optimization. Set "
                "confirm=true to proceed."
            ),
            "warnings": warnings
            + ["This operation will make permanent changes to your memory graph"],
            "dry_run": dry_run,
            "strategy": strategy,
            "analysisId": analysis_id,
        }

    # Create a pre-optimization snapshot for real runs (honor failure policy).
    snapshot_id: Optional[str] = None
    if not dry_run:
        try:
            snapshot = await snapshot_service.create_snapshot(
                repository,
                branch,
                description=f"Pre-optimization snapshot (strategy: {strategy})",
                metadata={"operation": "optimize", "strategy": strategy},
            )
            snapshot_id = snapshot.id
        except Exception as exc:
            if snapshot_failure_policy == "abort":
                logger.error("Snapshot creation failed; aborting", error=str(exc))
                return {
                    "success": False,
                    "operation": "optimize",
                    "error": f"Snapshot creation failed: {exc}",
                    "snapshotFailurePolicy": snapshot_failure_policy,
                }
            elif snapshot_failure_policy == "warn":
                logger.warning(
                    "Snapshot creation failed; continuing", error=str(exc)
                )
                warnings.append(f"Snapshot creation failed: {exc}")
            else:  # continue silently
                logger.info(
                    "Snapshot creation failed; continuing silently",
                    error=str(exc),
                )

    result = await _optimize_memory_bank(
        memory_service,
        repository,
        branch,
        strategy,
        dry_run=dry_run,
        max_deletions=max_deletions,
        focus_areas=focus_areas,
        preserve_categories=preserve_categories,
    )

    if result.get("errors"):
        warnings.append("Some optimization actions failed; see errors")

    return {
        "success": True,
        "operation": "optimize",
        "strategy": strategy,
        "dry_run": dry_run,
        "analysisId": analysis_id,
        "snapshot_id": snapshot_id,
        "focus_areas": focus_areas,
        "preserve_categories": preserve_categories,
        "max_deletions": max_deletions,
        "snapshotFailurePolicy": snapshot_failure_policy,
        "warnings": warnings,
        **result,
    }


async def _analyze_memory_bank(
    memory_service: MemoryService,
    repository: str,
    branch: str,
) -> Dict[str, Any]:
    """Analyze the memory bank for optimization opportunities.

    Args:
        memory_service: The memory service.
        repository: The repository name.
        branch: The branch name.

    Returns:
        Analysis results.
    """
    graph_analysis = await memory_service.graph_analysis
    entity_service = await memory_service.entity

    # Get statistics
    stats = await memory_service.get_statistics(repository, branch)

    # Detect issues
    cycles = await graph_analysis.detect_cycles(repository, branch)
    islands = await graph_analysis.detect_islands(repository, branch)

    # Get components by status
    all_components = await entity_service.get_all_components(repository, branch)
    deprecated_count = sum(
        1 for c in all_components
        if c.status and c.status.value == "deprecated"
    )

    # Build recommendations
    recommendations = []

    if cycles:
        recommendations.append({
            "type": "circular_dependency",
            "severity": "high",
            "message": f"Found {len(cycles)} circular dependency groups",
            "affected_count": sum(len(c) for c in cycles),
        })

    if len(islands) > 1:
        recommendations.append({
            "type": "disconnected_components",
            "severity": "medium",
            "message": f"Found {len(islands)} disconnected component groups",
            "affected_count": sum(len(i) for i in islands),
        })

    if deprecated_count > 0:
        recommendations.append({
            "type": "deprecated_components",
            "severity": "low",
            "message": (
                f"Found {deprecated_count} deprecated components that could "
                "be removed"
            ),
            "affected_count": deprecated_count,
        })

    # Calculate health score (0-100)
    health_score = 100
    if cycles:
        health_score -= min(30, len(cycles) * 10)
    if len(islands) > 1:
        health_score -= min(20, (len(islands) - 1) * 5)
    if deprecated_count > 0:
        health_score -= min(10, deprecated_count)
    health_score = max(0, health_score)

    return {
        "statistics": stats,
        "issues": {
            "cycles": len(cycles),
            "islands": len(islands),
            "deprecated": deprecated_count,
        },
        "recommendations": recommendations,
        "health_score": health_score,
    }


async def _optimize_memory_bank(
    memory_service: MemoryService,
    repository: str,
    branch: str,
    strategy: str,
    dry_run: bool = False,
    max_deletions: Optional[int] = None,
    focus_areas: Optional[List[str]] = None,
    preserve_categories: Optional[List[str]] = None,
) -> Dict[str, Any]:
    """Optimize the memory bank based on strategy and TS-parity options.

    Args:
        memory_service: The memory service.
        repository: The repository name.
        branch: The branch name.
        strategy: Optimization strategy (conservative, balanced, aggressive).
        dry_run: If True, report would-be actions without deleting.
        max_deletions: Optional cap on the number of deletions.
        focus_areas: Only perform categories tied to these focus areas.
            Empty/None means all categories are eligible.
        preserve_categories: Skip deleting entities whose category/tag matches.

    Returns:
        Optimization results.
    """
    entity_service = await memory_service.entity

    focus = set(focus_areas or [])
    preserve = set(preserve_categories or [])

    # When no focus areas are provided, every category is eligible.
    deprecated_enabled = not focus or bool(focus & _DEPRECATED_FOCUS)
    orphan_tags_enabled = not focus or bool(focus & _ORPHAN_TAG_FOCUS)

    actions_taken: List[Dict[str, Any]] = []
    would_delete: List[Dict[str, Any]] = []
    errors: List[Dict[str, Any]] = []
    skipped: List[Dict[str, Any]] = []

    def _remaining_budget() -> Optional[int]:
        if max_deletions is None:
            return None
        return max_deletions - (len(actions_taken) + len(would_delete))

    def _budget_exhausted() -> bool:
        rem = _remaining_budget()
        return rem is not None and rem <= 0

    async def _delete_component(component: Any, reason: str) -> None:
        entry = {
            "action": reason,
            "entity_type": "component",
            "entity_id": component.id,
            "name": component.name,
        }
        if dry_run:
            would_delete.append(entry)
            return
        try:
            await entity_service.delete_component(
                repository, component.id, branch
            )
            actions_taken.append(entry)
        except Exception as exc:
            errors.append({"entity_id": component.id, "error": str(exc)})

    # Deprecated-component removal (stale/redundancy/dependency focus).
    if deprecated_enabled:
        all_components = await entity_service.get_all_components(
            repository, branch
        )
        for component in all_components:
            if _budget_exhausted():
                break
            if not (component.status and component.status.value == "deprecated"):
                continue

            # preserveCategories: skip components whose kind is preserved.
            if component.kind and component.kind in preserve:
                skipped.append({
                    "entity_id": component.id,
                    "reason": "preserved_category",
                    "category": component.kind,
                })
                continue

            # Conservative only deletes deprecated with no dependents.
            if strategy == "conservative":
                container = await memory_service.get_service_container()
                comp_repo = await container.get_component_repository()
                dependents = await comp_repo.get_dependents(
                    repository, component.id, branch
                )
                if dependents:
                    skipped.append({
                        "entity_id": component.id,
                        "reason": "has_dependents",
                    })
                    continue

            await _delete_component(component, "delete_deprecated")

    # Orphaned-tag removal (orphan/tag/relationship focus), skips conservative.
    if orphan_tags_enabled and strategy in ("balanced", "aggressive"):
        container = await memory_service.get_service_container()
        tag_repo = await container.get_tag_repository()
        tag_stats = await tag_repo.get_tag_usage_stats(repository, branch)

        for tag_stat in tag_stats:
            if _budget_exhausted():
                break
            if tag_stat["usage_count"] != 0:
                continue

            category = tag_stat.get("category")
            if category and category in preserve:
                skipped.append({
                    "entity_id": tag_stat["id"],
                    "reason": "preserved_category",
                    "category": category,
                })
                continue

            entry = {
                "action": "delete_orphaned_tag",
                "entity_type": "tag",
                "entity_id": tag_stat["id"],
                "name": tag_stat["name"],
            }
            if dry_run:
                would_delete.append(entry)
                continue
            try:
                await entity_service.delete_tag(
                    repository, tag_stat["id"], branch
                )
                actions_taken.append(entry)
            except Exception as exc:
                errors.append({"entity_id": tag_stat["id"], "error": str(exc)})

    return {
        "actions_taken": actions_taken,
        "action_count": len(actions_taken),
        "would_delete": would_delete,
        "would_delete_count": len(would_delete),
        "skipped": skipped,
        "skipped_count": len(skipped),
        "errors": errors if errors else None,
        "error_count": len(errors),
    }
