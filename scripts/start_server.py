#!/usr/bin/env python3
"""Script to start the Cognitive Fabric MCP server (stdio transport).

Runs the server from a source checkout that has not been installed, which is
why the import below does not sit at the top of the file: the `sys.path` insert
has to happen before `cognitive_fabric` is importable.

The README points an MCP client at the installed console script
(`.venv/bin/cognitive-fabric-server`) instead, and nothing else in the
repository refers to this file.
"""

import sys
from pathlib import Path

# Add src to path for development
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from cognitive_fabric.main import main  # noqa: E402 -- the insert above must run first

if __name__ == "__main__":
    main()
