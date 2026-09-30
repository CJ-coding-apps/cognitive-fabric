"""CLI for Cognitive Fabric MCP server."""

import asyncio
import json
import sys
from pathlib import Path
from typing import Optional

import click

from cognitive_fabric.config import Settings
from cognitive_fabric.utils.logger import configure_logging


@click.group()
@click.version_option(version="1.0.0", prog_name="cognitive_fabric")
@click.option("--verbose", "-v", is_flag=True, help="Enable verbose output")
@click.pass_context
def cli(ctx: click.Context, verbose: bool) -> None:
    """Cognitive Fabric - Python MCP server for graph memory bank using KuzuDB."""
    ctx.ensure_object(dict)
    ctx.obj["verbose"] = verbose
    configure_logging(json_output=False)


@cli.command()
@click.option(
    "--db-path",
    "-d",
    type=click.Path(),
    help="Path to KuzuDB database directory",
    envvar="COGNITIVE_FABRIC_DB_PATH",
)
@click.option(
    "--log-level",
    "-l",
    type=click.Choice(["DEBUG", "INFO", "WARNING", "ERROR"]),
    default="INFO",
    help="Logging level",
)
@click.option(
    "--json-logs",
    is_flag=True,
    help="Output logs in JSON format",
)
@click.option(
    "--transport",
    "-t",
    type=click.Choice(["stdio", "http"]),
    default="stdio",
    help="Transport to serve (stdio or streamable HTTP)",
)
@click.option(
    "--host",
    default=None,
    help="Bind host for HTTP transport (default 127.0.0.1)",
)
@click.option(
    "--port",
    type=int,
    default=None,
    help="Bind port for HTTP transport (default 8001)",
)
@click.pass_context
def serve(
    ctx: click.Context,
    db_path: Optional[str],
    log_level: str,
    json_logs: bool,
    transport: str,
    host: Optional[str],
    port: Optional[int],
) -> None:
    """Start the MCP server (stdio by default, or --transport http).

    This starts the Cognitive Fabric MCP server for communication with MCP
    clients like Claude Code. stdio is the default; ``--transport http`` serves
    the streamable-HTTP transport at ``/mcp``.
    """
    from cognitive_fabric.mcp.server import run_http_server, run_server

    # Reconfigure logging if needed
    if json_logs or log_level != "INFO":
        configure_logging(log_level=log_level, json_output=json_logs)

    # Build settings
    settings = Settings()
    if db_path:
        settings.db_path_override = db_path

    if ctx.obj.get("verbose"):
        click.echo(
            f"Starting Cognitive Fabric MCP server ({transport})...", err=True
        )
        click.echo(f"Database path: {db_path or 'default'}", err=True)

    # Run the server
    try:
        if transport == "http":
            asyncio.run(
                run_http_server(
                    db_path=db_path, settings=settings, host=host, port=port
                )
            )
        else:
            asyncio.run(run_server(db_path=db_path, settings=settings))
    except KeyboardInterrupt:
        click.echo("\nServer stopped.", err=True)
    except Exception as e:
        click.echo(f"Error: {e}", err=True)
        sys.exit(1)


@cli.command()
@click.argument("db_path", type=click.Path())
@click.option(
    "--force",
    "-f",
    is_flag=True,
    help="Force initialization even if database exists",
)
@click.pass_context
def init(ctx: click.Context, db_path: str, force: bool) -> None:
    """Initialize a new KuzuDB database with schema.

    Creates a new KuzuDB database at the specified path and initializes
    the schema for memory bank storage.
    """
    from cognitive_fabric.db.kuzu_client import KuzuDBClient

    db_path_obj = Path(db_path)

    if db_path_obj.exists() and not force:
        click.echo(f"Database already exists at {db_path}", err=True)
        click.echo("Use --force to reinitialize.", err=True)
        sys.exit(1)

    if ctx.obj.get("verbose"):
        click.echo(f"Initializing database at {db_path}...", err=True)

    async def do_init():
        client = KuzuDBClient(str(db_path_obj))
        await client.initialize()
        click.echo(f"Database initialized at {db_path}")

    asyncio.run(do_init())


