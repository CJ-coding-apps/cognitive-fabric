"""Tag repository for Tag entity operations."""

from typing import Any, Optional

from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.types.entities import Tag, TagInput
from cognitive_fabric.utils.security import validate_label


class TagRepository(BaseRepository):
    """Repository for Tag entity operations."""

    async def find_by_id(
        self,
        repository: str,
        tag_id: str,
        branch: str = "main",
    ) -> Optional[Tag]:
        """Find a tag by ID.

        Args:
            repository: The repository name.
            tag_id: The tag ID.
            branch: The branch name.

        Returns:
            The Tag if found, None otherwise.
        """
        query = """
        MATCH (t:Tag {id: $id})
        WHERE t.repository = $repository AND t.branch = $branch
        RETURN t.id AS id, t.name AS name, t.color AS color,
               t.description AS description, t.category AS category,
               t.repository AS repository, t.branch AS branch,
               t.created_at AS created_at, t.updated_at AS updated_at
        LIMIT 1
        """

        row = self.fetch_one(query, {
            "id": tag_id,
            "repository": repository,
            "branch": branch,
        })

        if row is None:
            return None

        return self._row_to_tag(row, repository, branch)

    async def find_by_name(
        self,
        repository: str,
        name: str,
        branch: str = "main",
    ) -> Optional[Tag]:
        """Find a tag by name.

        Args:
            repository: The repository name.
            name: The tag name.
            branch: The branch name.

        Returns:
            The Tag if found, None otherwise.
        """
        query = """
        MATCH (t:Tag)
        WHERE t.name = $name
          AND t.repository = $repository
          AND t.branch = $branch
        RETURN t.id AS id, t.name AS name, t.color AS color,
               t.description AS description, t.category AS category,
               t.repository AS repository, t.branch AS branch,
               t.created_at AS created_at, t.updated_at AS updated_at
        LIMIT 1
        """

        row = self.fetch_one(query, {
            "name": name,
            "repository": repository,
            "branch": branch,
        })

        if row is None:
            return None

        return self._row_to_tag(row, repository, branch)

    async def get_all_tags(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[Tag]:
        """Get all tags.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all tags.
        """
        query = """
        MATCH (t:Tag)
        WHERE t.repository = $repository AND t.branch = $branch
        RETURN t.id AS id, t.name AS name, t.color AS color,
               t.description AS description, t.category AS category,
               t.repository AS repository, t.branch AS branch,
               t.created_at AS created_at, t.updated_at AS updated_at
        ORDER BY t.category, t.name
        """

        rows = self.fetch_all(query, {"repository": repository, "branch": branch})
        return [self._row_to_tag(row, repository, branch) for row in rows]

    async def get_tags_by_category(
        self,
        repository: str,
        category: str,
        branch: str = "main",
    ) -> list[Tag]:
        """Get tags by category.

        Args:
            repository: The repository name.
            category: The tag category.
            branch: The branch name.

        Returns:
            List of tags in the category.
        """
        query = """
        MATCH (t:Tag)
        WHERE t.repository = $repository
          AND t.branch = $branch
          AND t.category = $category
        RETURN t.id AS id, t.name AS name, t.color AS color,
               t.description AS description, t.category AS category,
               t.repository AS repository, t.branch AS branch,
               t.created_at AS created_at, t.updated_at AS updated_at
        ORDER BY t.name
        """

        rows = self.fetch_all(query, {
            "repository": repository,
            "branch": branch,
            "category": category,
        })
        return [self._row_to_tag(row, repository, branch) for row in rows]

    async def upsert_tag(
        self,
        repository: str,
        input_data: TagInput,
    ) -> Tag:
        """Create or update a tag.

        Args:
            repository: The repository name.
            input_data: The tag input data.

        Returns:
            The upserted Tag.
        """
        branch = input_data.branch or "main"
        now = self.get_current_timestamp()

        query = """
        MERGE (t:Tag {id: $id})
        ON CREATE SET
            t.name = $name,
            t.color = $color,
            t.description = $description,
            t.category = $category,
            t.repository = $repository,
            t.branch = $branch,
            t.created_at = $now,
            t.updated_at = $now
        ON MATCH SET
            t.name = $name,
            t.color = $color,
            t.description = $description,
            t.category = $category,
            t.repository = $repository,
            t.branch = $branch,
            t.updated_at = $now
        RETURN t.id AS id
        """

        params = {
            "id": input_data.id,
            "name": input_data.name,
            "color": input_data.color or "",
            "description": input_data.description or "",
            "category": input_data.category or "",
            "repository": repository,
            "branch": branch,
            "now": now,
        }

        self.execute_query(query, params)

        return Tag(
            id=input_data.id,
            repository=repository,
            branch=branch,
            name=input_data.name,
            color=input_data.color,
            description=input_data.description,
            category=input_data.category,
            created_at=now,
            updated_at=now,
        )

    async def delete_tag(
        self,
        repository: str,
        tag_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a tag and its relationships.

        Args:
            repository: The repository name.
            tag_id: The tag ID.
            branch: The branch name.

        Returns:
            True if deleted, False if not found.
        """
        query = """
        MATCH (t:Tag {id: $id})
        WHERE t.repository = $repository AND t.branch = $branch
        DETACH DELETE t
        RETURN count(*) AS deleted
        """

        result = self.fetch_one(query, {
            "id": tag_id,
            "repository": repository,
            "branch": branch,
        })
        return result is not None and result.get("deleted", 0) > 0

    async def get_items_with_tag(
        self,
        repository: str,
        tag_id: str,
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Get all items tagged with a specific tag.

        Args:
            repository: The repository name.
            tag_id: The tag ID.
            branch: The branch name.

        Returns:
            List of items with the tag (includes id, name, and type).
        """
        query = """
        MATCH (item)-[:TAGGED_WITH]->(t:Tag {id: $tag_id})
        WHERE t.repository = $repository AND t.branch = $branch
        RETURN item.id AS id,
               item.name AS name,
               labels(item)[0] AS type
        ORDER BY type, name
        """

        rows = self.fetch_all(query, {
            "tag_id": tag_id,
            "repository": repository,
            "branch": branch,
        })

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "type": row["type"],
            }
            for row in rows
        ]

    async def get_tags_for_item(
        self,
        repository: str,
        item_id: str,
        item_type: str,
        branch: str = "main",
    ) -> list[Tag]:
        """Get all tags for an item.

        Args:
            repository: The repository name.
            item_id: The item ID.
            item_type: The item type (Component, Decision, etc.).
            branch: The branch name.

        Returns:
            List of tags for the item.
        """
        # Build graph_unique_id for the item if needed
        if item_type in ["Component", "Decision", "Rule", "Context"]:
            item_graph_id = self.create_graph_unique_id(repository, branch, item_id)
            query = f"""
            MATCH (item:{item_type} {{graph_unique_id: $item_id}})
                  -[:TAGGED_WITH]->
                  (t:Tag)
            WHERE t.repository = $repository AND t.branch = $branch
            RETURN t.id AS id, t.name AS name, t.color AS color,
                   t.description AS description, t.category AS category,
                   t.repository AS repository, t.branch AS branch,
                   t.created_at AS created_at, t.updated_at AS updated_at
            ORDER BY t.category, t.name
            """
            params = {
                "item_id": item_graph_id,
                "repository": repository,
                "branch": branch,
            }
        else:
            query = f"""
            MATCH (item:{item_type} {{id: $item_id}})-[:TAGGED_WITH]->(t:Tag)
            WHERE t.repository = $repository AND t.branch = $branch
            RETURN t.id AS id, t.name AS name, t.color AS color,
                   t.description AS description, t.category AS category,
                   t.repository AS repository, t.branch AS branch,
                   t.created_at AS created_at, t.updated_at AS updated_at
            ORDER BY t.category, t.name
            """
            params = {
                "item_id": item_id,
                "repository": repository,
                "branch": branch,
            }

        rows = self.fetch_all(query, params)
        return [self._row_to_tag(row, repository, branch) for row in rows]

    async def create_tagged_with_relationship(
        self,
        repository: str,
        item_id: str,
        item_type: str,
        tag_id: str,
        branch: str = "main",
    ) -> bool:
        """Create a TAGGED_WITH relationship between an item and a tag.

        Args:
            repository: The repository name.
            item_id: The item ID.
            item_type: The item type (Component, Decision, etc.).
            tag_id: The tag ID.
            branch: The branch name.

        Returns:
            True if created, False otherwise.
        """
        # item_type is interpolated into the query, so validate it first.
        if not validate_label(item_type):
            raise ValueError(f"Invalid tag target type: {item_type}")

        # Build graph_unique_id for the item if needed
        if item_type in ["Component", "Decision", "Rule", "Context"]:
            item_graph_id = self.create_graph_unique_id(repository, branch, item_id)
            query = f"""
            MATCH (item:{item_type} {{graph_unique_id: $item_id}})
            MATCH (t:Tag {{id: $tag_id}})
            WHERE t.repository = $repository AND t.branch = $branch
            MERGE (item)-[:TAGGED_WITH]->(t)
            RETURN count(*) AS created
            """
            params = {
                "item_id": item_graph_id,
                "tag_id": tag_id,
                "repository": repository,
                "branch": branch,
            }
        else:
            query = f"""
            MATCH (item:{item_type} {{id: $item_id}})
            MATCH (t:Tag {{id: $tag_id}})
            WHERE t.repository = $repository AND t.branch = $branch
            MERGE (item)-[:TAGGED_WITH]->(t)
            RETURN count(*) AS created
            """
            params = {
                "item_id": item_id,
                "tag_id": tag_id,
                "repository": repository,
                "branch": branch,
            }

        result = self.fetch_one(query, params)
        return result is not None and result.get("created", 0) > 0

    async def remove_tagged_with_relationship(
        self,
        repository: str,
        item_id: str,
        item_type: str,
        tag_id: str,
        branch: str = "main",
    ) -> bool:
        """Remove a TAGGED_WITH relationship between an item and a tag.

        Args:
            repository: The repository name.
            item_id: The item ID.
            item_type: The item type (Component, Decision, etc.).
            tag_id: The tag ID.
            branch: The branch name.

        Returns:
            True if removed, False otherwise.
        """
        # Build graph_unique_id for the item if needed
        if item_type in ["Component", "Decision", "Rule", "Context"]:
            item_graph_id = self.create_graph_unique_id(repository, branch, item_id)
            query = f"""
            MATCH (item:{item_type} {{graph_unique_id: $item_id}})
                  -[r:TAGGED_WITH]->
                  (t:Tag {{id: $tag_id}})
            WHERE t.repository = $repository AND t.branch = $branch
            DELETE r
            RETURN count(*) AS deleted
            """
            params = {
                "item_id": item_graph_id,
                "tag_id": tag_id,
                "repository": repository,
                "branch": branch,
            }
        else:
            query = f"""
            MATCH (item:{item_type} {{id: $item_id}})
                  -[r:TAGGED_WITH]->
                  (t:Tag {{id: $tag_id}})
            WHERE t.repository = $repository AND t.branch = $branch
            DELETE r
            RETURN count(*) AS deleted
            """
            params = {
                "item_id": item_id,
                "tag_id": tag_id,
                "repository": repository,
                "branch": branch,
            }

        result = self.fetch_one(query, params)
        return result is not None and result.get("deleted", 0) > 0

    async def get_tag_usage_stats(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[dict[str, Any]]:
        """Get usage statistics for all tags.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of tags with usage counts.
        """
        query = """
        MATCH (t:Tag)
        WHERE t.repository = $repository AND t.branch = $branch
        OPTIONAL MATCH (item)-[:TAGGED_WITH]->(t)
        RETURN t.id AS id,
               t.name AS name,
               t.category AS category,
               count(item) AS usage_count
        ORDER BY usage_count DESC, name
        """

        rows = self.fetch_all(query, {"repository": repository, "branch": branch})

        return [
            {
                "id": row["id"],
                "name": row["name"],
                "category": row.get("category"),
                "usage_count": row.get("usage_count", 0),
            }
            for row in rows
        ]

    def _row_to_tag(
        self,
        row: dict[str, Any],
        repository: str,
        branch: str,
    ) -> Tag:
        """Convert a database row to a Tag.

        Args:
            row: The database row.
            repository: The repository name.
            branch: The branch name.

        Returns:
            The Tag instance.
        """
        return Tag(
            id=row["id"],
            repository=repository,
            branch=branch,
            name=row["name"],
            color=row.get("color"),
            description=row.get("description"),
            category=row.get("category"),
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )
