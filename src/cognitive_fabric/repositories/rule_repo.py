"""Rule repository for Rule entity operations."""

from typing import Any, Optional

from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.types.entities import Rule, RuleInput, RuleStatus


class RuleRepository(BaseRepository):
    """Repository for Rule entity operations."""

    async def find_by_id(
        self,
        repository: str,
        rule_id: str,
        branch: str = "main",
    ) -> Optional[Rule]:
        """Find a rule by ID.

        Args:
            repository: The repository name.
            rule_id: The rule ID.
            branch: The branch name.

        Returns:
            The Rule if found, None otherwise.
        """
        graph_id = self.create_graph_unique_id(repository, branch, rule_id)

        query = """
        MATCH (r:Rule {graph_unique_id: $graph_id})
        RETURN r.graph_unique_id AS graph_unique_id,
               r.id AS id, r.name AS name, r.created AS created,
               r.triggers AS triggers, r.content AS content,
               r.status AS status, r.category AS category,
               r.examples AS examples,
               r.repository AS repository, r.branch AS branch,
               r.created_at AS created_at, r.updated_at AS updated_at
        LIMIT 1
        """

        row = self.fetch_one(query, {"graph_id": graph_id})

        if row is None:
            return None

        return self._row_to_rule(row, repository, branch)

    async def get_all_rules(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[Rule]:
        """Get all rules.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all rules.
        """
        query = """
        MATCH (r:Rule)
        WHERE r.repository = $repository AND r.branch = $branch
        RETURN r.graph_unique_id AS graph_unique_id,
               r.id AS id, r.name AS name, r.created AS created,
               r.triggers AS triggers, r.content AS content,
               r.status AS status, r.category AS category,
               r.examples AS examples,
               r.repository AS repository, r.branch AS branch,
               r.created_at AS created_at, r.updated_at AS updated_at
        ORDER BY r.name
        """

        rows = self.fetch_all(query, {"repository": repository, "branch": branch})
        return [self._row_to_rule(row, repository, branch) for row in rows]

    async def get_active_rules(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[Rule]:
        """Get all active rules.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of active rules.
        """
        query = """
        MATCH (r:Rule)
        WHERE r.repository = $repository
          AND r.branch = $branch
          AND r.status = 'active'
        RETURN r.graph_unique_id AS graph_unique_id,
               r.id AS id, r.name AS name, r.created AS created,
               r.triggers AS triggers, r.content AS content,
               r.status AS status, r.category AS category,
               r.examples AS examples,
               r.repository AS repository, r.branch AS branch,
               r.created_at AS created_at, r.updated_at AS updated_at
        ORDER BY r.name
        """

        rows = self.fetch_all(query, {"repository": repository, "branch": branch})
        return [self._row_to_rule(row, repository, branch) for row in rows]

    async def get_rules_by_category(
        self,
        repository: str,
        category: str,
        branch: str = "main",
    ) -> list[Rule]:
        """Get rules by category.

        Args:
            repository: The repository name.
            category: The rule category.
            branch: The branch name.

        Returns:
            List of rules in the category.
        """
        query = """
        MATCH (r:Rule)
        WHERE r.repository = $repository
          AND r.branch = $branch
          AND r.category = $category
        RETURN r.graph_unique_id AS graph_unique_id,
               r.id AS id, r.name AS name, r.created AS created,
               r.triggers AS triggers, r.content AS content,
               r.status AS status, r.category AS category,
               r.examples AS examples,
               r.repository AS repository, r.branch AS branch,
               r.created_at AS created_at, r.updated_at AS updated_at
        ORDER BY r.name
        """

        rows = self.fetch_all(query, {
            "repository": repository,
            "branch": branch,
            "category": category,
        })
        return [self._row_to_rule(row, repository, branch) for row in rows]

    async def upsert_rule(
        self,
        repository: str,
        input_data: RuleInput,
    ) -> Rule:
        """Create or update a rule.

        Args:
            repository: The repository name.
            input_data: The rule input data.

        Returns:
            The upserted Rule.
        """
        branch = input_data.branch or "main"
        graph_id = self.create_graph_unique_id(repository, branch, input_data.id)
        now = self.get_current_timestamp()

        query = """
        MERGE (r:Rule {graph_unique_id: $graph_id})
        ON CREATE SET
            r.id = $id,
            r.name = $name,
            r.created = $created,
            r.triggers = $triggers,
            r.content = $content,
            r.status = $status,
            r.category = $category,
            r.examples = $examples,
            r.repository = $repository,
            r.branch = $branch,
            r.created_at = $now,
            r.updated_at = $now
        ON MATCH SET
            r.name = $name,
            r.triggers = $triggers,
            r.content = $content,
            r.status = $status,
            r.category = $category,
            r.examples = $examples,
            r.updated_at = $now
        RETURN r.graph_unique_id AS graph_unique_id
        """

        params = {
            "graph_id": graph_id,
            "id": input_data.id,
            "name": input_data.name,
            "created": input_data.created or now.date().isoformat(),
            "triggers": input_data.triggers or [],
            "content": input_data.content or "",
            "status": (input_data.status or RuleStatus.ACTIVE).value,
            "category": input_data.category or "",
            "examples": input_data.examples or [],
            "repository": repository,
            "branch": branch,
            "now": now,
        }

        self.execute_query(query, params)

        return Rule(
            id=input_data.id,
            repository=repository,
            branch=branch,
            name=input_data.name,
            created=input_data.created or now.date().isoformat(),
            triggers=input_data.triggers,
            content=input_data.content,
            status=input_data.status or RuleStatus.ACTIVE,
            category=input_data.category,
            examples=input_data.examples,
            created_at=now,
            updated_at=now,
        )

    async def update_rule_status(
        self,
        repository: str,
        rule_id: str,
        branch: str,
        status: RuleStatus,
    ) -> Optional[Rule]:
        """Update a rule's status.

        Args:
            repository: The repository name.
            rule_id: The rule ID.
            branch: The branch name.
            status: The new status.

        Returns:
            The updated Rule, or None if not found.
        """
        graph_id = self.create_graph_unique_id(repository, branch, rule_id)
        now = self.get_current_timestamp()

        query = """
        MATCH (r:Rule {graph_unique_id: $graph_id})
        SET r.status = $status, r.updated_at = $now
        RETURN r.graph_unique_id AS graph_unique_id,
               r.id AS id, r.name AS name, r.created AS created,
               r.triggers AS triggers, r.content AS content,
               r.status AS status, r.category AS category,
               r.examples AS examples,
               r.repository AS repository, r.branch AS branch,
               r.created_at AS created_at, r.updated_at AS updated_at
        """

        row = self.fetch_one(query, {
            "graph_id": graph_id,
            "status": status.value,
            "now": now,
        })

        if row is None:
            return None

        return self._row_to_rule(row, repository, branch)

    async def delete_rule(
        self,
        repository: str,
        rule_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a rule and its relationships.

        Args:
            repository: The repository name.
            rule_id: The rule ID.
            branch: The branch name.

        Returns:
            True if deleted, False if not found.
        """
        graph_id = self.create_graph_unique_id(repository, branch, rule_id)

        query = """
        MATCH (r:Rule {graph_unique_id: $graph_id})
        DETACH DELETE r
        RETURN count(*) AS deleted
        """

        result = self.fetch_one(query, {"graph_id": graph_id})
        return result is not None and result.get("deleted", 0) > 0

    async def get_rules_governing_component(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> list[Rule]:
        """Get rules that govern a specific component.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            List of rules governing the component.
        """
        component_graph_id = self.create_graph_unique_id(
            repository, branch, component_id
        )

        query = """
        MATCH (r:Rule)-[:GOVERNS]->(c:Component {graph_unique_id: $component_id})
        WHERE r.branch = $branch
        RETURN r.graph_unique_id AS graph_unique_id,
               r.id AS id, r.name AS name, r.created AS created,
               r.triggers AS triggers, r.content AS content,
               r.status AS status, r.category AS category,
               r.examples AS examples,
               r.repository AS repository, r.branch AS branch,
               r.created_at AS created_at, r.updated_at AS updated_at
        ORDER BY r.name
        """

        rows = self.fetch_all(query, {
            "component_id": component_graph_id,
            "branch": branch,
        })
        return [self._row_to_rule(row, repository, branch) for row in rows]

    async def create_governs_relationship(
        self,
        repository: str,
        rule_id: str,
        component_id: str,
        branch: str = "main",
    ) -> bool:
        """Create a GOVERNS relationship between a rule and a component.

        Args:
            repository: The repository name.
            rule_id: The rule ID.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            True if created, False otherwise.
        """
        rule_graph_id = self.create_graph_unique_id(
            repository, branch, rule_id
        )
        component_graph_id = self.create_graph_unique_id(
            repository, branch, component_id
        )

        query = """
        MATCH (r:Rule {graph_unique_id: $rule_id})
        MATCH (c:Component {graph_unique_id: $component_id})
        MERGE (r)-[:GOVERNS]->(c)
        RETURN count(*) AS created
        """

        result = self.fetch_one(query, {
            "rule_id": rule_graph_id,
            "component_id": component_graph_id,
        })

        return result is not None and result.get("created", 0) > 0

    async def find_rules_by_trigger(
        self,
        repository: str,
        trigger: str,
        branch: str = "main",
    ) -> list[Rule]:
        """Find rules that have a specific trigger.

        Args:
            repository: The repository name.
            trigger: The trigger to search for.
            branch: The branch name.

        Returns:
            List of rules with the trigger.
        """
        query = """
        MATCH (r:Rule)
        WHERE r.repository = $repository
          AND r.branch = $branch
          AND $trigger IN r.triggers
        RETURN r.graph_unique_id AS graph_unique_id,
               r.id AS id, r.name AS name, r.created AS created,
               r.triggers AS triggers, r.content AS content,
               r.status AS status, r.category AS category,
               r.examples AS examples,
               r.repository AS repository, r.branch AS branch,
               r.created_at AS created_at, r.updated_at AS updated_at
        ORDER BY r.name
        """

        rows = self.fetch_all(query, {
            "repository": repository,
            "branch": branch,
            "trigger": trigger,
        })
        return [self._row_to_rule(row, repository, branch) for row in rows]

    def _row_to_rule(
        self,
        row: dict[str, Any],
        repository: str,
        branch: str,
    ) -> Rule:
        """Convert a database row to a Rule.

        Args:
            row: The database row.
            repository: The repository name.
            branch: The branch name.

        Returns:
            The Rule instance.
        """
        status_str = row.get("status")
        status = None
        if status_str:
            try:
                status = RuleStatus(status_str)
            except ValueError:
                status = RuleStatus.ACTIVE

        return Rule(
            id=row["id"],
            repository=repository,
            branch=branch,
            name=row["name"],
            created=row.get("created"),
            triggers=row.get("triggers"),
            content=row.get("content"),
            status=status,
            category=row.get("category"),
            examples=row.get("examples"),
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )
