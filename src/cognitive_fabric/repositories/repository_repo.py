"""Repository repository for Repository entity operations."""

from typing import Optional

from cognitive_fabric.repositories.base import BaseRepository
from cognitive_fabric.types.entities import Repository, RepositoryInput
from cognitive_fabric.utils.id_utils import create_repository_node_id


class RepositoryRepository(BaseRepository):
    """Repository for Repository entity operations."""

    async def find_by_name(
        self,
        name: str,
        branch: str = "main",
    ) -> Optional[Repository]:
        """Find a repository by name and branch.

        Args:
            name: The repository name.
            branch: The branch name.

        Returns:
            The Repository if found, None otherwise.
        """
        repo_id = create_repository_node_id(name, branch)

        query = """
        MATCH (r:Repository {id: $id})
        RETURN r.id AS id, r.name AS name, r.branch AS branch,
               r.tech_stack AS tech_stack, r.architecture AS architecture,
               r.created_at AS created_at, r.updated_at AS updated_at
        LIMIT 1
        """

        row = self.fetch_one(query, {"id": repo_id})

        if row is None:
            return None

        return Repository(
            id=row["id"],
            name=row["name"],
            branch=row["branch"],
            tech_stack=row.get("tech_stack"),
            architecture=row.get("architecture"),
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )

    async def create(self, input_data: RepositoryInput) -> Repository:
        """Create a new repository.

        Args:
            input_data: The repository input data.

        Returns:
            The created Repository.
        """
        repo_id = create_repository_node_id(input_data.name, input_data.branch)
        now = self.get_current_timestamp()

        query = """
        CREATE (r:Repository {
            id: $id,
            name: $name,
            branch: $branch,
            tech_stack: $tech_stack,
            architecture: $architecture,
            created_at: $created_at,
            updated_at: $updated_at
        })
        RETURN r.id AS id
        """

        params = {
            "id": repo_id,
            "name": input_data.name,
            "branch": input_data.branch,
            "tech_stack": input_data.tech_stack or [],
            "architecture": input_data.architecture or "",
            "created_at": now,
            "updated_at": now,
        }

        self.execute_query(query, params)

        return Repository(
            id=repo_id,
            name=input_data.name,
            branch=input_data.branch,
            tech_stack=input_data.tech_stack,
            architecture=input_data.architecture,
            created_at=now,
            updated_at=now,
        )

    async def upsert(self, input_data: RepositoryInput) -> Repository:
        """Create or update a repository.

        Args:
            input_data: The repository input data.

        Returns:
            The upserted Repository.
        """
        existing = await self.find_by_name(input_data.name, input_data.branch)

        if existing:
            return await self.update(existing.id, input_data)

        return await self.create(input_data)

    async def update(
        self,
        repo_id: str,
        input_data: RepositoryInput,
    ) -> Repository:
        """Update an existing repository.

        Args:
            repo_id: The repository ID.
            input_data: The update data.

        Returns:
            The updated Repository.
        """
        now = self.get_current_timestamp()

        query = """
        MATCH (r:Repository {id: $id})
        SET r.tech_stack = $tech_stack,
            r.architecture = $architecture,
            r.updated_at = $updated_at
        RETURN r.id AS id, r.name AS name, r.branch AS branch,
               r.tech_stack AS tech_stack, r.architecture AS architecture,
               r.created_at AS created_at, r.updated_at AS updated_at
        """

        params = {
            "id": repo_id,
            "tech_stack": input_data.tech_stack or [],
            "architecture": input_data.architecture or "",
            "updated_at": now,
        }

        row = self.fetch_one(query, params)

        if row is None:
            raise ValueError(f"Repository not found: {repo_id}")

        return Repository(
            id=row["id"],
            name=row["name"],
            branch=row["branch"],
            tech_stack=row.get("tech_stack"),
            architecture=row.get("architecture"),
            created_at=self.normalize_timestamp(row.get("created_at")),
            updated_at=self.normalize_timestamp(row.get("updated_at")),
        )

    async def delete(self, repo_id: str) -> bool:
        """Delete a repository and its relationships.

        Args:
            repo_id: The repository ID.

        Returns:
            True if deleted, False if not found.
        """
        query = """
        MATCH (r:Repository {id: $id})
        DETACH DELETE r
        RETURN count(*) AS deleted
        """

        result = self.fetch_one(query, {"id": repo_id})
        return result is not None and result.get("deleted", 0) > 0

    async def find_all(self, branch: Optional[str] = None) -> list[Repository]:
        """Find all repositories, optionally filtered by branch.

        Args:
            branch: Optional branch filter.

        Returns:
            List of repositories.
        """
        if branch:
            query = """
            MATCH (r:Repository)
            WHERE r.branch = $branch
            RETURN r.id AS id, r.name AS name, r.branch AS branch,
                   r.tech_stack AS tech_stack, r.architecture AS architecture,
                   r.created_at AS created_at, r.updated_at AS updated_at
            ORDER BY r.name
            """
            rows = self.fetch_all(query, {"branch": branch})
        else:
            query = """
            MATCH (r:Repository)
            RETURN r.id AS id, r.name AS name, r.branch AS branch,
                   r.tech_stack AS tech_stack, r.architecture AS architecture,
                   r.created_at AS created_at, r.updated_at AS updated_at
            ORDER BY r.name, r.branch
            """
            rows = self.fetch_all(query)

        return [
            Repository(
                id=row["id"],
                name=row["name"],
                branch=row["branch"],
                tech_stack=row.get("tech_stack"),
                architecture=row.get("architecture"),
                created_at=self.normalize_timestamp(row.get("created_at")),
                updated_at=self.normalize_timestamp(row.get("updated_at")),
            )
            for row in rows
        ]

    async def exists(self, name: str, branch: str = "main") -> bool:
        """Check if a repository exists.

        Args:
            name: The repository name.
            branch: The branch name.

        Returns:
            True if exists, False otherwise.
        """
        repo_id = create_repository_node_id(name, branch)

        query = """
        MATCH (r:Repository {id: $id})
        RETURN count(*) AS count
        """

        count = self.count(query, {"id": repo_id})
        return count > 0
