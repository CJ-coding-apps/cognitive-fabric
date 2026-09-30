"""Metadata repository for Metadata entity operations."""

import json
from typing import Any, Optional

from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.types.entities import Metadata, MetadataContent, MetadataInput


class MetadataRepository(BaseRepository):
    """Repository for Metadata entity operations."""

    async def find_by_id(
        self,
        repository: str,
        metadata_id: str,
        branch: str = "main",
    ) -> Optional[Metadata]:
        """Find metadata by ID.

        Args:
            repository: The repository name.
            metadata_id: The metadata ID.
            branch: The branch name.

        Returns:
            The Metadata if found, None otherwise.
        """
        graph_id = self.create_graph_unique_id(repository, branch, metadata_id)

        query = """
        MATCH (m:Metadata {graph_unique_id: $graph_id})
        RETURN m.graph_unique_id AS graph_unique_id,
               m.id AS id, m.name AS name, m.content AS content,
               m.branch AS branch,
               m.created_at AS created_at, m.updated_at AS updated_at
        LIMIT 1
        """

        row = self.fetch_one(query, {"graph_id": graph_id})

        if row is None:
            return None

        return self._row_to_metadata(row, repository, branch)

    async def find_by_name(
        self,
        repository: str,
        name: str,
        branch: str = "main",
    ) -> Optional[Metadata]:
        """Find metadata by name.

        Args:
            repository: The repository name.
            name: The metadata name.
            branch: The branch name.

        Returns:
            The Metadata if found, None otherwise.
        """
        query = """
        MATCH (m:Metadata)
        WHERE m.name = $name AND m.branch = $branch
        RETURN m.graph_unique_id AS graph_unique_id,
               m.id AS id, m.name AS name, m.content AS content,
               m.branch AS branch,
               m.created_at AS created_at, m.updated_at AS updated_at
        LIMIT 1
        """

        row = self.fetch_one(query, {"name": name, "branch": branch})

        if row is None:
            return None

        return self._row_to_metadata(row, repository, branch)

    async def get_all_metadata(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[Metadata]:
        """Get all metadata entries.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all metadata entries.
        """
        query = """
        MATCH (m:Metadata)
        WHERE m.branch = $branch
        RETURN m.graph_unique_id AS graph_unique_id,
               m.id AS id, m.name AS name, m.content AS content,
               m.branch AS branch,
               m.created_at AS created_at, m.updated_at AS updated_at
        ORDER BY m.name
        """

        rows = self.fetch_all(query, {"branch": branch})
        return [self._row_to_metadata(row, repository, branch) for row in rows]

    async def upsert_metadata(
        self,
        repository: str,
        input_data: MetadataInput,
    ) -> Metadata:
        """Create or update metadata.

        Args:
            repository: The repository name.
            input_data: The metadata input data.

        Returns:
            The upserted Metadata.
        """
        branch = input_data.branch or "main"
        graph_id = self.create_graph_unique_id(repository, branch, input_data.id)
        now = self.get_current_timestamp()

        # Build a MetadataContent from the provided content or the flat fields,
        # then persist it as a JSON string.
        content_obj = input_data.content or MetadataContent(
            id=input_data.id,
            project=input_data.project,
            tech_stack=input_data.tech_stack,
            architecture=input_data.architecture,
            memory_spec_version=input_data.memory_spec_version,
        )
        content_json = json.dumps(content_obj.model_dump(mode="json"))

        query = """
        MERGE (m:Metadata {graph_unique_id: $graph_id})
        ON CREATE SET
            m.id = $id,
            m.name = $name,
            m.content = $content,
            m.branch = $branch,
            m.created_at = $now,
            m.updated_at = $now
        ON MATCH SET
            m.name = $name,
            m.content = $content,
            m.updated_at = $now
        RETURN m.graph_unique_id AS graph_unique_id
        """

        params = {
            "graph_id": graph_id,
            "id": input_data.id,
            "name": input_data.name,
            "content": content_json,
            "branch": branch,
            "now": now,
        }

        self.execute_query(query, params)

        return Metadata(
            id=input_data.id,
            repository=repository,
            branch=branch,
            name=input_data.name,
            content=content_obj,
            created_at=now,
            updated_at=now,
        )

    async def update_content(
        self,
        repository: str,
        metadata_id: str,
        branch: str,
        content: Any,
    ) -> Optional[Metadata]:
        """Update metadata content.

        Args:
            repository: The repository name.
            metadata_id: The metadata ID.
            branch: The branch name.
            content: The new content.

        Returns:
            The updated Metadata, or None if not found.
        """
        graph_id = self.create_graph_unique_id(repository, branch, metadata_id)
        now = self.get_current_timestamp()

        # Serialize content if it's a dict
        if isinstance(content, dict):
            content = json.dumps(content)

        query = """
        MATCH (m:Metadata {graph_unique_id: $graph_id})
        SET m.content = $content, m.updated_at = $now
        RETURN m.graph_unique_id AS graph_unique_id,
               m.id AS id, m.name AS name, m.content AS content,
               m.branch AS branch,
               m.created_at AS created_at, m.updated_at AS updated_at
        """

        row = self.fetch_one(query, {
            "graph_id": graph_id,
            "content": content or "",
            "now": now,
        })

        if row is None:
            return None

        return self._row_to_metadata(row, repository, branch)

    async def delete_metadata(
        self,
        repository: str,
        metadata_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete metadata and its relationships.

        Args:
            repository: The repository name.
            metadata_id: The metadata ID.
            branch: The branch name.

        Returns:
            True if deleted, False if not found.
        """
        graph_id = self.create_graph_unique_id(repository, branch, metadata_id)

        query = """
        MATCH (m:Metadata {graph_unique_id: $graph_id})
        DETACH DELETE m
        RETURN count(*) AS deleted
        """

        result = self.fetch_one(query, {"graph_id": graph_id})
        return result is not None and result.get("deleted", 0) > 0

    async def get_repository_metadata(
        self,
        repository: str,
        branch: str = "main",
    ) -> Optional[Metadata]:
        """Get the main metadata entry for a repository.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            The repository Metadata, or None if not found.
        """
        # Convention: repository metadata has name == repository name
        return await self.find_by_name(repository, repository, branch)

    async def create_has_metadata_relationship(
        self,
        repository: str,
        repository_node_id: str,
        metadata_id: str,
        branch: str = "main",
    ) -> bool:
        """Create a HAS_METADATA relationship between a repository and metadata.

        Args:
            repository: The repository name.
            repository_node_id: The repository node ID.
            metadata_id: The metadata ID.
            branch: The branch name.

        Returns:
            True if created, False otherwise.
        """
        metadata_graph_id = self.create_graph_unique_id(repository, branch, metadata_id)

        query = """
        MATCH (r:Repository {id: $repo_id})
        MATCH (m:Metadata {graph_unique_id: $metadata_id})
        MERGE (r)-[:HAS_METADATA]->(m)
        RETURN count(*) AS created
        """

        result = self.fetch_one(query, {
            "repo_id": repository_node_id,
            "metadata_id": metadata_graph_id,
        })

        return result is not None and result.get("created", 0) > 0

    async def get_metadata_for_repository(
        self,
        repository_node_id: str,
        repository: str,
        branch: str = "main",
    ) -> list[Metadata]:
        """Get all metadata linked to a repository.

        Args:
            repository_node_id: The repository node ID.
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of metadata entries linked to the repository.
        """
        query = """
        MATCH (r:Repository {id: $repo_id})-[:HAS_METADATA]->(m:Metadata)
        WHERE m.branch = $branch
        RETURN m.graph_unique_id AS graph_unique_id,
               m.id AS id, m.name AS name, m.content AS content,
               m.branch AS branch,
               m.created_at AS created_at, m.updated_at AS updated_at
        ORDER BY m.name
        """

        rows = self.fetch_all(query, {
            "repo_id": repository_node_id,
            "branch": branch,
        })
        return [self._row_to_metadata(row, repository, branch) for row in rows]

    def _row_to_metadata(
        self,
        row: dict[str, Any],
        repository: str,
        branch: str,
    ) -> Metadata:
        """Convert a database row to a Metadata.

        Args:
            row: The database row.
            repository: The repository name.
            branch: The branch name.

        Returns:
            The Metadata instance.
        """
        content_raw = row.get("content")
        content_obj = None
        if isinstance(content_raw, str) and content_raw:
            try:
                data = json.loads(content_raw)
                if isinstance(data, dict):
                    content_obj = MetadataContent(**data)
            except (json.JSONDecodeError, TypeError, ValueError):
                content_obj = None
        if content_obj is None:
            content_obj = MetadataContent(id=row.get("id", ""))

        return Metadata(
            id=row["id"],
            repository=repository,
            branch=branch,
            name=row["name"],
            content=content_obj,
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )
