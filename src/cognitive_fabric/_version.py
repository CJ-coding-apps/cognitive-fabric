"""The version number, from one place.

`importlib.metadata` reads the installed distribution's metadata, which is built
from `pyproject.toml` at install time. That makes this the single source for
`__version__`, `--version` and the MCP handshake, so they cannot disagree.
"""

from importlib.metadata import PackageNotFoundError, version

# Must match `[project] name` in pyproject.toml. The test suite asserts that.
DISTRIBUTION_NAME = "cognitive-fabric"

# Only reachable when running from a source tree that was never installed --
# the server handshake would otherwise advertise a value that is not a version.
_UNKNOWN = "0.0.0.dev0"

try:
    __version__ = version(DISTRIBUTION_NAME)
except PackageNotFoundError:  # pragma: no cover -- source tree, never installed
    __version__ = _UNKNOWN
