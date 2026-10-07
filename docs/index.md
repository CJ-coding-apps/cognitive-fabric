# Cognitive-Fabric Documentation

Welcome to the Cognitive-Fabric documentation. Cognitive-Fabric is a Python MCP (Model Context Protocol) server that provides a graph-based memory bank using KuzuDB for AI assistants like Claude.

## What is Cognitive-Fabric?

Cognitive-Fabric enables AI assistants to maintain persistent, structured memory about software projects. It stores architectural decisions, components, rules, and context in a knowledge graph, allowing for sophisticated queries and AI-powered optimization.

### Key Features

- **Graph-Based Memory**: Store and query interconnected knowledge using KuzuDB
- **13 MCP Tools**: Complete toolkit for memory management, querying, and optimization
- **Cognitive Fabric**: In-process tree-sitter symbolic ingestion, LanceDB semantic search, and a "dream" distillation engine (no Arrow Flight sidecar) — see [Cognitive Fabric](fabric.md)
- **AI-Powered Optimization**: Intelligent memory cleanup with analysis, planning, and safe execution
- **Graph Algorithms**: PageRank, Louvain community detection, k-core decomposition, shortest path
- **Branch Isolation**: Repository and branch-aware memory scoping
- **Snapshot & Rollback**: Safe optimization with automatic backup and restore

## Documentation Sections

### Getting Started

- [Quick Start Guide](guides/getting-started.md) - Get up and running in minutes
- [Installation](guides/installation.md) - Detailed installation instructions
- [Configuration](guides/configuration.md) - Configure the server for your needs

### Core Concepts

- [Architecture Overview](architecture.md) - Understand the system design
- [Entity Types](guides/entities.md) - Learn about the data model
- [Graph Relationships](guides/relationships.md) - How entities connect

### API Reference

- [MCP Tools Reference](api/tools.md) - Complete tool documentation
- [Entity Schemas](api/schemas.md) - Pydantic model definitions
- [CLI Commands](api/cli.md) - Command-line interface reference

### Guides

- [Memory Optimizer Agent](guides/memory-optimizer.md) - AI-powered optimization
- [Development Guide](guides/development.md) - Contributing and extending
- [Docker Usage](guides/docker.md) - Container-based deployment

### Examples

- [Basic Usage](examples/basic-usage.md) - Common operations
- [Advanced Queries](examples/advanced-queries.md) - Complex graph queries
- [Integration Examples](examples/integration.md) - Claude Code integration

## Quick Links

| Resource | Description |
|----------|-------------|
| [GitHub Repository](https://github.com/CJ-coding-apps/cognitive-fabric) | Source code |
| [Issue Tracker](https://github.com/CJ-coding-apps/cognitive-fabric/issues) | Report bugs |
| [MCP Specification](https://modelcontextprotocol.io/) | Protocol documentation |
| [KuzuDB Documentation](https://kuzudb.com/docs/) | Database documentation |

## System Requirements

- Python 3.11–3.13 (3.14 is excluded by `requires-python`; see the README)
- Docker (recommended for development)
- 512MB RAM minimum
- 100MB disk space for database

## Support

If you encounter issues:

1. Check the [Troubleshooting Guide](guides/troubleshooting.md)
2. Search existing [GitHub Issues](https://github.com/CJ-coding-apps/cognitive-fabric/issues)
3. Open a new issue with reproduction steps

## License

Cognitive-Fabric is released under the MIT License.