@cli.command()
@click.argument("db_path", type=click.Path(exists=True))
@click.pass_context
def info(ctx: click.Context, db_path: str) -> None:
    """Show information about a KuzuDB database.

    Displays statistics and metadata about the memory bank database.
    """
    from cognitive_fabric.db.kuzu_client import KuzuDBClient

    async def do_info():
        client = KuzuDBClient(db_path)
        await client.initialize()

        stats = {}
        tables = [
            "Repository",
            "Component",
            "Decision",
            "Rule",
            "Context",
            "File",
            "Tag",
            "Metadata",
        ]

        for table in tables:
            try:
                result = client.fetch_all(
                    f"MATCH (n:{table}) RETURN count(n) as count"
                )
                stats[table.lower()] = result[0]["count"] if result else 0
            except Exception:
                stats[table.lower()] = "N/A"

        click.echo("Cognitive Fabric Database Info")
        click.echo("=" * 40)
        click.echo(f"Path: {db_path}")
        click.echo("")
        click.echo("Entity Counts:")
        for table, count in stats.items():
            click.echo(f"  {table}: {count}")

    asyncio.run(do_info())


@cli.command()
@click.argument("db_path", type=click.Path(exists=True))
@click.argument("repository")
@click.option("--branch", "-b", default="main", help="Branch name")
@click.option(
    "--strategy",
    "-s",
    type=click.Choice(["conservative", "balanced", "aggressive"]),
    default="balanced",
    help="Optimization strategy",
)
@click.option(
    "--dry-run",
    is_flag=True,
    help="Simulate optimization without making changes",
)
@click.pass_context
def optimize(
    ctx: click.Context,
    db_path: str,
    repository: str,
    branch: str,
    strategy: str,
    dry_run: bool,
) -> None:
    """Run memory optimization on a repository.

    Analyzes the memory bank and suggests/applies optimizations based
    on the selected strategy.
    """
    from cognitive_fabric.agents.memory_optimizer import MemoryOptimizationAgent
    from cognitive_fabric.services.memory_service import MemoryService
    from cognitive_fabric.types.optimization import OptimizationStrategy

    async def do_optimize():
        memory_service = await MemoryService.get_instance(db_path)
        agent = MemoryOptimizationAgent(memory_service)

        strategy_enum = OptimizationStrategy(strategy)

        if ctx.obj.get("verbose"):
            click.echo(f"Analyzing {repository}:{branch}...", err=True)

        result = await agent.optimize(
            repository=repository,
            branch=branch,
            strategy=strategy_enum,
            dry_run=dry_run,
            create_snapshot=not dry_run,
        )

        # Output summary
        summary = result.get("summary", {})
        click.echo("")
        click.echo("Optimization Summary")
        click.echo("=" * 40)
        click.echo(f"Repository: {summary.get('repository')}")
        click.echo(f"Branch: {summary.get('branch')}")
        click.echo(f"Strategy: {summary.get('strategy')}")
        click.echo(f"Health Score: {summary.get('health_score', 'N/A')}")
        click.echo(f"Issues Found: {summary.get('issues_found', 0)}")
        click.echo(f"Actions Planned: {summary.get('actions_planned', 0)}")
        click.echo(f"Actions Executed: {summary.get('actions_executed', 0)}")
        click.echo(f"Actions Failed: {summary.get('actions_failed', 0)}")
        if summary.get("snapshot_id"):
            click.echo(f"Snapshot ID: {summary.get('snapshot_id')}")
        if dry_run:
            click.echo("")
            click.echo("(Dry run - no changes made)")

    asyncio.run(do_optimize())


@cli.command()
@click.argument("db_path", type=click.Path(exists=True))
@click.argument("repository")
@click.argument("snapshot_id")
@click.option("--branch", "-b", default="main", help="Branch name")
@click.pass_context
def rollback(
    ctx: click.Context,
    db_path: str,
    repository: str,
    snapshot_id: str,
    branch: str,
) -> None:
    """Rollback to a previous snapshot.

    Restores the memory bank to the state captured in the specified snapshot.
    """
    from cognitive_fabric.agents.memory_optimizer import MemoryOptimizationAgent
    from cognitive_fabric.services.memory_service import MemoryService

    async def do_rollback():
        memory_service = await MemoryService.get_instance(db_path)
        agent = MemoryOptimizationAgent(memory_service)

        if ctx.obj.get("verbose"):
            click.echo(f"Rolling back to snapshot {snapshot_id}...", err=True)

        result = await agent.rollback(repository, snapshot_id, branch)

        if result.get("success"):
            click.echo(f"Successfully rolled back to snapshot {snapshot_id}")
        else:
            click.echo(f"Rollback failed: {result.get('error')}", err=True)
            sys.exit(1)

    asyncio.run(do_rollback())


