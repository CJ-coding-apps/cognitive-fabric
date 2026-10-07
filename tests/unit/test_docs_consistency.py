"""The docs describe this package, or they fail the build.

Every page under `docs/` is a promise to someone who has not read the source. A
promise the code does not keep is worse than a missing page: it is read, relied
on, and only discovered to be false when it matters. This package had several --
a log-format setting the Dockerfile and three compose files set and nothing
reads, an optimizer setting documented for a release where nothing read it
either, a strategy table whose numbers were wrong in the direction that deletes
more than advertised, and CLI commands named with an underscore where the
console script has a hyphen.

Finding those one at a time is what produced them. So this module checks the
claims a page about this package makes, mechanically:

  * every `COGNITIVE_FABRIC_*` variable a shipping file names is a field of
    `Settings` -- including the Dockerfile, the compose file and `.env.example`,
    which is where the log-format phantom actually lived;
  * every JSON tool call a page shows validates against that tool's schema, and
    passes no key the tool does not read;
  * every CLI command and option a page shows exists, and every `"command"` in
    an MCP client config is a program the reader can run;
  * every parameter named in a table on `docs/api/tools.md` is one the tool
    accepts, and every tool the server advertises has a section there (the
    `fabric` tool had none, so eight operations had no page at all);
  * the defaults the tool schemas advertise are the ones `Settings` holds, so a
    schema default and the configured default cannot drift apart.

The strategy table is not checked against a copy in the prose: it is *rendered*
from `STRATEGY_CONFIGS`, and the pages embed the rendered block between two
markers. Run this module directly to regenerate it:

    python tests/unit/test_docs_consistency.py --write
"""

import json
import re
import sys
from pathlib import Path

import jsonschema
import pytest

from cognitive_fabric.agents.memory_optimizer.context_builder import STRATEGY_CONFIGS
from cognitive_fabric.cli.main import cli as cli_group
from cognitive_fabric.config import Settings
from cognitive_fabric.mcp.tool_registry import ToolRegistry

ROOT = Path(__file__).resolve().parents[2]
DOCS_DIR = ROOT / "docs"
PAGES = sorted(DOCS_DIR.rglob("*.md")) + [ROOT / "README.md"]

# Files that ship with the repo and name environment variables to a reader who
# will set them. The phantom this module was written for -- a log-format name
# nothing reads -- was set in the Dockerfile and in two compose services, and
# named on no page at all, so a scan of `docs/` alone would not have seen it.
ENV_SOURCES = PAGES + [
    ROOT / "Dockerfile",
    ROOT / "docker-compose.yml",
    ROOT / ".env.example",
]

ENV_PREFIX = "COGNITIVE_FABRIC_"

# Variables this package reads that do *not* carry the settings prefix. They are
# the provider SDKs' own names, read by the SDK rather than by `Settings`, and
# the docs are right to name them. Listed here so that a *new* unprefixed name
# is noticed rather than assumed to be one of these.
NON_SETTINGS_ENV = {
    "OPENAI_API_KEY",
    "ANTHROPIC_API_KEY",
}

FENCE = re.compile(r"^```([^\n]*)\n(.*?)^```", re.MULTILINE | re.DOTALL)

STRATEGY_TABLE_BEGIN = "<!-- BEGIN GENERATED: strategy table -->"
STRATEGY_TABLE_END = "<!-- END GENERATED: strategy table -->"


def render_strategy_table() -> str:
    """The strategy table, derived from the presets the optimizers read.

    `stale_days_threshold` is carried in the configs and not read by every
    path, so the column is labelled for what it is. The default is named in the
    table because a reader deciding whether to run `optimize` needs it more
    than any single row.
    """
    rows = [
        "| Strategy | Stale threshold (days) | Max deletions | Deletes orphaned tags | "
        "Requires no dependents |",
        "|----------|------------------------|---------------|-----------------------|"
        "-----------------------|",
    ]
    for name in ("conservative", "balanced", "aggressive"):
        config = STRATEGY_CONFIGS[name]
        marks = {
            True: "yes",
            False: "no",
        }
        rows.append(
            f"| {name} | {config['stale_days_threshold']} | "
            f"{config['max_deletions']} | "
            f"{marks[bool(config['delete_orphaned_tags'])]} | "
            f"{marks[bool(config['require_no_dependents'])]} |"
        )
    rows.append("")
    rows.append(
        "The strategy that applies when none is requested is "
        "`COGNITIVE_FABRIC_OPTIMIZER_DEFAULT_STRATEGY`, which is "
        "`conservative`. A name that is none of these three is refused, not "
        "resolved to one of them."
    )
    return "\n".join(rows)


def _pages_with(needle: str) -> list[str]:
    return [str(p.relative_to(ROOT)) for p in PAGES if needle in p.read_text()]


# --------------------------------------------------------------------------
# 1. Environment variables
# --------------------------------------------------------------------------


def _settings_env_vars() -> set[str]:
    return {ENV_PREFIX + name.upper() for name in Settings.model_fields}


# A variable name, always with at least one character after the prefix so that
# a prose `COGNITIVE_FABRIC_*` is not read as a setting called `COGNITIVE_FABRIC_`.
ENV_VAR = re.compile(
    r"\b(?:COGNITIVE_FABRIC_[A-Z0-9_]+|OPENAI_API_KEY|ANTHROPIC_API_KEY)\b"
)


def _documented_env_vars() -> dict[str, str]:
    """Every environment variable a shipping file names, and which one.

    Scanned over the whole file, not just fenced blocks: a variable is as
    binding in a reference table or an `ENV` line as in an example.
    """
    seen: dict[str, str] = {}
    for source in ENV_SOURCES:
        for name in ENV_VAR.findall(source.read_text()):
            seen.setdefault(name, str(source.relative_to(ROOT)))
    return seen


def test_every_documented_setting_exists() -> None:
    """A variable the docs name must be one the code reads.

    A phantom setting is the worst kind of documentation defect, because the
    reader who follows it believes they have configured something. The log
    format and the optimizer's stale-days threshold were both documented and
    both absent from `Settings`; so was `COGNITIVE_FABRIC_DB_PATH_OVERRIDE`,
    under which name the published image could not start at all.
    """
    known = _settings_env_vars()
    unknown = {
        name: page
        for name, page in _documented_env_vars().items()
        if name.startswith(ENV_PREFIX) and name not in known
    }
    assert not unknown, (
        "These environment variables are documented but are not fields of "
        "Settings, so nothing reads them:\n  "
        + "\n  ".join(
            f"{name} (named in {page})" for name, page in sorted(unknown.items())
        )
    )


def test_the_scan_finds_settings_variables() -> None:
    """Guard against the environment scan silently matching nothing."""
    assert len(_documented_env_vars()) >= 8


# --------------------------------------------------------------------------
# 2. JSON tool calls
# --------------------------------------------------------------------------


def _fenced_blocks(page: Path) -> list[tuple[str, str]]:
    return [(m.group(1).strip(), m.group(2)) for m in FENCE.finditer(page.read_text())]


def _decode_objects(text: str) -> list:
    """Every JSON object in a block, in order.

    A block may hold one call or several, one per line. Both are read; a block
    that holds neither is a parse failure rather than something to skip, because
    a reader copies these.
    """
    decoder = json.JSONDecoder()
    objects = []
    index = 0
    text = text.strip()
    while index < len(text):
        while index < len(text) and text[index] in " \t\r\n":
            index += 1
        if index >= len(text):
            break
        obj, index = decoder.raw_decode(text, index)
        objects.append(obj)
    return objects


