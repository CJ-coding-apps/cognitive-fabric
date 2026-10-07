"""The logging settings the configuration guide documents do something.

`configure_logging` accepted a `log_level` argument and never used it, and
`Settings.log_level` / `Settings.log_json` were read by nothing at all. So the
configuration guide's table of levels, its two worked output examples, the
Dockerfile's `COGNITIVE_FABRIC_LOG_JSON=true`, and the
`COGNITIVE_FABRIC_LOG_LEVEL=DEBUG cognitive-fabric serve` line in the
development guide all described a process that logged some other way.

The assertions below are written against the output measured from the
configured logger, not against the guide, so a change to either one has to be
made in both.
"""

import contextlib
import io
import json
import re
from pathlib import Path

import pytest
import structlog
from click.testing import CliRunner

from cognitive_fabric.cli import main as cli_main
from cognitive_fabric.utils.logger import configure_logging

ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(autouse=True)
def _restore_logging():
    """structlog's configuration is global; leave it as the module found it."""
    yield
    configure_logging()


def _emit(level: str, **fields) -> str:
    """Configure at `level`, log one INFO record, return the raw output.

    `PrintLoggerFactory` binds stderr at configure time, so both the
    configuration and the emit happen inside the redirect.
    """
    stream = io.StringIO()
    with contextlib.redirect_stderr(stream):
        configure_logging(json_output=True, log_level=level)
        structlog.get_logger("cognitive_fabric.mcp.server").info(
            "Tool called", tool="entity", **fields
        )
    return stream.getvalue()


def test_a_record_at_the_configured_level_is_emitted():
    record = json.loads(_emit("INFO"))
    # The key is `event`, and this is where the guide's example gets it from.
    assert record["event"] == "Tool called"
    assert record["tool"] == "entity"
    assert record["level"] == "info"


def test_a_record_below_the_configured_level_is_dropped():
    """The level argument decides. It used to be accepted and then ignored."""
    assert _emit("WARNING") == ""


@pytest.mark.parametrize(
    ("env", "flag", "expected"),
    [
        ("false", [], False),
        ("true", ["--no-json-logs"], False),
        ("false", ["--json-logs"], True),
    ],
)
def test_the_serve_flags_win_over_the_environment(
    monkeypatch, env, flag, expected
):
    """`serve` resolves format as flag > environment > nothing.

    Neither option could express "not given" before -- `--log-level` defaulted
    to the literal `"INFO"` and `--json-logs` was a flag -- so
    `COGNITIVE_FABRIC_LOG_JSON` never reached the server.
    """
    import cognitive_fabric.mcp.server as server_module

    seen: dict[str, object] = {}

    async def fake_run_server(**_kwargs):
        return None

    monkeypatch.setattr(server_module, "run_server", fake_run_server)
    monkeypatch.setattr(cli_main, "configure_logging", lambda **kw: seen.update(kw))
    monkeypatch.setenv("COGNITIVE_FABRIC_LOG_JSON", env)

    result = CliRunner().invoke(cli_main.cli, ["serve", *flag])
    assert result.exit_code == 0, result.output
    assert seen["json_output"] is expected


def test_the_documented_json_record_is_what_the_logger_emits():
    """The guide's example is measured, not remembered.

    It showed `"message"` and a `"logger"` field. The logger emits `"event"`
    and has no logger name, so a reader configuring a parser from that example
    would key on two fields that are never written.
    """
    page = (ROOT / "docs" / "guides" / "configuration.md").read_text()
    block = re.search(
        r"`COGNITIVE_FABRIC_LOG_JSON=true`.*?```json\n(.*?)```", page, re.S
    )
    assert block, "the JSON log format example is gone from the configuration guide"
    documented = json.loads(block.group(1))
    measured = json.loads(_emit("INFO", operation="create"))

    assert set(documented) == set(measured), (
        f"the guide documents the keys {sorted(documented)}; the logger writes "
        f"{sorted(measured)}"
    )
    for key, value in documented.items():
        if key != "timestamp":
            assert measured[key] == value, f"{key}: {value!r} vs {measured[key]!r}"
