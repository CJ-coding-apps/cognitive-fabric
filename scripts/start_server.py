#!/usr/bin/env python3
"""Script to start the Cognitive Fabric MCP server (stdio transport)."""

import sys
from pathlib import Path

# Add src to path for development
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from cognitive_fabric.main import main

if __name__ == "__main__":
    main()
