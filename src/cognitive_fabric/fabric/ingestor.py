"""Symbolic (AST) ingestion via tree-sitter.

Ported in-process from the former Arrow Flight sidecar (the Arrow serialization
helpers were dropped; symbols/files are consumed directly by DataFabricService).

tree-sitter is imported lazily so the rest of the package works without it.
"""

import hashlib
import os
from typing import Any


class SymbolicIngestor:
    """Scans a project with tree-sitter and extracts symbols + file metadata."""

    LANGUAGES = {
        ".ts": "typescript",
        ".tsx": "tsx",
        ".js": "javascript",
        ".py": "python",
    }

    # AST node types treated as "symbols" across the supported languages.
    _SYMBOL_NODE_TYPES = {
        "function_declaration",
        "class_declaration",
        "method_definition",
        "function_definition",
        "class_definition",
    }

    def __init__(self) -> None:
        self._parsers: dict[str, Any] = {}

    def get_parser(self, lang_name: str) -> Any:
        """Return a cached tree-sitter parser for the language."""
        if lang_name not in self._parsers:
            self._parsers[lang_name] = self._load_parser(lang_name)
        return self._parsers[lang_name]

    @staticmethod
    def _load_parser(lang_name: str) -> Any:
        """Load a tree-sitter parser (lazy, optional dependency).

        Prefers the maintained, Python 3.13-compatible `tree-sitter-language-pack`
        and falls back to the older `tree-sitter-languages` if that is what is
        installed. Both expose `get_parser(lang) -> Parser`.
        """
        try:
            from tree_sitter_language_pack import get_parser

            return get_parser(lang_name)
        except ImportError:
            from tree_sitter_languages import get_parser

            return get_parser(lang_name)

    def scan_project(
        self, root_path: str
    ) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
        """Walk a project directory and return (symbols, files).

        Skips hidden directories and node_modules.
        """
        symbols: list[dict[str, Any]] = []
        files: list[dict[str, Any]] = []

        for root, _, filenames in os.walk(root_path):
            parts = root.split(os.sep)
            if any(p.startswith(".") or p == "node_modules" for p in parts):
                continue

            for filename in filenames:
                ext = os.path.splitext(filename)[1]
                lang = self.LANGUAGES.get(ext)
                if not lang:
                    continue
                file_path = os.path.join(root, filename)
                rel_path = os.path.relpath(file_path, root_path)
                file_symbols, file_meta = self.parse_file(file_path, rel_path, lang)
                symbols.extend(file_symbols)
                files.append(file_meta)

        return symbols, files

    def parse_file(
        self, file_path: str, rel_path: str, language: str
    ) -> tuple[list[dict[str, Any]], dict[str, Any]]:
        """Parse a single file into (symbols, file_meta)."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        parser = self.get_parser(language)
        tree = parser.parse(bytes(content, "utf8"))

        file_meta = {
            "id": rel_path,
            "name": os.path.basename(file_path),
            "path": rel_path,
            "language": language,
            "hash": hashlib.sha256(content.encode()).hexdigest(),
        }

        symbols: list[dict[str, Any]] = []

        def traverse(node: Any) -> None:
            if node.type in self._SYMBOL_NODE_TYPES:
                name = "unknown"
                for child in node.children:
                    if child.type in ("identifier", "property_identifier"):
                        name = content[child.start_byte:child.end_byte]
                        break
                signature = content[node.start_byte:node.end_byte].split("{")[0].strip()
                symbols.append({
                    "id": f"{rel_path}:{name}",
                    "name": name,
                    "kind": node.type,
                    "signature": signature,
                    "file_id": rel_path,
                })
            for child in node.children:
                traverse(child)

        traverse(tree.root_node)
        return symbols, file_meta