# A tool call is not the only object with a `tool` field: the structured log
# record does too ({"event": "Tool called", "tool": "entity", "level": "info"}).
# It is not a request and has no `arguments`, so it would otherwise be read as
# a malformed call. `level` identifies it -- no request carries one, and an
# example that omits `arguments` *without* a `level` is still a failure, so
# this does not open a way for a malformed call to slip through.
_LOG_RECORD_FIELDS = {"level"}


def _tool_calls() -> list[tuple[str, dict]]:
    """Every `{"tool": ..., "arguments": {...}}` example, with its page.

    A block that mentions `"tool"` must parse, and must be in the wire shape.
    Blocks that do not are prose, response bodies and shell transcripts, and are
    left alone -- several of them are elided with `...` on purpose.
    """
    calls = []
    for page in PAGES:
        relative = str(page.relative_to(ROOT))
        for _info, text in _fenced_blocks(page):
            if '"tool"' not in text:
                continue
            try:
                parsed = _decode_objects(text)
            except json.JSONDecodeError as exc:
                pytest.fail(
                    f"{relative}: a tool-call example does not parse as JSON "
                    f"({exc}). Examples are copied by readers, so it has to be "
                    f"something that could be sent.\n{text}"
                )
            for call in parsed:
                assert isinstance(call, dict), f"{relative}: tool call is not an object"
                if _LOG_RECORD_FIELDS <= set(call):
                    continue  # a log record, not a request
                assert set(call) == {"tool", "arguments"}, (
                    f"{relative}: a tool call has keys {sorted(call)}; the wire "
                    "shape is {'tool': name, 'arguments': {...}}. An argument "
                    "written beside 'tool' instead of inside 'arguments' is "
                    "never sent."
                )
                calls.append((relative, call))
    return calls


def test_there_are_tool_call_examples() -> None:
    """Guard against the scan silently matching nothing."""
    assert len(_tool_calls()) >= 15


def test_every_tool_call_example_validates() -> None:
    """Each example must validate against the schema the server advertises.

    The examples are what a reader pastes into a client. An argument the schema
    does not carry is a call that is refused, and a `type` the tool renamed is
    a call that fails on the wire -- neither is visible by reading the page.

    Unknown keys are a failure too. `jsonschema` permits them by default, but
    the handlers read exactly the advertised names, so a `"operation": "cycles"`
    on the `detect` tool -- which reads `type` -- is accepted, ignored, and
    answered with an error about a missing `type`. A key the schema does not
    carry is a key nothing reads.
    """
    registry = ToolRegistry()
    problems: list[str] = []
    for page, call in _tool_calls():
        tool = registry.get_tool(call["tool"])
        if tool is None:
            problems.append(
                f"{page}: example calls tool {call['tool']!r}, which the server "
                "does not advertise"
            )
            continue
        schema = tool.parameters
        try:
            jsonschema.validate(call["arguments"], schema)
        except jsonschema.ValidationError as exc:
            where = "/".join(str(p) for p in exc.absolute_path) or "<root>"
            problems.append(
                f"{page}: {call['tool']} example is invalid at {where}: "
                f"{exc.message}"
            )
        documented = set(schema.get("properties", {}))
        unknown = set(call["arguments"]) - documented
        if unknown:
            problems.append(
                f"{page}: {call['tool']} example passes {sorted(unknown)}, which "
                f"the tool does not accept (it reads "
                f"{', '.join(sorted(documented))})"
            )
    assert not problems, "\n  ".join(["Tool-call examples must validate:"] + problems)


# --------------------------------------------------------------------------
# 3. CLI commands
# --------------------------------------------------------------------------

SHELL_KEYWORDS = {
    "if",
    "then",
    "elif",
    "else",
    "fi",
    "for",
    "do",
    "done",
    "while",
    "export",
    "set",
    "source",
    ".",
}

ASSIGNMENT = re.compile(r"[A-Za-z_][A-Za-z0-9_]*=")


def _console_scripts() -> set[str]:
    import tomllib

    with (ROOT / "pyproject.toml").open("rb") as fh:
        return set(tomllib.load(fh)["project"]["scripts"])


def _near_misses() -> set[str]:
    """Command names the pages use that are *not* the installed script names.

    Listed so the scan sees them and fails on them, rather than skipping a line
    it does not recognise. `cognitive_fabric` was used throughout the docs for
    a console script that is installed as `cognitive-fabric`; the underscore
    form is a module path, not a command, and is not on anyone's PATH.
    """
    return {"cognitive_fabric", "cognitive_fabric-server"}


def _command_argv(line: str) -> list[str] | None:
    """The argv of a line that runs the CLI, or None if it runs something else.

    Handles the shapes the pages use: leading `VAR=value` assignments and shell
    keywords (`if`, `done`), and `docker compose run --rm <service> <command>`.
    A usage synopsis (`cognitive-fabric [OPTIONS] COMMAND [ARGS]...`) is not an
    invocation and is skipped -- its tokens are placeholders, not arguments.
    """
    line = line.split("#", 1)[0].strip()
    if not line:
        return None
    tokens = line.split()
    if any(token.startswith("[") and token.endswith("]") for token in tokens):
        return None
    while tokens and (
        tokens[0] in SHELL_KEYWORDS or ASSIGNMENT.match(tokens[0])
    ):
        tokens.pop(0)
    if tokens[:2] == ["docker", "compose"]:
        # `docker compose run --rm <service> <command...>`: drop the service.
        run = [i for i, t in enumerate(tokens) if t == "run"]
        if not run:
            return None
        rest = [t for t in tokens[run[0] + 1 :] if t not in {"--rm", "-T"}]
        if len(rest) < 2:
            return None
        tokens = rest[1:]
    if not tokens or tokens[0].startswith(("$", "(")):
        return None
    return tokens


def _group_options() -> set[str]:
    """The options on the CLI group itself, not on a subcommand.

    `cognitive-fabric -v serve ...` is a real line: `-v` belongs to the group,
    and a check that only knows the subcommand's options would call it unknown.
    """
    accepted: set[str] = set()
    for param in cli_group.params:
        accepted.update(getattr(param, "opts", []))
        accepted.update(getattr(param, "secondary_opts", []))
    return accepted


def _cli_invocations() -> list[tuple[str, str, list[str]]]:
    """(page, line, argv) for every shell line that invokes a console script."""
    scripts = _console_scripts() | _near_misses()
    found = []
    for page in PAGES:
        relative = str(page.relative_to(ROOT))
        for info, text in _fenced_blocks(page):
            if info not in {"bash", "shell", "console", "sh"}:
                continue
            for line in text.splitlines():
                argv = _command_argv(line)
                if argv and argv[0] in scripts:
                    found.append((relative, line.strip(), argv))
    return found


def test_the_scan_finds_cli_invocations() -> None:
    assert len(_cli_invocations()) >= 15


def test_every_documented_command_exists() -> None:
    """A command line in the docs has to be one the reader can run.

    Checked against the click tree the package registers, not against a list in
    this file, so a renamed command fails here rather than in a stranger's
    terminal.
    """
    scripts = _console_scripts()
    commands = set(cli_group.commands)
    problems: list[str] = []
    for page, line, argv in _cli_invocations():
        if argv[0] not in scripts:
            problems.append(
                f"{page}: `{argv[0]}` is not an installed command "
                f"(installed: {', '.join(sorted(scripts))})\n    {line}"
            )
            continue
        rest = [t for t in argv[1:] if not t.startswith("-")]
        if not rest:
            continue
        sub, *tail = rest
        if sub in commands:
            accepted = _group_options()
            for param in cli_group.commands[sub].params:
                accepted.update(getattr(param, "opts", []))
                accepted.update(getattr(param, "secondary_opts", []))
            for token in argv[1:]:
                if token.startswith("-") and token not in accepted:
                    problems.append(
                        f"{page}: `{sub} {token}` is not an option of `{sub}`\n"
                        f"    {line}"
                    )
        else:
            problems.append(
                f"{page}: `{argv[0]} {sub}` is not a command "
                f"(known: {', '.join(sorted(commands))})\n    {line}"
            )
    assert not problems, "\n  ".join(
        ["Command lines in the docs must work:"] + problems
    )


def test_every_command_is_documented() -> None:
    """And the reference page lists them all, so a new one is not invisible."""
    cli_md = (DOCS_DIR / "api" / "cli.md").read_text()
    undocumented = [
        name for name in sorted(cli_group.commands) if f"### {name}" not in cli_md
    ]
    assert not undocumented, (
        "These CLI commands have no section in docs/api/cli.md:\n  "
        + "\n  ".join(undocumented)
    )


# --------------------------------------------------------------------------
# 4. MCP client configurations
# --------------------------------------------------------------------------

# Programs a client config may launch that are not this package's own console
# scripts. Listed so that an unknown name fails here rather than in a reader's
# editor, where the failure is a server that never appears.
EXTERNAL_COMMANDS = {"docker", "python", "python3", "uv", "uvx", "npx", "node"}


def _walk_commands(obj: object) -> list[str]:
    if isinstance(obj, dict):
        found = [
            value for key, value in obj.items()
            if key == "command" and isinstance(value, str)
        ]
        for value in obj.values():
            found.extend(_walk_commands(value))
        return found
    if isinstance(obj, list):
        found = []
        for value in obj:
            found.extend(_walk_commands(value))
        return found
    return []


def _mcp_commands() -> list[tuple[str, str]]:
    """(page, command) for every `"command"` in a fenced block that parses.

    A block has to be JSON for a client to paste it, so one that does not parse
    is skipped -- the tool-call scan above is the strict one. These blocks carry
    `<placeholder>` values and elisions on purpose.
    """
    found: list[tuple[str, str]] = []
    for page in PAGES:
        relative = str(page.relative_to(ROOT))
        for _info, block in _fenced_blocks(page):
            if '"command"' not in block:
                continue
            try:
                parsed = _decode_objects(block)
            except json.JSONDecodeError:
                continue
            for obj in parsed:
                found.extend((relative, cmd) for cmd in _walk_commands(obj))
    return found


def test_the_scan_finds_mcp_commands() -> None:
    """Guard against the scan silently matching nothing."""
    assert len(_mcp_commands()) >= 4


def test_every_mcp_command_is_runnable() -> None:
    """A client config names a program the reader's shell has to find.

    Some pages give a path (`/absolute/path/to/.../.venv/bin/cognitive-fabric`)
    and others a bare name, so the check is on the basename. The
    getting-started page named `cognitive_fabric-server` -- the module path,
    with an underscore -- and no shell has that.
    """
    scripts = _console_scripts()
    problems = []
    for page, command in _mcp_commands():
        base = command.rsplit("/", 1)[-1]
        if base in scripts or base in EXTERNAL_COMMANDS:
            continue
        problems.append(
            f"{page}: MCP client config runs `{command}`, which is neither an "
            f"installed command ({', '.join(sorted(scripts))}) nor a known "
            f"launcher ({', '.join(sorted(EXTERNAL_COMMANDS))})"
        )
    assert not problems, "\n  ".join(
        ["MCP client configs must run something the reader has:"] + problems
    )


# --------------------------------------------------------------------------
# 4b. The parameter tables on the tool reference page
# --------------------------------------------------------------------------

TOOLS_PAGE = DOCS_DIR / "api" / "tools.md"

TABLE_ROW = re.compile(r"^\|\s*([A-Za-z_][A-Za-z0-9_]*)\s*\|")


def _documented_parameters() -> dict[str, set[str]]:
    """{tool name: parameter names its tables on the reference page use}.

    Read from the `## <tool>` sections of docs/api/tools.md, which is where a
    reader looks up what to send. A tool section is one that lists operations;
    the page also has `## Tool Overview` and `## Error Handling`, which are not
    tools and are not read.
    """
    text = TOOLS_PAGE.read_text()
    sections: dict[str, set[str]] = {}
    parts = re.split(r"^## (.+)$", text, flags=re.MULTILINE)[1:]
    for name, body in zip(parts[0::2], parts[1::2]):
        if "### Operations" not in body:
            continue
        found: set[str] = set()
        for line in body.splitlines():
            match = TABLE_ROW.match(line)
            if match and match.group(1) != "Parameter":
                found.add(match.group(1))
        sections[name.strip()] = found
    return sections


def _table_parameters() -> list[tuple[str, str]]:
    """(tool, parameter) for every parameter named in a table on that page."""
    registry = ToolRegistry()
    found = []
    for name, parameters in _documented_parameters().items():
        tool = registry.get_tool(name)
        if tool is None:
            continue
        advertised = set(tool.parameters.get("properties", {}))
        found.extend((name, p) for p in sorted(parameters - advertised))
    return found


def test_the_scan_finds_parameter_tables() -> None:
    """Guard against the scan silently matching nothing."""
    total = sum(len(v) for v in _documented_parameters().values())
    assert total >= 60, total


def test_every_tool_has_a_section() -> None:
    """Each tool the server advertises is described somewhere on the page.

    The whole `fabric` tool was missing from the reference until this check
    existed, so eight operations had no page at all -- the tool is registered
    and callable, and a reader looking it up found nothing.
    """
    documented = set(_documented_parameters())
    advertised = {t.name for t in ToolRegistry().list_tools()}
    assert advertised - documented == set(), (
        "These tools are advertised by the server and have no section on "
        f"{TOOLS_PAGE.name}: {sorted(advertised - documented)}"
    )
    assert documented - advertised == set(), (
        f"{TOOLS_PAGE.name} has sections for tools that do not exist: "
        f"{sorted(documented - advertised)}"
    )


def test_every_documented_parameter_is_accepted() -> None:
    """A parameter the reference lists must be one the tool's handler reads.

    The handler reads the names in the schema and no others, so a table row
    naming something else is a call that is accepted, ignored, and answered with
    an error about a missing key -- `delete`'s `operation` reads `deleteType`, so
    a reader following the page would not be understood.
    """
    registry = ToolRegistry()
    problems = []
    for tool, parameter in _table_parameters():
        advertised = registry.get_tool(tool).parameters["properties"]
        problems.append(
            f"{tool}: the page documents `{parameter}`, which the tool does not "
            f"accept (it reads {', '.join(sorted(advertised))})"
        )
    assert not problems, "\n  ".join(
        ["Parameter tables must name parameters the tools read:"] + problems
    )


# --------------------------------------------------------------------------
# 5. The defaults the tool schema advertises
# --------------------------------------------------------------------------

# Schema key -> the Settings field the server reads when the caller omits it.
# `definitions.py` derives each of these from the field, so they cannot drift
# today; the table pins which field each one comes from, so a future literal
# substitution is caught rather than silently advertised.
ADVERTISED_DEFAULTS = {
    "strategy": "optimizer_default_strategy",
    "enableMCPSampling": "optimizer_enable_mcp_sampling",
    "samplingStrategy": "optimizer_default_sampling_strategy",
}


def test_the_advertised_defaults_are_the_configured_ones() -> None:
    """The schema's `default` is a promise about what the server does.

    `strategy` advertised `balanced` while the handler resolved
    `optimizer_default_strategy`, which is `conservative`. A client that omitted
    the key and read the schema was told it would get a 50-deletion run and
    would in fact get a 10-deletion one.
    """
    schema = ToolRegistry().get_tool("memory-optimizer").parameters["properties"]
    settings = Settings()
    problems = [
        f"{key}: schema advertises {schema[key].get('default')!r}, "
        f"Settings.{field} is {getattr(settings, field)!r}"
        for key, field in ADVERTISED_DEFAULTS.items()
        if schema[key].get("default") != getattr(settings, field)
    ]
    assert not problems, "\n  ".join(
        ["The tool schema must advertise the defaults the server applies:"] + problems
    )


# --------------------------------------------------------------------------
# The generated strategy table
# --------------------------------------------------------------------------


def _strategy_pages() -> list[Path]:
    return [p for p in PAGES if STRATEGY_TABLE_BEGIN in p.read_text()]


def test_the_strategy_table_is_generated_into_both_pages() -> None:
    pages = _strategy_pages()
    assert len(pages) >= 2, (
        "The strategy table is generated; the pages that state a strategy "
        "number must embed the generated block rather than restate it."
    )


@pytest.mark.parametrize("page", sorted(_strategy_pages()), ids=lambda p: p.name)
def test_the_generated_strategy_table_matches_the_code(page: Path) -> None:
    text = page.read_text()
    start = text.index(STRATEGY_TABLE_BEGIN) + len(STRATEGY_TABLE_BEGIN)
    end = text.index(STRATEGY_TABLE_END)
    embedded = text[start:end].strip()
    assert embedded == render_strategy_table(), (
        f"{page.relative_to(ROOT)}: the strategy table does not match "
        "STRATEGY_CONFIGS. Regenerate it with\n"
        "    python tests/unit/test_docs_consistency.py --write\n"
        "Do not hand-edit the block; it is derived from the code that deletes."
    )


def test_no_strategy_number_is_restated_outside_the_generated_block() -> None:
    """A second copy of the numbers is how the first one went wrong.

    The docs said `balanced` deletes at most 20 for as long as the code deleted
    50. The check is deliberately blunt -- *any* number on a line that names a
    strategy -- because the wrong number is the failure, not the repeated one.
    `docs/api/cli.md` listed "conservative - max 5 deletions", which restated
    nothing and was wrong in the direction that misleads: 5 is neither the real
    10 nor anything the optimizer honours.
    """
    problems = []
    for page in PAGES:
        text = page.read_text()
        text = re.sub(
            re.escape(STRATEGY_TABLE_BEGIN) + ".*?" + re.escape(STRATEGY_TABLE_END),
            "",
            text,
            flags=re.DOTALL,
        )
        for line in text.splitlines():
            # A list marker is not a claim about the optimizer: "2. Execute with
            # balanced" names a strategy and carries a digit, and none of it is
            # a restatement.
            body = re.sub(r"^\s*(?:[-*+]|\d+[.)])\s+", "", line)
            if not any(name in body.lower() for name in STRATEGY_CONFIGS):
                continue
            if re.search(r"\b\d", body):
                problems.append(f"{page.relative_to(ROOT)}: {body.strip()}")
    assert not problems, (
        "These lines put a number beside a strategy name. The numbers live in "
        "STRATEGY_CONFIGS and are embedded as a generated table; a hand-written "
        "one drifts and is believed:\n  " + "\n  ".join(problems)
    )


# --------------------------------------------------------------------------
# Regeneration
# --------------------------------------------------------------------------


def _rewrite() -> int:
    rendered = render_strategy_table()
    changed = 0
    for page in _strategy_pages():
        text = page.read_text()
        start = text.index(STRATEGY_TABLE_BEGIN) + len(STRATEGY_TABLE_BEGIN)
        end = text.index(STRATEGY_TABLE_END)
        if text[start:end].strip() == rendered:
            continue
        page.write_text(
            text[:start] + "\n" + rendered + "\n" + text[end:]
        )
        changed += 1
        print(f"rewrote {page.relative_to(ROOT)}")
    return changed


if __name__ == "__main__":
    if "--write" not in sys.argv:
        raise SystemExit("usage: test_docs_consistency.py --write")
    raise SystemExit(0 if _rewrite() is not None else 1)
