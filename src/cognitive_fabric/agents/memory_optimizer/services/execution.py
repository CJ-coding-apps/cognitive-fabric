"""Optimization execution service for memory optimizer agent."""

from typing import Any, Dict, List, Optional

import structlog

from cognitive_fabric.services.memory_service import MemoryService
from cognitive_fabric.services.snapshot_service import SnapshotService
from cognitive_fabric.types.optimization import (
    AgentOptimizationAction as OptimizationAction,
)
from cognitive_fabric.types.optimization import (
    AgentOptimizationPlan as OptimizationPlan,
)
from cognitive_fabric.types.optimization import (
    ExecutionResult,
)

logger = structlog.get_logger(__name__)


class OptimizationExecutionService:
    """Service for executing optimization plans."""

    def __init__(
        self,
        memory_service: MemoryService,
        snapshot_service: SnapshotService,
    ) -> None:
        """Initialize the execution service.

        Args:
            memory_service: The memory service instance.
            snapshot_service: The snapshot service instance.
        """
        self._memory_service = memory_service
        self._snapshot_service = snapshot_service

    async def execute_plan(
        self,
        plan: OptimizationPlan,
        dry_run: bool = False,
        create_snapshot: bool = True,
    ) -> ExecutionResult:
        """Execute an optimization plan.

        Args:
            plan: The optimization plan to execute.
            dry_run: If True, simulate execution without making changes.
            create_snapshot: Whether to create a snapshot before execution.

        Returns:
            The execution result.
        """
        logger.info(
            "Executing optimization plan",
            plan_id=plan.id,
            repository=plan.repository,
            branch=plan.branch,
            action_count=len(plan.actions),
            dry_run=dry_run,
        )

        snapshot_id: Optional[str] = None
        executed_actions: List[Dict[str, Any]] = []
        failed_actions: List[Dict[str, Any]] = []
        skipped_actions: List[Dict[str, Any]] = []

        # Create snapshot before execution (unless dry run)
        if create_snapshot and not dry_run:
            try:
                snapshot_id = await self._snapshot_service.create_snapshot(
                    plan.repository,
                    plan.branch,
                    f"Pre-optimization snapshot for plan {plan.id}",
                )
                logger.info("Created pre-execution snapshot", snapshot_id=snapshot_id)
            except Exception as e:
                logger.error("Failed to create snapshot", error=str(e))
                # Continue without snapshot if it fails

        # Execute each action
        for action in plan.actions:
            try:
                if dry_run:
                    # Simulate execution
                    executed_actions.append({
                        "action": action.model_dump(mode="json"),
                        "status": "simulated",
                        "message": "Dry run - no changes made",
                    })
                else:
                    # Actually execute
                    result = await self._execute_action(
                        plan.repository,
                        plan.branch,
                        action,
                    )

                    if result["success"]:
                        executed_actions.append({
                            "action": action.model_dump(mode="json"),
                            "status": "success",
                            "message": result.get("message", "Action completed"),
                        })
                    else:
                        failed_actions.append({
                            "action": action.model_dump(mode="json"),
                            "status": "failed",
                            "error": result.get("error", "Unknown error"),
                        })

            except Exception as e:
                logger.error(
                    "Action execution failed",
                    action_type=action.action_type,
                    entity_id=action.entity_id,
                    error=str(e),
                )
                failed_actions.append({
                    "action": action.model_dump(mode="json"),
                    "status": "error",
                    "error": str(e),
                })

        return ExecutionResult(
            plan_id=plan.id,
            repository=plan.repository,
            branch=plan.branch,
            snapshot_id=snapshot_id,
            dry_run=dry_run,
            executed=executed_actions,
            failed=failed_actions,
            skipped=skipped_actions,
            summary={
                "total_actions": len(plan.actions),
                "executed": len(executed_actions),
                "failed": len(failed_actions),
                "skipped": len(skipped_actions),
            },
        )

    async def _execute_action(
        self,
        repository: str,
        branch: str,
        action: OptimizationAction,
    ) -> Dict[str, Any]:
        """Execute a single optimization action.

        Args:
            repository: The repository name.
            branch: The branch name.
            action: The action to execute.

        Returns:
            Action result dictionary.
        """
        if action.action_type == "delete":
            return await self._execute_delete(repository, branch, action)
        elif action.action_type == "update":
            return await self._execute_update(repository, branch, action)
        elif action.action_type == "merge":
            return await self._execute_merge(repository, branch, action)
        else:
            return {
                "success": False,
                "error": f"Unknown action type: {action.action_type}",
            }

    async def _execute_delete(
        self,
        repository: str,
        branch: str,
        action: OptimizationAction,
    ) -> Dict[str, Any]:
        """Execute a delete action.

        Args:
            repository: The repository name.
            branch: The branch name.
            action: The delete action.

        Returns:
            Action result dictionary.
        """
        entity_service = await self._memory_service.entity

        try:
            if action.entity_type == "component":
                await entity_service.delete_component(
                    repository, action.entity_id, branch
                )
            elif action.entity_type == "tag":
                await entity_service.delete_tag(
                    repository, action.entity_id, branch
                )
            elif action.entity_type == "rule":
                await entity_service.delete_rule(
                    repository, action.entity_id, branch
                )
            elif action.entity_type == "decision":
                await entity_service.delete_decision(
                    repository, action.entity_id, branch
                )
            elif action.entity_type == "context":
                await entity_service.delete_context(
                    repository, action.entity_id, branch
                )
            else:
                return {
                    "success": False,
                    "error": f"Unknown entity type for delete: {action.entity_type}",
                }

            logger.info(
                "Deleted entity",
                entity_type=action.entity_type,
                entity_id=action.entity_id,
                reason=action.reason,
            )

            return {
                "success": True,
                "message": f"Deleted {action.entity_type} {action.entity_id}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def _execute_update(
        self,
        repository: str,
        branch: str,
        action: OptimizationAction,
    ) -> Dict[str, Any]:
        """Execute an update action.

        Args:
            repository: The repository name.
            branch: The branch name.
            action: The update action.

        Returns:
            Action result dictionary.
        """
        # Update actions require additional data in the action
        # For now, we mainly support status updates
        entity_service = await self._memory_service.entity

        try:
            updates = action.updates or {}

            if action.entity_type == "component":
                await entity_service.update_component(
                    repository, action.entity_id, updates, branch
                )
            elif action.entity_type == "rule":
                await entity_service.update_rule(
                    repository, action.entity_id, updates, branch
                )
            elif action.entity_type == "decision":
                await entity_service.update_decision(
                    repository, action.entity_id, updates, branch
                )
            else:
                return {
                    "success": False,
                    "error": f"Updates not supported for: {action.entity_type}",
                }

            logger.info(
                "Updated entity",
                entity_type=action.entity_type,
                entity_id=action.entity_id,
                updates=updates,
            )

            return {
                "success": True,
                "message": f"Updated {action.entity_type} {action.entity_id}",
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
            }

    async def _execute_merge(
        self,
        repository: str,
        branch: str,
        action: OptimizationAction,
    ) -> Dict[str, Any]:
        """Execute a merge action.

        Args:
            repository: The repository name.
            branch: The branch name.
            action: The merge action.

        Returns:
            Action result dictionary.
        """
        # Merge is a complex operation that combines entities
        # This is a placeholder for future implementation
        return {
            "success": False,
            "error": "Merge actions not yet implemented",
        }

    async def rollback(
        self,
        repository: str,
        snapshot_id: str,
        branch: str = "main",
    ) -> Dict[str, Any]:
        """Rollback to a snapshot.

        Args:
            repository: The repository name.
            snapshot_id: The snapshot ID to rollback to.
            branch: The branch name.

        Returns:
            Rollback result dictionary.
        """
        logger.info(
            "Rolling back to snapshot",
            repository=repository,
            snapshot_id=snapshot_id,
            branch=branch,
        )

        try:
            result = await self._snapshot_service.restore_snapshot(
                repository, snapshot_id, branch
            )

            return {
                "success": True,
                "message": f"Rolled back to snapshot {snapshot_id}",
                "restored_entities": result.get("restored_entities", 0),
            }

        except Exception as e:
            logger.error("Rollback failed", error=str(e))
            return {
                "success": False,
                "error": str(e),
            }

    async def list_snapshots(
        self,
        repository: str,
        branch: str = "main",
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """List available snapshots.

        Args:
            repository: The repository name.
            branch: The branch name.
            limit: Maximum number of snapshots to return.

        Returns:
            List of snapshot metadata.
        """
        return await self._snapshot_service.list_snapshots(
            repository, branch, limit
        )
