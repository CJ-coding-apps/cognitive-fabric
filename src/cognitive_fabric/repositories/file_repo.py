"""File repository for File entity operations."""

import json
from typing import Any, Optional

from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.types.entities import File, FileInput


class FileRepository(BaseRepository):
    """Repository for File entity operations."""

    async def find_by_id(
        self,
        repository: str,
        file_id: str,
        branch: str = "main",
    ) -> Optional[File]:
        """Find a file by ID.

        Args:
            repository: The repository name.
            file_id: The file ID.
            branch: The branch name.

        Returns:
            The File if found, None otherwise.
        """
        query = """
        MATCH (f:File {id: $id})
        WHERE f.repository = $repository AND f.branch = $branch
        RETURN f.id AS id, f.name AS name, f.path AS path,
               f.size AS size, f.mime_type AS mime_type,
               f.metrics AS metrics, f.checksum AS checksum,
               f.repository AS repository, f.branch AS branch,
               f.created_at AS created_at, f.updated_at AS updated_at
        LIMIT 1
        """

        row = self.fetch_one(query, {
            "id": file_id,
            "repository": repository,
            "branch": branch,
        })

        if row is None:
            return None

        return self._row_to_file(row, repository, branch)

    async def find_by_path(
        self,
        repository: str,
        path: str,
        branch: str = "main",
    ) -> Optional[File]:
        """Find a file by path.

        Args:
            repository: The repository name.
            path: The file path.
            branch: The branch name.

        Returns:
            The File if found, None otherwise.
        """
        query = """
        MATCH (f:File)
        WHERE f.path = $path
          AND f.repository = $repository
          AND f.branch = $branch
        RETURN f.id AS id, f.name AS name, f.path AS path,
               f.size AS size, f.mime_type AS mime_type,
               f.metrics AS metrics, f.checksum AS checksum,
               f.repository AS repository, f.branch AS branch,
               f.created_at AS created_at, f.updated_at AS updated_at
        LIMIT 1
        """

        row = self.fetch_one(query, {
            "path": path,
            "repository": repository,
            "branch": branch,
        })

        if row is None:
            return None

        return self._row_to_file(row, repository, branch)

    async def get_all_files(
        self,
        repository: str,
        branch: str = "main",
    ) -> list[File]:
        """Get all files.

        Args:
            repository: The repository name.
            branch: The branch name.

        Returns:
            List of all files.
        """
        query = """
        MATCH (f:File)
        WHERE f.repository = $repository AND f.branch = $branch
        RETURN f.id AS id, f.name AS name, f.path AS path,
               f.size AS size, f.mime_type AS mime_type,
               f.metrics AS metrics, f.checksum AS checksum,
               f.repository AS repository, f.branch AS branch,
               f.created_at AS created_at, f.updated_at AS updated_at
        ORDER BY f.path
        """

        rows = self.fetch_all(query, {"repository": repository, "branch": branch})
        return [self._row_to_file(row, repository, branch) for row in rows]

    async def get_files_by_mime_type(
        self,
        repository: str,
        mime_type: str,
        branch: str = "main",
    ) -> list[File]:
        """Get files by MIME type.

        Args:
            repository: The repository name.
            mime_type: The MIME type to filter by.
            branch: The branch name.

        Returns:
            List of files with the given MIME type.
        """
        query = """
        MATCH (f:File)
        WHERE f.repository = $repository
          AND f.branch = $branch
          AND f.mime_type = $mime_type
        RETURN f.id AS id, f.name AS name, f.path AS path,
               f.size AS size, f.mime_type AS mime_type,
               f.metrics AS metrics, f.checksum AS checksum,
               f.repository AS repository, f.branch AS branch,
               f.created_at AS created_at, f.updated_at AS updated_at
        ORDER BY f.path
        """

        rows = self.fetch_all(query, {
            "repository": repository,
            "branch": branch,
            "mime_type": mime_type,
        })
        return [self._row_to_file(row, repository, branch) for row in rows]

    async def get_files_in_directory(
        self,
        repository: str,
        directory: str,
        branch: str = "main",
        recursive: bool = False,
    ) -> list[File]:
        """Get files in a directory.

        Args:
            repository: The repository name.
            directory: The directory path.
            branch: The branch name.
            recursive: Whether to include subdirectories.

        Returns:
            List of files in the directory.
        """
        # Ensure directory ends with /
        if not directory.endswith("/"):
            directory += "/"

        if recursive:
            # Match any file starting with the directory path
            query = """
            MATCH (f:File)
            WHERE f.repository = $repository
              AND f.branch = $branch
              AND f.path STARTS WITH $directory
            RETURN f.id AS id, f.name AS name, f.path AS path,
                   f.size AS size, f.mime_type AS mime_type,
                   f.metrics AS metrics, f.checksum AS checksum,
                   f.repository AS repository, f.branch AS branch,
                   f.created_at AS created_at, f.updated_at AS updated_at
            ORDER BY f.path
            """
        else:
            # Match files directly in the directory (no additional / after directory)
            query = """
            MATCH (f:File)
            WHERE f.repository = $repository
              AND f.branch = $branch
              AND f.path STARTS WITH $directory
              AND NOT substring(f.path, size($directory)) CONTAINS '/'
            RETURN f.id AS id, f.name AS name, f.path AS path,
                   f.size AS size, f.mime_type AS mime_type,
                   f.metrics AS metrics, f.checksum AS checksum,
                   f.repository AS repository, f.branch AS branch,
                   f.created_at AS created_at, f.updated_at AS updated_at
            ORDER BY f.path
            """

        rows = self.fetch_all(query, {
            "repository": repository,
            "branch": branch,
            "directory": directory,
        })
        return [self._row_to_file(row, repository, branch) for row in rows]

    async def upsert_file(
        self,
        repository: str,
        input_data: FileInput,
    ) -> File:
        """Create or update a file.

        Args:
            repository: The repository name.
            input_data: The file input data.

        Returns:
            The upserted File.
        """
        branch = input_data.branch or "main"
        now = self.get_current_timestamp()

        # Serialize metrics if it's a dict
        metrics = input_data.metrics
        if isinstance(metrics, dict):
            metrics = json.dumps(metrics)

        query = """
        MERGE (f:File {id: $id})
        ON CREATE SET
            f.name = $name,
            f.path = $path,
            f.size = $size,
            f.mime_type = $mime_type,
            f.metrics = $metrics,
            f.checksum = $checksum,
            f.repository = $repository,
            f.branch = $branch,
            f.created_at = $now,
            f.updated_at = $now
        ON MATCH SET
            f.name = $name,
            f.path = $path,
            f.size = $size,
            f.mime_type = $mime_type,
            f.metrics = $metrics,
            f.checksum = $checksum,
            f.repository = $repository,
            f.branch = $branch,
            f.updated_at = $now
        RETURN f.id AS id
        """

        params = {
            "id": input_data.id,
            "name": input_data.name,
            "path": input_data.path,
            "size": input_data.size or 0,
            "mime_type": input_data.mime_type or "",
            "metrics": metrics or "",
            "checksum": input_data.checksum or "",
            "repository": repository,
            "branch": branch,
            "now": now,
        }

        self.execute_query(query, params)

        return File(
            id=input_data.id,
            repository=repository,
            branch=branch,
            name=input_data.name,
            path=input_data.path,
            size=input_data.size,
            mime_type=input_data.mime_type,
            metrics=input_data.metrics,
            checksum=input_data.checksum,
            created_at=now,
            updated_at=now,
        )

    async def delete_file(
        self,
        repository: str,
        file_id: str,
        branch: str = "main",
    ) -> bool:
        """Delete a file and its relationships.

        Args:
            repository: The repository name.
            file_id: The file ID.
            branch: The branch name.

        Returns:
            True if deleted, False if not found.
        """
        query = """
        MATCH (f:File {id: $id})
        WHERE f.repository = $repository AND f.branch = $branch
        DETACH DELETE f
        RETURN count(*) AS deleted
        """

        result = self.fetch_one(query, {
            "id": file_id,
            "repository": repository,
            "branch": branch,
        })
        return result is not None and result.get("deleted", 0) > 0

    async def get_files_for_component(
        self,
        repository: str,
        component_id: str,
        branch: str = "main",
    ) -> list[File]:
        """Get files that implement a component.

        Args:
            repository: The repository name.
            component_id: The component ID.
            branch: The branch name.

        Returns:
            List of files implementing the component.
        """
        component_graph_id = self.create_graph_unique_id(
            repository, branch, component_id
        )

        query = """
        MATCH (c:Component {graph_unique_id: $component_id})-[:IMPLEMENTS]->(f:File)
        WHERE f.branch = $branch
        RETURN f.id AS id, f.name AS name, f.path AS path,
               f.size AS size, f.mime_type AS mime_type,
               f.metrics AS metrics, f.checksum AS checksum,
               f.repository AS repository, f.branch AS branch,
               f.created_at AS created_at, f.updated_at AS updated_at
        ORDER BY f.path
        """

        rows = self.fetch_all(query, {
            "component_id": component_graph_id,
            "branch": branch,
        })
        return [self._row_to_file(row, repository, branch) for row in rows]

    async def create_implements_relationship(
        self,
        repository: str,
        component_id: str,
        file_id: str,
        branch: str = "main",
    ) -> bool:
        """Create an IMPLEMENTS relationship between a component and a file.

        Args:
            repository: The repository name.
            component_id: The component ID.
            file_id: The file ID.
            branch: The branch name.

        Returns:
            True if created, False otherwise.
        """
        component_graph_id = self.create_graph_unique_id(
            repository, branch, component_id
        )

        query = """
        MATCH (c:Component {graph_unique_id: $component_id})
        MATCH (f:File {id: $file_id})
        WHERE f.repository = $repository AND f.branch = $branch
        MERGE (c)-[:IMPLEMENTS]->(f)
        RETURN count(*) AS created
        """

        result = self.fetch_one(query, {
            "component_id": component_graph_id,
            "file_id": file_id,
            "repository": repository,
            "branch": branch,
        })

        return result is not None and result.get("created", 0) > 0

    async def remove_implements_relationship(
        self,
        repository: str,
        component_id: str,
        file_id: str,
        branch: str = "main",
    ) -> bool:
        """Remove an IMPLEMENTS relationship between a component and a file.

        Args:
            repository: The repository name.
            component_id: The component ID.
            file_id: The file ID.
            branch: The branch name.

        Returns:
            True if removed, False otherwise.
        """
        component_graph_id = self.create_graph_unique_id(
            repository, branch, component_id
        )

        query = """
        MATCH (c:Component {graph_unique_id: $component_id})
              -[r:IMPLEMENTS]->(f:File {id: $file_id})
        WHERE f.repository = $repository AND f.branch = $branch
        DELETE r
        RETURN count(*) AS deleted
        """

        result = self.fetch_one(query, {
            "component_id": component_graph_id,
            "file_id": file_id,
            "repository": repository,
            "branch": branch,
        })

        return result is not None and result.get("deleted", 0) > 0

    async def search_files_by_name(
        self,
        repository: str,
        name_pattern: str,
        branch: str = "main",
    ) -> list[File]:
        """Search files by name pattern.

        Args:
            repository: The repository name.
            name_pattern: The name pattern to search for.
            branch: The branch name.

        Returns:
            List of files matching the pattern.
        """
        query = """
        MATCH (f:File)
        WHERE f.repository = $repository
          AND f.branch = $branch
          AND f.name CONTAINS $pattern
        RETURN f.id AS id, f.name AS name, f.path AS path,
               f.size AS size, f.mime_type AS mime_type,
               f.metrics AS metrics, f.checksum AS checksum,
               f.repository AS repository, f.branch AS branch,
               f.created_at AS created_at, f.updated_at AS updated_at
        ORDER BY f.path
        LIMIT 100
        """

        rows = self.fetch_all(query, {
            "repository": repository,
            "branch": branch,
            "pattern": name_pattern,
        })
        return [self._row_to_file(row, repository, branch) for row in rows]

    def _row_to_file(
        self,
        row: dict[str, Any],
        repository: str,
        branch: str,
    ) -> File:
        """Convert a database row to a File.

        Args:
            row: The database row.
            repository: The repository name.
            branch: The branch name.

        Returns:
            The File instance.
        """
        metrics = row.get("metrics")
        if isinstance(metrics, str):
            # Empty string (the stored default) must become None for Optional[dict].
            try:
                metrics = json.loads(metrics) if metrics else None
            except json.JSONDecodeError:
                metrics = None

        return File(
            id=row["id"],
            repository=repository,
            branch=branch,
            name=row["name"],
            path=row.get("path"),
            size=row.get("size"),
            mime_type=row.get("mime_type"),
            metrics=metrics,
            checksum=row.get("checksum"),
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )
