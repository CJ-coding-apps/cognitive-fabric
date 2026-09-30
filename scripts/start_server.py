#!/usr/bin/env python3
"""Script to start the KuzuMemPy MCP server."""

import asyncio
import sys
from pathlib import Path

# Add src to path for development
src_path = Path(__file__).parent.parent / "src"
sys.path.insert(0, str(src_path))

from kuzumempy.main import main

if __name__ == "__main__":
    main()
