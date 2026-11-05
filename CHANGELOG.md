# Changelog

Notable changes to cognitive-fabric. Format follows [Keep a Changelog](https://keepachangelog.com/en/1.1.0/);
versions follow [SemVer](https://semver.org/spec/v2.0.0.html).

cognitive-fabric is pre-1.0: a minor release may change a tool's behaviour or a setting's meaning, and a
patch release will not. Breaking changes are listed as breaking either way, because a reader of this file is
entitled to know which of their own setup stops working. The supported interfaces are the MCP tools, the CLI
commands and the configuration settings; the Python modules behind them are not a public API.

## [Unreleased]

## [0.1.1] - 2026-11-05

A release-hygiene patch: nothing in the server's code or behaviour changes.

### Added

- PyPI classifiers and keywords, so the package page states the supported Pythons (3.11–3.13), platforms
  and maturity instead of nothing.
- A "Status and support" section in the README: what the supported interfaces are (and that the Python
  modules are not one), the pre-1.0 versioning policy, the tested platforms, the archived storage engine,
  and where to report a vulnerability.
- This changelog. The PyPI "Changelog" link points here rather than at the releases page, and a "Security"
  link points at the security policy.
- The security policy says what happens to a vulnerability in KùzuDB itself, now that Kùzu is archived
  upstream and will not ship a fix.
- CI runs the test suite on macOS as well as Linux, in both install profiles on every supported Python.
  macOS was claimed and untested; the native dependencies (Kùzu, LanceDB, tree-sitter's grammars) ship
  separate macOS wheels that a Linux run never touched.

### Fixed

- CI's Docker handshake check compared the server's advertised version against the literal `"0.1.0"`, so
  the first version bump would have failed it on the release pull request itself. It now reads the
  expected version from `pyproject.toml`, the source the package and the handshake already derive from.

## [0.1.0] - 2026-10-07

First public release, on PyPI and ghcr.io.

### Added

- A Python MCP server for a graph "memory bank" on KùzuDB: components, decisions, rules, context, files,
  tags and metadata, isolated by repository and branch. Thirteen tools: `memory-bank`, `entity`,
  `context`, `query`, `associate`, `analyze`, `detect`, `introspect`, `bulk-import`, `search`, `delete`,
  `memory-optimizer` and `fabric`.
- The Cognitive Fabric layer, in-process: tree-sitter symbolic ingestion (`Symbol`/`File` nodes and
  `DEFINED_IN` edges); semantic search over a LanceDB vector store (the `[semantic]` extra), which reports
  itself unavailable rather than raising when the extra is absent; and the "dream" engine, which distills
  recent context into decisions through an LLM (the `[cloud]` extra) and skips cleanly without a key.
- An AI memory optimizer with snapshots and rollback, and graph algorithms (PageRank, Louvain, k-core,
  shortest path).
- Transports: stdio by default; streamable HTTP on request, which binds only loopback and refuses
  requests whose `Host` or `Origin` is not this machine's (DNS-rebinding protection the MCP SDK leaves off
  by default).
- Agent-supplied paths for AST ingestion are confined to the session's project root, checked on fully
  resolved paths so that `..`, absolute paths and symlinks cannot escape it.
- One version source: `__version__`, `--version` and the MCP handshake all read the installed package's
  metadata.
- A security policy (`docs/SECURITY.md`) and a `NOTICE` recording the tool surface and data model's
  derivation from KuzuMem-MCP.

[Unreleased]: https://github.com/CJ-coding-apps/cognitive-fabric/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/CJ-coding-apps/cognitive-fabric/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/CJ-coding-apps/cognitive-fabric/releases/tag/v0.1.0
