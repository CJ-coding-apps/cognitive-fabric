# Security policy

## Reporting a vulnerability

Report suspected vulnerabilities through GitHub's
[private vulnerability reporting](https://github.com/CJ-coding-apps/cognitive-fabric/security/advisories/new),
not as a public issue. If you cannot use that form, open an issue that says only that you have a security
report to share, and wait for a maintainer to open a private channel — please do not put the details in
the issue.

Useful to include: the version, the tool or endpoint involved, what you did, and what happened. A
reproduction is worth more than a description.

## Supported versions

Cognitive Fabric is pre-1.0. Only the most recent release is supported; fixes land there and are not
backported. Please reproduce against the latest version before reporting.

## What this project does with your data

Worth stating plainly, because it decides what is and is not a vulnerability here.

- **The graph is local.** The KuzuDB database, the LanceDB vector store, the AST ingestion and the
  "dream" engine all run in-process and write to paths you configure. Nothing is sent anywhere to build
  or query the graph.
- **There is no network data plane by default.** This is a single-runtime server: no Arrow Flight sidecar,
  and the default stdio transport talks to a parent process over pipes and opens no socket at all.
- **The HTTP transport is opt-in, loopback-only, and guarded.** `--transport http` serves `/mcp` over the
  streamable-HTTP transport. Two things keep it yours:
  - *It refuses to bind anything but loopback.* Binding `127.0.0.1` is not by itself a control, because a
    page in your browser can reach loopback too. `--host` is therefore rejected unless it is a loopback
    address or `localhost`; the transport has no authentication, and this release will not publish it to
    a network. Put an authenticated reverse proxy in front if you need that.
  - *It refuses requests that are not addressed to it.* A name an attacker controls can be made to resolve
    to `127.0.0.1` (DNS rebinding), at which point a page's requests arrive on your loopback address
    carrying the attacker's `Host`. The transport checks `Host` and `Origin` against an allowlist of this
    machine's own spellings on the port actually bound, and answers 421 or 403 otherwise. This check is
    off in the MCP SDK unless settings are supplied, so it is supplied explicitly.
- **LLM features are opt-in and go to your provider.** The optimizer and the dream engine can call
  OpenAI or Anthropic, and when you enable them the text they send goes to that provider under its
  terms. With those features off, no provider request is made.

Anything that breaks one of those statements — a database or vector store written outside the configured
directory, a tool argument that reaches a path outside the project root, a request made with no provider
configured — is a vulnerability, and we would want to hear about it.

## Out of scope

Findings that depend on an attacker already running code as the user who runs the server; and the content
of the repositories you chose to ingest.
