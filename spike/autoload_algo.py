"""Evidence harness for the Ladybug spike: load ALGO on every Connection.

This is the pytest plugin that produced the "Port + ALGO" rows in
SPIKE-ladybug-report.md (188/191 passed). It is deliberately not part of the
package: a real port must decide how the extension is provisioned and where
the LOAD belongs (connection_manager.Connect, not a monkeypatch).

Reproduce with:

    HOME=<home-with-algo-installed> \
    PYTHONPATH=spike \
    python -m pytest tests/unit/ tests/integration/ tests/e2e/ \
        -v --tb=short -rs -p autoload_algo

`INSTALL ALGO` must have run once beforehand (it needs network); after that
`LOAD EXTENSION ALGO` is offline. Failures are printed rather than swallowed
silently, so a missing extension is visible instead of producing a false red
that looks like a Cypher failure.
"""

import sys

import ladybug

_orig_init = ladybug.Connection.__init__


def _init(self, *args, **kwargs):
    _orig_init(self, *args, **kwargs)
    try:
        self.execute("LOAD EXTENSION ALGO")
    except Exception as exc:  # noqa: BLE001 - evidence harness, not package code
        print(f"autoload_algo: LOAD EXTENSION ALGO failed: {exc}", file=sys.stderr)


ladybug.Connection.__init__ = _init