@cli.command("list-snapshots")
@click.argument("db_path", type=click.Path(exists=True))
@click.argument("repository")
@click.option("--branch", "-b", default="main", help="Branch name")
@click.option("--limit", "-n", default=10, help="Maximum number of snapshots")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def list_snapshots(
    ctx: click.Context,
    db_path: str,
    repository: str,
    branch: str,
    limit: int,
    json_output: bool,
) -> None:
    """List available snapshots for a repository."""
    from cognitive_fabric.agents.memory_optimizer import MemoryOptimizationAgent
    from cognitive_fabric.services.memory_service import MemoryService

    async def do_list():
        memory_service = await MemoryService.get_instance(db_path)
        agent = MemoryOptimizationAgent(memory_service)

        snapshots = await agent.list_snapshots(repository, branch, limit)

        if json_output:
            click.echo(json.dumps(snapshots, indent=2, default=str))
        else:
            if not snapshots:
                click.echo("No snapshots found.")
                return

            click.echo("Available Snapshots")
            click.echo("=" * 60)
            for snapshot in snapshots:
                click.echo(f"ID: {snapshot.get('id')}")
                click.echo(f"  Created: {snapshot.get('created_at')}")
                click.echo(f"  Description: {snapshot.get('description', 'N/A')}")
                click.echo("")

    asyncio.run(do_list())


@cli.command()
@click.argument("db_path", type=click.Path(exists=True))
@click.argument("query")
@click.option("--json", "json_output", is_flag=True, help="Output as JSON")
@click.pass_context
def query(
    ctx: click.Context,
    db_path: str,
    query: str,
    json_output: bool,
) -> None:
    """Execute a raw Cypher query against the database.

    Use with caution - this allows direct database access.
    """
    from cognitive_fabric.db.kuzu_client import KuzuDBClient

    async def do_query():
        client = KuzuDBClient(db_path)
        await client.initialize()

        try:
            result = client.fetch_all(query)

            if json_output:
                click.echo(json.dumps(result, indent=2, default=str))
            else:
                if not result:
                    click.echo("No results.")
                    return

                # Simple table output
                if result:
                    keys = list(result[0].keys())
                    click.echo(" | ".join(keys))
                    click.echo("-" * 60)
                    for row in result:
                        values = [str(row.get(k, "")) for k in keys]
                        click.echo(" | ".join(values))

        except Exception as e:
            click.echo(f"Query error: {e}", err=True)
            sys.exit(1)

    asyncio.run(do_query())


@cli.command("fabric-ingest")
@click.argument("db_path", type=click.Path())
@click.argument("repository")
@click.option(
    "--path",
    "-p",
    "project_path",
    type=click.Path(exists=True),
    required=True,
    help="Project directory to scan",
)
@click.option("--branch", "-b", default="main", help="Branch name")
@click.pass_context
def fabric_ingest(
    ctx: click.Context,
    db_path: str,
    repository: str,
    project_path: str,
    branch: str,
) -> None:
    """Ingest a project's symbols/files into the memory graph (Cognitive Fabric)."""
    from cognitive_fabric.services.memory_service import MemoryService

    async def do_ingest():
        service = await MemoryService.get_instance(db_path)
        try:
            data_fabric = await service.data_fabric
            result = await data_fabric.ingest_project(project_path, repository, branch)
            click.echo(
                f"Ingested: {result['symbols_upserted']} symbols, "
                f"{result['files_upserted']} files, "
                f"{result['edges_created']} DEFINED_IN edges, "
                f"{result['symbols_indexed']} indexed."
            )
        finally:
            await service.close()

    asyncio.run(do_ingest())


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
